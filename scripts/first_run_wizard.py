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
DEFAULT_REPO = "https://github.com/contentscoin/hermes-for-web.git"
FALLBACK_REPO = DEFAULT_REPO
DEFAULT_REPO_REF = "main"
# This commit contains the FMG-customized WebUI packaging fix. Keep it in sync
# with contentscoin/hermes-for-web main when cutting installer releases.
DEFAULT_EXPECTED_WEBUI_COMMIT = "cef6c20c93ba80f4682aa6c6f470055b18ffcbf9"
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


def hermes_config_path():
    return HERMES / "config.yaml"


def opencrab_configured():
    cfg = hermes_config_path()
    if not cfg.exists():
        return False
    text = cfg.read_text(errors='ignore')
    return 'mcp_servers:' in text and 'opencrab:' in text


def configure_opencrab_mcp(args):
    if args.skip_opencrab:
        return
    print('OpenCrab MCP: optional ontology evidence tools for Hermes/Paperclip. The endpoint may contain a key and will not be printed back.')
    url = '' if args.yes else ask('OpenCrab MCP endpoint URL (blank to configure later)', '', secret=True)
    if not url:
        return
    cfg = hermes_config_path()
    HERMES.mkdir(parents=True, exist_ok=True)
    if cfg.exists():
        text = cfg.read_text(errors='ignore')
        if 'mcp_servers:' in text and 'opencrab:' in text:
            print('OpenCrab MCP already appears in Hermes config; leaving existing local value unchanged.')
            return
        backup = cfg.with_suffix(cfg.suffix + f'.bak-{int(time.time())}')
        shutil.copy2(cfg, backup)
    else:
        text = ''
    block = '\n' if text and not text.endswith('\n') else ''
    if 'mcp_servers:' not in text:
        block += 'mcp_servers:\n'
    block += '  opencrab:\n    url: "' + url.replace('"', '\"') + '"\n    timeout: 180\n    connect_timeout: 60\n'
    cfg.write_text(text + block)
    print('Configured OpenCrab MCP in Hermes config (endpoint redacted). Restart Hermes gateway/agents for tool discovery.')


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
        'paperclip_workflow_control': 'available' if (Path(__file__).resolve().parent / 'paperclip_workflow_control.py').exists() else 'missing',
        'opencrab': 'configured' if opencrab_configured() else 'missing',
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


def clone_or_update(repo, install_dir, repo_ref=DEFAULT_REPO_REF, expected_commit=DEFAULT_EXPECTED_WEBUI_COMMIT):
    install_dir.parent.mkdir(parents=True, exist_ok=True)
    ref = repo_ref or DEFAULT_REPO_REF
    expected = (expected_commit or '').strip()
    if (install_dir/'.git').exists():
        print(f'Updating FMG-customized WebUI: {install_dir}')
        rc, out = run(['git','-C',str(install_dir),'remote','get-url','origin'])
        current_remote = out.strip() if rc == 0 else ''
        if current_remote != repo:
            print(f'Switching WebUI source to FMG repo: {repo}')
            rc, out = run(['git','-C',str(install_dir),'remote','set-url','origin',repo])
            if rc != 0:
                print(out)
                raise SystemExit('Could not update WebUI git remote')
        rc, out = run(['git','-C',str(install_dir),'fetch','--prune','origin',ref])
        print(out)
        if rc != 0:
            raise SystemExit('WebUI fetch failed')
        if ref == 'main':
            rc, out = run(['git','-C',str(install_dir),'checkout','-B','main','origin/main'])
        else:
            rc, out = run(['git','-C',str(install_dir),'checkout',ref])
        print(out)
        if rc != 0:
            raise SystemExit('WebUI checkout failed')
        target = f'origin/{ref}' if ref == 'main' else ref
        rc, out = run(['git','-C',str(install_dir),'reset','--hard',target])
        print(out)
        if rc != 0:
            raise SystemExit('WebUI update failed')
    else:
        print(f'Cloning FMG-customized WebUI: {repo} ({ref}) -> {install_dir}')
        rc, out = run(['git','clone','--branch',ref,repo,str(install_dir)])
        if rc != 0 and repo != FALLBACK_REPO:
            print('Primary repo clone failed; trying fallback repo.')
            rc, out = run(['git','clone','--branch',ref,FALLBACK_REPO,str(install_dir)])
        print(out)
        if rc != 0:
            raise SystemExit('WebUI clone failed')
    rc, head = run(['git','-C',str(install_dir),'rev-parse','HEAD'])
    if rc == 0:
        print(f'Installed WebUI commit: {head}')
        if expected and head != expected:
            raise SystemExit(f'Installed WebUI commit {head} does not match expected FMG commit {expected}. Rerun setup after installer update or check network/cache.')
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
    ap.add_argument('--repo-ref', default=DEFAULT_REPO_REF)
    ap.add_argument('--expected-webui-commit', default=DEFAULT_EXPECTED_WEBUI_COMMIT)
    ap.add_argument('--install-dir', default=str(DEFAULT_INSTALL_DIR))
    ap.add_argument('--skip-codex', action='store_true')
    ap.add_argument('--skip-telegram', action='store_true')
    ap.add_argument('--skip-paperclip', action='store_true')
    ap.add_argument('--skip-opencrab', action='store_true', help='skip OpenCrab MCP endpoint prompt')
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
    clone_or_update(args.repo, install_dir, args.repo_ref, args.expected_webui_commit)
    configure_integrations(args)
    configure_opencrab_mcp(args)
    codex_flow(args.skip_codex, args.yes)
    if which('hermes'):
        run(['hermes','doctor'], capture=False)
    if not args.no_start:
        start_webui(install_dir, args.port)
    print(json.dumps(status(args.port, install_dir), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
