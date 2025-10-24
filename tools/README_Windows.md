# Windows Compatibility Guide

The complete site generation is available in multiple formats for Windows compatibility:

## 🚀 **Option 1: PowerShell Script (Recommended)**

**For Windows 10/11 with PowerShell 5.0+:**

```powershell
# Generate site
.\tools\generate_complete_site.ps1

# Generate and serve
.\tools\generate_complete_site.ps1 -Serve
```

**Features:**
- ✅ Native Windows PowerShell support
- ✅ Colored output and error handling
- ✅ Automatic conda environment activation
- ✅ Full feature parity with bash version

---

## 🚀 **Option 2: Batch File**

**For older Windows systems or simple usage:**

```cmd
# Generate site
tools\generate_complete_site.cmd

# Generate and serve
tools\generate_complete_site.cmd serve
```

**Features:**
- ✅ Works on all Windows versions
- ✅ No PowerShell required
- ✅ Simple command-line interface

---

## 🚀 **Option 3: Bash Script via Git Bash/WSL**

**If you have Git Bash, WSL, or Cygwin:**

```bash
# Generate site
./tools/generate_complete_site.sh

# Generate and serve
./tools/generate_complete_site.sh --serve
```

**Prerequisites:**
- Git Bash (comes with Git for Windows)
- WSL (Windows Subsystem for Linux)
- Cygwin

---

## 🛠 **Setup Requirements (All Options)**

1. **Conda Environment:**
   ```cmd
   conda activate hazelbean_env
   ```

2. **Python Dependencies:**
   - All required packages should be installed in your `hazelbean_env`
   - pytest, mkdocs, coverage, etc.

3. **MkDocs:**
   - Ensure mkdocs is available in your environment
   - Test with: `mkdocs --version`

---

## 🌐 **After Generation**

All scripts will generate the same output:

**Generated Files:**
- `docs-site/docs/reports/test-results.md`
- `docs-site/docs/reports/coverage-report.md`
- `docs-site/docs/reports/performance-baselines.md`
- `docs-site/docs/reports/benchmark-results.md`
- `docs-site/docs/reports/index.md` (no "Coming Soon" text)

**View Site:**
- http://127.0.0.1:8005/hazelbean_dev/reports/ (when serving)

---

## 🐛 **Troubleshooting**

### **Conda Environment Issues:**
```cmd
# Manual activation if automatic fails
conda activate hazelbean_env
```

### **PowerShell Execution Policy:**
```powershell
# If PowerShell script won't run
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### **Path Issues:**
- Always run from project root directory
- Use absolute paths if relative paths fail

### **MkDocs Not Found:**
```cmd
# Install in conda environment
conda activate hazelbean_env
conda install -c conda-forge mkdocs-material
```

---

## ✨ **Recommendation**

**For most Windows users:** Use the PowerShell script (`.ps1`) as it provides the best experience with full error handling and colored output.
