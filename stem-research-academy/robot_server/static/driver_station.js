'use strict';
/* 3TSahur Driver Station. The robot's code is built into the server; this page
   only sends forward / strafe / turn, ramp commands, and stops. */

const $ = selector => document.querySelector(selector);
const $$ = selector => document.querySelectorAll(selector);
const headers = {'Content-Type': 'application/json', 'X-Robot-Token': window.ROBOT_TOKEN};
const WHEEL_LABELS = {front_left: 'Front left', front_right: 'Front right', rear_left: 'Rear left', rear_right: 'Rear right'};
const DRIVE_KEYS = new Set(['w', 'a', 's', 'd', 'q', 'e']);
const IDLE = {forward: 0, strafe: 0, rotate: 0};

let sequence = Date.now() * 1000;
let connected = false;
let enabled = false;
let rampState = 'released';
let rampBusy = false;
let padIndex = null;
let padButtons = [];
let cameraStarted = false;
const held = new Set();

async function api(url, body) {
  const options = body === undefined ? {cache: 'no-store'} : {method: 'POST', headers, body: JSON.stringify(body)};
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({error: `HTTP ${response.status}`}));
  if (!response.ok || data.ok === false) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function setSignal(id, state, text) {
  const signal = $(id);
  signal.className = `signal ${state || ''}`;
  signal.querySelector('strong').textContent = text;
}

/* Enable / disable ------------------------------------------------------------ */

function updateButtons() {
  $('#enableButton').disabled = !connected || enabled || !$('#armConfirm').checked;
  $$('[data-ramp]').forEach(button => { button.disabled = !enabled || rampBusy; });
  $('#rampNote').textContent = enabled ? 'R toggles the ramp. It keeps holding when you disable.' : 'Enable the robot to move the ramp.';
}

function setEnabled(value) {
  enabled = Boolean(value && connected);
  const state = $('#robotState');
  state.classList.toggle('enabled', enabled);
  state.querySelector('strong').textContent = enabled ? 'ENABLED' : 'DISABLED';
  state.querySelector('small').textContent = enabled ? 'Driver commands are live' : 'Driver commands are blocked';
  if (!enabled) softStop();
  updateButtons();
}

function softStop() {
  held.clear();
  paintKeys();
  fetch('/api/stop', {method: 'POST', headers, body: '{}', keepalive: true}).catch(() => {});
}

function emergencyStop() {
  $('#armConfirm').checked = false;
  enabled = false;
  setEnabled(false);
  fetch('/api/stop', {method: 'POST', headers, body: JSON.stringify({emergency: true}), keepalive: true}).catch(() => {});
}

/* Driving ---------------------------------------------------------------------- */

const axis = (positive, negative) => (held.has(positive) ? 1 : 0) - (held.has(negative) ? 1 : 0);
const deadzone = value => Math.abs(value) < 0.12 ? 0 : value;

function activePad() {
  if (typeof navigator.getGamepads !== 'function') return null;
  const pads = [...navigator.getGamepads()].filter(Boolean);
  if (!pads.length) { padIndex = null; return null; }
  const pad = pads.find(item => item.index === padIndex) || pads[0];
  padIndex = pad.index;
  return pad;
}

function axisRow(label, value) {
  const row = document.createElement('div');
  row.className = 'axis';
  const bar = document.createElement('div');
  bar.className = 'power-bar';
  const fill = document.createElement('i');
  paintBar(fill, value);
  bar.append(fill);
  const name = document.createElement('span');
  name.textContent = label;
  const out = document.createElement('output');
  out.textContent = value.toFixed(2);
  row.append(name, bar, out);
  return row;
}

function readPad() {
  const pad = activePad();
  if (!pad) {
    $('#padName').textContent = 'No game controller detected';
    $('#inputSummary').textContent = 'Keyboard';
    $('#axisList').replaceChildren();
    padButtons = [];
    return null;
  }
  const axes = pad.axes || [];
  const command = {forward: -deadzone(axes[1] || 0), strafe: deadzone(axes[0] || 0), rotate: -deadzone(axes[2] || 0)};
  $('#padName').textContent = (pad.id || 'Game controller').split('(')[0].trim() || 'Game controller';
  $('#inputSummary').textContent = 'Controller';
  $('#axisList').replaceChildren(axisRow('Forward', command.forward), axisRow('Strafe', command.strafe), axisRow('Turn', command.rotate));
  // Buttons act on the press, not while held: Y opens, A closes, B soft-stops.
  const pressed = (pad.buttons || []).map(button => Boolean(button && button.pressed));
  const edge = index => pressed[index] && !padButtons[index];
  if (enabled && edge(3)) setRamp('open');
  if (enabled && edge(0)) setRamp('closed');
  if (edge(1)) setEnabled(false);
  padButtons = pressed;
  return command.forward || command.strafe || command.rotate ? command : null;
}

