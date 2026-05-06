#!/usr/bin/env python3
"""First-run setup wizard for Hermes CEO Console.
Secret-safe: never prints token values back to stdout.
"""
from __future__ import annotations
import argparse, getpass, json, os, platform, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

HOME = Path.home()
HERMES = HOME / ".hermes"
ENV = HERMES / ".env"
DEFAULT_REPO = "https://github.com/contentscoin/hermes-for-web-ceo-console.git"
FALLBACK_REPO = "https://github.com/reallygood83/hermes-for-web.git"
DEFAULT_INSTALL_DIR = HERMES / "webui" / "workspace" / "hermes-for-web"


def run(cmd, check=False, capture=True, shell=False):
    try:
        if capture:
            p = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=check, shell=shell)
            return p.returncode, (p.stdout or '').strip()
        p = subprocess.run(cmd, check=check, shell=shell)
        return p.returncode, ''
    except Exception as e:
        return 127, str(e)


def which(name):
    return shutil.which(name) or ""


def ask(prompt, default="", secret=False, yes=False):
    if yes:
        return default
    suffix = f" [{default}]" if default else ""
    if secret:
        return getpass.getpass(prompt + suffix + ": ").strip() or default
    return input(prompt + suffix + ": ").strip() or default


def read_env():
    data = {}
    if ENV.exists():
        for line in ENV.read_text(errors='ignore').splitlines():
            if not line or line.lstrip().startswith('#') or '=' not in line:
                continue
            k, v = line.split('=', 1)
            data[k.strip()] = v.strip().strip('"').strip("'")
    return data


def write_env(updates):
    HERMES.mkdir(parents=True, exist_ok=True)
    old_lines = ENV.read_text(errors='ignore').splitlines() if ENV.exists() else []
    keys = set(updates)
    out = []
    seen = set()
    for line in old_lines:
        if '=' in line and not line.lstrip().startswith('#'):
            k = line.split('=',1)[0].strip()
            if k in updates:
                v = updates[k]
                if v:
                    out.append(f'{k}="{v}"')
                else:
                    out.append(line)
                seen.add(k)
            else:
                out.append(line)
        else:
            out.append(line)
    if out and out[-1].strip():
        out.append('')
    for k, v in updates.items():
        if k not in seen and v:
            out.append(f'{k}="{v}"')
    ENV.write_text('\n'.join(out).rstrip()+"\n")


