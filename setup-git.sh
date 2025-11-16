#!/bin/bash
# PKMS Data Repository Git Configuration Setup
# Run this to configure git hooks, aliases, and settings for the data repository

set -e

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$REPO_ROOT"

echo "🔧 Setting up PKMS Data Repository Git configuration..."
echo ""

# 1. Configure commit template
echo "→ Setting commit message template..."
git config commit.template .gitmessage
echo "  ✓ Template: .gitmessage"

# 2. Configure hooks path
echo "→ Configuring git hooks..."
git config core.hooksPath .git-hooks
chmod +x .git-hooks/pre-commit 2>/dev/null || true
chmod +x .git-hooks/pre-push 2>/dev/null || true
chmod +x .git-hooks/post-merge 2>/dev/null || true
echo "  ✓ Hooks path: .git-hooks"
echo "  ✓ Enabled: pre-commit, pre-push, post-merge"

# 3. Configure diff drivers
echo "→ Configuring diff drivers..."
git config diff.json.textconv 'python3 -m json.tool'
git config diff.toml.textconv 'cat'
git config diff.markdown.textconv 'cat'
echo "  ✓ JSON, TOML, Markdown diff drivers configured"

# 4. Configure git aliases
echo "→ Configuring PKMS git aliases..."

# pkms-status: Show git status + pending reviews
git config alias.pkms-status '!f() {
    git status &&
    echo "" &&
    if [ -d "data/queue/reviews/pending" ]; then
        PENDING=$(ls -1 data/queue/reviews/pending/*.json 2>/dev/null | wc -l);
        echo "📋 Pending reviews: $PENDING";
        if command -v pkms-review &> /dev/null && [ "$PENDING" -gt 0 ]; then
            echo "";
            pkms-review list 2>/dev/null || true;
        fi;
    fi;
}; f'

# pkms-log: Show commits with PKMS-specific formatting
git config alias.pkms-log 'log --oneline --graph --decorate --all -20'

# pkms-changes: Show what changed in data directories
git config alias.pkms-changes '!git log --stat --oneline -- vault/ data/metadata/ data/chunks/ .pkms/taxonomy.toml'

# pkms-tag-history: Show taxonomy tag history
git config alias.pkms-tag-history '!git log --oneline --follow -- .pkms/taxonomy.toml'

# pkms-note-history: Show history of a specific note
git config alias.pkms-note-history '!f() { git log --follow --patch -- "$@"; }; f'

# pkms-sync: Pull, show pending reviews, offer to review
git config alias.pkms-sync '!f() {
    git pull &&
    if [ -d "data/queue/reviews/pending" ]; then
        PENDING=$(ls -1 data/queue/reviews/pending/*.json 2>/dev/null | wc -l);
        if [ "$PENDING" -gt 0 ]; then
            echo "";
            echo "⚠️  $PENDING pending review(s) after sync";
            echo "";
            if command -v pkms-review &> /dev/null; then
                pkms-review list;
                echo "";
                read -p "Review now? [y/N] " -n 1 -r;
                echo;
                if [[ $REPLY =~ ^[Yy]$ ]]; then
                    pkms-review interactive;
                fi;
            fi;
        fi;
    fi;
}; f'

# pkms-update-code: Update pkms-core submodule
git config alias.pkms-update-code '!f() {
    echo "🔄 Updating pkms-core submodule...";
    cd .pkms || { echo "Error: .pkms directory not found"; return 1; };
    git fetch origin;
    CURRENT=$(git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD);
    git pull origin master;
    UPDATED=$(git describe --tags --exact-match 2>/dev/null || git rev-parse --short HEAD);
    cd ..;
    if [ "$CURRENT" != "$UPDATED" ]; then
        echo "✅ Updated: $CURRENT → $UPDATED";
        git add .pkms;
        echo "";
        echo "Submodule updated. Commit with:";
        echo "  git commit -m \"chore: Update pkms-core to $UPDATED\"";
    else
        echo "✅ Already up to date: $CURRENT";
    fi;
}; f'

echo "  ✓ pkms-status    - Show status + pending reviews"
echo "  ✓ pkms-log       - Pretty commit log"
echo "  ✓ pkms-changes   - Show data directory changes"
echo "  ✓ pkms-tag-history - Show taxonomy history"
echo "  ✓ pkms-note-history <file> - Show note history"
echo "  ✓ pkms-sync      - Pull + review pending items"
echo "  ✓ pkms-update-code - Update pkms-core submodule"

# 5. Configure merge strategy for generated files
echo "→ Configuring merge strategies..."
# Use 'ours' strategy for certain generated files if conflicts occur
git config merge.ours.driver 'true'
echo "  ✓ Merge strategies configured"

# 6. Set up git attributes
echo "→ Git attributes already configured via .gitattributes"
echo "  ✓ Better diffs for JSON, TOML, Markdown"

echo ""
echo "✅ PKMS Data Repository Git configuration complete!"
echo ""
echo "Available commands:"
echo "  git pkms-status           - Show status with pending reviews"
echo "  git pkms-log              - Pretty commit log"
echo "  git pkms-changes          - Show data changes"
echo "  git pkms-tag-history      - Show taxonomy history"
echo "  git pkms-note-history <file> - Show note history"
echo "  git pkms-sync             - Pull and review"
echo "  git pkms-update-code      - Update pkms-core submodule"
echo ""
echo "Hooks enabled:"
echo "  pre-commit  - Validate JSON/TOML, taxonomy, check for secrets"
echo "  pre-push    - Check for pending reviews"
echo "  post-merge  - Notify of pending reviews after pull"
echo ""
