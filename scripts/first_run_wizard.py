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
# This commit contains the FMG-customized WebUI Research Intake safety ladder dashboard package. Keep it in sync
# with contentscoin/hermes-for-web main when cutting installer releases.
DEFAULT_EXPECTED_WEBUI_COMMIT = "e3e593dc2dc526dedcd8fa0b66ed13f858d65b09"
DEFAULT_INSTALL_DIR = HERMES / "webui" / "workspace" / "hermes-for-web"
DEFAULT_PAPERCLIP_REPO = "https://github.com/paperclipai/paperclip.git"
DEFAULT_PAPERCLIP_REPO_REF = "master"
# FMG-customized Paperclip commit with Live Workflow DAG, OpenCrab plugin, and legacy issue blank-page fix.
DEFAULT_EXPECTED_PAPERCLIP_COMMIT = "9aea3e3d35fe47a745857b91c392da5b3fc0ae17"
DEFAULT_PAPERCLIP_INSTALL_DIR = HERMES / "webui" / "workspace" / "paperclip"
DEFAULT_PAPERCLIP_PORT = 3100


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



def neo4j_env_status():
    env = read_env()
    uri = env.get('NEO4J_URI') or ''
    user = env.get('NEO4J_USER') or ''
    database = env.get('NEO4J_DATABASE') or 'neo4j'
    write_enabled = str(env.get('NEO4J_WRITE_ENABLED') or '').lower() in ('1', 'true', 'yes', 'on')
    return {
        'configured': bool(uri and user),
        'uri_present': bool(uri),
        'user_present': bool(user),
        'password_present': bool(env.get('NEO4J_PASSWORD')),
        'database': database,
        'write_enabled': write_enabled,
    }


def neo4j_reachable(uri=''):
    # Credential-free readiness probe only. Bolt auth/queries are intentionally not attempted here.
    uri = (uri or '').strip()
    if not uri:
        uri = 'bolt://127.0.0.1:7687'
    try:
        import socket
        target = uri.split('://', 1)[-1].split('/', 1)[0]
        host, _, port_text = target.partition(':')
        port = int(port_text or 7687)
        with socket.create_connection((host or '127.0.0.1', port), timeout=1.5):
            return True
    except Exception:
        return False


def configure_neo4j(args):
    if args.skip_neo4j:
        return
    print('Neo4j: optional local/external graph store for reviewed ontology packs. Installer never writes graph data automatically.')
    updates = {}
    if args.yes:
        updates.setdefault('NEO4J_WRITE_ENABLED', 'false')
        if updates:
            write_env(updates)
        return
    uri = ask('Neo4j URI (blank to configure later)', '', secret=False)
    if uri:
        updates['NEO4J_URI'] = uri
        user = ask('Neo4j user', 'neo4j')
        password = ask('Neo4j password (blank to skip)', '', secret=True)
        database = ask('Neo4j database', 'neo4j')
        updates['NEO4J_USER'] = user
        if password:
            updates['NEO4J_PASSWORD'] = password
        updates['NEO4J_DATABASE'] = database or 'neo4j'
    updates['NEO4J_WRITE_ENABLED'] = 'false'
    if updates:
        write_env(updates)
        print(f'Updated {ENV} with Neo4j settings (password redacted, writes disabled).')


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
        'paperclip_dir': str(DEFAULT_PAPERCLIP_INSTALL_DIR),
        'paperclip_dir_exists': DEFAULT_PAPERCLIP_INSTALL_DIR.exists(),
        'paperclip_health': paperclip_health(DEFAULT_PAPERCLIP_PORT),
        'paperclip_expected_commit': DEFAULT_EXPECTED_PAPERCLIP_COMMIT,
        'paperclip_workflow_control': 'available' if (Path(__file__).resolve().parent / 'paperclip_workflow_control.py').exists() else 'missing',
        'opencrab': 'configured' if opencrab_configured() else 'missing',
        'neo4j': neo4j_env_status(),
        'neo4j_reachable': neo4j_reachable(env.get('NEO4J_URI') or ''),
        'codex': 'installed_login_unverified' if codex_ok else 'missing',
        'secrets_redacted': True,
    }
    return st