async function sendDrive() {
  if (!enabled || !connected) return;
  const keys = {forward: axis('w', 's'), strafe: axis('d', 'a'), rotate: axis('q', 'e')};
  const keyboard = keys.forward || keys.strafe || keys.rotate;
  const command = keyboard ? keys : readPad() || IDLE;
  try {
    await api('/api/drive', {sequence: ++sequence, ...command, speed: Number($('#speed').value) / 100});
  } catch (_) {
    setEnabled(false);
  }
}

/* Ramp ------------------------------------------------------------------------- */

async function setRamp(state) {
  if (!enabled || rampBusy) return;
  rampBusy = true;
  updateButtons();
  try {
    const data = await api('/api/ramp', {state});
    renderRamp(data.ramp);
  } catch (error) {
    $('#rampNote').textContent = error.message;
  } finally {
    rampBusy = false;
    updateButtons();
  }
}

function renderRamp(ramp) {
  if (!ramp) return;
  rampState = ramp.state;
  const box = $('#rampState');
  const fault = Boolean(ramp.error);
  box.className = `ramp-state ${ramp.state === 'open' ? 'open' : ''} ${fault ? 'fault' : ''}`;
  const angle = ramp.state === 'open' ? ramp.open_angle : ramp.state === 'closed' ? ramp.closed_angle : null;
  box.querySelector('strong').textContent = fault ? 'Fault' : ramp.state;
  box.querySelector('small').textContent = fault ? 'Servo board not answering'
    : ramp.holding ? `Holding ${Number(angle).toFixed(0)}°`
    : ramp.state === 'manual' ? 'Set from Debug' : 'Servos released';
}

/* Status ----------------------------------------------------------------------- */

function paintBar(fill, value) {
  const magnitude = Math.min(1, Math.abs(value)) * 50;
  fill.style.width = `${magnitude}%`;
  fill.style.left = value < 0 ? `${50 - magnitude}%` : '50%';
  fill.classList.toggle('reverse', value < 0);
}

function renderWheels(robot) {
  for (const [wheel, info] of Object.entries(robot.wheels || {})) {
    const card = $(`[data-wheel="${wheel}"]`);
    if (!card) continue;
    if (!card.firstChild) {
      card.innerHTML = '<header><strong></strong><small></small></header><output>0%</output><div class="power-bar"><i></i></div>';
      card.querySelector('strong').textContent = WHEEL_LABELS[wheel];
    }
    const port = robot.ports?.[String(info.port)] || {};
    card.querySelector('small').textContent = `PORT ${info.port}${port.inverted ? ' · INV' : ''}`;
    card.querySelector('output').textContent = `${Math.round(info.power * 100)}%`;
    paintBar(card.querySelector('i'), info.power);
  }
  const command = robot.command || {};
  $('#cmdForward').textContent = (command.forward || 0).toFixed(2);
  $('#cmdStrafe').textContent = (command.strafe || 0).toFixed(2);
  $('#cmdRotate').textContent = (command.rotate || 0).toFixed(2);
  $('#cmdSpeed').textContent = `${$('#speed').value}%`;
}

const degrees = (value, suffix = '°') => Number.isFinite(value) ? `${Number(value).toFixed(1)}${suffix}` : '—';

function renderImu(imu) {
  const live = Boolean(imu && imu.connected);
  $('#imuStatus').textContent = !live ? 'Offline' : imu.simulated ? 'Simulated' : imu.calibrated ? 'Ready' : 'Calibrating';
  setSignal('#imuSignal', !live ? 'bad' : imu.calibrated && !imu.simulated ? 'good' : 'warn',
    !live ? 'Not detected' : imu.simulated ? 'Simulated' : imu.calibrated ? `BNO055 ${imu.address}` : 'Calibrating gyro');
  $('#imuYaw').textContent = degrees(imu?.yaw);
  $('#imuPitch').textContent = degrees(imu?.pitch);
  $('#imuRoll').textContent = degrees(imu?.roll);
  $('#imuRate').textContent = degrees(imu?.rate, '°/s');
  $('#headingDial').style.setProperty('--yaw', `${live && Number.isFinite(imu.yaw) ? imu.yaw : 0}deg`);
  $('#imuDetail').textContent = live
    ? 'Yaw is counter-clockwise positive. Zero heading with the robot facing forward.'
    : `No BNO055 answered at ${imu?.address || '0x28'}. ${imu?.error || ''}`;
  $('#zeroHeading').disabled = !live;
}

function connectCamera() {
  $('#cameraFeed').src = `/camera.mjpg?t=${Date.now()}`;
}

