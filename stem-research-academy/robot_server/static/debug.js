'use strict';
/* 3TSahur Debug page: map motor ports and servo channels, run single outputs,
   and read the servo board and IMU. Nothing here needs code uploads. */

const $ = selector => document.querySelector(selector);
const $$ = selector => document.querySelectorAll(selector);
const headers = {'Content-Type': 'application/json', 'X-Robot-Token': window.ROBOT_TOKEN};
const clone = value => JSON.parse(JSON.stringify(value));

let config = null;
let saved = null;
let draft = null;
let status = null;
let connected = false;
let selectedChannel = 0;
let holdTimer = null;
let saveError = '';

async function api(url, body) {
  const options = body === undefined ? {cache: 'no-store'} : {method: 'POST', headers, body: JSON.stringify(body)};
  const response = await fetch(url, options);
  const data = await response.json().catch(() => ({error: `HTTP ${response.status}`}));
  if (!response.ok || data.ok === false) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}

function setSignal(id, state, text) {
  const signal = $(id);
  signal.className = `signal ${state || ''}`;
  signal.querySelector('strong').textContent = text;
}

const dirty = () => Boolean(draft && saved && JSON.stringify(draft) !== JSON.stringify(saved));
const confirmed = () => $('#safeConfirm').checked;
const wheelLabel = id => config.wheels.find(wheel => wheel.id === id)?.label || id;
const wheelOnPort = port => Object.keys(draft.wheels).find(wheel => draft.wheels[wheel] === port) || '';

function showError(message) {
  saveError = message;
  renderSaveBar();
}

/* Hold-to-run ------------------------------------------------------------------ */

function stopHold() {
  if (!holdTimer) return;
  clearInterval(holdTimer);
  holdTimer = null;
  $$('.button.hold').forEach(button => button.classList.remove('active'));
  fetch('/api/stop', {method: 'POST', headers, body: '{}', keepalive: true}).catch(() => {});
}

function startHold(button, port, power) {
  stopHold();
  if (!confirmed()) { showError('Tick the safety check above before running a motor.'); return; }
  button.classList.add('active');
  const send = () => api('/api/debug/motor', {port, power, confirmed: true}).catch(error => { stopHold(); showError(error.message); });
  send();
  holdTimer = setInterval(send, 100);
}

function holdButton(label, getTarget) {
  const button = element('button', 'button hold', label);
  button.type = 'button';
  const begin = event => { event.preventDefault(); const [port, power] = getTarget(); startHold(button, port, power); };
  button.addEventListener('pointerdown', begin);
  ['pointerup', 'pointerleave', 'pointercancel'].forEach(type => button.addEventListener(type, stopHold));
  button.addEventListener('keydown', event => { if ((event.key === ' ' || event.key === 'Enter') && !event.repeat) begin(event); });
  button.addEventListener('keyup', event => { if (event.key === ' ' || event.key === 'Enter') stopHold(); });
  return button;
}

/* Motor ports -------------------------------------------------------------------- */

function assignWheel(port, wheel) {
  // Swapping keeps the map valid: the wheel's old port takes this port's old wheel.
  const previousWheel = wheelOnPort(port);
  if (wheel && wheel !== previousWheel) {
    const previousPort = draft.wheels[wheel];
    draft.wheels[wheel] = port;
    if (previousWheel) draft.wheels[previousWheel] = previousPort;
  }
  renderAll();
}

function renderPorts() {
  const grid = $('#portGrid');
  grid.replaceChildren(...config.ports.map(port => {
    const card = element('article', 'port-card');
    card.dataset.port = port.port;
    const changed = draft.wheels && (wheelOnPort(port.port) !== Object.keys(saved.wheels).find(w => saved.wheels[w] === port.port)
      || draft.inverted[String(port.port)] !== saved.inverted[String(port.port)]);
    card.classList.toggle('dirty', Boolean(changed));

    const head = element('header');
    head.append(element('h3', null, `Port ${port.port}`), element('small', null, port.label));
    const pins = element('div', 'pins',
      `FWD GPIO${port.forward_gpio} · pin ${port.forward_physical}\nREV GPIO${port.reverse_gpio} · pin ${port.reverse_physical}`);
    pins.style.whiteSpace = 'pre-line';

    const field = element('label', 'field', 'Drives wheel');
    const select = element('select');
    for (const wheel of config.wheels) {
      const option = element('option', null, wheel.label);
      option.value = wheel.id;
      select.append(option);
    }
    select.value = wheelOnPort(port.port);
    select.addEventListener('change', () => assignWheel(port.port, select.value));
    field.append(select);

    const invert = element('label', 'toggle-row');
    const box = element('input');
    box.type = 'checkbox';
    box.checked = Boolean(draft.inverted[String(port.port)]);
    box.addEventListener('change', () => { draft.inverted[String(port.port)] = box.checked; renderAll(); });
    invert.append(element('span', null, 'Invert direction'), box);

    const live = element('div', 'live');
    const bar = element('div', 'power-bar');
    bar.append(element('i'));
    live.append(bar, element('output', null, '0%'));

    const test = element('div', 'test-row');
    const range = element('label', 'range-label');
    const out = element('output', null, '20%');
    const label = element('span', null, 'Test power ');
    label.append(out);
    const slider = element('input');
    Object.assign(slider, {type: 'range', min: -config.debug_motor_limit * 100, max: config.debug_motor_limit * 100, step: 5, value: 20});
    slider.addEventListener('input', () => { out.textContent = `${slider.value}%`; });
    range.append(label, slider);
    test.append(range, holdButton('Hold to run', () => [port.port, Number(slider.value) / 100]));

    card.append(head, pins, field, invert, live, test);
    return card;
  }));
}