def hermes_cli_info():
    exe = which('hermes')
    if not exe:
        return {'found': False}
    rc, version = run(['hermes', '--version'])
    src = HERMES / 'hermes-agent'
    info = {'found': True, 'path': exe, 'version': version if rc == 0 else 'unknown'}
    if (src / '.git').exists():
        rc, head = run(['git', '-C', str(src), 'rev-parse', 'HEAD'])
        if rc == 0:
            info['source_commit'] = head.strip()
        rc, remote = run(['git', '-C', str(src), 'remote', 'get-url', 'origin'])
        if rc == 0:
            info['source_remote'] = remote.strip()
    return info


def print_hermes_cli_info(prefix='Hermes CLI'):
    info = hermes_cli_info()
    if not info.get('found'):
        print(f'{prefix}: missing')
        return info
    print(f"{prefix}: found at {info.get('path')}")
    print(f"{prefix} version output: {info.get('version')}")
    if info.get('source_remote'):
        print(f"{prefix} source remote: {info.get('source_remote')}")
    if info.get('source_commit'):
        print(f"{prefix} source commit: {info.get('source_commit')}")
    if 'v0.14.0' not in str(info.get('version')):
        print('Hermes version note: this installer targets Hermes Agent v0.14.0; use the source commit plus WebUI/Paperclip commits to verify freshness.')
    return info


def install_hermes_if_missing(yes, skip_update=False):
    if which('hermes'):
        print_hermes_cli_info()
        if skip_update:
            print('Hermes update: skipped by installer flag')
            return
        print('Hermes update: running hermes update')
        run(['hermes','update'], capture=False)
        print_hermes_cli_info('Hermes CLI after update')
        return
    print('Hermes CLI: missing')
    if yes or ask('Install Hermes Agent now? y/N', 'y').lower().startswith('y'):
        cmd = 'curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash'
        rc, out = run(cmd, capture=False, shell=True)
        if rc != 0:
            print('Hermes install failed. Please run the official installer manually.', file=sys.stderr)
        print_hermes_cli_info('Hermes CLI after install')


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


