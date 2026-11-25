let laptopStream = null;
let ws = null;
let voiceRec = null;

async function postJSON(url, body={}) {
  const res = await fetch(url, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
  const data = await res.json().catch(()=>({}));
  if (!res.ok) throw new Error(data.error || JSON.stringify(data));
  return data;
}

function updateBadge(state) {
  const b = document.getElementById('statusBadge');
  b.className = 'badge ' + (state.mode === 'ALARM' || state.mode === 'EMERGENCY' ? 'alarm' : state.unlocked ? 'unlocked' : 'locked');
  b.textContent = `${state.mode} ${state.unlocked ? 'UNLOCKED' : 'LOCKED'}`;
}

function fmt(x, digits=2) {
  if (x === null || x === undefined || Number.isNaN(Number(x))) return 'N/A';
  return Number(x).toFixed(digits);
}

function updateDashboard(state) {
  const t = state.telemetry || {};
  const speed = Number(t.speed || 0);
  const speedMpm = t.speedMpm !== undefined ? Number(t.speedMpm) : speed * 60;
  document.getElementById('dashSpeed').textContent = `${fmt(speed,2)} m/s`;
  document.getElementById('dashSpeedMpm').textContent = `${fmt(speedMpm,1)} m/min`;
  document.getElementById('dashDist').textContent = t.dist > 0 ? `${fmt(t.dist,1)} cm` : 'N/A';
  document.getElementById('dashIR').textContent = t.ir ? 'BLOCK' : 'CLEAR';
  document.getElementById('dashMotorBat').textContent = t.motorBatV !== undefined ? `${fmt(t.motorBatV,2)}V / ${fmt(t.motorBatPct,0)}%` : 'N/A';
  const camAngleEl = document.getElementById('dashCamAngle');
  const usAngleEl = document.getElementById('dashUsAngle');
  if (camAngleEl) camAngleEl.textContent = t.camAngle !== undefined ? `${t.camAngle}°` : 'N/A';
  if (usAngleEl) usAngleEl.textContent = t.usAngle !== undefined ? `${t.usAngle}°` : 'N/A';
  const p = state.pipower5 || {};
  if (p.available) {
    const src = p.power_source === 1 ? 'BAT' : 'EXT';
    const chg = p.charging === 1 ? ' charging' : '';
    document.getElementById('dashPiBat').textContent = `${p.battery_percent}% ${src}${chg}`;
  } else {
    document.getElementById('dashPiBat').textContent = 'N/A';
  }
}

function connectWS() {
  ws = new WebSocket(`ws://${location.host}/ws`);
  ws.onmessage = (ev) => {
    const state = JSON.parse(ev.data);
    updateBadge(state);
    updateDashboard(state);
    document.getElementById('telemetry').textContent = JSON.stringify(state, null, 2);
  };
  ws.onclose = () => setTimeout(connectWS, 1500);
}
connectWS();

async function startLaptopCamera() {
  laptopStream = await navigator.mediaDevices.getUserMedia({video: {width: 640, height: 480}, audio: false});
  document.getElementById('laptopCam').srcObject = laptopStream;
  document.getElementById('faceMsg').textContent = 'Laptop camera OK';
}

function captureFaceImage() {
  const video = document.getElementById('laptopCam');
  const canvas = document.getElementById('faceCanvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.82);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function registerFace() {
  if (!laptopStream) await startLaptopCamera();
  const name = document.getElementById('faceName').value.trim();
  if (!name) { alert('Nhập tên trước khi đăng ký mặt.'); return; }
  const imgs = [];
  document.getElementById('faceMsg').textContent = `Đang lấy mẫu khuôn mặt cho ${name}...`;
  for (let i=0; i<18; i++) {
    imgs.push(captureFaceImage());
    await sleep(120);
  }
  const data = await postJSON('/api/face/register', {name, images: imgs});
  document.getElementById('faceMsg').textContent = data.message || JSON.stringify(data);
  loadEvents();
  loadFaces();
}

async function verifyFace() {
  if (!laptopStream) await startLaptopCamera();
  const img = captureFaceImage();
  try {
    const data = await postJSON('/api/face/verify', {image: img});
    document.getElementById('faceMsg').textContent = data.ok ? `Mở khóa OK: ${data.name} distance=${data.distance?.toFixed?.(3)}` : JSON.stringify(data);
  } catch(e) {
    document.getElementById('faceMsg').textContent = 'Verify error: ' + e.message;
  }
  loadEvents();
}

async function loadFaces() {
  const res = await fetch('/api/faces');
  const data = await res.json();
  const box = document.getElementById('facesList');
  if (!data.users || data.users.length === 0) {
    box.innerHTML = '<p>Chưa có khuôn mặt nào được lưu.</p>';
    return;
  }
  box.innerHTML = data.users.map(u => `<div class="faceItem"><b>${u.name}</b> (${u.template_count} samples) <button onclick="deleteFace(${u.id})">Xóa</button></div>`).join('');
}

async function deleteFace(id) {
  if (!confirm('Xóa khuôn mặt đã lưu này?')) return;
  await fetch(`/api/faces/${id}`, {method:'DELETE'});
  loadFaces();
  loadEvents();
}
loadFaces();

function getSpeed() {
  return Number(document.getElementById('speedRange').value || 120);
}
function updateSpeedLabel() {
  document.getElementById('speedLabel').textContent = getSpeed();
}
updateSpeedLabel();

async function lockCar() { await postJSON('/api/lock'); }
async function beepTest() { await postJSON('/api/beep', {ms: Number(document.getElementById('beepMs')?.value || 100)}).catch(()=>postJSON('/api/beep', {ms:100})); }
async function drive(l, r) { try { await postJSON('/api/drive', {left:l, right:r}); } catch(e) { alert(e.message); } }
async function stopCar() { await postJSON('/api/stop'); }
async function laneAI() { await postJSON('/api/ai/lane'); }
async function parkAI() { await postJSON('/api/ai/park'); }
async function roamAI() { await postJSON('/api/ai/roam'); }

function manualDrive(dir) {
  const s = getSpeed();
  if (dir === 'forward') return drive(s, s);
  if (dir === 'back') return drive(-s, -s);
  if (dir === 'left') return drive(-Math.round(s*0.8), Math.round(s*0.8));
  if (dir === 'right') return drive(Math.round(s*0.8), -Math.round(s*0.8));
}


async function setServo(target, angle) {
  angle = Number(angle);
  await postJSON('/api/servo', {target, angle});
}
function updateServoLabels() {
  const cam = document.getElementById('camServoRange')?.value || 90;
  const us = document.getElementById('usServoRange')?.value || 90;
  const camLabel = document.getElementById('camServoLabel');
  const usLabel = document.getElementById('usServoLabel');
  if (camLabel) camLabel.textContent = cam + '°';
  if (usLabel) usLabel.textContent = us + '°';
}
async function setCamServoFromSlider() {
  updateServoLabels();
  await setServo('CAM', document.getElementById('camServoRange').value);
}
async function setUsServoFromSlider() {
  updateServoLabels();
  await setServo('US', document.getElementById('usServoRange').value);
}
async function look(where) {
  await postJSON(`/api/look/${where}`);
  const cam = document.getElementById('camServoRange');
  const us = document.getElementById('usServoRange');
  const angle = where === 'left' ? 150 : where === 'right' ? 30 : 90;
  if (cam) cam.value = angle;
  if (us) us.value = angle;
  updateServoLabels();
}
setTimeout(updateServoLabels, 0);

async function loadEvents() {
  const res = await fetch('/api/events?limit=80');
  const data = await res.json();
  const tbody = document.getElementById('eventsBody');
  tbody.innerHTML = '';
  for (const e of data.events) {
    const d = new Date(e.ts * 1000).toLocaleString();
    let img = '';
    if (e.image_path) {
      const name = e.image_path.split('/').pop();
      img = `<a href="/api/failed_face/${name}" target="_blank">open</a>`;
    }
    tbody.innerHTML += `<tr><td>${d}</td><td>${e.event}</td><td>${e.detail || ''}</td><td>${img}</td></tr>`;
  }
}
loadEvents();

function includesAny(text, words) {
  return words.some(w => text.includes(w));
}

function handleVoice(text, lang) {
  text = text.toLowerCase();
  document.getElementById('voiceText').textContent = `Voice ${lang}: ` + text;
  const s = getSpeed();
  if (includesAny(text, ['tiến', 'đi thẳng', '前', 'まえ', '進んで', '進め', 'まっすぐ'])) manualDrive('forward');
  else if (includesAny(text, ['lùi', 'バック', '後ろ', 'うしろ', '下がって'])) manualDrive('back');
  else if (includesAny(text, ['trái', '左', 'ひだり'])) manualDrive('left');
  else if (includesAny(text, ['phải', '右', 'みぎ'])) manualDrive('right');
  else if (includesAny(text, ['dừng', 'stop', '止まれ', '停止', 'ストップ'])) stopCar();
  else if (includesAny(text, ['nhìn trái', 'camera trái', '左を見て', '左見て'])) look('left');
  else if (includesAny(text, ['nhìn phải', 'camera phải', '右を見て', '右見て'])) look('right');
  else if (includesAny(text, ['nhìn giữa', 'camera giữa', '正面', 'まんなか', '中央'])) look('center');
  else if (includesAny(text, ['bám đường', 'line', 'ライン', '線をたどって', 'ライントレース'])) laneAI();
  else if (includesAny(text, ['tự di chuyển', 'tự chạy', 'đi xung quanh', '自動運転', '巡回', 'うろうろ', '探検'])) roamAI();
  else if (includesAny(text, ['tự đỗ', 'đỗ xe', '駐車', '駐車して'])) parkAI();
  else if (includesAny(text, ['khóa', 'ロック', '施錠'])) lockCar();
}

function startVoice(lang='vi-VN') {
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) { alert('Trình duyệt không hỗ trợ Web Speech API. Dùng Chrome/Edge trên laptop.'); return; }
  if (voiceRec) {
    try { voiceRec.stop(); } catch(e) {}
    voiceRec = null;
  }
  const rec = new SpeechRecognition();
  rec.lang = lang;
  rec.continuous = true;
  rec.interimResults = false;
  postJSON('/api/voice_mode').catch(()=>{});
  rec.onresult = (ev) => {
    const text = ev.results[ev.results.length-1][0].transcript;
    handleVoice(text, lang);
  };
  rec.onerror = (e) => console.log(e);
  rec.start();
  voiceRec = rec;
}
