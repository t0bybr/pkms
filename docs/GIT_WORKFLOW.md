# PKMS Git Workflow Guide

**Version:** 0.3.1
**Last Updated:** 2025-11-16

Complete guide to Git workflows, hooks, aliases, and submodule architecture for PKMS.

---

## 📑 Table of Contents

1. [Quick Start](#quick-start)
2. [Git Hooks](#git-hooks)
3. [Git Aliases](#git-aliases)
4. [Taxonomy Versioning](#taxonomy-versioning)
5. [Worktrees](#worktrees)
6. [Submodule Architecture](#submodule-architecture)
7. [Best Practices](#best-practices)

---

## Quick Start

### Initial Setup

```bash
# Run setup script to configure hooks, aliases, and templates
.pkms/setup-git.sh

# This configures:
# - Commit message template
# - Git hooks (pre-commit, pre-push, post-merge)
# - Diff drivers for JSON/TOML/Markdown
# - PKMS git aliases
```

---

## Git Hooks

PKMS uses git hooks to enforce quality and prevent common mistakes.

### Pre-commit Hook

**Location:** `.git-hooks/pre-commit`

**What it does:**
- ✅ Validates JSON files (metadata, reviews)
- ✅ Validates TOML files (config, taxonomy)
- ✅ Checks taxonomy structure
- ✅ Warns about broken wikilinks
- ✅ Prevents committing .env files

**Example:**
```bash
git add data/metadata/01HAR6DP.json
git commit -m "Update metadata"

# Output:
# 🔍 PKMS Pre-commit validation...
#   → Validating JSON files...
#   ✓ data/metadata/01HAR6DP.json
#   ✅ Pre-commit validation PASSED
```

**If validation fails:**
```bash
# Fix the file
python -m json.tool data/metadata/broken.json

# Try again
git add data/metadata/broken.json
git commit -m "Fix metadata"
```

### Pre-push Hook

**Location:** `.git-hooks/pre-push`

**What it does:**
- ⚠️ Warns if pending reviews exist
- 📋 Lists pending reviews
- ❓ Asks for confirmation before pushing

**Example:**
```bash
git push

# Output:
# ⚠️  Warning: 3 pending PKMS review(s)
#
# Pending reviews:
# tag_approval_20251116_143022
# tag_approval_20251116_145533
#
# Recommended: Review pending items before pushing
#   Run: pkms-review interactive
#
# Push anyway? [y/N]
```

### Post-merge Hook

**Location:** `.git-hooks/post-merge`

**What it does:**
- 📢 Notifies about pending reviews after `git pull`

**Example:**
```bash
git pull

# Output:
# ...
# ⚠️  PKMS: 2 review(s) pending
#    Run: pkms-review list
```

---

## Git Aliases

PKMS provides several git aliases for common workflows.

### pkms-status

Show git status + pending reviews in one command.

```bash
git pkms-status

# Output:
# On branch main
# Your branch is up to date with 'origin/main'.
#
# nothing to commit, working tree clean
#
# 📋 Pending reviews: 2
#
# [1] tag_approval_20251116_143022
#     Created: 2025-11-16 14:30:22
#     Data: 3 new tags
```

### pkms-log

Pretty git log with graph and decorations.

```bash
git pkms-log

# Output (last 20 commits):
# * 84ff215 (HEAD -> main) fix: Track data/queue/ in git
# * c40239c fix: Track embeddings in git
# * 7b4c671 fix: Correct .gitignore to track metadata
# * 9263f69 docs: Update documentation for v0.3.1
```

### pkms-changes

Show what changed in data directories.

```bash
git pkms-changes

# Output:
# 9263f69 docs: Update documentation for v0.3.1
#  README.md           | 100 ++++++
#  TAGGING_GUIDE.md    | 413 +++++++++++++++++++++
#
# 84ff215 fix: Track data/queue/ in git
#  .gitignore          |   5 +-
#  README.md           |  11 +-
```

### pkms-tag-history

Show taxonomy change history.

```bash
git pkms-tag-history

# Output:
# 84ff215 fix: Track data/queue/ in git
# 7b4c671 fix: Correct .gitignore to track metadata
# c40239c fix: Track embeddings in git
# ...changes to .pkms/taxonomy.toml
```

### pkms-note-history

Show full history of a specific note.

```bash
git pkms-note-history vault/2025-11/pizza-recipe--01HAR6DP.md

# Shows full git log with diffs for that file
```

### pkms-sync

Pull + review pending items interactively.

```bash
git pkms-sync

# Output:
# Already up to date.
#
# ⚠️  2 pending review(s) after sync
#
# [1] tag_approval_20251116_143022
# [2] tag_approval_20251116_145533
#
# Review now? [y/N] y
#
# [Opens pkms-review interactive mode]
```

---

## Taxonomy Versioning

Use git tags to version your taxonomy for easy rollback.

### Create Taxonomy Tag

```bash
# After making taxonomy changes
pkms-taxonomy-tag create

# Output:
# Creating taxonomy tag: taxonomy-v1.1
#   Previous version: taxonomy-v1.0
#
# Proceed? [Y/n] y
#
# ✅ Created taxonomy tag: taxonomy-v1.1
#    6 categories, 45 tags
#
# To push tag: git push origin taxonomy-v1.1
# To view:     git show taxonomy-v1.1
# To rollback: git checkout taxonomy-v1.1 -- .pkms/taxonomy.toml
```

### List Taxonomy Versions

```bash
pkms-taxonomy-tag list

# Output:
# Taxonomy Version History:
# ============================================================
#
# taxonomy-v1.1 (2025-11-16)
#   Added 3 tag(s): sourdough, fermentation, baking
#
# taxonomy-v1.0 (2025-11-15)
#   Initial taxonomy with 42 tags
```

### Rollback to Previous Version

```bash
# View what changed
git diff taxonomy-v1.0 taxonomy-v1.1 -- .pkms/taxonomy.toml

# Rollback to v1.0
git checkout taxonomy-v1.0 -- .pkms/taxonomy.toml
git commit -m "Rollback taxonomy to v1.0"

# Or create new tag for current state
pkms-taxonomy-tag create --major  # Bump to v2.0
```

### Automatic Tagging (Recommended)

```bash
# After pkms-review approves new tags
pkms-review approve tag_approval_20251116_143022

# Automatically suggest creating tag
git add .pkms/taxonomy.toml
git commit -m "Add approved tags: sourdough, fermentation"

# Then create tag
pkms-taxonomy-tag auto  # Non-interactive
```

---

## Worktrees

Use git worktrees for parallel workflows without branch switching chaos.

### What are Worktrees?

Worktrees let you have **multiple working directories** for the same repository, each on a different branch.

**Normal workflow (problematic):**
```bash
git checkout -b synthesis/python
# Work on synthesis...
git checkout main  # Have to stop, commit/stash
# Can't work on both simultaneously
```

**With worktrees (elegant):**
```bash
# Main directory stays on main branch
cd pkms

# Create separate worktree for synthesis
git worktree add ../pkms-synthesis synthesis/python

# Now you have two directories:
# pkms/           (on main)
# pkms-synthesis/ (on synthesis/python)

# Work in pkms-synthesis/ without affecting pkms/
cd ../pkms-synthesis
pkms-synth --find-clusters --tags python
pkms-synth --create python-workflow

git add .
git commit -m "Synthesize Python workflow notes"
git push

# Meanwhile, pkms/ is untouched
cd ../pkms
git status  # Still on main, no changes
```

### Use Cases

**1. Parallel Synthesis:**
```bash
# Synthesis 1: Python notes
git worktree add ../pkms-synth-python synthesis/python

# Synthesis 2: Cooking notes
git worktree add ../pkms-synth-cooking synthesis/cooking

# Synthesis 3: Work notes
git worktree add ../pkms-synth-work synthesis/work

# All working independently!
```

**2. Tagging Experiments:**
```bash
# Try new taxonomy without affecting main
git worktree add ../pkms-tag-experiment feature/new-taxonomy

cd ../pkms-tag-experiment
# Edit .pkms/taxonomy.toml
# Test with pkms-tag
# If good, merge. If bad, delete worktree.
```

**3. Testing Code Changes:**
```bash
# Test new search algorithm
git worktree add ../pkms-test-search feature/improved-search

cd ../pkms-test-search
# Modify .pkms/lib/search/
pip install -e .pkms/
pkms-search "test query"
# If good, merge. If bad, delete worktree.
```

### Worktree Commands

```bash
# List all worktrees
git worktree list

# Output:
# /home/user/pkms              84ff215 [main]
# /home/user/pkms-synthesis    7b4c671 [synthesis/python]
# /home/user/pkms-cooking      9263f69 [synthesis/cooking]

# Remove worktree when done
git worktree remove ../pkms-synthesis

# Or delete directory and prune
rm -rf ../pkms-synthesis
git worktree prune
```

---

## Submodule Architecture

Separate code (`.pkms/`) from data (`vault/`, `data/`) for better versioning.

### Current Structure (Default)

```
pkms/
├── .pkms/          # Code (embedded in repo)
├── vault/          # Data
└── data/           # Generated data
```

**Problem:** Code and data changes mixed in same commits.

### Submodule Structure (Recommended)

```
pkms-data/          # This repository (data only)
├── vault/          # Your notes
├── data/           # Generated metadata/chunks/embeddings
└── .pkms/          → git submodule → pkms-core

pkms-core/          # Separate repository (code only)
├── lib/            # Core libraries
├── models/         # Pydantic models
├── tools/          # CLI tools
└── config.toml     # Default config
```

**Benefits:**
- ✅ Code repo versioned independently (v0.3.0, v0.3.1, ...)
- ✅ Multiple data repos can use same code
- ✅ Update code without touching data
- ✅ Fork code separately from data

### Migration to Submodules

**Run the migration script:**

```bash
./migrate-to-submodule.sh

# This will:
# 1. Create backup
# 2. Create pkms-core repository
# 3. Move .pkms/ to pkms-core
# 4. Remove .pkms/ from current repo
# 5. Add .pkms/ as submodule
# 6. Test installation
```

**After migration:**

```bash
# Your repository structure:
ls -la
# vault/
# data/
# .pkms/  → submodule

# Update code in future:
cd .pkms
git pull origin main
cd ..
git add .pkms
git commit -m "Update pkms-core to v0.3.2"
```

### Using Submodules

**Clone repository with submodules:**
```bash
git clone --recurse-submodules <repo-url>

# Or if already cloned:
git submodule init
git submodule update
```

**Update submodule to latest:**
```bash
cd .pkms
git pull origin main
cd ..
git add .pkms
git commit -m "Update pkms-core"
```

**Pin submodule to specific version:**
```bash
cd .pkms
git checkout v0.3.1  # Pin to specific tag
cd ..
git add .pkms
git commit -m "Pin pkms-core to v0.3.1"
```

**Multiple data repos with same code:**
```bash
# Repo 1: Personal notes
pkms-personal/
└── .pkms/  → pkms-core@v0.3.1

# Repo 2: Work notes
pkms-work/
└── .pkms/  → pkms-core@v0.3.1

# Repo 3: Shared team notes
pkms-team/
└── .pkms/  → pkms-core@v0.3.0  # Older stable version
```

---

## Best Practices

### 1. Commit Message Template

Use the provided template for structured commits:

```bash
# Template automatically loaded after setup-git.sh
git commit

# Opens editor with:
# <type>: <summary in 50 characters or less>
#
# <Detailed description of changes>
# - What was changed and why
#
# Type: feat, fix, docs, refactor, tag, synth, test, chore
```

**Good commits:**
```
feat(search): Add German stemming to BM25 index

- Improves search quality for German text
- Uses Whoosh StemmingAnalyzer with lang="de"
- Tested with "backofen" → "Ofen Temperatur"

Affects: data/index/
```

```
tag: Add sourdough, fermentation, baking tags

Approved from review tag_approval_20251116_143022.
Total tags: 45 (was 42)

Affects: .pkms/taxonomy.toml
```

### 2. Regular Taxonomy Tags

```bash
# After significant taxonomy changes
git add .pkms/taxonomy.toml
git commit -m "tag: Add 5 cooking-related tags"
pkms-taxonomy-tag create

# Push with tags
git push --follow-tags
```

### 3. Use Worktrees for Experiments

```bash
# Instead of:
git checkout -b experiment
# ...mess around...
git checkout main
git branch -D experiment  # Lost work!

# Do this:
git worktree add ../pkms-experiment experiment
cd ../pkms-experiment
# ...mess around...
cd ../pkms
git worktree remove ../pkms-experiment  # Clean!
```

### 4. Review Before Pushing

```bash
# Always review changes
git pkms-status
git pkms-changes

# Review pending items
pkms-review list

# Then push
git push
```

### 5. Sync Regularly

```bash
# Use pkms-sync instead of plain git pull
git pkms-sync

# This pulls AND shows pending reviews
```

---

## Troubleshooting

### Hook Not Running

```bash
# Ensure hooks path is configured
git config core.hooksPath .git-hooks

# Ensure hooks are executable
chmod +x .git-hooks/*

# Re-run setup
.pkms/setup-git.sh
```

### JSON Validation Fails

```bash
# Find the broken JSON
python -m json.tool data/metadata/01HAR6DP.json

# Fix it manually or regenerate
pkms-update vault/2025-11/note.md
```

### Taxonomy Tag Already Exists

```bash
# List existing tags
pkms-taxonomy-tag list

# Use next version or specify custom
pkms-taxonomy-tag create --version v1.5
```

### Submodule Out of Sync

```bash
# Update submodule
cd .pkms
git pull origin main
cd ..

# Or reset to tracked version
git submodule update --init

# Or update to latest and commit
git submodule update --remote
git add .pkms
git commit -m "Update pkms-core to latest"
```

---

## Summary

**Setup:**
```bash
.pkms/setup-git.sh  # One-time setup
```

**Daily Workflow:**
```bash
git pkms-status     # Check status + reviews
git pkms-sync       # Pull + review
git add .
git commit          # Uses template
git push            # Checks for pending reviews
```

**Taxonomy Management:**
```bash
pkms-taxonomy-tag create   # After taxonomy changes
pkms-taxonomy-tag list     # View history
```

**Advanced:**
```bash
git worktree add ../pkms-synthesis synthesis/batch-001
./migrate-to-submodule.sh  # Convert to submodule architecture
```

---

**Happy Git-ing! 🚀**

For questions, see main [README.md](README.md) or [TAGGING_GUIDE.md](TAGGING_GUIDE.md).
