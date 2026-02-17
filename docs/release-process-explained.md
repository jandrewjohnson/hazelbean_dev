# Complete Release Process: PyPI → conda-forge

This document explains the entire automated release pipeline for Hazelbean, from creating a GitHub release to having your package available on both PyPI and conda-forge.

---

## 📋 Quick Summary (TL;DR)

**What you do:**
1. Create a git tag (e.g., `v1.7.7`)
2. Push the tag to GitHub
3. Create a GitHub Release
4. Review and merge the auto-generated conda-forge PR (usually within 24 hours)

**What happens automatically:**
- GitHub Actions builds wheels and uploads to PyPI
- conda-forge bot detects the PyPI release
- conda-forge bot creates a PR to update the conda recipe
- After you merge: conda-forge builds and publishes to Anaconda.org

**Do you need to change anything?** 
- ✅ **No changes needed to your repository!** The automation is already set up.
- ✅ You just need to be a maintainer on the conda-forge feedstock (which you are now).

---

## 🎯 The Complete Pipeline (Detailed)

### Phase 1: GitHub Release → PyPI (Fully Automated)

#### Step 1: Create a Git Tag

```bash
# Decide on your version number
VERSION="1.7.7"

# Create and push the tag
git tag -a "v${VERSION}" -m "Release version ${VERSION}"
git push origin "v${VERSION}"
```

**Why?** Your project uses `setuptools_scm`, which automatically determines the package version from git tags. The tag **IS** your version number.

**Note:** The `v` prefix is conventional (e.g., `v1.7.7`), but `setuptools_scm` strips it to create version `1.7.7`.

#### Step 2: Create a GitHub Release

1. Go to https://github.com/jandrewjohnson/hazelbean_dev/releases
2. Click "Draft a new release"
3. Select your tag from the dropdown
4. Add release notes (what's new, what's fixed)
5. Click **"Publish release"**

#### Step 3: GitHub Actions Takes Over

When you click "Publish release", the `build-python.yml` workflow automatically:

**A) Builds Binary Wheels** (the `build-wheels` job):
- Runs on Ubuntu, Windows, and macOS
- Builds for Python 3.10, 3.11, 3.12, and 3.13
- Compiles your Cython extensions for each platform
- Creates `.whl` files

**B) Builds Source Distribution** (the `build-sdist` job):
- Creates a `.tar.gz` source archive
- Includes all source code and setup files

**C) Uploads to PyPI**:
```yaml
- name: Upload to pypi
  if: github.event_name == 'release'
  run: twine upload --username="__token__" --password=${{secrets.PYPI_APIKEY}} dist/*.tar.gz
```

**D) Attaches Files to GitHub Release**:
- All wheels and source distributions are attached to your GitHub release for direct download

**E) Updates CHANGELOG.md** (the `changelog.yml` workflow):
- Automatically generates changelog from commits
- Commits back to the `main` branch

**Timeline:** Usually completes in 15-30 minutes.

---

### Phase 2: PyPI → conda-forge (Semi-Automated)

#### Step 4: conda-forge Bot Detects New Release

**What happens:**
- The `regro-cf-autotick-bot` monitors PyPI for new releases of packages in conda-forge
- When it detects your new version on PyPI (usually within 1-24 hours), it springs into action

**The bot checks:**
- Your new version number
- The new source tarball URL on PyPI
- The SHA256 hash of the tarball
- Any changes in your dependencies

#### Step 5: Bot Creates Pull Request

**Where:** https://github.com/conda-forge/hazelbean-feedstock

The bot creates a PR that updates `recipe/meta.yaml`:

```yaml
# OLD (example from 1.7.6)
{% set version = "1.7.6" %}

source:
  url: https://pypi.io/packages/source/h/hazelbean/hazelbean-1.7.6.tar.gz
  sha256: abc123def456...

# NEW (what the bot changes to 1.7.7)
{% set version = "1.7.7" %}

source:
  url: https://pypi.io/packages/source/h/hazelbean/hazelbean-1.7.7.tar.gz
  sha256: xyz789uvw012...
```

**Special Note:** Currently, the hazelbean feedstock includes a patch file (`1.7.6-utils-fstring-patch.diff`) that fixes a syntax error. See `CONDA_FORGE_FSTRING_FIX.md` for details. Once you release 1.7.7+ with the fix, you can remove this patch from the feedstock.

#### Step 6: Review the Pull Request

**Your responsibilities as a maintainer:**

1. **Check the PR** - GitHub will notify you
2. **Verify changes:**
   - Version number is correct
   - SHA256 hash matches PyPI (bot calculates this automatically)
   - Dependencies are still correct
