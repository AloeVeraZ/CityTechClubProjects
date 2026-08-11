(() => {
  const bigPressed = new Set();
  const scoutPressed = {a: new Set(), b: new Set()};
  const speed = document.querySelector('#speed');
  const speedValue = document.querySelector('#speed-value');
  const direction = document.querySelector('#direction');
  const status = document.querySelector('#pi-status');
  const host = document.querySelector('#host');
  const toast = document.querySelector('#toast');
  const session = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
  let bigSequence = 0;
  let lastVector = '';
  const scoutSequences = {a: 0, b: 0};
  const bigKeys = new Set(['w', 'a', 's', 'd', 'q', 'e']);
  const scoutKeys = {
    a: {ArrowLeft: 'left', ArrowUp: 'forward', ArrowDown: 'back', ArrowRight: 'right'},
    b: {j: 'left', i: 'forward', k: 'back', l: 'right'}
  };
  const labels = {
    '1,0,0': 'Moving forward', '-1,0,0': 'Moving backward',
    '0,1,0': 'Strafing left', '0,-1,0': 'Strafing right',
    '0,0,1': 'Rotating left', '0,0,-1': 'Rotating right', '0,0,0': 'Standing by'
  };

  function bigVector() {
    return {
      forward: Number(bigPressed.has('w')) - Number(bigPressed.has('s')),
      strafe: Number(bigPressed.has('a')) - Number(bigPressed.has('d')),
      rotate: Number(bigPressed.has('q')) - Number(bigPressed.has('e')),
      speed: Number(speed.value) / 100
    };
  }

  function renderKeys() {
    document.querySelectorAll('[data-key]').forEach(key => key.classList.toggle('active', bigPressed.has(key.dataset.key)));
  }

  async function sendBig(force = false, override = null) {
    const command = override || bigVector();
    const signature = JSON.stringify(command);
    const moving = command.forward || command.strafe || command.rotate;
    if (!force && !moving && signature === lastVector) return;
    lastVector = signature;
    const sequence = ++bigSequence;
    direction.textContent = labels[`${command.forward},${command.strafe},${command.rotate}`] || 'Combined movement';
    try {
      const response = await fetch('/api/drive', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({...command, session, sequence}), cache: 'no-store', keepalive: !moving
      });
      if (!response.ok) throw new Error('drive request failed');
      status.classList.remove('offline');
      status.innerHTML = '<i></i> Pi online';
    } catch (_) {
      status.classList.add('offline');
      status.innerHTML = '<i></i> Disconnected';
      showToast('Control link lost - motors stopped');
    }
  }

  function killBig(show = false) {
    bigPressed.clear();
    renderKeys();
    direction.textContent = 'Big robot stopped';
    lastVector = '';
    sendBig(true, {forward: 0, strafe: 0, rotate: 0, speed: 0}).catch(() => {});
    if (show) showToast('Big robot kill switch activated');
  }

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    window.setTimeout(() => toast.classList.remove('show'), 2200);
  }

  const scoutMotion = {
    left: {x: -100, y: 0}, forward: {x: 0, y: 100},
    stop: {x: 0, y: 0}, back: {x: 0, y: -100}, right: {x: 100, y: 0}
  };

  function activeScoutMotion(id) {
    const motions = scoutPressed[id];
    const x = Number(motions.has('right')) - Number(motions.has('left'));
    const y = Number(motions.has('forward')) - Number(motions.has('back'));
    if (y > 0) return 'forward';
    if (y < 0) return 'back';
    if (x < 0) return 'left';
    if (x > 0) return 'right';
    return 'stop';
  }

  async function sendScout(id, motion) {
    const controls = document.querySelector(`[data-scout="${id}"]`);
    const vector = scoutMotion[motion] || scoutMotion.stop;
    const speedLimit = Number(controls.querySelector('input').value);
    const sequence = ++scoutSequences[id];
    const response = await fetch(`/api/scouts/${id}/drive`, {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({...vector, speed: speedLimit, session, sequence}),
      cache: 'no-store', keepalive: motion === 'stop'
    });
    if (!response.ok) throw new Error('scout unavailable');
  }

  function renderScoutButtons(id, motion = activeScoutMotion(id)) {
    document.querySelectorAll(`[data-scout="${id}"] [data-motion]`).forEach(button => {
      button.classList.toggle('active', motion !== 'stop' && button.dataset.motion === motion);
    });
  }

  function killScout(id, show = false) {
    scoutPressed[id].clear();
    renderScoutButtons(id, 'stop');
    sendScout(id, 'stop').catch(() => {});
    if (show) showToast(`ECHO Scout ${id.toUpperCase()} kill switch activated`);
  }

  function killAll(show = false) {
    killBig(false);
    killScout('a');
    killScout('b');
    if (show) showToast('ALL ROBOTS STOPPED');
  }

  function keyMotion(event, id) {
    return scoutKeys[id][id === 'a' ? event.key : event.key.toLowerCase()];
  }

  window.addEventListener('keydown', event => {
    const key = event.key.toLowerCase();
    if (event.key === 'Escape') {
      event.preventDefault();
      killAll(true);
      return;
    }
    if (key === ' ') {
      event.preventDefault();
      killBig(true);
      return;
    }
    if (bigKeys.has(key)) {
      event.preventDefault();
      if (event.repeat) return;
      bigPressed.add(key);
      renderKeys();
      sendBig(true);
      return;
    }
    for (const id of ['a', 'b']) {
      const motion = keyMotion(event, id);
      if (!motion) continue;
      event.preventDefault();
      if (event.repeat) return;
      scoutPressed[id].add(motion);
      renderScoutButtons(id);
      sendScout(id, activeScoutMotion(id)).catch(() => {});
      return;
    }
  });

  window.addEventListener('keyup', event => {
    const key = event.key.toLowerCase();
    if (bigKeys.has(key)) {
      event.preventDefault();
      bigPressed.delete(key);
      renderKeys();
      sendBig(true);
      return;
    }
    for (const id of ['a', 'b']) {
      const motion = keyMotion(event, id);
      if (!motion) continue;
      event.preventDefault();
      scoutPressed[id].delete(motion);
      renderScoutButtons(id);
      sendScout(id, activeScoutMotion(id)).catch(() => {});
      return;
    }
  });

  window.addEventListener('blur', () => killAll());
  document.addEventListener('visibilitychange', () => { if (document.hidden) killAll(); });
  window.addEventListener('pagehide', () => killAll());
  document.querySelector('#stop').addEventListener('click', () => killBig(true));
  document.querySelector('#kill-all').addEventListener('click', () => killAll(true));
  speed.addEventListener('input', () => { speedValue.value = `${speed.value}%`; sendBig(true); });

  document.querySelectorAll('.scout-controls').forEach(controls => {
    const id = controls.dataset.scout;
    const slider = controls.querySelector('input');
    const output = controls.querySelector('output');
    slider.addEventListener('input', () => { output.value = `${slider.value}%`; });
    controls.querySelectorAll('[data-motion]').forEach(button => {
      const motion = button.dataset.motion;
      if (motion === 'stop') {
        button.addEventListener('click', () => killScout(id, true));
        return;
      }
      button.addEventListener('pointerdown', event => {
        event.preventDefault();
        button.setPointerCapture?.(event.pointerId);
        scoutPressed[id].add(motion);
        renderScoutButtons(id);
        sendScout(id, activeScoutMotion(id)).catch(() => {});
      });
      ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(type => button.addEventListener(type, () => {
        scoutPressed[id].delete(motion);
        renderScoutButtons(id);
        sendScout(id, activeScoutMotion(id)).catch(() => {});
      }));
    });
  });

  async function refreshStatus() {
    try {
      const response = await fetch('/api/status', {cache: 'no-store'});
      const data = await response.json();
      status.classList.remove('offline');
      status.innerHTML = `<i></i> Pi ${data.gpio === 'hardware' ? 'online' : 'simulation'}`;
      host.textContent = `${data.hostname} / ${location.host}`;
    } catch (_) {
      status.classList.add('offline');
      status.innerHTML = '<i></i> Disconnected';
    }
  }

  async function refreshScout(id) {
    const panel = document.querySelector(`[data-scout-panel="${id}"]`);
    const statusElement = document.querySelector(`#scout-${id}-status`);
    const connectionElement = document.querySelector(`#scout-${id}-connection`);
    const motionElement = document.querySelector(`#scout-${id}-motion`);
    try {
      const response = await fetch(`/api/scouts/${id}/status`, {cache: 'no-store'});
      const data = await response.json();
      const connected = Boolean(data.connected || data.online);
      panel.classList.toggle('scout-connected', connected);
      statusElement.classList.toggle('waiting', !connected);
      statusElement.classList.toggle('offline', !connected);
      statusElement.innerHTML = `<i></i> ${data.online ? 'Ready' : connected ? 'Connected' : 'Waiting'}`;
      connectionElement.textContent = connected ? 'ECHO connected to EchoSwarm' : 'Waiting for ECHO heartbeat';
      motionElement.textContent = data.online
        ? `${data.motion ? 'CSI disturbance' : 'CSI idle'} / ${Math.round(data.motion_level || 0)}%`
        : connected ? 'Heartbeat received' : 'Scout not connected';
    } catch (_) {
      panel.classList.remove('scout-connected');
      statusElement.classList.add('offline');
      statusElement.innerHTML = '<i></i> Waiting';
      connectionElement.textContent = 'Waiting for ECHO heartbeat';
      motionElement.textContent = 'Scout not connected';
    }
  }

  window.setInterval(() => { if (bigPressed.size) sendBig(true); }, 60);
  window.setInterval(() => {
    for (const id of ['a', 'b']) if (scoutPressed[id].size) sendScout(id, activeScoutMotion(id)).catch(() => {});
  }, 80);
  window.setInterval(refreshStatus, 3000);
  window.setInterval(() => { refreshScout('a'); refreshScout('b'); }, 1000);
  refreshStatus();
  refreshScout('a');
  refreshScout('b');
})();
