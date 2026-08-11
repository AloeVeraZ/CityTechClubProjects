(() => {
  const pressed = new Set();
  const speed = document.querySelector('#speed');
  const speedValue = document.querySelector('#speed-value');
  const direction = document.querySelector('#direction');
  const status = document.querySelector('#pi-status');
  const host = document.querySelector('#host');
  const toast = document.querySelector('#toast');
  let lastVector = '';
  let driveTimer = null;
  const scoutTimers = {};

  const controls = new Set(['w', 'a', 's', 'd', 'q', 'e']);
  const labels = {
    '1,0,0': 'Moving forward', '-1,0,0': 'Moving backward',
    '0,1,0': 'Strafing left', '0,-1,0': 'Strafing right',
    '0,0,1': 'Rotating left', '0,0,-1': 'Rotating right', '0,0,0': 'Standing by'
  };

  function vector() {
    return {
      forward: Number(pressed.has('w')) - Number(pressed.has('s')),
      strafe: Number(pressed.has('a')) - Number(pressed.has('d')),
      rotate: Number(pressed.has('q')) - Number(pressed.has('e')),
      speed: Number(speed.value) / 100
    };
  }

  function renderKeys() {
    document.querySelectorAll('[data-key]').forEach(key => key.classList.toggle('active', pressed.has(key.dataset.key)));
  }

  async function sendDrive(force = false) {
    const command = vector();
    const signature = JSON.stringify(command);
    const moving = command.forward || command.strafe || command.rotate;
    if (!force && !moving && signature === lastVector) return;
    lastVector = signature;
    const labelKey = `${command.forward},${command.strafe},${command.rotate}`;
    direction.textContent = labels[labelKey] || 'Combined movement';
    try {
      const response = await fetch('/api/drive', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: signature,
        cache: 'no-store'
      });
      if (!response.ok) throw new Error('drive request failed');
      status.classList.remove('offline');
      status.innerHTML = '<i></i> Pi online';
    } catch (_) {
      status.classList.add('offline');
      status.innerHTML = '<i></i> Disconnected';
      showToast();
    }
  }

  async function stopAll(show = false) {
    pressed.clear();
    renderKeys();
    direction.textContent = 'Emergency stop';
    lastVector = '';
    try { await fetch('/api/stop', {method: 'POST', keepalive: true}); } catch (_) {}
    stopScout('a');
    stopScout('b');
    if (show) showToast();
  }

  function showToast() {
    toast.classList.add('show');
    window.setTimeout(() => toast.classList.remove('show'), 2200);
  }

  window.addEventListener('keydown', event => {
    const key = event.key.toLowerCase();
    if (key === ' ') {
      event.preventDefault();
      stopAll(true);
      return;
    }
    if (!controls.has(key) || event.repeat) return;
    event.preventDefault();
    pressed.add(key);
    renderKeys();
    sendDrive(true);
  });

  window.addEventListener('keyup', event => {
    const key = event.key.toLowerCase();
    if (!controls.has(key)) return;
    event.preventDefault();
    pressed.delete(key);
    renderKeys();
    sendDrive(true);
  });

  window.addEventListener('blur', () => stopAll());
  document.addEventListener('visibilitychange', () => { if (document.hidden) stopAll(); });
  window.addEventListener('pagehide', () => {
    navigator.sendBeacon('/api/stop');
    navigator.sendBeacon('/api/scouts/a/stop');
    navigator.sendBeacon('/api/scouts/b/stop');
  });
  document.querySelector('#stop').addEventListener('click', () => stopAll(true));
  speed.addEventListener('input', () => { speedValue.value = `${speed.value}%`; sendDrive(true); });

  async function refreshStatus() {
    try {
      const response = await fetch('/api/status', {cache: 'no-store'});
      const data = await response.json();
      status.classList.remove('offline');
      status.innerHTML = `<i></i> Pi ${data.gpio === 'hardware' ? 'online' : 'simulation'}`;
      host.textContent = `${data.hostname} · ${location.host}`;
    } catch (_) {
      status.classList.add('offline');
      status.innerHTML = '<i></i> Disconnected';
    }
  }

  const scoutMotion = {
    left: {x: -100, y: 0}, forward: {x: 0, y: 100},
    stop: {x: 0, y: 0}, back: {x: 0, y: -100}, right: {x: 100, y: 0}
  };

  async function sendScout(id, motion) {
    const controls = document.querySelector(`[data-scout="${id}"]`);
    const vector = scoutMotion[motion] || scoutMotion.stop;
    const speedLimit = Number(controls.querySelector('input').value);
    const response = await fetch(`/api/scouts/${id}/drive`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({...vector, speed: speedLimit}), cache: 'no-store'
    });
    if (!response.ok) throw new Error('scout unavailable');
  }

  function clearScoutTimer(id) {
    window.clearInterval(scoutTimers[id]);
    scoutTimers[id] = null;
    document.querySelectorAll(`[data-scout="${id}"] [data-motion]`).forEach(button => button.classList.remove('active'));
  }

  function startScout(id, motion, button) {
    clearScoutTimer(id);
    button.classList.add('active');
    const send = () => sendScout(id, motion).catch(() => clearScoutTimer(id));
    send();
    scoutTimers[id] = window.setInterval(send, 150);
  }

  function stopScout(id) {
    clearScoutTimer(id);
    fetch(`/api/scouts/${id}/stop`, {method: 'POST', keepalive: true}).catch(() => {});
  }

  document.querySelectorAll('.scout-controls').forEach(controls => {
    const id = controls.dataset.scout;
    const slider = controls.querySelector('input');
    const output = controls.querySelector('output');
    slider.addEventListener('input', () => { output.value = `${slider.value}%`; });
    controls.querySelectorAll('[data-motion]').forEach(button => {
      const motion = button.dataset.motion;
      if (motion === 'stop') {
        button.addEventListener('click', () => stopScout(id));
        return;
      }
      button.addEventListener('pointerdown', event => {
        event.preventDefault();
        button.setPointerCapture?.(event.pointerId);
        startScout(id, motion, button);
      });
      ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(type => button.addEventListener(type, () => stopScout(id)));
    });
  });

  document.querySelectorAll('[data-scout-panel]').forEach(panel => {
    const video = panel.querySelector('.scout-video');
    video.addEventListener('load', () => panel.classList.add('camera-live'));
    video.addEventListener('error', () => panel.classList.remove('camera-live'));
  });

  async function refreshScout(id) {
    const statusElement = document.querySelector(`#scout-${id}-status`);
    const motionElement = document.querySelector(`#scout-${id}-motion`);
    try {
      const response = await fetch(`/api/scouts/${id}/status`, {cache: 'no-store'});
      const data = await response.json();
      statusElement.classList.toggle('waiting', !data.online);
      statusElement.classList.toggle('offline', !data.online);
      statusElement.innerHTML = `<i></i> ${data.online ? 'Online' : 'Waiting'}`;
      motionElement.textContent = data.online
        ? `${data.motion ? 'CSI disturbance' : 'CSI idle'} · ${Math.round(data.motion_level || 0)}%`
        : 'Scout not connected';
    } catch (_) {
      statusElement.classList.add('offline');
      statusElement.innerHTML = '<i></i> Waiting';
      motionElement.textContent = 'Scout not connected';
    }
  }

  driveTimer = window.setInterval(() => { if (pressed.size) sendDrive(true); }, 120);
  window.setInterval(refreshStatus, 3000);
  window.setInterval(() => { refreshScout('a'); refreshScout('b'); }, 1500);
  refreshStatus();
  refreshScout('a');
  refreshScout('b');
})();