3. **Run CI checks:**
   - conda-forge automatically builds on Linux, macOS, Windows
   - Tests run in each environment
   - You can see build logs before merging
4. **Merge when green ✅**

**Common scenarios:**

- ✅ **Everything auto-updates correctly** → Just merge
- ⚠️ **New dependencies added** → You may need to manually add them to `meta.yaml`
- ⚠️ **Build constraints changed** → Update build requirements if needed
- ⚠️ **Patches need updating** → Remove obsolete patches (like the f-string fix)

#### Step 7: conda-forge Builds and Publishes

**After you merge:**
1. conda-forge CI rebuilds your package for all platforms
2. Packages are uploaded to https://anaconda.org/conda-forge/hazelbean
3. Users can now install via: `conda install -c conda-forge hazelbean`

**Timeline:** Build and publish usually completes within 1-2 hours of merging.

---

## 🔧 Technical Details

### How setuptools_scm Works

Your `pyproject.toml` configures automatic versioning:

```toml
[tool.setuptools_scm]
version_scheme = "post-release"
local_scheme = "node-and-date"
```

**What this means:**
- **Git tag `v1.7.7`** → Package version `1.7.7`
- **Commits after tag** → Version becomes `1.7.7.post1.dev0+g1234567` (development version)
- **No manual version editing needed** - it's all automatic!

### GitHub Secrets Required

Your repository needs this secret configured (already set up):

- **`PYPI_APIKEY`**: API token for uploading to PyPI
  - Type: PyPI API token
  - Permissions: Upload packages
  - Set in: Repository Settings → Secrets → Actions

### conda-forge Feedstock Structure

The feedstock repository contains:

```
hazelbean-feedstock/
├── recipe/
│   ├── meta.yaml              # Main recipe file
│   ├── build.sh               # Unix build script
│   ├── bld.bat                # Windows build script
│   └── patches/               # Temporary patches
│       └── 1.7.6-utils-fstring-patch.diff
└── README.md
```

**Key file:** `recipe/meta.yaml` defines:
- Package version and source URL
- Build requirements (Cython, numpy, etc.)
- Runtime requirements (gdal, geopandas, etc.)
- Test commands
- Metadata (license, maintainers, etc.)

---

## 🚀 Release Checklist

Use this checklist for each release:

### Pre-Release
- [ ] All tests passing locally
- [ ] Version number decided
- [ ] CHANGELOG.md updated (or will auto-update)
- [ ] Any breaking changes documented
- [ ] Fix any issues noted in previous conda-forge builds

### GitHub Release
- [ ] Create git tag: `git tag -a v1.X.Y -m "Release 1.X.Y"`
- [ ] Push tag: `git push origin v1.X.Y`
- [ ] Create GitHub release with notes
- [ ] Wait for GitHub Actions to complete (~20 min)
- [ ] Verify wheels uploaded to PyPI
- [ ] Test pip install: `pip install hazelbean==1.X.Y`

### conda-forge Release
- [ ] Wait for bot PR (usually < 24 hours)
- [ ] Review bot's PR on conda-forge/hazelbean-feedstock
- [ ] Check if patches need updating/removing
- [ ] Verify dependencies are correct
- [ ] Wait for CI builds to pass
- [ ] Merge PR
- [ ] Wait for publication (~1-2 hours)
- [ ] Test conda install: `conda install -c conda-forge hazelbean==1.X.Y`

### Post-Release
- [ ] Update documentation if needed
- [ ] Announce on relevant channels
- [ ] Close milestone/issues for this release

---

## 🐛 Troubleshooting

### PyPI Upload Fails

**Symptom:** GitHub Action fails at "Upload to pypi" step

**Common causes:**
1. **Version already exists on PyPI** - You can't re-upload the same version
   - Fix: Increment version and create new tag
2. **PYPI_APIKEY expired or invalid**
   - Fix: Regenerate token on PyPI, update GitHub secret
3. **Package metadata issues**
   - Fix: Check `pyproject.toml` and `setup.py` for errors

### conda-forge Bot Doesn't Create PR

**Symptom:** 48+ hours, no PR on feedstock

**Common causes:**
1. **PyPI release not visible** - Check https://pypi.org/project/hazelbean/
2. **Bot is temporarily down** - Check conda-forge status
3. **Manual trigger needed**

**Manual solution:**
```bash
# Fork conda-forge/hazelbean-feedstock
# Clone your fork
git clone https://github.com/YOUR_USERNAME/hazelbean-feedstock.git
cd hazelbean-feedstock

# Update recipe/meta.yaml
# - Change version number
# - Update source URL
# - Update sha256 hash (get from PyPI)

# Commit and create PR
git checkout -b update-1.7.7
git add recipe/meta.yaml
git commit -m "Update to 1.7.7"
git push origin update-1.7.7
# Create PR on GitHub
```

