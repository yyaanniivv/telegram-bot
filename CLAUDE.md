# CLAUDE.md - Project Instructions

## Branch Protection Rules for `main`

The `main` branch has the following protection rules configured via GitHub API:

```json
{
  "required_pull_request_reviews": {
    "required_approving_review_count": 1,
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": false
  },
  "enforce_admins": true,
  "required_linear_history": true,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": true,
  "lock_branch": false
}
```

**Key settings:**
- ✅ 1 approving review required
- ✅ Stale reviews dismissed on new commits
- ✅ Linear history enforced (no merge commits)
- ✅ Force pushes blocked
- ✅ Deletions blocked
- ✅ Conversation resolution required
- ✅ **Admin enforcement enabled** — even admins must use PRs

---

## Development Workflow

1. Create feature branch: `git checkout -b feat/your-feature`
2. Make changes, commit
3. Push branch: `git push origin feat/your-feature`
4. Create PR: `gh pr create --title "..." --body "..."`
5. Wait for review/approval (1 required)
6. Merge via GitHub UI or `gh pr merge --squash`

---

## Python Environment

```bash
pyenv activate telegram-bot
pip install -r requirements.txt
pip install pytest
```

## Testing

```bash
PYTHONPATH=. pytest tests/ -v
```

## Docker

```bash
docker compose build
docker compose up -d
```
