# PKMS Tagging Guide

**Version:** 0.3.1
**Last Updated:** 2025-11-16

A comprehensive guide to automated tagging, taxonomy management, and review workflows in PKMS.

---

## 📑 Table of Contents

1. [Overview](#overview)
2. [Taxonomy System](#taxonomy-system)
3. [Automated Tagging](#automated-tagging)
4. [Review Queue](#review-queue)
5. [Workflows](#workflows)
6. [Best Practices](#best-practices)
7. [Integration](#integration)

---

## Overview

PKMS v0.3.1 introduces **LLM-powered automated tagging** with a **controlled vocabulary** system and **human-in-the-loop approval** workflow.

### Key Components

1. **taxonomy.toml** - Controlled vocabulary (categories, tags, suggestions)
2. **pkms-tag** - LLM-based tag suggestion tool
3. **pkms-review** - Review queue management
4. **Git hooks** - Notifications for pending reviews
5. **Cline integration** - Agent checks reviews before operations

### Design Principles

- **Controlled Vocabulary**: Tags must be in taxonomy (prevents tag explosion)
- **LLM Suggestions**: Ollama analyzes content and suggests appropriate tags
- **Human Approval**: All new tags require explicit approval
- **Git-Native**: Review queue stored in `data/queue/reviews/` (git-trackable)
- **Incremental**: Only process notes without tags (unless `--verify`)

---

## Taxonomy System

### What is a Taxonomy?

A taxonomy is a **controlled vocabulary** that defines:

- **Categories**: Broad classifications (e.g., "technology", "cooking", "personal")
- **Tags**: Specific labels (e.g., "python", "docker", "pizza", "italian")
- **Suggestions**: Recommended tag combinations per category
- **Metadata**: Auto-tracked information (usage stats, approval dates)

### File Structure: `.pkms/taxonomy.toml`

```toml
[taxonomy.categories]
# Broad classifications (choose ONE per note)
allowed = [
    "technology",
    "cooking",
    "travel",
    "personal",
    "work",
    "reference"
]

[taxonomy.tags]
# Specific labels (choose 3-5 per note)
allowed = [
    # Technology
    "python", "docker", "api", "database", "linux",
    "git", "vscode", "kubernetes", "ci-cd",

    # Cooking
    "recipe", "italian", "german", "pizza", "pasta",
    "baking", "fermentation", "sourdough",

    # Travel
    "germany", "italy", "hiking", "photography",

    # Work
    "meeting-notes", "project-planning", "documentation",

    # Personal
    "journal", "ideas", "learning"
]

[taxonomy.suggestions]
# Recommended tags per category (helps LLM)
technology = ["python", "docker", "api", "database", "git"]
cooking = ["recipe", "italian", "german", "pizza", "baking"]
travel = ["germany", "italy", "hiking", "photography"]
personal = ["journal", "ideas", "learning"]
work = ["meeting-notes", "project-planning", "documentation"]

[taxonomy.metadata]
# Auto-tracked by pkms-review
last_updated = "2025-11-16T14:30:22Z"
total_tags = 42
total_categories = 6
```

### Creating Your Taxonomy

```bash
# Create initial taxonomy
cat > .pkms/taxonomy.toml <<'EOF'
[taxonomy.categories]
allowed = ["technology", "personal"]

[taxonomy.tags]
allowed = ["python", "docker", "learning"]

[taxonomy.suggestions]
technology = ["python", "docker"]
personal = ["learning"]

[taxonomy.metadata]
EOF
```

**Tip:** Start small (5-10 tags) and grow organically based on LLM suggestions.

---

## Automated Tagging

### How It Works

1. **Read Note**: Parse frontmatter and content
2. **LLM Analysis**: Send to Ollama with taxonomy context
3. **Suggest Tags**: LLM returns tags, category, confidence score
4. **Filter**: Only suggest tags from taxonomy (unless `--suggest-new`)
5. **Approval**: Show to user for approval (or queue for later)
6. **Apply**: Update frontmatter if approved

### LLM Prompt Structure

```
Analyze this note and suggest classification:

Title: {note_title}
Content: {first_1000_chars}

Categories (choose one): technology, cooking, travel, ...
Choose ONLY from these tags: python, docker, recipe, ...

Return JSON only:
{
  "category": "technology",
  "tags": ["python", "docker", "api"],
  "confidence": 0.85,
  "reasoning": "Note discusses Docker API usage in Python"
}

Guidelines:
- Choose 3-5 most relevant tags
- Category should be broad classification
- Tags should be specific and descriptive
- Confidence: how certain you are (0.0-1.0)
```

### Usage Examples

**Interactive Mode (default):**
```bash
pkms-tag

# Shows suggestions for each note:
# File: pizza-recipe.md
# Suggested tags:     cooking, italian, pizza, recipe
# Suggested category: cooking
# Confidence:         0.89
# [a]pprove / [r]eject / [e]dit / [s]kip:
```

**Queue Mode (automated workflows):**
```bash
pkms-tag --queue

# Creates review for later approval:
# [tag] Created review: tag_approval_20251116_143022
# [tag] Run 'pkms-review interactive' to approve
```

**Auto Mode (use carefully!):**
```bash
pkms-tag --auto

# Applies tags directly without review
# Only applies tags that exist in taxonomy
```

**Other Options:**
```bash
pkms-tag vault/2025-11/note.md     # Tag single note
pkms-tag --only-empty              # Only notes without tags
pkms-tag --verify                  # Re-analyze existing tags
pkms-tag --suggest-new             # Allow tags not in taxonomy
```

### Configuration

In `.pkms/config.toml`:

```toml
[llm]
model = "qwen2.5-coder:latest"     # Fast, good at analysis
ollama_url = "http://localhost:11434"
temperature = 0.3                   # Lower = more deterministic
max_tokens = 2000
```

**Recommended Models:**
- `qwen2.5-coder:latest` - Fast, excellent at analysis (default)
- `llama3.1:latest` - Good balance of speed and quality
- `mistral:latest` - Fast and accurate
- `gemma2:latest` - Lightweight alternative

---

## Review Queue

### What is the Review Queue?

A **git-native approval workflow** for automated operations. Tools like `pkms-tag --queue` create pending reviews that require human approval before applying changes.

### Review Structure

**File:** `data/queue/reviews/pending/{review_id}.json`

```json
{
  "id": "tag_approval_20251116_143022",
  "type": "tag_approval",
  "created": "2025-11-16T14:30:22Z",
  "status": "pending",
  "data": {
    "new_tags": ["sourdough", "fermentation", "baking"],
    "tag_usage": {
      "sourdough": 5,
      "fermentation": 3,
      "baking": 8
    },
    "affected_notes": 16
  },
  "context": {
    "triggered_by": "pkms-tag --queue",
    "timestamp": "/home/user/pkms"
  }
}
```

### Review Commands

**List all pending reviews:**
```bash
pkms-review list

# Output:
# Pending Reviews:
# ================
#
# [1] tag_approval_20251116_143022
#     Type: tag_approval
#     Created: 2025-11-16 14:30:22
#     Data: 3 new tags, 16 affected notes
```

**Show specific review:**
```bash
pkms-review show tag_approval_20251116_143022

# Shows full JSON details
```

**Approve/reject specific review:**
```bash
pkms-review approve tag_approval_20251116_143022
pkms-review reject tag_approval_20251116_143022
```

**Interactive review (recommended):**
```bash
pkms-review interactive

# For each pending review:
#
# Review: tag_approval_20251116_143022
# Type: tag_approval
# Created: 2025-11-16 14:30:22
#
# New Tags:
# - sourdough (used in 5 notes)
# - fermentation (used in 3 notes)
# - baking (used in 8 notes)
#
# [a]pprove / [r]eject / [s]kip:
```

### Review Types

| Type | Description | Created By | Applied To |
|------|-------------|------------|------------|
| `tag_approval` | New tag suggestions | `pkms-tag --queue` | `taxonomy.toml` |

**Future types** (extensible):
- `note_merge` - Note consolidation suggestions
- `link_suggestion` - Wikilink suggestions
- `archive_suggestion` - Archive candidates

---

## Workflows

### Workflow 1: Initial Setup

```bash
# 1. Create taxonomy
vim .pkms/taxonomy.toml

# 2. Tag all notes interactively
pkms-tag

# 3. Review and approve suggestions
# (interactive mode shows each note)

# 4. Commit approved tags
git add vault/
git commit -m "Add tags to notes"
```

### Workflow 2: Automated Batch Tagging

```bash
# 1. Tag notes in queue mode
pkms-tag --queue --only-empty

# Output:
# [tag] Created review: tag_approval_20251116_143022
# [tag] Run 'pkms-review interactive' to approve

# 2. Review suggestions
pkms-review interactive

# 3. If approved, taxonomy is auto-updated
# 4. Re-run tagging to apply approved tags
pkms-tag --only-empty

# 5. Commit changes
git add vault/ .pkms/taxonomy.toml
git commit -m "Add tags: sourdough, fermentation, baking"
```

### Workflow 3: Agent Integration

```bash
# 1. Configure Cline with user-prompt-submit-hook
# (See Integration section below)

# 2. Agent automatically checks for pending reviews
# Before each task:
# "There are 2 pending PKMS reviews (5 new tags). Review them first?"

# 3. User approves reviews via agent or CLI
pkms-review interactive

# 4. Agent continues with original task
```

### Workflow 4: Continuous Maintenance

```bash
# Weekly: Verify existing tags still fit
pkms-tag --verify --queue

# Review and approve changes
pkms-review interactive

# Monthly: Audit taxonomy
cat .pkms/taxonomy.toml | grep allowed
# → Remove unused tags
# → Add frequently suggested new tags
```

---

## Best Practices

### Taxonomy Design

**DO:**
- ✅ Start with 5-10 core tags
- ✅ Use lowercase, kebab-case for multi-word tags
- ✅ Keep categories broad (5-10 max)
- ✅ Keep tags specific but reusable
- ✅ Use `suggestions` to guide LLM
- ✅ Review and prune taxonomy quarterly

**DON'T:**
- ❌ Create hundreds of tags upfront
- ❌ Use overly specific tags (e.g., "pizza-margherita-with-basil")
- ❌ Mix languages in tag names
- ❌ Duplicate concepts (e.g., both "python" and "python-programming")

### Tagging Strategy

**Recommended tag counts per note:**
- **Categories**: 1 (broad classification)
- **Tags**: 3-5 (specific descriptors)

**Tag hierarchy example:**
```
Category: technology
Tags: python, docker, api, kubernetes, ci-cd
```

### Review Workflow

**DO:**
- ✅ Review in batches (not one-by-one)
- ✅ Check tag usage counts (high usage = valuable tag)
- ✅ Reject overly specific tags
- ✅ Commit taxonomy updates separately

**DON'T:**
- ❌ Auto-approve all suggestions
- ❌ Let reviews accumulate for weeks
- ❌ Approve tags you won't reuse

### LLM Configuration

**For accuracy (slower):**
```toml
[llm]
model = "llama3.1:latest"
temperature = 0.1
```

**For speed (faster):**
```toml
[llm]
model = "qwen2.5-coder:latest"
temperature = 0.3
```

---

## Integration

### Git Hooks

**Notify on pending reviews after `git pull`:**

File: `.git-hooks/post-merge`

```bash
#!/bin/bash
PENDING_DIR="data/queue/reviews/pending"

if [ -d "$PENDING_DIR" ]; then
    PENDING_COUNT=$(ls -1 "$PENDING_DIR"/*.json 2>/dev/null | wc -l)

    if [ "$PENDING_COUNT" -gt 0 ]; then
        echo ""
        echo "⚠️  PKMS: $PENDING_COUNT review(s) pending"
        echo "   Run: pkms-review list"
        echo ""
    fi
fi
```

**Install hook:**
```bash
chmod +x .git-hooks/post-merge
git config core.hooksPath .git-hooks
```

### Cline Integration (VSCode)

**Check reviews before executing tasks:**

File: `.cline/prompts/user-prompt-submit-hook.md`

```markdown
# PKMS Review Check Hook

Before executing any task, check for pending PKMS reviews.

## Steps:

1. Run: `pkms-review list`

2. If pending reviews exist:
   - Show summary to user
   - Ask: "There are pending PKMS reviews. Review them before proceeding?"
   - If yes: Run `pkms-review interactive`
   - Wait for user to complete review
   - Then: Continue with original task

3. If no pending reviews:
   - Proceed with task immediately

## Example:

User: "Search for pizza recipes"

Agent checks: pkms-review list
→ Output: "2 pending reviews: tag_suggestions (5 new tags)"

Agent asks: "There are 2 pending PKMS reviews (5 new tags). Review them first?"

User: "Yes"

Agent runs: pkms-review interactive
→ User approves tags

Agent continues: "Now searching for pizza recipes..."
```

### MCP Server Integration

The MCP server doesn't directly interact with reviews, but you can:

1. **Add review tool to MCP** (future enhancement)
2. **Agent checks reviews via CLI** (current approach)
3. **Automated review via cron** (see below)

### Automated Review (Cron)

**Tag notes weekly, queue for review:**

```bash
# crontab -e
0 3 * * 0 cd /path/to/pkms && pkms-tag --queue --only-empty
```

**Review manually on Monday mornings:**
```bash
pkms-review interactive
```

---

## Troubleshooting

### LLM Returns Empty Tags

**Problem**: `[tag] No tags suggested for: note.md`

**Solutions:**
1. Check Ollama is running: `ollama list`
2. Check model is downloaded: `ollama pull qwen2.5-coder:latest`
3. Check note has content (not empty)
4. Try different model (see Configuration section)
5. Increase temperature: `temperature = 0.5`

### LLM Suggests Invalid Tags

**Problem**: Tags not in taxonomy appear in suggestions

**Solutions:**
1. Don't use `--suggest-new` flag
2. Check taxonomy file exists: `cat .pkms/taxonomy.toml`
3. Verify `[taxonomy.tags.allowed]` is populated
4. LLM may hallucinate - reject invalid suggestions

### Review Queue Not Working

**Problem**: `pkms-review list` shows no reviews

**Solutions:**
1. Check directory exists: `ls data/queue/reviews/pending/`
2. Use `--queue` flag: `pkms-tag --queue` (not `--auto`)
3. Check for JSON files: `ls data/queue/reviews/pending/*.json`

### Git Hooks Not Firing

**Problem**: No notification after `git pull`

**Solutions:**
1. Check hook is executable: `chmod +x .git-hooks/post-merge`
2. Configure git hooks path: `git config core.hooksPath .git-hooks`
3. Test hook manually: `.git-hooks/post-merge`

---

## FAQ

**Q: Can I use multiple categories per note?**
A: The LLM suggests one category, but you can manually add more in frontmatter. Keep it to 1-2 for best results.

**Q: How do I remove a tag from taxonomy?**
A: Edit `.pkms/taxonomy.toml` and remove the tag from `allowed`. Existing notes keep the tag until you re-tag with `--verify`.

**Q: Can I rename tags in bulk?**
A: Not yet implemented. Manual approach: `git grep "old-tag"` → edit files → `pkms-update` → commit.

**Q: What happens to rejected reviews?**
A: They're moved to `data/queue/reviews/rejected/` for audit purposes.

**Q: Can I auto-approve certain tags?**
A: Not directly, but you can pre-add them to taxonomy. Use `--auto` mode for fully automated tagging (no review).

**Q: How do I export my taxonomy?**
A: It's already in TOML format (`.pkms/taxonomy.toml`). Convert to JSON/CSV with external tools if needed.

---

## Next Steps

1. **Create your taxonomy** - Start with 5-10 core tags
2. **Tag existing notes** - Use `pkms-tag` interactively
3. **Set up git hooks** - Get notified of pending reviews
4. **Integrate with Cline** - Automate review checks
5. **Grow organically** - Add tags based on LLM suggestions

---

**Happy Tagging! 🏷️**

For questions, open an issue on GitHub or consult the main [README.md](README.md).
