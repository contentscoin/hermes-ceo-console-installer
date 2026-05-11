const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const mode = params.get('mode') || 'unknown';
const port = params.get('port') || '8788';
const dir = params.get('dir') || '~/.hermes/webui/workspace/hermes-for-web';
function setStatus(s){ $('status').textContent = s; }
function setMeta(){ $('meta').textContent = `WebUI: http://127.0.0.1:${port}\nInstall dir: ${dir}\nLog: ~/.hermes/logs/hermes-ceo-console.log`; }
const setupGuide = [
  'CMD/PowerShell 창이 열리면:',
  '1. 이 창은 FMG 제공 WebUI를 설치/업데이트하고 바로 실행하는 quick setup입니다.',
  '2. SmartScreen 또는 권한 요청이 나오면 실행/허용을 선택하세요.',
  '3. WSL2/Ubuntu가 없으면 installer가 Ubuntu 설치를 자동으로 시도합니다. 관리자 권한/재부팅 요청이 나오면 허용하세요.',
  '4. Ubuntu 첫 실행 시에는 Ubuntu 사용자 이름과 비밀번호를 한 번 만들어야 합니다.',
  '5. Codex/Telegram/Paperclip 설정 질문은 여기서 기본적으로 건너뜁니다. WebUI가 열린 뒤 설정에서 진행하세요.',
  '6. 완료 메시지가 나오면 이 앱으로 돌아와 “다시 확인”을 누르세요.',
  '7. 오류가 보이면 CMD 창을 닫지 말고 마지막 오류 줄과 로그 경로를 확인하세요.',
].join('\n');
function api(){
  if(window.hermesDesktop) return window.hermesDesktop;
  setStatus('Desktop bridge가 준비되지 않았습니다. 앱을 다시 열거나 설치 파일을 다시 실행하세요.');
  return null;
}
async function callDesktop(action, fallback){
  const desktop = api();
  if(!desktop || typeof desktop[action] !== 'function') return fallback;
  try { return await desktop[action](); }
  catch(err){
    setStatus(`작업 중 오류가 발생했습니다: ${err && err.message ? err.message : err}`);
    return fallback;
  }
}
function applyMode(){
  setMeta();
  if(mode === 'starting-existing'){
    $('title').textContent = '기존 세팅 감지됨 — 앱 시작 중';
    $('lead').innerHTML = `이미 Hermes WebUI 설치 경로가 있어 <code>localhost:${port}</code> 서버를 자동으로 시작하고 있습니다. 잠시 후 앱 화면으로 전환됩니다.`;
    setStatus('기존 설치를 시작하는 중입니다. 30초 이상 걸리면 로그를 확인하거나 “다시 확인”을 누르세요.');
    $('setup').classList.add('secondary');
    $('start').classList.remove('secondary');
  } else if(mode === 'existing-failed'){
    $('title').textContent = '기존 세팅 시작 실패';
    $('lead').innerHTML = `설치 경로는 감지됐지만 <code>localhost:${port}</code>가 아직 응답하지 않습니다.`;
    setStatus('로그를 확인한 뒤 “기존 세팅으로 앱 시작” 또는 “다시 확인”을 눌러주세요. 설정이 깨졌다면 Setup Wizard를 다시 실행하세요.');
    $('setup').classList.add('secondary');
    $('start').classList.remove('secondary');
  } else if(mode === 'first-run'){
    $('title').textContent = '처음 설치 / 초기 설정 필요';
    $('lead').innerHTML = `이 장비에는 아직 Hermes CEO Console 런타임이 감지되지 않았습니다. Setup Wizard를 열면 FMG 제공 WebUI를 설치/업데이트하고 바로 실행합니다. Codex, Telegram, Paperclip 같은 상세 설정은 WebUI가 열린 뒤 진행합니다.`;
    setStatus(`“처음 설치 / Setup Wizard”를 누르면 CMD/PowerShell 창이 열립니다.\n\n${setupGuide}`);
    $('start').classList.add('secondary');
  } else {
    $('title').textContent = 'Hermes CEO Console 상태 확인';
    setStatus('상태를 확인하려면 “다시 확인”을 누르세요.');
  }
}
$('setup').onclick = async () => {
  setStatus(`Setup Wizard를 CMD/PowerShell 창으로 여는 중입니다.\n\n${setupGuide}`);
  const result = await callDesktop('runSetup', {started:false});
  if(result && result.started){
    const modeText = result.mode === 'windows-cmd-launcher' ? '명령 프롬프트 창' : (result.mode === 'windows-visible-powershell' ? 'PowerShell 창' : '터미널');
    const manual = result.launcher ? `\n\n새 창이 보이지 않으면 아래 파일을 직접 더블클릭하세요:\n${result.launcher}` : '';
    setStatus(`Setup Wizard를 ${modeText}으로 열었습니다.\n\n${setupGuide}\n\n새 창이 보이지 않으면 작업표시줄/보안 경고를 확인하세요.\n\nInstaller: ${result.script || '(unknown)'}${manual}\n\n설치가 끝나면 “다시 확인”을 누르세요.`);
  } else {
    const manual = result && result.launcher ? `\n직접 실행 파일: ${result.launcher}` : '';
    setStatus(`Setup Wizard를 시작하지 못했습니다.\n원인: ${(result && result.error) || 'unknown'}${result && result.detail ? `\n상세: ${result.detail}` : ''}\nInstaller: ${(result && result.script) || '(unknown)'}${manual}\n로그 또는 설치파일 위치를 확인하세요.`);
  }
};
$('start').onclick = async () => {
  setStatus('기존 WebUI 런타임을 시작하는 중입니다...');
  const result = await callDesktop('startExisting', {started:false, healthy:false});
  if(result && result.healthy){ setStatus('WebUI가 준비됐습니다. 앱 화면으로 전환합니다.'); await callDesktop('retry', false); }
  else if(result && result.started) setStatus('시작 명령은 실행됐지만 아직 준비되지 않았습니다. 잠시 후 “다시 확인”을 누르거나 로그를 확인하세요.');
  else setStatus('기존 설치 경로를 찾지 못했습니다. 처음 설치 / Setup Wizard를 진행하세요.');
};
$('retry').onclick = async () => { setStatus(`localhost:${port} 상태를 다시 확인합니다...`); const ok = await callDesktop('health', false); if(ok){ setStatus('WebUI가 준비됐습니다. 앱 화면으로 전환합니다.'); await callDesktop('retry', false); } else { await callDesktop('retry', false); } };
$('logs').onclick = () => callDesktop('openLogs', false);
$('browser').onclick = () => callDesktop('openWebui', false);
applyMode();
callDesktop('runtimeStatus', null).then(st => {
  if(st) $('meta').textContent = `WebUI: ${st.webUrl}\nInstall dir: ${st.webuiDir}\nLog: ${st.logPath}\nRuntime exists: ${st.runtimeExists}\nHealthy: ${st.healthy}`;
});
