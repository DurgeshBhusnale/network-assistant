# Developer setup (Windows + WSL2 Ubuntu)

All development happens inside WSL2 Ubuntu, with the repo in the Linux filesystem (`~/code/networking-assistant`), never under `/mnt/c` or `/mnt/d` (slow file watching, line-ending and permission problems).

## 1. Windows side (PowerShell as Administrator)

```powershell
wsl --install -d Ubuntu-24.04      # reboot if asked, then open "Ubuntu 24.04" and create your Linux user
wsl --set-default Ubuntu-24.04
wsl --update
```

Docker Desktop (Windows):
1. Install or update Docker Desktop.
2. Settings → General → **Use the WSL 2 based engine**: on.
3. Settings → Resources → WSL integration → enable **Ubuntu-24.04**. Apply & restart.
4. Give it at least 6 GB memory (Supabase local runs ~10 containers).

## 2. Ubuntu side (inside the Ubuntu terminal)

```bash
# Base tools: make, git, compilers, curl
sudo apt update && sudo apt install -y build-essential make git curl unzip ca-certificates

# Docker check (Docker Desktop's WSL integration provides the CLI)
docker version && docker compose version

# Node 24 LTS via fnm, then pnpm via corepack (the version is pinned in package.json "packageManager")
curl -fsSL https://fnm.vercel.app/install | bash
source ~/.bashrc
fnm install 24 && fnm default 24
corepack enable

# uv (Python manager); it installs Python 3.12 for the project on first `uv sync`
curl -LsSf https://astral.sh/uv/install.sh | sh
source ~/.bashrc

# Supabase CLI: latest Linux release from GitHub
SUPABASE_VERSION=$(curl -fsSL https://api.github.com/repos/supabase/cli/releases/latest | grep -oP '"tag_name": "v\K[^"]+')
curl -fsSL -o /tmp/supabase.deb \
  "https://github.com/supabase/cli/releases/download/v${SUPABASE_VERSION}/supabase_${SUPABASE_VERSION}_linux_amd64.deb"
sudo apt install -y /tmp/supabase.deb

# GitHub CLI
(type -p wget >/dev/null || sudo apt install -y wget) \
  && sudo mkdir -p -m 755 /etc/apt/keyrings \
  && wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null \
  && sudo chmod go+r /etc/apt/keyrings/githubcli-archive-keyring.gpg \
  && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null \
  && sudo apt update && sudo apt install -y gh
gh auth login            # GitHub.com → HTTPS → login with browser

# Git identity (same as on Windows)
git config --global user.name "DurgeshBhusnale"
git config --global user.email "<your email>"
git config --global core.autocrlf input
git config --global init.defaultBranch main
```

Verify:

```bash
make --version | head -1; node -v; pnpm -v; uv --version; supabase --version; gh --version | head -1; docker ps
```

## 3. Get the repo into Linux

Once the GitHub repo exists and `main` is pushed:

```bash
mkdir -p ~/code && cd ~/code
gh repo clone <owner>/networking-assistant
cd networking-assistant
git switch sprint-0/foundations
make setup
make dev
```

Until then you can clone straight from the Windows copy: `git clone /mnt/d/networking-assistant ~/code/networking-assistant`, then `git remote set-url origin <github url>` once it exists.

Open it in VS Code with the **WSL** extension: `code .` from the Ubuntu terminal.

## 4. Testing on an Android phone

PWA install and service workers need HTTPS or `localhost`, so a LAN IP won't do. Use USB port forwarding:

1. Phone: Developer options → USB debugging on; connect by USB.
2. Desktop Chrome → `chrome://inspect/#devices` → **Port forwarding** → `3000` → `localhost:3000` → enable.
3. Phone Chrome → `http://localhost:3000`. The web app proxies `/api/*` to the API, so only port 3000 is needed.

WSL2 forwards `localhost:3000` to Windows by default, so Chrome on Windows reaches the dev server.
