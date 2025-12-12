# Release Checklist Template

**Copy this checklist for each release**

---

## Release Version: ________

**Date Started:** ________  
**Target Release Date:** ________  
**Release Manager:** ________

---

## Phase 1: Pre-Release Preparation

### Code Quality
- [ ] All tests passing locally
  ```bash
  conda activate hazelbean_env
  pytest hazelbean_tests/
  ```
- [ ] No critical linter errors
  ```bash
  flake8 hazelbean --select=E9,F63,F7,F82
  ```
- [ ] Cython extensions compile cleanly
  ```bash
  python setup.py build_ext --inplace
  ```
- [ ] Documentation is up to date
- [ ] Examples run successfully

### Version Planning
- [ ] Version number decided: `v________`
  - Bug fix: increment patch (1.7.6 → 1.7.7)
  - New feature: increment minor (1.7.7 → 1.8.0)
  - Breaking change: increment major (1.7.7 → 2.0.0)
- [ ] Version follows semantic versioning

### Release Notes
- [ ] Changelog drafted with:
  - [ ] New features
  - [ ] Bug fixes
  - [ ] Breaking changes (if any)
  - [ ] Deprecations (if any)
  - [ ] Contributors acknowledged
- [ ] Migration guide written (if breaking changes)

### Dependencies
- [ ] All dependencies up to date
- [ ] No known security vulnerabilities
- [ ] Minimum versions tested
- [ ] environment.yml reflects current requirements

---

## Phase 2: GitHub Release (PyPI)

### Create Git Tag
- [ ] On correct branch (usually `main`)
- [ ] Local branch up to date with remote
  ```bash
  git checkout main
  git pull origin main
  ```
- [ ] Tag created:
  ```bash
  VERSION="1.X.Y"
  git tag -a "v${VERSION}" -m "Release version ${VERSION}"
  ```
- [ ] Tag pushed:
  ```bash
  git push origin "v${VERSION}"
  ```
- [ ] Tag visible on GitHub: https://github.com/jandrewjohnson/hazelbean_dev/tags

### Create GitHub Release
- [ ] Navigated to: https://github.com/jandrewjohnson/hazelbean_dev/releases/new
- [ ] Tag selected: `v________`
- [ ] Release title: `Hazelbean v________`
- [ ] Release notes pasted from preparation
- [ ] Pre-release checkbox (if applicable): ☐
- [ ] "Publish release" clicked
- [ ] Release visible: https://github.com/jandrewjohnson/hazelbean_dev/releases

### Monitor GitHub Actions
- [ ] build-python.yml workflow started
  - Link: https://github.com/jandrewjohnson/hazelbean_dev/actions
- [ ] check-syntax-errors job: ☐ Pass ☐ Fail
- [ ] build-wheels job (Ubuntu): ☐ Pass ☐ Fail
- [ ] build-wheels job (Windows): ☐ Pass ☐ Fail  
- [ ] build-wheels job (macOS): ☐ Pass ☐ Fail
- [ ] build-sdist job: ☐ Pass ☐ Fail
- [ ] Upload to PyPI: ☐ Success ☐ Failed
- [ ] changelog.yml workflow: ☐ Success ☐ Failed

**If any failures, record here:**
```
Job: _______________
Error: _______________
Resolution: _______________
```

### Verify PyPI Upload
- [ ] Package visible on PyPI: https://pypi.org/project/hazelbean/
- [ ] Correct version number showing: `________`
- [ ] All wheels uploaded:
  - [ ] Linux wheels (3.10, 3.11, 3.12, 3.13)
  - [ ] Windows wheels (3.10, 3.11, 3.12, 3.13)
  - [ ] macOS wheels (3.10, 3.11, 3.12, 3.13)
  - [ ] Source distribution (.tar.gz)
- [ ] Test installation:
  ```bash
  pip install hazelbean==1.X.Y
  python -c "import hazelbean as hb; print(hb.__version__)"
  ```
- [ ] Installation works: ☐ Yes ☐ No

**Time PyPI became available:** ________ (should be ~20 min after release)

---

## Phase 3: conda-forge Release

### Wait for Bot PR
- [ ] Waited 24 hours after PyPI upload
- [ ] Bot PR created on feedstock
  - Link: https://github.com/conda-forge/hazelbean-feedstock/pulls
  - PR number: #________
- [ ] GitHub notification received

**If no PR after 48 hours:**
- [ ] Verified package on PyPI is public
- [ ] Checked conda-forge status: https://conda-forge.org/status
- [ ] Consider manual PR (see troubleshooting guide)

