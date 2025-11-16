# PKMS Review Check Hook

Before executing any task, check for pending PKMS reviews.

## Steps:

1. Run: `pkms-review list`

2. If pending reviews exist:
   - Show summary to user
   - Ask: "There are pending PKMS reviews. Would you like to review them before proceeding?"
   - If yes: Run `pkms-review interactive`
   - Wait for user to complete review
   - Then: Continue with original task

3. If no pending reviews:
   - Proceed with task immediately

## Example:

```
User: "Search for pizza recipes"

Agent checks: pkms-review list
→ Output: "2 pending reviews: tag_suggestions (5 new tags)"

Agent asks: "There are 2 pending PKMS reviews (5 new tag suggestions). Would you like to review them before searching?"

User: "Yes"

Agent runs: pkms-review interactive
→ User approves tags

Agent continues: "Now searching for pizza recipes..."
```

## Notes:

- This hook ensures reviews are handled before making changes
- Prevents conflicts from automated operations
- Keeps human in the loop for important decisions
