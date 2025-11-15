# Git Workflow Management Skill

This skill automates version control workflows for the kapnode-deployments repository, ensuring consistent git practices across all Claude Code sessions.

## Skill Purpose

Automatically manage git operations for homelab deployment projects:
- Pull latest changes at session start
- Track file modifications during session
- Generate meaningful commit messages
- Validate for secrets before committing
- Push changes at session end

## When to Use This Skill

This skill should be invoked:
1. **Automatically at session start** - Pull latest changes
2. **Automatically at session end** - Commit and push changes
3. **On-demand** - When user requests git operations
4. **Before major changes** - Create feature branches

## Session Start Workflow

When a new Claude Code session begins, automatically execute:

```bash
# 1. Check if we're in a git repository
if [ -d .git ]; then
  echo "📦 Git repository detected: kapnode-deployments"

  # 2. Fetch latest changes from remote
  git fetch origin

  # 3. Check current status
  git status --short

  # 4. Check for uncommitted changes
  if [ -n "$(git status --porcelain)" ]; then
    echo "⚠️  Uncommitted changes detected from previous session:"
    git status --short
    echo ""
    echo "Options:"
    echo "  1. Commit changes now (recommended)"
    echo "  2. Stash changes temporarily"
    echo "  3. Continue without pulling (may cause conflicts)"
    # Ask user for preference
  else
    # 5. Pull latest changes (fast-forward only)
    echo "⬇️  Pulling latest changes..."
    git pull --ff-only origin main || {
      echo "❌ Cannot fast-forward. Manual merge required."
      echo "Run: git pull --rebase origin main"
      exit 1
    }

    # 6. Show what changed since last session
    echo "✅ Repository up to date"
    echo ""
    echo "Recent changes:"
    git log --oneline --graph --decorate -5
  fi
else
  echo "ℹ️  Not a git repository. Run 'git init' to initialize."
fi
```

## Session End Workflow

When Claude Code session ends or user requests commit, automatically execute:

```bash
# 1. Check repository status
echo "📝 Preparing to commit changes..."
git status

# 2. List modified files
CHANGED_FILES=$(git status --porcelain | wc -l | tr -d ' ')

if [ "$CHANGED_FILES" -eq 0 ]; then
  echo "✅ No changes to commit"
  exit 0
fi

echo "Modified files: $CHANGED_FILES"
echo ""

# 3. Scan for secrets/sensitive data
echo "🔍 Scanning for secrets..."
SECRETS_FOUND=false

# Check for common secret patterns
if git diff --cached | grep -iE "(password|secret|api[_-]?key|auth[_-]?token|private[_-]?key|tskey-auth)" > /dev/null; then
  echo "⚠️  WARNING: Possible secrets detected in staged files!"
  echo "Please review carefully before committing:"
  git diff --cached | grep -iE "(password|secret|api[_-]?key|auth[_-]?token|private[_-]?key|tskey-auth)"
  SECRETS_FOUND=true
fi

# Check for SSH keys
if git diff --cached | grep -E "BEGIN (RSA|OPENSSH|EC) PRIVATE KEY" > /dev/null; then
  echo "❌ ERROR: SSH private key detected! DO NOT COMMIT."
  echo "Add to .gitignore and remove from staging."
  exit 1
fi

# Check for .conf files with potential secrets
if git status --porcelain | grep "\.conf$" | grep -v "example" > /dev/null; then
  echo "⚠️  WARNING: .conf files detected (may contain secrets)"
  echo "Ensure these are example files only, not real config."
fi

if [ "$SECRETS_FOUND" = true ]; then
  echo ""
  echo "Continue with commit? (y/N)"
  # Ask user for confirmation
fi

# 4. Stage all changes (or selective staging based on user preference)
echo "📦 Staging changes..."
git add .

# 5. Generate commit message based on session activity
echo "✍️  Generating commit message..."

# Analyze changed files to determine commit type
COMMIT_TYPE="chore"
COMMIT_SCOPE=""
COMMIT_DESC=""

# Detect what was changed
if git diff --cached --name-only | grep -q "^tui/"; then
  COMMIT_TYPE="feat"
  COMMIT_SCOPE="tui"
  COMMIT_DESC="update TUI components"
elif git diff --cached --name-only | grep -q "^scripts/"; then
  COMMIT_TYPE="feat"
  COMMIT_SCOPE="scripts"
  COMMIT_DESC="update deployment scripts"
elif git diff --cached --name-only | grep -q "^docs/"; then
  COMMIT_TYPE="docs"
  COMMIT_SCOPE=""
  COMMIT_DESC="update documentation"
elif git diff --cached --name-only | grep -q "^ansible/"; then
  COMMIT_TYPE="feat"
  COMMIT_SCOPE="ansible"
  COMMIT_DESC="update Ansible playbooks"
elif git diff --cached --name-only | grep -q "\.md$"; then
  COMMIT_TYPE="docs"
  COMMIT_DESC="update documentation"
fi

# Build commit message following Conventional Commits spec
COMMIT_MSG="$COMMIT_TYPE"
if [ -n "$COMMIT_SCOPE" ]; then
  COMMIT_MSG="$COMMIT_MSG($COMMIT_SCOPE)"
fi
COMMIT_MSG="$COMMIT_MSG: $COMMIT_DESC"

# Add detailed body with file list
COMMIT_BODY=$(cat <<EOF

Changes:
$(git diff --cached --name-status | head -20)

Session: Claude Code $(date +%Y-%m-%d)
EOF
)

# Full commit message
FULL_COMMIT_MSG="$COMMIT_MSG

$COMMIT_BODY"

echo "Proposed commit message:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "$FULL_COMMIT_MSG"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 6. Ask user to review/edit commit message
echo "Press Enter to use this message, or type custom message:"
# Get user input

# 7. Create commit
git commit -m "$FULL_COMMIT_MSG"

# 8. Push to remote
echo "⬆️  Pushing to origin/main..."
git push origin main || {
  echo "❌ Push failed. Check network connection or remote repository."
  echo "Your changes are committed locally. Push manually when ready:"
  echo "  git push origin main"
  exit 1
}

echo "✅ Changes committed and pushed successfully!"
```