### conda-forge Build Fails

**Symptom:** CI fails on feedstock PR

**Common causes:**
1. **Missing dependencies** - Add to `meta.yaml` requirements
2. **Cython compilation errors** - Check build constraints
3. **Test failures** - Package tests run during build
4. **Platform-specific issues** - Check each platform's log

**Where to look:**
- Each platform (Linux/macOS/Windows) has separate logs
- Click on the failing check to see detailed output
- Look for error messages in the build log

### Patch Files in Feedstock

**Current situation:** The feedstock has a patch for the f-string bug in 1.7.6

**When to update:**
1. After releasing 1.7.7+ with the fix applied
2. Edit `recipe/meta.yaml` to remove the patch reference:
   ```yaml
   # Remove these lines:
   patches:
     - 1.7.6-utils-fstring-patch.diff
   ```
3. Delete the patch file
4. Submit PR with these changes

---

## 📊 Package Distribution Comparison

### PyPI (pip install)
- **Pros:**
  - Faster updates (within minutes of release)
  - Wider reach (anyone with pip)
  - Direct from source
- **Cons:**
  - Users must handle system dependencies (GDAL, etc.)
  - Binary wheels only for common platforms
  - Can have dependency conflicts

### conda-forge (conda install)
- **Pros:**
  - All dependencies included (GDAL, PROJ, etc.)
  - Binary packages for all platforms
  - Better reproducibility
  - No system package requirements
- **Cons:**
  - Slower updates (24h+ delay)
  - Requires conda/mamba
  - Build process is more complex

**Best practice:** Maintain both! Different users have different needs.

---

## 🎓 Learning Resources

### conda-forge Documentation
- Main docs: https://conda-forge.org/docs/
- Maintainer guide: https://conda-forge.org/docs/maintainer/
- Updating packages: https://conda-forge.org/docs/maintainer/updating_pkgs.html

### Your Repositories
- **Source code:** https://github.com/jandrewjohnson/hazelbean_dev
- **conda-forge feedstock:** https://github.com/conda-forge/hazelbean-feedstock
- **PyPI page:** https://pypi.org/project/hazelbean/

### Monitoring
- **PyPI downloads:** https://pepy.tech/project/hazelbean
- **conda-forge downloads:** https://anaconda.org/conda-forge/hazelbean
- **GitHub Actions:** https://github.com/jandrewjohnson/hazelbean_dev/actions

---

## ❓ Common Questions

### Q: Do I need to manually update conda-forge for every release?

**A:** You only need to **review and merge** the bot's PR. The bot does 95% of the work automatically.

### Q: Can I skip the conda-forge release?

**A:** Yes, but it's not recommended. Many users prefer conda because it handles system dependencies. Just don't merge the bot's PR if you want to skip it.

### Q: What if I want to release a hotfix quickly?

**A:** The PyPI release is nearly instant (20 minutes). conda-forge will be slower (24-48 hours total), but that's usually acceptable for hotfixes.

### Q: Can I test the conda package before it's published?

**A:** Yes! The feedstock CI builds test packages. You can download them from the PR's "Artifacts" section and test locally before merging.

### Q: What version numbering should I use?

**A:** Follow [Semantic Versioning](https://semver.org/):
- `1.7.7` → `1.7.8` for bug fixes
- `1.7.7` → `1.8.0` for new features
- `1.7.7` → `2.0.0` for breaking changes

### Q: What if the bot updates the wrong thing?

**A:** You can edit the bot's PR before merging! Just push commits to the bot's branch to fix any issues.

---

## 🔮 Future Improvements

Possible enhancements to consider:

1. **Automated testing before release:**
   - Add a "pre-release" workflow that runs extended tests
   - Gate releases on passing tests

2. **Release notes automation:**
   - Auto-generate more detailed release notes from commit messages
   - Include contributor acknowledgments

3. **Multi-stage releases:**
   - Release to PyPI test server first
   - Promote to production after validation

4. **Conda-forge co-maintenance:**
   - Add more maintainers to the feedstock
   - Faster PR reviews and merges

---

## 📝 Summary

**The beauty of this setup:** Once configured (which it already is!), releasing Hazelbean to both PyPI and conda-forge requires minimal manual work:

1. **30 seconds:** Create and push a git tag
2. **2 minutes:** Create GitHub release with notes
3. **5 minutes:** Review conda-forge bot PR (when it arrives)

Everything else is automated. Your job is to make great software - the infrastructure handles distribution! 🚀




