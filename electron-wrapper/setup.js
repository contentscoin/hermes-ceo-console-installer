const $ = id => document.getElementById(id);
function setStatus(s){ $('status').textContent = s; }
$('setup').onclick = async () => { setStatus('Setup wizard started. Follow terminal or system prompts, then click Retry.'); await window.hermesDesktop.runSetup(); };
$('retry').onclick = async () => { setStatus('Checking localhost:8788...'); const ok = await window.hermesDesktop.health(); if(ok){ setStatus('Healthy. Opening WebUI...'); await window.hermesDesktop.retry(); } else setStatus('Still not ready. Run setup or open logs.'); };
$('logs').onclick = () => window.hermesDesktop.openLogs();
$('browser').onclick = () => window.hermesDesktop.openWebui();
