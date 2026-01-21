# Hazelbean Release Quick Reference

**🎯 Goal:** Release new version to PyPI and conda-forge

---

## ⚡ Quick Steps (5 minutes of your time)

### 1️⃣ Create Git Tag (30 seconds)

```bash
VERSION="1.7.7"  # Your new version
git tag -a "v${VERSION}" -m "Release version ${VERSION}"
git push origin "v${VERSION}"
```

### 2️⃣ Create GitHub Release (2 minutes)

1. Go to: https://github.com/jandrewjohnson/hazelbean_dev/releases
2. Click "Draft a new release"
3. Select your tag (`v1.7.7`)
4. Write release notes
5. Click "Publish release" 

**✨ Automation kicks in:**
- GitHub Actions builds wheels (~20 min)
- Uploads to PyPI automatically
- Updates CHANGELOG.md

### 3️⃣ Review conda-forge PR (5 minutes, ~24h later)

1. Wait for notification from `regro-cf-autotick-bot`
2. Go to: https://github.com/conda-forge/hazelbean-feedstock/pulls
3. Review the bot's PR:
   - Check version number ✅
   - Check dependencies ✅
   - Wait for CI builds to pass ✅
4. Click "Merge pull request"

**✨ Automation completes:**
- conda-forge builds packages (~1-2 hours)
- Publishes to anaconda.org

### ✅ Done!

Users can now install via:
```bash
pip install hazelbean==1.7.7          # PyPI (immediate)
conda install -c conda-forge hazelbean==1.7.7  # conda-forge (few hours later)
```

---

## 📋 Pre-Release Checklist

- [ ] Tests passing
- [ ] Version number decided
- [ ] Release notes drafted
- [ ] Branch is `main` (or appropriate)

---

## 🎬 What Happens Automatically

| Step | System | Time | Action |
|------|--------|------|--------|
| 1 | You | 30s | Create git tag |
| 2 | You | 2m | Create GitHub release |
| 3 | GitHub Actions | 15-20m | Build wheels + upload to PyPI |
| 4 | GitHub Actions | 1m | Update CHANGELOG |
| 5 | conda-forge bot | 1-24h | Detect PyPI release |
| 6 | conda-forge bot | 1m | Create PR on feedstock |
| 7 | You | 5m | Review & merge PR |
| 8 | conda-forge CI | 1-2h | Build & publish packages |

**Total manual time:** ~7 minutes  
**Total elapsed time:** 1-3 days (mostly waiting)

---

## 🔧 Do You Need to Change Any Code?

**NO!** 🎉

Everything is already configured:
- ✅ GitHub Actions workflows in `.github/workflows/`
- ✅ PyPI credentials in GitHub Secrets (`PYPI_APIKEY`)
- ✅ Version management via `setuptools_scm`
- ✅ You're a maintainer on conda-forge feedstock

You just follow the steps above for each release!

---

## 🐛 Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| GitHub Action fails | Check workflow logs in Actions tab |
| PyPI upload rejected | Version might already exist - increment |
| No conda-forge PR after 48h | Check PyPI page, may need manual PR |
| conda-forge build fails | Check each platform's CI log for errors |

---

## 📚 Full Documentation

See [`docs/release-process-explained.md`](./release-process-explained.md) for:
- Detailed explanation of each step
- Technical background on how it works
- Troubleshooting guide
- Common questions answered

---

## 🔗 Important Links

- **Source:** https://github.com/jandrewjohnson/hazelbean_dev
- **PyPI:** https://pypi.org/project/hazelbean/
- **conda-forge feedstock:** https://github.com/conda-forge/hazelbean-feedstock
- **GitHub Actions:** https://github.com/jandrewjohnson/hazelbean_dev/actions

---

**Remember:** The automation does 95% of the work. Your job is just to trigger it! 🚀