## Common Git Operations

### Create Feature Branch

When starting work on a major feature:

```bash
# Create and switch to feature branch
FEATURE_NAME="add-kubectl-integration"
git checkout -b "feature/$FEATURE_NAME"
git push -u origin "feature/$FEATURE_NAME"

echo "✅ Created feature branch: feature/$FEATURE_NAME"
echo "Work on this branch, then merge when complete"
```

### Handle Merge Conflicts

If conflicts occur during pull:

```bash
echo "⚠️  Merge conflicts detected. Resolving..."

# Show conflicted files
git status --short | grep "^UU"

echo "Please resolve conflicts in the files above, then:"
echo "  git add <resolved-files>"
echo "  git commit"
echo "  git push origin main"
```

### Stash Changes

If need to pull but have uncommitted work:

```bash
# Stash current changes
git stash push -m "Work in progress - $(date +%Y-%m-%d)"

# Pull latest
git pull --rebase origin main

# Re-apply stashed changes
git stash pop

echo "✅ Stashed changes re-applied. Review for conflicts."
```

### View Recent History

Show recent commits and changes:

```bash
# Last 10 commits with graph
git log --oneline --graph --decorate -10

# Changes in last commit
git show --stat

# Files changed in last 5 commits
git log --name-status -5
```

### Undo Last Commit (Keep Changes)

If committed too early:

```bash
git reset --soft HEAD~1
echo "✅ Last commit undone. Changes still staged."
```

### Check What Will Be Committed

Before committing:

```bash
# Show staged changes
git diff --cached

# Show unstaged changes
git diff

# Show all changes (staged + unstaged)
git diff HEAD
```

## Commit Message Convention

Follow Conventional Commits specification:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

### Scopes (for this repository):
- `tui`: TUI application changes
- `scripts`: Deployment script changes
- `ansible`: Ansible playbook changes
- `docs`: Documentation changes
- `config`: Configuration file changes

### Examples:

```
feat(tui): add SSH key auto-detection

Implemented smart SSH key detection that checks for homelab_rsa,
falls back to default keys, and offers to generate if none found.

Changes:
- Added ssh_manager.py with key detection logic
- Updated deployment wizard to use auto-detected keys
- Added tests for key detection

Session: Claude Code 2025-11-15
```

```
fix(scripts): correct Tailscale auth key expiration

Updated deploy-ubuntu-vm.sh to use new 90-day expiration auth key
instead of previous 7-day key.

Changes:
- scripts/deploy-ubuntu-vm.sh

Session: Claude Code 2025-11-15
```

