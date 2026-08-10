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
  window.addEventListener('pagehide', () => navigator.sendBeacon('/api/stop'));
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

  driveTimer = window.setInterval(() => { if (pressed.size) sendDrive(true); }, 120);
  window.setInterval(refreshStatus, 3000);
  refreshStatus();
})();
