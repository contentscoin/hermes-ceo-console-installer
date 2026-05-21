#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const mainPath = path.join(__dirname, '..', 'main.js');
const preloadPath = path.join(__dirname, '..', 'preload.js');
const setupHtmlPath = path.join(__dirname, '..', 'setup.html');
const setupJsPath = path.join(__dirname, '..', 'setup.js');
const text = fs.readFileSync(mainPath, 'utf8');
const preloadText = fs.readFileSync(preloadPath, 'utf8');
const setupHtmlText = fs.readFileSync(setupHtmlPath, 'utf8');
const setupJsText = fs.readFileSync(setupJsPath, 'utf8');

function assertIncludes(needle, message){
  if(!text.includes(needle)){
    throw new Error(`${message}: missing ${needle}`);
  }
}
function assertMatches(regex, message){
  if(!regex.test(text)){
    throw new Error(`${message}: ${regex}`);
  }
}
function assertTextIncludes(haystack, needle, message){
  if(!haystack.includes(needle)){
    throw new Error(`${message}: missing ${needle}`);
  }
}

assertIncludes('function paperclipHealth(', 'Paperclip health probe function should exist');
assertIncludes('async function startPaperclipServer(', 'Paperclip start/recovery function should exist');
assertIncludes("ipcMain.handle('start-paperclip-server'", 'Renderer IPC handler should expose Paperclip start');
assertIncludes("label:'Paperclip 서버 시작/복구'", 'Top Hermes menu should include Paperclip start/recovery item');
assertMatches(/paperclipai\s+run\s+--instance\s+default/, 'Paperclip launch command should use paperclipai run --instance default');
assertMatches(/http:\/\/127\.0\.0\.1:3100\/api\/health/, 'Paperclip health URL should target local trusted Paperclip');
assertMatches(/paperclip.*log/i, 'Paperclip start path should write to a Paperclip log');
assertTextIncludes(preloadText, 'startPaperclipServer', 'Preload should expose Paperclip server starter to setup UI');
assertTextIncludes(preloadText, "ipcRenderer.invoke('start-paperclip-server')", 'Preload should call the Paperclip IPC channel');
assertTextIncludes(setupHtmlText, 'id="paperclip"', 'Setup screen should show a Paperclip recovery button');
assertTextIncludes(setupJsText, "$('paperclip').onclick", 'Setup screen Paperclip button should call desktop bridge');
assertTextIncludes(setupJsText, 'FMG-customized Paperclip은 설치/업데이트하고 로컬 서버를 시작합니다', 'Setup guide should state Paperclip is installed and started by quick setup');

console.log('desktop-menu-paperclip-tests-ok');