function renderCamera(camera) {
  const feed = $('#cameraFeed');
  if (!cameraStarted) {
    cameraStarted = true;
    // A dropped stream (USB unplugged, Wi-Fi hiccup) reconnects by itself.
    feed.addEventListener('error', () => setTimeout(connectCamera, 2000));
    connectCamera();
  }
  feed.hidden = !camera.available;
  $('#cameraEmpty').hidden = camera.available;
  $('#cameraName').textContent = camera.name || 'USB camera';
  $('#cameraMeta').textContent = camera.available ? `${camera.width}×${camera.height} · ${camera.fps} fps` : 'OFFLINE';
  if (!camera.available) {
    $('#cameraEmpty').querySelector('strong').textContent = camera.error ? 'Camera offline' : 'Waiting for camera';
    $('#cameraEmpty').querySelector('span').textContent = camera.error || 'The USB camera on the robot is found automatically.';
  }
  $$('#cameraProfiles button').forEach(button => button.classList.toggle('active', button.dataset.profile === camera.profile));
}

function markDisconnected() {
  connected = false;
  if (enabled) setEnabled(false);
  $('#connectionBanner').classList.add('visible');
  setSignal('#commsSignal', 'bad', 'Disconnected');
  updateButtons();
}

async function refreshStatus() {
  try {
    const data = await api('/api/status');
    const robot = data.robot;
    connected = true;
    $('#connectionBanner').classList.remove('visible');
    setSignal('#commsSignal', 'good', data.hostname || 'Connected');
    setSignal('#driveSignal', robot.hardware ? 'good' : 'warn', robot.hardware ? 'Pi GPIO · 4 ports' : 'Simulation');
    const board = robot.servo_board;
    setSignal('#servoSignal', !board.available ? 'bad' : board.fault || !board.outputs_enabled ? 'warn' : 'good',
      !board.available ? 'Not detected' : !board.outputs_enabled ? 'Outputs cut (OE)' : board.fault ? 'Write fault' : `PCA9685 ${board.address}`);
    $('#watchdogLabel').textContent = robot.watchdog_tripped ? 'Watchdog stopped motors' : `${robot.watchdog_ms} ms watchdog`;
    renderWheels(robot);
    renderImu(robot.imu);
    renderRamp(robot.ramp);
    renderCamera(data.camera);
  } catch (_) {
    markDisconnected();
  }
  updateButtons();
}

/* Keyboard --------------------------------------------------------------------- */

const keyName = event => event.key.length === 1 ? event.key.toLowerCase() : event.key;
function paintKeys() { $$('kbd[data-key]').forEach(key => key.classList.toggle('active', held.has(key.dataset.key))); }
function flash(key) {
  const node = $(`kbd[data-key="${key}"]`);
  if (!node) return;
  node.classList.add('active');
  setTimeout(() => node.classList.remove('active'), 180);
}

addEventListener('keydown', event => {
  const key = keyName(event);
  // Esc always works, even when disabled or while a control has focus.
  if (key === 'Escape') { event.preventDefault(); flash('Escape'); emergencyStop(); return; }
  if (['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement.tagName) && key !== ' ') return;
  if (key === ' ') { event.preventDefault(); flash(' '); setEnabled(false); return; }
  if (!enabled || event.repeat) return;
  if (key === 'r') { event.preventDefault(); flash('r'); setRamp(rampState === 'open' ? 'closed' : 'open'); return; }
  if (!DRIVE_KEYS.has(key)) return;
  event.preventDefault();
  held.add(key);
  paintKeys();
  sendDrive();
});
addEventListener('keyup', event => {
  const key = keyName(event);
  if (!DRIVE_KEYS.has(key)) return;
  held.delete(key);
  paintKeys();
  sendDrive();
});

/* Anything that takes the operator's attention away disables the robot. */
addEventListener('blur', () => setEnabled(false));
addEventListener('pagehide', softStop);
document.addEventListener('visibilitychange', () => { if (document.hidden) setEnabled(false); });
addEventListener('gamepaddisconnected', () => { padIndex = null; setEnabled(false); });

$('#armConfirm').addEventListener('change', () => { if (!$('#armConfirm').checked) setEnabled(false); updateButtons(); });
$('#enableButton').addEventListener('click', () => setEnabled(true));
$('#disableButton').addEventListener('click', () => setEnabled(false));
$('#killButton').addEventListener('click', emergencyStop);
$('#speed').addEventListener('input', () => { $('#speedValue').textContent = `${$('#speed').value}%`; });
$$('[data-ramp]').forEach(button => button.addEventListener('click', () => setRamp(button.dataset.ramp)));
$('#zeroHeading').addEventListener('click', () => api('/api/imu/zero', {}).then(data => renderImu(data.imu)).catch(() => {}));
$$('#cameraProfiles button').forEach(button => button.addEventListener('click', async () => {
  try { await api('/api/camera/profile', {profile: button.dataset.profile}); } catch (error) { $('#cameraMeta').textContent = error.message; }
}));

refreshStatus();
readPad();
setInterval(refreshStatus, 250);
setInterval(() => { if (!enabled) readPad(); }, 150);
setInterval(sendDrive, 80);
setInterval(() => { $('#clock').textContent = new Date().toLocaleTimeString([], {hour12: false}); }, 1000);
