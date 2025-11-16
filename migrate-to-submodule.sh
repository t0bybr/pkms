#!/bin/bash
# PKMS Submodule Migration Script
# Converts .pkms/ from embedded directory to git submodule
#
# This allows:
# - Separate versioning of code (pkms-core) and data (pkms-data)
# - Multiple data repositories using same code base
# - Easier code updates without touching data
#
# WARNING: This is a destructive operation. Backup first!

set -e

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         PKMS Submodule Migration                          ║${NC}"
echo -e "${BLUE}║  Convert .pkms/ to git submodule                          ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 0: Pre-flight checks
echo -e "${YELLOW}[0/7] Pre-flight checks...${NC}"

if [ ! -d ".pkms" ]; then
    echo -e "${RED}✗ .pkms/ directory not found${NC}"
    exit 1
fi

if [ -d ".pkms/.git" ]; then
    echo -e "${RED}✗ .pkms/ is already a git repository${NC}"
    echo "  This might already be a submodule or separate repo."
    exit 1
fi

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${RED}✗ You have uncommitted changes${NC}"
    echo "  Commit or stash them first:"
    echo "    git status"
    echo "    git add . && git commit -m 'Pre-migration commit'"
    exit 1
fi

echo -e "${GREEN}✓ Pre-flight checks passed${NC}"
echo ""

# Step 1: Explain what will happen
echo -e "${YELLOW}[1/7] Migration Overview${NC}"
echo ""
echo "This script will:"
echo "  1. Create backup of .pkms/ directory"
echo "  2. Create new pkms-core git repository (for code)"
echo "  3. Remove .pkms/ from this repository"
echo "  4. Add .pkms/ as git submodule pointing to pkms-core"
echo "  5. Test installation still works"
echo ""
echo -e "${YELLOW}After migration:${NC}"
echo "  • This repo (pkms-data): vault/, data/, inbox/"
echo "  • pkms-core repo: .pkms/ (code, config, tools)"
echo ""
echo -e "${RED}WARNING: This modifies your git history and repository structure!${NC}"
echo ""
read -p "Continue with migration? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Migration cancelled."
    exit 0
fi
echo ""

# Step 2: Create backup
echo -e "${YELLOW}[2/7] Creating backup...${NC}"
BACKUP_DIR="../pkms-backup-$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"
cp -r .pkms "$BACKUP_DIR/"
cp -r .git "$BACKUP_DIR/"
echo -e "${GREEN}✓ Backup created: $BACKUP_DIR${NC}"
echo ""

# Step 3: Ask for pkms-core repository location
echo -e "${YELLOW}[3/7] pkms-core Repository Setup${NC}"
echo ""
echo "Where should the pkms-core repository be located?"
echo "  1) Create new local repository at ../pkms-core"
echo "  2) Use existing remote repository (GitHub/GitLab URL)"
echo "  3) Create new repository at custom path"
echo ""
read -p "Choice [1/2/3]: " -n 1 -r REPO_CHOICE
echo
echo ""

case $REPO_CHOICE in
    1)
        PKMS_CORE_PATH="../pkms-core"
        PKMS_CORE_URL="$PKMS_CORE_PATH"

        if [ -d "$PKMS_CORE_PATH" ]; then
            echo -e "${RED}✗ Directory $PKMS_CORE_PATH already exists${NC}"
            exit 1
        fi

        echo "→ Creating new repository at $PKMS_CORE_PATH"
        mkdir -p "$PKMS_CORE_PATH"
        cd "$PKMS_CORE_PATH"
        git init
        echo "# PKMS Core" > README.md
        echo "PKMS code repository (lib, models, tools, config)" >> README.md
        echo "" >> README.md
        echo "This is the code component of PKMS, designed to be used as a git submodule." >> README.md
        git add README.md
        git commit -m "Initial commit: pkms-core repository"
        cd "$REPO_ROOT"
        echo -e "${GREEN}✓ Created $PKMS_CORE_PATH${NC}"
        ;;
    2)
        echo ""
        read -p "Enter remote repository URL: " PKMS_CORE_URL
        echo "→ Will use remote: $PKMS_CORE_URL"
        ;;
    3)
        echo ""
        read -p "Enter path for new repository: " PKMS_CORE_PATH
        PKMS_CORE_URL="$PKMS_CORE_PATH"

        if [ -d "$PKMS_CORE_PATH" ]; then
            echo -e "${RED}✗ Directory $PKMS_CORE_PATH already exists${NC}"
            exit 1
        fi

        echo "→ Creating new repository at $PKMS_CORE_PATH"
        mkdir -p "$PKMS_CORE_PATH"
        cd "$PKMS_CORE_PATH"
        git init
        echo "# PKMS Core" > README.md
        git add README.md
        git commit -m "Initial commit"
        cd "$REPO_ROOT"
        echo -e "${GREEN}✓ Created $PKMS_CORE_PATH${NC}"
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac
echo ""