def health(port):
    try:
        with urllib.request.urlopen(f'http://127.0.0.1:{port}/health', timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def status(port, install_dir):
    env = read_env()
    codex_ok = bool(which('codex'))
    # Login status is provider-dependent; version means installed, not authenticated.
    st = {
        'os': platform.platform(),
        'python': sys.version.split()[0],
        'git': bool(which('git')),
        'curl': bool(which('curl')),
        'hermes': bool(which('hermes')),
        'codex_cli': codex_ok,
        'webui_dir': str(install_dir),
        'webui_dir_exists': install_dir.exists(),
        'webui_health': health(port),
        'webui_url': f'http://127.0.0.1:{port}',
        'telegram': 'configured' if env.get('TELEGRAM_BOT_TOKEN') else 'missing',
        'paperclip': 'configured' if env.get('PAPERCLIP_BASE_URL') and env.get('PAPERCLIP_DEFAULT_COMPANY') else 'missing',
        'paperclip_web_url': env.get('PAPERCLIP_WEB_URL') or 'http://127.0.0.1:3100',
        'codex': 'installed_login_unverified' if codex_ok else 'missing',
        'secrets_redacted': True,
    }
    return st


def install_hermes_if_missing(yes, skip_update=False):
    if which('hermes'):
        print('Hermes CLI: found')
        if skip_update:
            print('Hermes update: skipped')
            return
        run(['hermes','update'], capture=False)
        return
    print('Hermes CLI: missing')
    if yes or ask('Install Hermes Agent now? y/N', 'y').lower().startswith('y'):
        cmd = 'curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash'
        rc, out = run(cmd, capture=False, shell=True)
        if rc != 0:
            print('Hermes install failed. Please run the official installer manually.', file=sys.stderr)


def clone_or_update(repo, install_dir):
    install_dir.parent.mkdir(parents=True, exist_ok=True)
    if (install_dir/'.git').exists():
        print(f'Updating WebUI: {install_dir}')
        rc, out = run(['git','-C',str(install_dir),'pull','--ff-only'])
        print(out)
    else:
        print(f'Cloning WebUI: {repo} -> {install_dir}')
        rc, out = run(['git','clone',repo,str(install_dir)])
        if rc != 0 and repo != FALLBACK_REPO:
            print('Primary repo clone failed; trying fallback public repo.')
            rc, out = run(['git','clone',FALLBACK_REPO,str(install_dir)])
        print(out)
        if rc != 0:
            raise SystemExit('WebUI clone failed')
    if (install_dir/'start.sh').exists():
        (install_dir/'start.sh').chmod(0o755)


def configure_integrations(args):
    updates = {}
    if not args.skip_paperclip:
        web_url = ask('Paperclip web URL for WebUI live tab', 'http://127.0.0.1:3100', yes=args.yes)
        base = ask('Paperclip API/base URL for MCP work (blank to skip)', '', yes=args.yes)
        company = ask('Paperclip default company', 'FMG', yes=args.yes)
        token = '' if args.yes else ask('Paperclip API token if required (blank to skip)', '', secret=True)
        if web_url: updates['PAPERCLIP_WEB_URL'] = web_url
        if base: updates['PAPERCLIP_BASE_URL'] = base
        if company: updates['PAPERCLIP_DEFAULT_COMPANY'] = company
        if token: updates['PAPERCLIP_API_TOKEN'] = token
    if not args.skip_telegram:
        print('Telegram: create a bot with https://t.me/BotFather or use an existing token.')
        token = '' if args.yes else ask('Telegram bot token (blank to skip)', '', secret=True)
        chats = ask('Telegram allowed chat IDs, comma-separated (blank to configure later)', '', yes=args.yes)
        if token: updates['TELEGRAM_BOT_TOKEN'] = token
        if chats: updates['TELEGRAM_ALLOWED_CHATS'] = chats
    if updates:
        write_env(updates)
        print(f'Updated {ENV} (secret values redacted).')


def codex_flow(skip, yes):
    if skip:
        return
    if not which('codex'):
        print('Codex CLI not found. Install it first, then rerun wizard. Common options: npm i -g @openai/codex or official Codex CLI instructions.')
        return
    print('Codex CLI found.')
    if not yes and ask('Run codex login now? y/N','y').lower().startswith('y'):
        run(['codex','login'], capture=False)


def start_webui(install_dir, port):
    if health(port):
        print(f'WebUI already healthy: http://127.0.0.1:{port}')
        return
    log = HERMES / 'logs' / 'hermes-ceo-console.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    if platform.system() == 'Windows':
        cmd = [sys.executable, 'server.py', '--port', str(port)]
    else:
        cmd = ['./start.sh', str(port)] if (install_dir/'start.sh').exists() else [sys.executable, 'server.py', '--port', str(port)]
    print('Starting WebUI...')
    with log.open('ab') as f:
        subprocess.Popen(cmd, cwd=str(install_dir), stdout=f, stderr=subprocess.STDOUT)
    for _ in range(20):
        if health(port):
            print(f'WebUI healthy: http://127.0.0.1:{port}')
            return
        time.sleep(1)
    print(f'WebUI health check failed. See log: {log}')


def main():
    ap = argparse.ArgumentParser(description='Hermes CEO Console first-run setup wizard')
    ap.add_argument('--yes', action='store_true', help='use non-secret defaults; skip interactive secret prompts')
    ap.add_argument('--port', type=int, default=8788)
    ap.add_argument('--repo', default=DEFAULT_REPO)
    ap.add_argument('--install-dir', default=str(DEFAULT_INSTALL_DIR))
    ap.add_argument('--skip-codex', action='store_true')
    ap.add_argument('--skip-telegram', action='store_true')
    ap.add_argument('--skip-paperclip', action='store_true')
    ap.add_argument('--skip-hermes-update', action='store_true', help='do not run hermes update when Hermes CLI already exists')
    ap.add_argument('--no-start', action='store_true')
    ap.add_argument('--status-json', action='store_true')
    args = ap.parse_args()
    install_dir = Path(os.path.expanduser(args.install_dir))
    if args.status_json:
        print(json.dumps(status(args.port, install_dir), ensure_ascii=False, indent=2))
        return
    print('Hermes CEO Console setup wizard')
    install_hermes_if_missing(args.yes, args.skip_hermes_update)
    clone_or_update(args.repo, install_dir)
    configure_integrations(args)
    codex_flow(args.skip_codex, args.yes)
    if which('hermes'):
        run(['hermes','doctor'], capture=False)
    if not args.no_start:
        start_webui(install_dir, args.port)
    print(json.dumps(status(args.port, install_dir), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
