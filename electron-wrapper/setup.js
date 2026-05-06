const $ = id => document.getElementById(id);
const params = new URLSearchParams(location.search);
const mode = params.get('mode') || 'unknown';
const port = params.get('port') || '8788';
const dir = params.get('dir') || '~/.hermes/webui/workspace/hermes-for-web';
function setStatus(s){ $('status').textContent = s; }
function setMeta(){ $('meta').textContent = `WebUI: http://127.0.0.1:${port}\nInstall dir: ${dir}\nLog: ~/.hermes/logs/hermes-ceo-console.log`; }
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
    $('lead').innerHTML = `이 장비에는 아직 Hermes CEO Console 런타임이 감지되지 않았습니다. Setup Wizard를 열어 Hermes Agent, WebUI, Codex, Telegram, Paperclip 설정을 순서대로 진행하세요.`;
    setStatus('“처음 설치 / Setup Wizard”를 누르면 터미널이 열립니다. 터미널 안내에 따라 초기 설정을 완료한 뒤 여기서 “다시 확인”을 누르세요.');
    $('start').classList.add('secondary');
  } else {
    $('title').textContent = 'Hermes CEO Console 상태 확인';
    setStatus('상태를 확인하려면 “다시 확인”을 누르세요.');
  }
}
$('setup').onclick = async () => {
  setStatus('Setup Wizard를 터미널로 여는 중입니다. 터미널에서 초기 설정을 완료한 뒤 “다시 확인”을 누르세요.');
  const result = await window.hermesDesktop.runSetup();
  if(!result || !result.started) setStatus('Setup Wizard를 시작하지 못했습니다. 로그 또는 설치파일 위치를 확인하세요.');
};
$('start').onclick = async () => {
  setStatus('기존 WebUI 런타임을 시작하는 중입니다...');
  const result = await window.hermesDesktop.startExisting();
  if(result && result.healthy){ setStatus('WebUI가 준비됐습니다. 앱 화면으로 전환합니다.'); await window.hermesDesktop.retry(); }
  else if(result && result.started) setStatus('시작 명령은 실행됐지만 아직 준비되지 않았습니다. 잠시 후 “다시 확인”을 누르거나 로그를 확인하세요.');
  else setStatus('기존 설치 경로를 찾지 못했습니다. 처음 설치 / Setup Wizard를 진행하세요.');
};
$('retry').onclick = async () => { setStatus(`localhost:${port} 상태를 다시 확인합니다...`); const ok = await window.hermesDesktop.health(); if(ok){ setStatus('WebUI가 준비됐습니다. 앱 화면으로 전환합니다.'); await window.hermesDesktop.retry(); } else { await window.hermesDesktop.retry(); } };
$('logs').onclick = () => window.hermesDesktop.openLogs();
$('browser').onclick = () => window.hermesDesktop.openWebui();
applyMode();