function renderWheelCheck() {
  const locked = dirty();
  $('#wheelCheck').replaceChildren(...config.wheels.map(wheel => {
    const port = saved.wheels[wheel.id];
    const button = holdButton(`${wheel.label} ▲ · port ${port}`, () => [saved.wheels[wheel.id], 0.25]);
    button.disabled = locked;
    button.title = locked ? 'Save your changes to test by wheel' : 'Hold: this wheel should roll the robot forward';
    return button;
  }));
}

/* Servos ------------------------------------------------------------------------- */

function rampRoleFor(channel) {
  const entry = Object.entries(draft.ramp.servos).find(([, servo]) => servo.channel === channel);
  return entry ? config.ramp_servos.find(servo => servo.id === entry[0])?.label : '';
}

function renderChannels() {
  // Tiles are built once and updated in place, so a click never lands on a
  // tile that the 300 ms status poll has just replaced.
  const grid = $('#channelGrid');
  if (grid.children.length !== config.servo.channels) {
    grid.replaceChildren(...Array.from({length: config.servo.channels}, (_, channel) => {
      const tile = element('button', 'channel');
      tile.type = 'button';
      tile.append(element('b', null, String(channel)), element('small'));
      tile.addEventListener('click', () => { selectedChannel = channel; $('#selectedChannel').textContent = channel; renderChannels(); });
      return tile;
    }));
  }
  const pulses = status?.robot?.servo_board?.pulses || {};
  [...grid.children].forEach((tile, channel) => {
    const pulse = pulses[String(channel)];
    const role = rampRoleFor(channel);
    tile.classList.toggle('held', pulse != null);
    tile.classList.toggle('selected', channel === selectedChannel);
    tile.querySelector('small').textContent = pulse != null ? `${Math.round(pulse)} µs` : role || 'free';
    tile.title = role || `Channel ${channel}`;
  });
}

function assignRampChannel(name, channel) {
  const other = Object.keys(draft.ramp.servos).find(key => key !== name && draft.ramp.servos[key].channel === channel);
  if (other) draft.ramp.servos[other].channel = draft.ramp.servos[name].channel;
  draft.ramp.servos[name].channel = channel;
  renderAll();
}

function renderRamp() {
  const pulses = status?.robot?.servo_board?.pulses || {};
  $('#rampGrid').replaceChildren(...config.ramp_servos.map(servo => {
    const settings = draft.ramp.servos[servo.id];
    const card = element('div', 'ramp-card');
    const field = element('label', 'field', 'Servo channel');
    const select = element('select');
    for (let channel = 0; channel < config.servo.channels; channel += 1) {
      const option = element('option', null, `Channel ${channel}`);
      option.value = channel;
      select.append(option);
    }
    select.value = settings.channel;
    select.addEventListener('change', () => assignRampChannel(servo.id, Number(select.value)));
    field.append(select);
    const mirror = element('label', 'toggle-row');
    const box = element('input');
    box.type = 'checkbox';
    box.checked = settings.reversed;
    box.addEventListener('change', () => { settings.reversed = box.checked; renderAll(); });
    mirror.append(element('span', null, 'Mirrored'), box);
    const holding = element('small', 'note');
    holding.dataset.rampLive = servo.id;
    card.append(element('strong', null, servo.label), field, mirror, holding);
    return card;
  }));
  const bind = (id, key, integer) => {
    const input = $(id);
    if (document.activeElement !== input) input.value = draft.ramp[key];
    input.onchange = () => {
      const value = Number(input.value);
      if (Number.isFinite(value)) draft.ramp[key] = integer ? Math.round(value) : value;
      renderAll();
    };
  };
  bind('#rampClosed', 'closed_angle', false);
  bind('#rampOpen', 'open_angle', false);
  bind('#rampMin', 'min_pulse_us', true);
  bind('#rampMax', 'max_pulse_us', true);
  $$('[data-ramp]').forEach(button => { button.disabled = dirty(); });
  updateRampLive();
}

