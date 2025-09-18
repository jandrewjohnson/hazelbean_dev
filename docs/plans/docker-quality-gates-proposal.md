# Docker-Based Quality Gates Environment Proposal

## Title
Cross-Platform Docker Quality Gates for Consistent Testing

## Summary
- **Goal:** Create identical testing environments across Windows, macOS, Linux for both local development and CI/CD
- **Scope:** Containerize all quality gate tests (unit, integration, performance, system) with consistent performance characteristics
- **Assumptions/Constraints:** Must maintain existing workflow speed, support all geospatial dependencies, integrate with GitHub Actions
- **Current Problem:** Different platforms produce different test results, especially performance benchmarks, making quality gates unreliable

## Current State (What Exists)

### Relevant files/modules:
- `.github/workflows/testing-quality-gates.yml` — 4-tier quality gate system
- `.github/workflows/advanced-ci-validation.yml` — Multi-platform CI testing  
- `.github/workflows/basic-ci-validation.yml` — Lightweight validation
- `environment.yml` — 44 complex geospatial dependencies (GDAL, geopandas, etc.)
- `hazelbean_tests/` — 50+ tests across 4 categories
- `scripts/run_performance_benchmarks.py` — Sophisticated performance regression system

### Current Local Testing Workflow:
```bash
# Every developer/CI must run:
conda activate hazelbean_env  # Required 43+ times in documentation
python -m pytest hazelbean_tests/unit/ -v
python scripts/run_performance_benchmarks.py --check-regression --threshold 10.0
```

### Platform-Specific Issues Identified:
- **Performance inconsistency:** Different CPU/memory specs produce different benchmark baselines
- **OS path differences:** Windows vs Unix path handling in tests
- **Dependency versions:** Conda/mamba resolve differently on different platforms
- **Resource constraints:** GitHub runners vary between runs (`ubuntu-latest` changes)
- **Environment setup:** Complex geospatial stack (GDAL, PROJ, GEOS) behaves differently per platform

### Reusable utilities/patterns:
- **Existing conda environment:** `environment.yml` with locked dependencies
- **Quality gate scripts:** Performance benchmarking, test organization
- **CI workflow patterns:** 4-tier quality gate system already established
- **Test categorization:** Unit/Integration/Performance/System structure

### Gaps:
- **No containerization:** All testing depends on host environment setup
- **No performance consistency:** Benchmarks vary significantly between machines
- **No cross-platform validation:** Tests may pass on one OS, fail on another
- **Complex local setup:** 44 geospatial dependencies difficult to install consistently

## Options

### 1) **Docker Quality Gates (Preferred)**
**Steps:**
1. Create multi-stage Dockerfile with geospatial dependencies
2. Build platform-agnostic container with locked versions
3. Create local wrapper scripts for seamless `docker run` integration
4. Update GitHub Actions to use containers
5. Provide fallback to native environment for development

**Pros:**
- ✅ **Identical environments:** Same container everywhere (Windows/Mac/Linux/CI)
- ✅ **Performance consistency:** Locked CPU/memory resources for benchmarking
- ✅ **Dependency isolation:** No more complex conda environment conflicts
- ✅ **CI reliability:** Consistent GitHub Actions runners
- ✅ **Developer experience:** One `docker build`, works everywhere

**Cons:**
- ⚠️ **Initial complexity:** Docker learning curve for team
- ⚠️ **Performance overhead:** Container virtualization adds ~5-10% overhead
- ⚠️ **Geospatial complexity:** GDAL/PROJ/GEOS challenging to containerize properly
- ⚠️ **File mounting:** Local data/results need volume mounting

### 2) **Enhanced Conda Lock Files**
**Steps:**
1. Generate fully locked conda environment files per platform
2. Use conda-lock to create platform-specific lock files
3. Enhanced CI matrix testing across all platforms
4. Local environment validation scripts

**Pros:**
- ✅ **Less disruptive:** Builds on existing conda workflow
- ✅ **No virtualization overhead:** Native performance
- ✅ **Familiar tooling:** Team already knows conda

**Cons:**
- ❌ **Still platform-dependent:** Can't solve fundamental OS differences
- ❌ **No performance consistency:** Still varies between machines
- ❌ **Dependency conflicts:** Complex geospatial stack still problematic

### 3) **Hybrid: Docker for CI, Conda for Local**
**Steps:**
1. Docker containers for all GitHub Actions
2. Enhanced local conda environment with validation
3. Cross-validation between both approaches
4. Gradual migration path

**Pros:**
- ✅ **Best of both worlds:** CI consistency + local flexibility
- ✅ **Gradual adoption:** Team can transition slowly
- ✅ **Risk mitigation:** Fallback to conda if Docker issues

**Cons:**
- ⚠️ **Maintenance overhead:** Two environments to maintain
- ⚠️ **Potential drift:** Docker and conda may diverge over time

## Recommended Approach

### **Option 1: Docker Quality Gates (Preferred)**

**Why this option:** Solves the fundamental cross-platform consistency problem while providing the most reliable foundation for performance benchmarking quality gates.

**Estimated Impact:** 
- **Modules touched:** All GitHub Actions workflows, local development scripts
- **Risk level:** Medium (geospatial dependencies complex, but manageable)
- **Performance impact:** ~5-10% overhead acceptable for consistency gains

## Core Proof Tests (3 only)

**Intent:** Minimal checks that prove Docker environment provides identical results across platforms.

### Test 1 (Cross-Platform Consistency)
**Trigger:** Same test suite run on Windows, macOS, Linux using Docker containers
**Expected Observable:** Identical test results (pass/fail) across all platforms

### Test 2 (Performance Benchmark Consistency) 
**Trigger:** Performance regression test run on different machines using same Docker image
**Expected Observable:** <5% variance in benchmark results (vs current ~50%+ variance)

