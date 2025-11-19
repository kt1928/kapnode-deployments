# Code Review: Kapnode Deployment TUI

## ✅ Positive observations
- The new Textual-based screens cover the expected user flows (deploy, update, history) and the UI layout code is reasonably organized.
- SSH, inventory, and configuration helpers are broken out into dedicated modules, which will make future testing and reuse easier.

## 🚫 Blocking issues

1. **Hard-coded Tailscale auth key checked into version control**
   - `ConfigManager._get_default_config` returns what appears to be a live `tskey-auth-*` key so every fresh install will write that secret into `~/.homelab-deploy.conf`.【F:tui/lib/config_manager.py†L79-L124】
   - Because the TUI auto-loads this configuration, anyone who clones the repo immediately gets the same credential, and cloud-init then writes it into every VM image. This is a serious secret-leak that could let anyone join your tailnet or exhaust the auth key quota.
   - 🔧 **Fix**: Replace the real key with a placeholder and require the user to provide their own key (ideally via environment variable or prompt). Consider integrating a secret-store instead of embedding it in source.

2. **Command injection / quoting vulnerabilities when constructing the deployment command**
   - `ScriptExecutor.prepare_deployment` concatenates user-controlled fields directly into the shell command (e.g., hostname, DNS, Tailscale key, SSH public key) without any quoting or escaping besides wrapping a few values in single quotes.【F:tui/lib/script_executor.py†L21-L86】
   - Any single quote or shell metacharacter in a field (think `node && rm -rf /`) will break the command string and execute arbitrary commands on the Proxmox host as root, since the script runs over SSH as `root@kapmox`.
   - 🔧 **Fix**: Build the command with `shlex.quote` for every argument or, even better, execute the script via Paramiko's `exec_command` while passing a JSON/ENV payload rather than shell concatenation.

3. **Packaged CLI cannot run because `deploy_node.py` is not part of the build**
   - `pyproject.toml` declares a console script entry point `deploy-node = "deploy_node:main"`, but the `[tool.setuptools]` section only packages the `components`, `screens`, and `lib` packages. The top-level module `deploy_node.py` is never included in the wheel/sdist, so installing the project yields `ModuleNotFoundError: No module named 'deploy_node'` when the entrypoint runs.【F:tui/pyproject.toml†L51-L61】
   - 🔧 **Fix**: add `py_modules = ["deploy_node"]` (or turn the app into a proper package) and verify `pip install .` works by running the generated console script.

## ⚠️ Additional observations
- The cloud-init template in `deploy-ubuntu-vm.sh` stores the Tailscale auth key in plain text on disk and inside `/var/lib/vz/snippets`, so rotating to ephemeral keys sooner rather than later would be safer.
- `LogViewerScreen` still pushes Textual screens from inside an `@work` coroutine, which is not thread-safe; consider scheduling UI updates back on the main thread with `self.app.call_from_thread`.

## ✅ Tests executed
- `python -m compileall tui`【8b46fe†L1-L21】
