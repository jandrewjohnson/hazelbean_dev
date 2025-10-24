#!/bin/bash
# Generate changelog from git history
# This script ensures changelog is generated with proper parameters

auto-changelog \
  --template compact \
  --title "Hazelbean Changelog" \
  --unreleased \
  --starting-commit v1.6.7 \
  --tag-prefix v \
  --output CHANGELOG.md

echo "Changelog generated successfully!"