# Step 4: Copy .pkms/ to pkms-core repository (if local)
if [ "$REPO_CHOICE" != "2" ]; then
    echo -e "${YELLOW}[4/7] Populating pkms-core repository...${NC}"

    # Copy .pkms/ contents to pkms-core
    cp -r .pkms/* "$PKMS_CORE_PATH/" 2>/dev/null || true
    cp .pkms/.gitignore "$PKMS_CORE_PATH/" 2>/dev/null || true

    # Commit in pkms-core
    cd "$PKMS_CORE_PATH"
    git add .
    git commit -m "Import PKMS core code from main repository

Contents:
- lib/ - Core libraries
- models/ - Pydantic models
- tools/ - CLI tools
- config.toml - Default configuration
- pyproject.toml - Python package config
"

    # Tag this version
    git tag -a v0.3.1 -m "PKMS Core v0.3.1 - Initial submodule version"

    cd "$REPO_ROOT"
    echo -e "${GREEN}✓ pkms-core repository populated${NC}"
else
    echo -e "${YELLOW}[4/7] Skipping (using remote repository)${NC}"
fi
echo ""

# Step 5: Remove .pkms/ from current repository
echo -e "${YELLOW}[5/7] Removing .pkms/ from data repository...${NC}"

# Remove from git tracking
git rm -rf .pkms/

# Commit removal
git commit -m "refactor: Remove .pkms/ directory (preparing for submodule)

.pkms/ will be re-added as git submodule pointing to pkms-core repository.
This allows separate versioning of code and data.

Backup created at: $BACKUP_DIR
"

echo -e "${GREEN}✓ .pkms/ removed from git${NC}"
echo ""

# Step 6: Add .pkms/ as submodule
echo -e "${YELLOW}[6/7] Adding .pkms/ as git submodule...${NC}"

git submodule add "$PKMS_CORE_URL" .pkms

# Checkout specific version if tagged
if [ "$REPO_CHOICE" != "2" ]; then
    cd .pkms
    git checkout v0.3.1
    cd "$REPO_ROOT"
fi

git commit -m "feat: Add .pkms/ as git submodule

.pkms/ now points to: $PKMS_CORE_URL

This enables:
- Separate versioning of code and data
- Multiple data repositories using same code
- Easier code updates via submodule update
"

echo -e "${GREEN}✓ .pkms/ added as submodule${NC}"
echo ""

# Step 7: Test installation
echo -e "${YELLOW}[7/7] Testing installation...${NC}"

if [ -f ".pkms/pyproject.toml" ]; then
    echo "→ Testing pip installation..."

    # Test in dry-run mode
    if pip install --dry-run -e .pkms/ &>/dev/null; then
        echo -e "${GREEN}✓ Installation test passed${NC}"
    else
        echo -e "${YELLOW}⚠ Installation test failed, but this might be okay${NC}"
        echo "  Try manually: pip install -e .pkms/"
    fi
else
    echo -e "${RED}✗ .pkms/pyproject.toml not found${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ Migration Complete!                                   ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Your repository structure is now:"
echo ""
echo "  pkms-data/ (this repository)"
echo "  ├── vault/          - Your notes"
echo "  ├── data/           - Generated data"
echo "  └── .pkms/          → git submodule → pkms-core"
echo ""
echo "  pkms-core/ (submodule)"
echo "  ├── lib/            - Core libraries"
echo "  ├── models/         - Pydantic models"
echo "  ├── tools/          - CLI tools"
echo "  └── config.toml     - Configuration"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo ""
echo "  1. Reinstall PKMS: pip install -e .pkms/"
echo "  2. Test tools work: pkms-search --help"
echo "  3. Push changes:"
echo "       git push"
echo ""
echo "  4. If using remote pkms-core, push it too:"
if [ "$REPO_CHOICE" != "2" ]; then
    echo "       cd $PKMS_CORE_PATH"
    echo "       git remote add origin <your-remote-url>"
    echo "       git push -u origin main --tags"
fi
echo ""
echo -e "${BLUE}Updating .pkms/ code in the future:${NC}"
echo ""
echo "  cd .pkms/"
echo "  git pull origin main"
echo "  cd .."
echo "  git add .pkms"
echo "  git commit -m 'Update pkms-core to latest version'"
echo ""
echo -e "${BLUE}Using same code in another data repository:${NC}"
echo ""
echo "  git clone <your-data-repo> pkms-data-2"
echo "  cd pkms-data-2"
echo "  git submodule init"
echo "  git submodule update"
echo "  pip install -e .pkms/"
echo ""
echo -e "${YELLOW}Backup location: $BACKUP_DIR${NC}"
echo -e "${YELLOW}Keep this backup until you've confirmed everything works!${NC}"
echo ""
