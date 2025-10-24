#!/bin/bash
# Setup script for GitHub Pages deployment
# This script configures mkdocs.yml for your specific GitHub repository
# 
# NOTE: This repository is already configured for jandrewjohnson/hazelbean_dev
# This script is provided for reference if you fork the repository

set -e

echo "🚀 Setting up MkDocs for GitHub Pages deployment..."

# Check if already configured for jandrewjohnson/hazelbean_dev
if grep -q "jandrewjohnson/hazelbean_dev" mkdocs.yml; then
    echo "✅ This repository is already configured for jandrewjohnson/hazelbean_dev"
    echo "🔗 GitHub Pages URL: https://jandrewjohnson.github.io/hazelbean_dev/"
    echo ""
    echo "ℹ️  If you've forked this repository, you may want to reconfigure for your own GitHub account."
    read -p "Continue with reconfiguration? (y/N): " CONTINUE
    if [[ ! $CONTINUE =~ ^[Yy]$ ]]; then
        echo "✨ No changes needed. Repository is ready for GitHub Pages deployment!"
        exit 0
    fi
fi

# Check if we're in the right directory
if [ ! -f "mkdocs.yml" ]; then
    echo "❌ Error: mkdocs.yml not found. Please run this script from the docs-site directory."
    exit 1
fi

# Get GitHub repository information
echo "📋 Please provide your GitHub repository information:"

# Try to detect from git remote if available
if command -v git >/dev/null 2>&1 && git remote -v >/dev/null 2>&1; then
    REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
    if [[ $REMOTE_URL =~ github\.com[:/]([^/]+)/([^/.]+) ]]; then
        DETECTED_USER="${BASH_REMATCH[1]}"
        DETECTED_REPO="${BASH_REMATCH[2]}"
        echo "🔍 Detected from git remote: $DETECTED_USER/$DETECTED_REPO"
        echo ""
    fi
fi

# Get username
if [ -n "$DETECTED_USER" ]; then
    read -p "GitHub username [$DETECTED_USER]: " USERNAME
    USERNAME=${USERNAME:-$DETECTED_USER}
else
    read -p "GitHub username: " USERNAME
fi

# Get repository name
if [ -n "$DETECTED_REPO" ]; then
    read -p "Repository name [$DETECTED_REPO]: " REPO_NAME
    REPO_NAME=${REPO_NAME:-$DETECTED_REPO}
else
    read -p "Repository name: " REPO_NAME
fi

# Validate inputs
if [ -z "$USERNAME" ] || [ -z "$REPO_NAME" ]; then
    echo "❌ Error: Username and repository name are required."
    exit 1
fi

echo ""
echo "🔧 Configuring mkdocs.yml for:"
echo "   • GitHub Pages URL: https://$USERNAME.github.io/$REPO_NAME/"
echo "   • Repository: $USERNAME/$REPO_NAME"
echo "   • Repository URL: https://github.com/$USERNAME/$REPO_NAME"
echo ""

# Create backup
cp mkdocs.yml mkdocs.yml.backup
echo "💾 Created backup: mkdocs.yml.backup"

# Update mkdocs.yml
sed -i.tmp "s|https://{user}\.github\.io/hazelbean_dev/|https://$USERNAME.github.io/$REPO_NAME/|" mkdocs.yml
sed -i.tmp "s|{user}/hazelbean_dev|$USERNAME/$REPO_NAME|g" mkdocs.yml
sed -i.tmp "s|https://github.com/{user}/hazelbean_dev|https://github.com/$USERNAME/$REPO_NAME|" mkdocs.yml

# Clean up temporary file
rm -f mkdocs.yml.tmp

echo "✅ Configuration updated successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Commit and push your changes to the main branch"
echo "2. Enable GitHub Pages in your repository settings:"
echo "   • Go to: Settings > Pages"
echo "   • Source: GitHub Actions"
echo "3. The documentation will be available at: https://$USERNAME.github.io/$REPO_NAME/"
echo ""
echo "🔍 To verify the changes:"
echo "   cat mkdocs.yml | grep -E 'site_url|repo_name|repo_url'"
echo ""
echo "🧪 To test locally:"
echo "   conda activate hazelbean_env"
echo "   mkdocs serve"
echo ""

# Show the changes made
echo "🔍 Configuration changes:"
echo "----------------------------------------"
grep -E 'site_url|repo_name|repo_url' mkdocs.yml | head -3
echo "----------------------------------------"
echo ""

echo "✨ Setup complete! Your MkDocs site is now configured for GitHub Pages."