### Review Bot PR

#### Automated Changes
- [ ] Version number correct: `________`
- [ ] Source URL correct:
  ```
  https://pypi.io/packages/source/h/hazelbean/hazelbean-______.tar.gz
  ```
- [ ] SHA256 hash looks valid (64 hex characters)

#### Dependencies Check
Compare `recipe/meta.yaml` requirements to `environment.yml`:

- [ ] All new dependencies added
- [ ] Removed dependencies deleted
- [ ] Version constraints match
- [ ] Build requirements (Cython, numpy) correct

**Dependencies that need updating:**
```
Package: _______________
Current: _______________
Should be: _______________
```

#### Patches Check
- [ ] Review existing patches in `recipe/patches/`
- [ ] Remove obsolete patches
- [ ] Current known patches:
  - [ ] `1.7.6-utils-fstring-patch.diff` - Remove after 1.7.7+ released

**Patches modified:**
```
Added: _______________
Removed: _______________
Modified: _______________
```

### CI Build Monitoring
Wait for all CI checks to complete:

- [ ] Linux builds: ☐ Pass ☐ Fail
- [ ] macOS builds: ☐ Pass ☐ Fail
- [ ] Windows builds: ☐ Pass ☐ Fail
- [ ] Recipe linting: ☐ Pass ☐ Fail

**If any failures:**
```
Platform: _______________
Error: _______________
Fix needed: _______________
```

### Merge PR
- [ ] All checks green
- [ ] Approved by at least one maintainer
- [ ] "Merge pull request" clicked
- [ ] PR merged successfully
- [ ] Merge time: ________

### Monitor conda-forge Build
After merging, track the final build:

- [ ] Azure Pipelines triggered
- [ ] Build logs viewed: https://dev.azure.com/conda-forge/feedstock-builds/_build
- [ ] Packages built successfully:
  - [ ] linux-64
  - [ ] osx-64
  - [ ] osx-arm64
  - [ ] win-64
- [ ] Packages uploaded to anaconda.org

**Time conda-forge became available:** ________ (should be ~1-2 hours after merge)

### Verify conda-forge Upload
- [ ] Package visible: https://anaconda.org/conda-forge/hazelbean
- [ ] Correct version showing: `________`
- [ ] All platforms available
- [ ] Test installation:
  ```bash
  mamba create -n test-hazelbean python=3.11
  mamba activate test-hazelbean
  mamba install -c conda-forge hazelbean==1.X.Y
  python -c "import hazelbean as hb; print(hb.__version__)"
  ```
- [ ] Installation works: ☐ Yes ☐ No

---

## Phase 4: Post-Release

### Documentation
- [ ] CHANGELOG.md updated (auto-updated by workflow)
- [ ] Release announcement drafted
- [ ] Documentation site updated (if needed)
- [ ] Migration guide published (if breaking changes)

### Communication
- [ ] Announcement posted to:
  - [ ] Project mailing list
  - [ ] Relevant Slack/Discord channels
  - [ ] Social media (if applicable)
  - [ ] Project website news
- [ ] Major users notified directly (if breaking changes)

### Project Management
- [ ] GitHub milestone closed
- [ ] Related issues closed with "Fixed in vX.Y.Z"
- [ ] Project board updated
- [ ] Next version milestone created

### Verification
After 24-48 hours:
- [ ] No critical bug reports
- [ ] Installation working for users
- [ ] Downloads tracking normally
  - PyPI: https://pepy.tech/project/hazelbean
  - conda-forge: https://anaconda.org/conda-forge/hazelbean

### Rollback Plan (If Needed)
**Only if critical issues discovered:**
- [ ] Issues documented: _______________
- [ ] Severity assessed: ☐ Hotfix needed ☐ Can wait
- [ ] Hotfix version planned: `________`
- [ ] Users notified of issue

---

## Metrics

**Release Statistics:**
- Total time from tag to PyPI: ________ minutes
- Total time from tag to conda-forge: ________ hours/days
- Manual effort required: ________ minutes
- Issues encountered: ________ 
- Platforms tested: ________

**Downloads (check after 1 week):**
- PyPI downloads: ________
- conda-forge downloads: ________

---

## Retrospective

**What went well:**
```


```

**What could be improved:**
```


```

**Action items for next release:**
```


```

---

## Sign-off

Release completed by: ________________  
Date: ________________  
Status: ☐ Success ☐ Success with issues ☐ Partial ☐ Failed

**Notes:**
```




```

---

**Template version:** 1.0  
**Last updated:** 2025-10-31