```
docs: update TUI user guide with new features

Added section on SSH key auto-setup and Tailscale hostname
connection workflows.

Session: Claude Code 2025-11-15
```

## Security Checks

### Pre-commit Validation

Always check for these before committing:

1. **SSH Private Keys**
   - Pattern: `BEGIN (RSA|OPENSSH|EC) PRIVATE KEY`
   - Action: BLOCK commit, add to .gitignore

2. **Auth Tokens**
   - Pattern: `(password|secret|api[_-]?key|auth[_-]?token|tskey-auth)`
   - Action: WARN user, ask for confirmation

3. **Config Files**
   - Pattern: `*.conf` (except *.example.conf)
   - Action: WARN user, verify it's example only

4. **Environment Files**
   - Pattern: `.env`, `*.env`
   - Action: BLOCK commit, should be in .gitignore

5. **Large Files**
   - Pattern: Files > 10MB
   - Action: WARN user, suggest Git LFS or exclusion

### Secret Scanning Commands

```bash
# Scan staged files for secrets
git diff --cached | grep -iE "(password|secret|api[_-]?key|token)" || echo "No obvious secrets found"

# Check for SSH keys
git diff --cached | grep "BEGIN.*PRIVATE KEY" || echo "No private keys found"

# List large files being committed
git diff --cached --name-only | xargs ls -lh | awk '$5 ~ /M$/ {print $9, $5}'

# Scan entire repository history for secrets (if concerned)
git log -p | grep -iE "(password|secret|api[_-]?key)" | head -20
```

## Repository-Specific Rules

### For kapnode-deployments:

1. **Never commit real Tailscale auth keys**
   - Use placeholders in examples: `tskey-auth-XXXX`
   - Real keys should be passed via TUI input or env vars

2. **Never commit SSH private keys**
   - Only public keys in examples (if needed)
   - Private keys stay in `~/.ssh/`

3. **Never commit real inventory files**
   - Commit `inventory.example.yml` only
   - Real `inventory.yml` is gitignored

4. **Never commit real .conf files**
   - Commit `.example.conf` templates
   - Real configs are gitignored

5. **Always update DEPLOYMENT-FIXES-REPORT.md**
   - When fixing bugs in deployment scripts
   - Document what was fixed and why

## Integration with Other Skills

### With Documentation Skill

```bash
# After updating code, update docs
invoke-skill documentation-agent "Update TUI_USER_GUIDE.md with new SSH key auto-setup feature"

# Then commit both
git add tui/ docs/
git commit -m "feat(tui): add SSH key auto-setup with documentation"
```

### With Testing Skill

```bash
# Run tests before committing
invoke-skill testing-agent "Run all TUI unit tests"

# If tests pass, commit
git add .
git commit -m "feat(tui): add new feature with passing tests"
```

## Troubleshooting

### "fatal: refusing to merge unrelated histories"

```bash
# If repository was re-initialized
git pull --allow-unrelated-histories origin main
```

### "fatal: not a git repository"

```bash
# Initialize repository
git init
git remote add origin https://github.com/[username]/kapnode-deployments.git
git branch -M main
git push -u origin main
```

### "error: failed to push some refs"

```bash
# Pull with rebase first
git pull --rebase origin main
git push origin main
```

### Large uncommitted changes

```bash
# Commit in smaller logical chunks
git add tui/
git commit -m "feat(tui): add deployment wizard"

git add scripts/
git commit -m "feat(scripts): update Tailscale key"

git add docs/
git commit -m "docs: update documentation"

git push origin main
```

## Best Practices

1. **Commit frequently** - Small, focused commits are better than large ones
2. **Write clear messages** - Future you will thank present you
3. **Pull before push** - Always sync with remote before pushing
4. **Review before commit** - Use `git diff --cached` to review changes
5. **Don't commit secrets** - Use .gitignore and pre-commit checks
6. **Use branches for features** - Keep main branch stable
7. **Tag releases** - Use semantic versioning for major updates

## Summary

This skill ensures:
- ✅ Always working with latest code
- ✅ Changes are tracked and documented
- ✅ No secrets committed to repository
- ✅ Consistent commit message format
- ✅ Changes are safely pushed to remote
- ✅ Easy collaboration across Claude Code sessions

Invoke this skill with: `/git-workflow` or let it auto-trigger at session boundaries.
