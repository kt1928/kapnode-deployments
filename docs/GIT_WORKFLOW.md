# Git Workflow Guide

Version control best practices for the Kapnode Deployments repository.

## Table of Contents

- [Overview](#overview)
- [Git Workflow Skill](#git-workflow-skill)
- [Manual Git Operations](#manual-git-operations)
- [Commit Message Conventions](#commit-message-conventions)
- [Branching Strategy](#branching-strategy)
- [Handling Conflicts](#handling-conflicts)
- [Best Practices](#best-practices)

---

## Overview

This repository uses **Conventional Commits** and an **automated git workflow** to maintain clean version control history.

### Key Principles

1. **Commit frequently** - Small, atomic commits are better than large ones
2. **Write clear messages** - Follow conventional commit format
3. **Sync regularly** - Pull before starting work, push when done
4. **Never commit secrets** - Use `.gitignore` and pre-commit validation
5. **Document changes** - Update docs when adding features

---

## Git Workflow Skill

The repository includes a Claude Code skill (`.claude/skills/git-workflow.md`) that automates common git operations.

### Session Start Workflow

Automatically executed when Claude Code session starts:

```bash
# Fetch latest changes
git fetch origin

# Pull with fast-forward only
git pull --ff-only origin main

# Show recent commits
git log --oneline -5

# Show current status
git status
```

**What it does:**
- Ensures you're working with latest code
- Prevents merge conflicts
- Shows recent changes for context

### During Session

As you work, commit frequently:

```bash
# Stage all changes
git add .

# Commit with conventional format
git commit -m "feat(tui): add deployment validation"

# Continue working...
```

### Session End Workflow

Automatically executed when Claude Code session ends:

```bash
# Final status check
git status

# Add all changes
git add .

# Generate summary of changes
git diff --cached --stat

# Commit with descriptive message
git commit -m "feat(tui): implement complete TUI system"

# Push to remote
git push origin main
```

**What it does:**
- Ensures no work is lost
- Creates meaningful commit history
- Syncs with remote repository

---

## Manual Git Operations

### Check Status

```bash
git status
```

Shows:
- Modified files
- Staged changes
- Untracked files
- Current branch

### View Changes

```bash
# See unstaged changes
git diff

# See staged changes
git diff --cached

# See changes in specific file
git diff path/to/file.py
```

### Stage Changes

```bash
# Stage specific files
git add file1.py file2.py

# Stage all changes
git add .

# Stage by pattern
git add tui/lib/*.py

# Interactive staging
git add -p
```

### Commit Changes

```bash
# Commit staged changes
git commit -m "feat(tui): add SSH manager"

# Commit with multi-line message
git commit -m "feat(tui): add deployment screens

- Main menu with navigation
- Deploy screen with form validation
- Update screen for existing nodes
- History screen with filtering"

# Amend last commit (use carefully)
git commit --amend -m "feat(tui): add SSH manager with key detection"
```

### View History

```bash
# Show recent commits
git log --oneline -10

# Show detailed history
git log -5

# Show changes in each commit
git log -p -3

# Show commits by author
git log --author="Claude"

# Show commits affecting specific file
git log -- path/to/file.py
```

### Syncing

```bash
# Fetch changes (doesn't merge)
git fetch origin

# Pull with fast-forward
git pull --ff-only origin main

# Pull with rebase
git pull --rebase origin main

# Push to remote
git push origin main

# Force push (DANGEROUS - use with care)
git push --force-with-lease origin main
```

---

## Commit Message Conventions

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types

| Type | Description | Example |
|------|-------------|---------|
| `feat` | New feature | `feat(tui): add deployment wizard` |
| `fix` | Bug fix | `fix(ssh): correct key path detection` |
| `docs` | Documentation | `docs: update TUI user guide` |
| `style` | Code style (no logic change) | `style: format with black` |
| `refactor` | Code refactoring | `refactor(lib): simplify validators` |
| `test` | Adding/updating tests | `test(ssh): add connection tests` |
| `chore` | Maintenance tasks | `chore: update dependencies` |
| `perf` | Performance improvement | `perf(inventory): optimize node search` |
| `ci` | CI/CD changes | `ci: add GitHub Actions workflow` |

### Scopes

Common scopes for this repository:

- `tui` - Terminal UI code
- `lib` - Business logic libraries
- `screens` - TUI screen layouts
- `components` - Reusable TUI components
- `scripts` - Bash deployment scripts
- `ansible` - Ansible playbooks
- `docs` - Documentation
- `config` - Configuration files
- `examples` - Templates and examples

### Examples

**Good commits:**

```bash
feat(tui): add SSH key auto-detection
fix(scripts): correct Tailscale key handling
docs: add comprehensive TUI user guide
refactor(lib): extract validation logic
chore: update Python dependencies to latest
```

**Bad commits:**

```bash
# Too vague
git commit -m "fixes"

# No type
git commit -m "added new feature"

# Too long description (should use body)
git commit -m "feat(tui): add new deployment screen with form validation and SSH connection testing and many other features"

# No scope when it would be helpful
git commit -m "feat: update code"
```

### Multi-line Commits

For complex changes:

```bash
git commit -m "feat(tui): implement complete deployment workflow

- Add SSH manager with auto-detection
- Create deployment form with validation
- Implement real-time log viewer
- Add inventory integration
- Support for multiple locations

This completes Phase 2 of the TUI implementation.
Closes #42"
```

---

## Branching Strategy

### Main Branch

- `main` - Production-ready code
- Always in a deployable state
- Protected (no force push)

### Feature Branches

For new features or significant changes:

```bash
# Create feature branch
git checkout -b feature/kubectl-integration

# Work on feature
# ... make changes ...

# Commit regularly
git add .
git commit -m "feat(tui): add kubectl cluster status"

# Push feature branch
git push -u origin feature/kubectl-integration

# Create pull request (on GitHub)

# After review and merge, delete branch
git checkout main
git pull
git branch -d feature/kubectl-integration
```

### Hotfix Branches

For urgent fixes:

```bash
# Create hotfix branch
git checkout -b hotfix/ssh-key-bug

# Fix the bug
git add .
git commit -m "fix(ssh): resolve key path resolution issue"

# Push and merge quickly
git push -u origin hotfix/ssh-key-bug
```

### Branch Naming

```
feature/descriptive-name
fix/bug-description
hotfix/urgent-fix
docs/documentation-update
refactor/component-name
```

---

## Handling Conflicts

### When Conflicts Occur

```bash
# Attempt pull
git pull origin main
# ERROR: Merge conflict in tui/lib/ssh_manager.py

# View conflicted files
git status

# Open conflicted file
nano tui/lib/ssh_manager.py
```

### Conflict Markers

```python
<<<<<<< HEAD
# Your local changes
def detect_ssh_key():
    return Path("~/.ssh/homelab_rsa")
=======
# Incoming changes
def detect_ssh_key():
    return Path.home() / ".ssh" / "homelab_rsa"
>>>>>>> origin/main
```

### Resolving Conflicts

1. **Edit the file** to keep desired changes
2. **Remove conflict markers** (`<<<<<<<`, `=======`, `>>>>>>>`)
3. **Test the resolution** (run code, check functionality)
4. **Stage the resolution**:
   ```bash
   git add tui/lib/ssh_manager.py
   ```
5. **Complete the merge**:
   ```bash
   git commit -m "merge: resolve conflict in SSH manager"
   ```

### Avoiding Conflicts

1. **Pull frequently** - Stay up to date
2. **Commit often** - Smaller commits = smaller conflicts
3. **Communicate** - Coordinate when working on same files
4. **Use feature branches** - Isolate changes

---

## Best Practices

### 1. Commit Frequency

**Do:**
- Commit after completing a logical unit of work
- Commit when tests pass
- Commit before switching tasks

**Don't:**
- Commit broken code
- Wait too long between commits
- Commit unrelated changes together

### 2. Secret Management

**Never commit:**
- SSH private keys
- Tailscale auth keys
- K3s tokens
- API keys
- Passwords

**Use `.gitignore`:**
```gitignore
# SSH Keys
*.pem
*_rsa
*_rsa.pub
*_ed25519

# Configuration with secrets
.homelab-deploy.conf
inventory.yml

# Tokens and keys
*.key
*.token
```

### 3. Pre-Commit Checks

Before committing:

```bash
# 1. Run tests
pytest tests/

# 2. Format code
black .

# 3. Check linting
flake8 .

# 4. Type checking
mypy tui/

# 5. Verify no secrets
git diff --cached | grep -i "key\|token\|password"
```

### 4. Commit Size

**Good commit:**
- Single responsibility
- Complete thought
- Independently revertible
- Clear purpose

**Too small:**
```bash
git commit -m "fix: add comma"
git commit -m "fix: remove comma"
```

**Too large:**
```bash
git commit -m "feat: implement entire TUI, update all docs, refactor all scripts, fix 10 bugs"
```

### 5. Git Hygiene

**Clean up:**
```bash
# Remove untracked files
git clean -fd

# Reset local changes
git reset --hard HEAD

# Remove old branches
git branch --merged | grep -v "main" | xargs git branch -d
```

**Verify state:**
```bash
# Before starting work
git status
git log --oneline -5

# After finishing work
git status
git log --oneline -1
```

---

## Advanced Operations

### Interactive Rebase

Clean up commit history before pushing:

```bash
# Rebase last 3 commits
git rebase -i HEAD~3

# Options:
# pick - keep commit
# reword - change commit message
# squash - combine with previous commit
# drop - remove commit
```

### Cherry-Pick

Apply specific commit from another branch:

```bash
# Copy commit abc123 to current branch
git cherry-pick abc123
```

### Stash Changes

Temporarily save work:

```bash
# Stash current changes
git stash

# List stashes
git stash list

# Apply most recent stash
git stash pop

# Apply specific stash
git stash apply stash@{1}
```

### Undo Operations

```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Undo last commit (discard changes)
git reset --hard HEAD~1

# Revert commit (create new commit)
git revert abc123

# Restore file to last commit
git checkout HEAD -- file.py
```

---

## CI/CD Integration

### GitHub Actions (Future)

Automated workflows on push:

```yaml
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: pytest tests/
      - name: Check formatting
        run: black --check .
```

### Pre-commit Hooks

Local validation before commit:

```bash
# Install pre-commit
pip install pre-commit

# Setup hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

---

## Troubleshooting

### Detached HEAD State

```bash
# You see: "HEAD detached at abc123"
git checkout main
```

### Accidentally Committed to Wrong Branch

```bash
# On wrong branch
git log --oneline -1  # Note commit hash

# Switch to correct branch
git checkout correct-branch

# Cherry-pick the commit
git cherry-pick abc123

# Go back and remove from wrong branch
git checkout wrong-branch
git reset --hard HEAD~1
```

### Push Rejected

```bash
# ERROR: Updates were rejected
git pull --rebase origin main
git push origin main
```

---

## Resources

- [Conventional Commits](https://www.conventionalcommits.org/)
- [Git Documentation](https://git-scm.com/doc)
- [GitHub Flow](https://docs.github.com/en/get-started/quickstart/github-flow)
- [Atlassian Git Tutorial](https://www.atlassian.com/git/tutorials)

---

**Last Updated**: 2025-11-19
**Version**: 1.0.0
**Maintained by**: Kapnode Team