function updateRampLive() {
  const pulses = status?.robot?.servo_board?.pulses || {};
  $$('[data-ramp-live]').forEach(node => {
    const pulse = pulses[String(draft.ramp.servos[node.dataset.rampLive].channel)];
    node.textContent = pulse != null ? `Holding ${Math.round(pulse)} µs` : 'Not holding';
  });
  const ramp = status?.robot?.ramp;
  if (ramp) $('#rampNote').textContent = ramp.error
    ? ramp.error
    : `Ramp is ${ramp.state}. A mirrored servo turns the opposite way so both sides match. Save before testing.`;
}

/* Status ------------------------------------------------------------------------- */

const degrees = (value, suffix = '°') => Number.isFinite(value) ? `${Number(value).toFixed(1)}${suffix}` : '—';

function renderStatus() {
  if (!status) return;
  const robot = status.robot;
  setSignal('#gpioSignal', robot.hardware ? 'good' : 'warn', robot.hardware ? 'Pi GPIO · ports 1–4' : 'Simulation (no GPIO)');
  const board = robot.servo_board;
  setSignal('#servoSignal', !board.available ? 'bad' : board.fault || !board.outputs_enabled ? 'warn' : 'good',
    !board.available ? `No answer at ${board.address}` : !board.outputs_enabled ? 'Outputs cut (OE high)' : board.fault ? 'Write fault' : `PCA9685 ${board.address}`);
  $('#servoBoardLabel').textContent = board.available ? `PCA9685 ${board.address}` : 'Not detected';
  $('#oeToggle').textContent = board.outputs_enabled ? 'Cut outputs (OE)' : 'Enable outputs (OE)';
  setSignal('#watchdogSignal', robot.watchdog_tripped ? 'warn' : 'good',
    robot.watchdog_tripped ? 'Stopped stale motors' : robot.watchdog_armed ? 'Armed · motors running' : `${robot.watchdog_ms} ms · idle`);

  for (const card of $$('.port-card')) {
    const port = robot.ports[card.dataset.port];
    if (!port) continue;
    const fill = card.querySelector('.power-bar i');
    const magnitude = Math.min(1, Math.abs(port.value)) * 50;
    fill.style.width = `${magnitude}%`;
    fill.style.left = port.value < 0 ? `${50 - magnitude}%` : '50%';
    fill.classList.toggle('reverse', port.value < 0);
    card.querySelector('.live output').textContent = `${Math.round(port.value * 100)}%`;
  }

  const imu = robot.imu;
  const live = Boolean(imu?.connected);
  setSignal('#imuSignal', !live ? 'bad' : imu.simulated ? 'warn' : imu.calibrated ? 'good' : 'warn',
    !live ? `No BNO055 at ${imu?.address || '0x28'}` : imu.simulated ? 'Simulated' : imu.calibrated ? 'BNO055 ready' : 'Calibrating');
  $('#imuYaw').textContent = degrees(imu?.yaw);
  $('#imuPitch').textContent = degrees(imu?.pitch);
  $('#imuRoll').textContent = degrees(imu?.roll);
  $('#imuRate').textContent = degrees(imu?.rate, '°/s');
  const cal = imu?.calibration || {};
  $('#calSystem').textContent = cal.system != null ? `${cal.system}/3` : '—';
  $('#calGyro').textContent = cal.gyro != null ? `${cal.gyro}/3` : '—';
  $('#calAccel').textContent = cal.accel != null ? `${cal.accel}/3` : '—';
  $('#imuAddress').textContent = imu?.address || '—';
  $('#zeroHeading').disabled = !live;
  if (!live && imu?.error) $('#imuNote').textContent = `Not detected: ${imu.error}. Check VIN (3.3 V), GND, SDA and SCL.`;
}

function renderSaveBar() {
  const bar = $('#saveBar');
  const changed = dirty();
  bar.className = `save-bar ${saveError ? 'error' : changed ? 'dirty' : ''}`;
  $('#saveTitle').textContent = saveError ? 'Not saved' : changed ? 'Unsaved changes' : 'Settings saved';
  $('#saveDetail').textContent = saveError || (changed
    ? 'The robot keeps using the saved map until you save.'
    : `Stored in ${config.settings_path}`);
  $('#saveButton').disabled = !changed;
  $('#revertButton').disabled = !changed;
}

