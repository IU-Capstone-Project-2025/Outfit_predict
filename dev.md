# Development recomendations
Before pushing new commit, check that you created new branch for feature/fix/ and so on. Also take attention that the branch name is `[type]/[name of feature etc.]` for example `fix/backend-dependecies`

## ⚙️  Pre-commit Hook Quick Start

### 1 · Create & activate a virtual environment

```bash
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 2 · Install dev dependencies

```bash
pip install -r requirements-dev.txt     # or:  pip install pre-commit commitizen
```

### 3 · Install the Git hooks

```bash
# All pre-commit & pre-push hooks
pre-commit install
# Commit-message hook for Conventional Commits
pre-commit install --hook-type commit-msg
```

### 4 · Lint everything once (helpful before your first PR)

```bash
pre-commit run --all-files
```

### 5 · Make commits *through* Commitizen

Use the interactive prompt so commit messages always follow Conventional Commits:

```bash
cz c          # or:  cz commit
```

### 6 · Updating hooks

```bash
pre-commit autoupdate   # pull latest tagged versions
pre-commit clean        # rebuild isolated hook environments
```

---

## FAQ

| Question                                              | Answer                                                                                                                                                         |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Do I need to install flake8/black/mypy myself?**    | Not strictly—`pre-commit` downloads the exact versions it needs into its own cache. Install them in your venv only if you want IDE integration or manual runs. |
| **A file was auto-formatted during commit—what now?** | `pre-commit` already re-added the file (`git add`). Just review `git status`, amend if needed, and finish the commit.                                          |
| **How do I skip hooks for a one-off commit?**         | `git commit --no-verify` (use sparingly).                                                                                                                      |
| **How do I bump tool versions?**                      | Run `pre-commit autoupdate`, commit the updated `rev:` hashes.                                                                                                 |

---

### Hook Summary

| Category               | Hooks                                                                                             |
| ---------------------- | ------------------------------------------------------------------------------------------------- |
| **Styling/Formatters** | `black`, `isort`, `prettier`                                                                      |
| **Linters**            | `flake8`,                                                                                         |
| **Type Checks**        | `mypy`                                                                                            |
| **Security**           | `gitleaks`,                                                                                       |
| **Repo Hygiene**       | `end-of-file-fixer`, `trailing-whitespace`, `check-yaml`, `check-added-large-files`, `nbstripout` |
| **Git workflow**       | `commitizen`                                                                                      |