def http_health(url, path='/api/health'):
    try:
        with urllib.request.urlopen(url.rstrip('/') + path, timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def paperclip_health(port=DEFAULT_PAPERCLIP_PORT):
    return http_health(f'http://127.0.0.1:{port}', '/api/health')


def node_major():
    rc, out = run(['node', '--version'])
    if rc != 0:
        return 0
    s = out.strip().lstrip('v')
    try:
        return int(s.split('.', 1)[0])
    except Exception:
        return 0


def bash_login(cmd):
    return run(['bash', '-lc', cmd])


def ensure_node20_and_pnpm():
    if node_major() >= 20 and which('pnpm'):
        return
    print('Paperclip runtime: installing/checking Node.js 20 and pnpm 9.15.4 via nvm/corepack if needed.')
    cmd = """
set -e
export NVM_DIR="$HOME/.nvm"
if [ ! -s "$NVM_DIR/nvm.sh" ]; then
  curl -fsSL https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
fi
. "$NVM_DIR/nvm.sh"
nvm install 20
nvm alias default 20
nvm use 20
corepack enable
corepack prepare pnpm@9.15.4 --activate
node --version
pnpm --version
"""
    rc, out = bash_login(cmd)
    print(out)
    if rc != 0:
        raise SystemExit('Paperclip runtime prerequisite install failed')


def clone_or_update_git_project(label, repo, install_dir, repo_ref, expected_commit):
    install_dir.parent.mkdir(parents=True, exist_ok=True)
    if (install_dir / '.git').exists():
        print(f'Updating {label}: {install_dir}')
        rc, out = run(['git', '-C', str(install_dir), 'remote', 'get-url', 'origin'])
        if rc != 0 or out.strip() != repo:
            print(f'Switching {label} source to: {repo}')
            rc, out = run(['git', '-C', str(install_dir), 'remote', 'set-url', 'origin', repo])
            if rc != 0:
                print(out)
                raise SystemExit(f'{label} remote update failed')
        rc, out = run(['git', '-C', str(install_dir), 'fetch', '--prune', 'origin', repo_ref])
        print(out)
        if rc != 0:
            raise SystemExit(f'{label} fetch failed')
        target = f'origin/{repo_ref}'
        if repo_ref in ('main', 'master'):
            rc, out = run(['git', '-C', str(install_dir), 'checkout', '-B', repo_ref, target])
        else:
            local_branch = repo_ref.replace('/', '-')
            rc, out = run(['git', '-C', str(install_dir), 'checkout', '-B', local_branch, target])
        print(out)
        if rc != 0:
            raise SystemExit(f'{label} checkout failed')
        rc, out = run(['git', '-C', str(install_dir), 'reset', '--hard', target])
        print(out)
        if rc != 0:
            raise SystemExit(f'{label} reset failed')
    else:
        print(f'Cloning {label}: {repo} ({repo_ref}) -> {install_dir}')
        rc, out = run(['git', 'clone', '--branch', repo_ref, repo, str(install_dir)])
        print(out)
        if rc != 0:
            raise SystemExit(f'{label} clone failed')
    rc, head = run(['git', '-C', str(install_dir), 'rev-parse', 'HEAD'])
    if rc == 0:
        print(f'Installed {label} commit: {head}')
        if expected_commit and head.strip() != expected_commit:
            raise SystemExit(f'Installed {label} commit {head.strip()} does not match expected FMG commit {expected_commit}.')
    return install_dir


def install_or_update_paperclip(args):
    if args.skip_paperclip:
        print('Paperclip install/update: skipped by installer flag')
        return
    install_dir = Path(os.path.expanduser(args.paperclip_install_dir))
    clone_or_update_git_project('FMG-customized Paperclip', args.paperclip_repo, install_dir, args.paperclip_repo_ref, args.expected_paperclip_commit)
    ensure_node20_and_pnpm()
    print('Paperclip runtime: installing dependencies with pnpm. First run can take several minutes.')
    cmd = f"""
set -e
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 20 >/dev/null
cd {str(install_dir)!r}
corepack enable >/dev/null 2>&1 || true
corepack prepare pnpm@9.15.4 --activate >/dev/null 2>&1 || true
pnpm install --frozen-lockfile
"""
    rc, out = bash_login(cmd)
    print(out)
    if rc != 0:
        raise SystemExit('Paperclip dependency install failed')
    if not args.no_start:
        start_paperclip(install_dir, args.paperclip_port)


def start_paperclip(install_dir, port=DEFAULT_PAPERCLIP_PORT):
    if paperclip_health(port):
        print(f'Paperclip already healthy: http://127.0.0.1:{port}')
        return
    log = HERMES / 'logs' / 'paperclip-fmg.log'
    log.parent.mkdir(parents=True, exist_ok=True)
    command = f"""
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm use 20 >/dev/null
cd {str(install_dir)!r}
exec pnpm paperclipai run --instance default
"""
    print('Starting FMG Paperclip...')
    with log.open('ab') as f:
        subprocess.Popen(['bash', '-lc', command], stdout=f, stderr=subprocess.STDOUT)
    for _ in range(45):
        if paperclip_health(port):
            print(f'Paperclip healthy: http://127.0.0.1:{port}')
            return
        time.sleep(1)
    print(f'Paperclip health check failed. See log: {log}')


def configure_integrations(args):
    updates = {}
    if not args.skip_paperclip:
        web_url = ask('Paperclip web URL for WebUI live tab', 'http://127.0.0.1:3100', yes=args.yes)
        base = ask('Paperclip API/base URL for MCP work', 'http://127.0.0.1:3100', yes=args.yes)
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
    ap.add_argument('--paperclip-repo', default=DEFAULT_PAPERCLIP_REPO)
    ap.add_argument('--paperclip-repo-ref', default=DEFAULT_PAPERCLIP_REPO_REF)
    ap.add_argument('--expected-paperclip-commit', default=DEFAULT_EXPECTED_PAPERCLIP_COMMIT)
    ap.add_argument('--paperclip-install-dir', default=str(DEFAULT_PAPERCLIP_INSTALL_DIR))
    ap.add_argument('--paperclip-port', type=int, default=DEFAULT_PAPERCLIP_PORT)
    ap.add_argument('--skip-codex', action='store_true')
    ap.add_argument('--skip-telegram', action='store_true')
    ap.add_argument('--skip-paperclip', action='store_true')
    ap.add_argument('--skip-opencrab', action='store_true', help='skip OpenCrab MCP endpoint prompt')
    ap.add_argument('--skip-neo4j', action='store_true', help='skip Neo4j optional config/readiness check')
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
    install_or_update_paperclip(args)
    configure_opencrab_mcp(args)
    configure_neo4j(args)
    codex_flow(args.skip_codex, args.yes)
    if which('hermes'):
        run(['hermes','doctor'], capture=False)
    if not args.no_start:
        start_webui(install_dir, args.port)
    print(json.dumps(status(args.port, install_dir), ensure_ascii=False, indent=2))

if __name__ == '__main__':
    main()