function renderWiring() {
  $('#wiringTable').replaceChildren(...config.header.map(row => {
    const tr = element('tr');
    tr.dataset.group = row.group;
    tr.append(element('td', 'mono', String(row.physical)), element('td', 'mono', row.signal), element('td', null, row.to));
    return tr;
  }));
  $('#pulseRange').textContent = `${config.servo.min_pulse_us}–${config.servo.max_pulse_us}`;
  $('#imuLabel').textContent = `${config.imu.model} · ${config.imu.address}`;
}

function renderAll() {
  if (!config) return;
  saveError = '';
  renderPorts();
  renderWheelCheck();
  renderChannels();
  renderRamp();
  renderStatus();
  renderSaveBar();
}

async function refreshStatus() {
  try {
    status = await api('/api/status');
    connected = true;
    $('#connectionBanner').classList.remove('visible');
    renderStatus();
    renderChannels();
    updateRampLive();
  } catch (_) {
    connected = false;
    stopHold();
    $('#connectionBanner').classList.add('visible');
  }
}

async function loadConfig() {
  config = await api('/api/config');
  saved = clone(config.settings);
  draft = clone(config.settings);
  const banner = $('#settingsBanner');
  banner.textContent = config.settings_error || '';
  banner.classList.toggle('visible', Boolean(config.settings_error));
  renderWiring();
  renderAll();
}

/* Actions ------------------------------------------------------------------------ */

$('#saveButton').addEventListener('click', async () => {
  stopHold();
  try {
    const data = await api('/api/settings', draft);
    saved = clone(data.settings);
    draft = clone(data.settings);
    $('#settingsBanner').classList.remove('visible');
    renderAll();
  } catch (error) {
    showError(error.message);
  }
});
$('#revertButton').addEventListener('click', () => { draft = clone(saved); renderAll(); });
$('#defaultsButton').addEventListener('click', () => { draft = clone(config.defaults); renderAll(); });

$('#servoAngle').addEventListener('input', () => { $('#servoAngleValue').textContent = `${$('#servoAngle').value}°`; });
$('#servoSet').addEventListener('click', async () => {
  if (!confirmed()) { showError('Tick the safety check above before moving a servo.'); return; }
  try {
    await api('/api/debug/servo', {channel: selectedChannel, angle: Number($('#servoAngle').value), confirmed: true});
    refreshStatus();
  } catch (error) { showError(error.message); }
});
$('#servoRelease').addEventListener('click', () => api('/api/debug/servo/release', {channel: selectedChannel}).then(refreshStatus).catch(error => showError(error.message)));
$('#releaseAll').addEventListener('click', () => api('/api/debug/servo/release', {all: true}).then(refreshStatus).catch(error => showError(error.message)));
$('#oeToggle').addEventListener('click', () => {
  const enabled = !status?.robot?.servo_board?.outputs_enabled;
  api('/api/servos/output-enable', {enabled}).then(refreshStatus).catch(error => showError(error.message));
});
$$('[data-ramp]').forEach(button => button.addEventListener('click', async () => {
  if (!confirmed()) { showError('Tick the safety check above before moving the ramp.'); return; }
  try { await api('/api/ramp', {state: button.dataset.ramp}); refreshStatus(); } catch (error) { showError(error.message); }
}));
$('#zeroHeading').addEventListener('click', () => api('/api/imu/zero', {}).then(refreshStatus).catch(error => showError(error.message)));
$('#stopAll').addEventListener('click', () => {
  stopHold();
  $('#safeConfirm').checked = false;
  fetch('/api/stop', {method: 'POST', headers, body: JSON.stringify({emergency: true}), keepalive: true}).then(refreshStatus).catch(() => {});
});
$('#safeConfirm').addEventListener('change', () => { if (!confirmed()) stopHold(); });

addEventListener('keydown', event => { if (event.key === 'Escape') $('#stopAll').click(); });
addEventListener('blur', stopHold);
addEventListener('pagehide', stopHold);
document.addEventListener('visibilitychange', () => { if (document.hidden) stopHold(); });
addEventListener('beforeunload', event => { if (dirty()) { event.preventDefault(); event.returnValue = ''; } });

loadConfig().then(refreshStatus).catch(error => {
  $('#connectionBanner').textContent = `Could not load the robot configuration: ${error.message}`;
  $('#connectionBanner').classList.add('visible');
});
setInterval(refreshStatus, 300);