### Test 3 (CI/Local Parity)
**Trigger:** Quality gates run locally in Docker vs GitHub Actions Docker
**Expected Observable:** Identical results between local Docker and CI Docker runs

**How to run locally:**
```bash
# Build the environment
docker build -f Dockerfile.quality-gates -t hazelbean/quality-gates:latest .

# Run quality gates locally (matches CI exactly)
docker run -v $(pwd):/workspace hazelbean/quality-gates:latest quality-gates-all

# Run specific test categories  
docker run -v $(pwd):/workspace hazelbean/quality-gates:latest pytest hazelbean_tests/performance/ -v
```

## Implementation Plan

### Phase 1: Core Docker Environment (Week 1)
1. **Multi-stage Dockerfile** with optimized geospatial dependency installation
2. **Local wrapper scripts** for seamless Docker integration (`./docker/run-tests.sh`)
3. **Basic quality gate integration** (unit + integration tests)
4. **Local validation** on Windows/Mac/Linux

### Phase 2: Performance & CI Integration (Week 2)  
5. **Performance benchmark consistency** with resource constraints
6. **GitHub Actions integration** for all workflows
7. **Performance regression validation** (Docker vs native comparison)
8. **Documentation updates** for new workflow

### Phase 3: Production Rollout (Week 3)
9. **Team training** on Docker workflow
10. **Gradual migration** from conda to Docker for quality gates
11. **Monitoring & optimization** of container performance
12. **Fallback procedures** if issues arise

## Technical Architecture

### Docker Environment Structure:
```dockerfile
# Base: Official mambaforge with consistent platform
FROM continuumio/mambaforge:latest

# Locked geospatial dependencies from environment.yml
RUN mamba env create -f environment.yml

# Performance consistency settings
ENV OMP_NUM_THREADS=2
ENV GDAL_NUM_THREADS=1
ENV PYTHONHASHSEED=42

# Resource constraints for consistent benchmarking
HEALTHCHECK --interval=30s --timeout=10s CMD python -c "import hazelbean; print('OK')"
```

### Local Integration Scripts:
```bash
# ./docker/quality-gates.sh - Single command for all quality gates
#!/bin/bash
docker run --rm -v $(pwd):/workspace \
  --memory=4g --cpus=2.0 \
  hazelbean/quality-gates:latest \
  quality-gates-all

# ./docker/run-performance.sh - Performance benchmarks only  
docker run --rm -v $(pwd):/workspace \
  hazelbean/quality-gates:latest \
  python scripts/run_performance_benchmarks.py --check-regression --threshold 10.0
```

### GitHub Actions Integration:
```yaml
quality-gates-docker:
  runs-on: ubuntu-22.04
  container:
    image: hazelbean/quality-gates:latest
    options: --memory=4g --cpus=2.0
  steps:
    - uses: actions/checkout@v4
    - run: quality-gates-all
```

## Risks, Pushback, Alternatives

### Risks:
1. **Geospatial complexity:** GDAL/PROJ/GEOS challenging to containerize consistently
   - *Mitigation:* Use proven base images (continuumio/mambaforge), extensive testing
2. **Team adoption:** Docker learning curve for conda-familiar team
   - *Mitigation:* Wrapper scripts hide complexity, gradual rollout
3. **Performance overhead:** Container virtualization may slow tests
   - *Mitigation:* Accept 5-10% overhead for consistency gains, optimize if needed

### Likely Pushback:
1. **"Why not just fix conda?"** — Platform differences are fundamental, can't be solved at package level
2. **"Docker is overkill"** — Cross-platform consistency requires container isolation
3. **"Too complex"** — Wrapper scripts make it simpler than current 44-dependency conda setup

### Realistic Alternatives:
1. **Status quo + better documentation** — Accepts platform inconsistencies
2. **Self-hosted runners only** — Expensive, doesn't solve local development issues
3. **conda-lock enhanced approach** — Partial solution, still platform-dependent

## Rollback/Migration Strategy

### Migration Path:
1. **Phase 1:** Docker optional, conda remains primary
2. **Phase 2:** Docker default for CI, conda backup for local
3. **Phase 3:** Docker primary, conda deprecated for quality gates

### Rollback Plan:
```bash
# If Docker issues arise:
git checkout HEAD~1 .github/workflows/  # Restore original CI
export USE_CONDA=1  # Environment variable to force conda
```

### Testing Strategy:
- **Parallel execution:** Run both Docker and conda for 2 weeks, compare results
- **Gradual team adoption:** Start with willing early adopters
- **Performance monitoring:** Track test execution times Docker vs conda

## Success Criteria

### Immediate (4 weeks):
- ✅ **Cross-platform parity:** Identical test results Windows/Mac/Linux
- ✅ **Performance consistency:** <5% variance in benchmark results  
- ✅ **CI reliability:** No more "works on my machine" issues
- ✅ **Team adoption:** 80%+ of developers using Docker for quality gates

### Long-term (3 months):
- ✅ **Zero platform-specific test failures**
- ✅ **Reliable performance regression detection** (no false positives from platform differences)
- ✅ **Simplified onboarding** (single `docker build` instead of complex conda setup)
- ✅ **Maintainable CI/CD** (consistent environments, predictable behavior)

## Expected Outcome

After implementation:
- **Developers:** Single command quality gate execution across all platforms
- **CI/CD:** Reliable, consistent test results every run
- **Performance benchmarks:** Accurate regression detection without platform noise
- **Team velocity:** Reduced debugging time from environment-specific issues
- **Code quality:** Higher confidence in quality gate enforcement

**This transforms the current "works on my machine" problem into a truly consistent, reliable quality gate system.** 🐳
