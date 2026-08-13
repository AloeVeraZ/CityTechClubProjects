(() => {
  const bigPressed = new Set();
  const speed = document.querySelector('#speed');
  const speedValue = document.querySelector('#speed-value');
  const direction = document.querySelector('#direction');
  const status = document.querySelector('#pi-status');
  const host = document.querySelector('#host');
  const cameraMessage = document.querySelector('#camera-message');
  const cameraImage = document.querySelector('[data-stream-for="3tsahur"]');
  const hubCameraLabel = document.querySelector('#hub-camera-label');
  const hubCameraModel = document.querySelector('#hub-camera-model');
  const hubCameraMode = document.querySelector('#hub-camera-mode');
  const cameraFeeds = [...document.querySelectorAll('[data-stream-for][data-stream-src]')];
  const toast = document.querySelector('#toast');
  const autoPriority = document.querySelector('#auto-priority');
  const healthSummary = document.querySelector('#health-summary');
  const session = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
  const initialServerTime = Number(document.querySelector('meta[name="server-time-ms"]')?.content);
  let serverClockOffset = Number.isFinite(initialServerTime) ? initialServerTime - Date.now() : 0;
  let bigSequence = 0;
  let lastVector = '';
  let lastCameraRetryAt = 0;
  let actuatorState = {ramp: {state: 'closed', closed_angle: 0}};
  let rampCommandPending = false;
  const controlLatencySamples = [];
  let controlPriorityUntil = 0;
  let cameraTrafficPaused = false;
  let gamepadWasMoving = false;
  const bigKeys = new Set(['w', 'a', 's', 'd', 'q', 'e']);
  const labels = {
    '1,0,0': 'Moving forward', '-1,0,0': 'Moving backward',
    '0,1,0': 'Strafing left', '0,-1,0': 'Strafing right',
    '0,0,1': 'Rotating left', '0,0,-1': 'Rotating right', '0,0,0': 'Standing by'
  };

  // At most one request per robot may be active. If input changes while that
  // request is running, only the newest command is retained. An urgent stop
  // aborts the active fetch and goes to the front immediately.
  function createLatestChannel(url, onFailure = () => {}, onTiming = () => {}) {
    let active = null;
    let pending = null;
    let generation = 0;

    async function pump() {
      if (active || !pending) return;
      const payload = pending;
      pending = null;
      const controller = new AbortController();
      const currentGeneration = ++generation;
      const startedAt = performance.now();
      let succeeded = false;
      active = {controller, generation: currentGeneration};
      // Drive requests use a small latest-command budget. A delayed request is
      // discarded so the next current command is never stuck behind it.
      const timeout = window.setTimeout(() => controller.abort(), 140);
      try {
        const response = await fetch(url, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(payload),
          cache: 'no-store',
          signal: controller.signal
        });
        if (!response.ok && response.status !== 409) throw new Error(`request failed: ${response.status}`);
        succeeded = true;
      } catch (error) {
        if (error.name !== 'AbortError') onFailure(error);
      } finally {
        window.clearTimeout(timeout);
        onTiming(performance.now() - startedAt, succeeded);
        if (active?.generation === currentGeneration) active = null;
        if (pending) pump();
      }
    }

    return (payload, urgent = false) => {
      pending = payload;
      if (urgent && active) {
        active.controller.abort();
        active = null;
      }
      pump();
    };
  }

  function commandTiming() {
    const issuedAt = Math.round(Date.now() + serverClockOffset);
    return {issued_at_ms: issuedAt, expires_at_ms: issuedAt + 300};
  }

  function showControlFailure() {
    status.classList.add('offline');
    status.innerHTML = '<i></i> Control delayed';
    showToast('Command link delayed - watchdog stopped the motors');
  }

  function anyRobotMoving() {
    return Boolean(bigPressed.size || gamepadWasMoving);
  }

  function applyControlPriority() {
    const shouldPause = Boolean(autoPriority?.checked && anyRobotMoving() && performance.now() < controlPriorityUntil);
    if (shouldPause) {
      cameraFeeds.forEach(feed => feed.removeAttribute('src'));
      if (!cameraTrafficPaused) showToast('Control priority active - auxiliary traffic paused');
      cameraTrafficPaused = true;
      document.body.dataset.controlPriority = 'active';
      return;
    }
    if (cameraTrafficPaused) {
      cameraTrafficPaused = false;
      delete document.body.dataset.controlPriority;
      activateSelectedCameras();
    }
  }

  function recordControlTiming(duration, succeeded) {
    controlLatencySamples.push(succeeded ? duration : 140);
    if (controlLatencySamples.length > 20) controlLatencySamples.shift();
    const ordered = [...controlLatencySamples].sort((a, b) => a - b);
    const p95 = ordered[Math.max(0, Math.ceil(ordered.length * .95) - 1)] || 0;
    if (!succeeded || (ordered.length >= 5 && p95 >= 100)) {
      controlPriorityUntil = performance.now() + 10000;
    }
    applyControlPriority();
  }

  const queueBig = createLatestChannel('/api/drive', showControlFailure, recordControlTiming);

  function bigVector() {
    const rotate = Number(bigPressed.has('q')) - Number(bigPressed.has('e'));
    // Q/E are fixed, pure pivots. Translation is intentionally suppressed so
    // every wheel receives the same 75% magnitude during a keyboard turn.
    if (rotate) return {forward: 0, strafe: 0, rotate, speed: 0.75};
    return {
      forward: Number(bigPressed.has('w')) - Number(bigPressed.has('s')),
      strafe: Number(bigPressed.has('a')) - Number(bigPressed.has('d')),
      rotate: 0,
      speed: Number(speed.value) / 100
    };
  }

  function renderKeys() {
    document.querySelectorAll('[data-key]').forEach(key => key.classList.toggle('active', bigPressed.has(key.dataset.key)));
  }

  function sendBig(force = false, override = null, urgent = false) {
    if (document.querySelector('#deadman')?.checked && !override && document.body.dataset.deadman !== 'held') return;
    const command = override || bigVector();
    const signature = JSON.stringify(command);
    const moving = command.forward || command.strafe || command.rotate;
    if (!force && !moving && signature === lastVector) return;
    lastVector = signature;
    direction.textContent = labels[`${command.forward},${command.strafe},${command.rotate}`] || 'Combined movement';
    queueBig({...command, session, sequence: ++bigSequence, ...commandTiming()}, urgent);
    applyControlPriority();
  }

  function killBig(show = false) {
    bigPressed.clear();
    renderKeys();
  direction.textContent = '3TSahur stopped';
    lastVector = '';
    sendBig(true, {forward: 0, strafe: 0, rotate: 0, speed: 0}, true);
  if (show) showToast('3TSahur kill switch activated');
  }

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('show');
    window.setTimeout(() => toast.classList.remove('show'), 2200);
  }

  function killAll(show = false) {
    killBig(false);
    if (show) showToast('3TSAHUR STOPPED');
  }

  const selectedCameras = new Set(['3tsahur']);

  function activateSelectedCameras() {
    cameraFeeds.forEach(feed => {
      if (cameraTrafficPaused) {
        feed.removeAttribute('src');
        return;
      }
      if (selectedCameras.has(feed.dataset.streamFor)) {
        if (!feed.getAttribute('src')) feed.src = feed.dataset.streamSrc;
      } else {
        feed.removeAttribute('src');
      }
    });
  }

  function renderCameraSelection() {
    activateSelectedCameras();
  }

  function renderActuatorStatus(data = actuatorState) {
    actuatorState = data || actuatorState;
    const ramp = actuatorState.ramp || {state: "closed", closed_angle: 0};
    const isOpen = ramp.state === "open";
    const openLabel = Number.isFinite(Number(ramp.open_angle)) ? Number(ramp.open_angle) + "°" : "120°";
    document.querySelector("#ramp-readout").value = isOpen ? "Open · " + openLabel : "Closed · 0°";
    const toggle = document.querySelector("#ramp-toggle");
    toggle.textContent = (isOpen ? "Close" : "Open") + " ramp · R";
    toggle.setAttribute("aria-pressed", String(isOpen));
    document.querySelector("#actuator-status").value = actuatorState.configured
      ? "Ramp servos ready"
      : (actuatorState.reason || "Servo GPIO unavailable");
  }

  async function toggleRamp() {
    if (rampCommandPending) return;
    rampCommandPending = true;
    const toggle = document.querySelector("#ramp-toggle");
    toggle.disabled = true;
    const next = actuatorState.ramp?.state === "open" ? "closed" : "open";
    try {
      const response = await fetch("/api/actuators/ramp", {
        method: "POST", headers: {"Content-Type": "application/json"}, cache: "no-store",
        body: JSON.stringify({state: next})
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error);
      renderActuatorStatus(data);
      showToast("Ramp " + next + (data.configured ? "" : " (awaiting driver connection)"));
    } catch (error) {
      showToast(error.message || "Ramp command unavailable");
    } finally {
      rampCommandPending = false;
      toggle.disabled = false;
    }
  }
  window.addEventListener('keydown', event => {
    const key = event.key.toLowerCase();
    if (event.key === 'Escape') {
      event.preventDefault();
      killAll(true);
      return;
    }
    if (event.target.closest?.('input, select, button, summary, a')) return;
    if (key === ' ') {
      event.preventDefault();
      killBig(true);
      return;
    }
    if (key === 'r' && !event.repeat) {
      event.preventDefault();
      toggleRamp();
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
  });

  window.addEventListener('keyup', event => {
    const key = event.key.toLowerCase();
    if (event.target.closest?.('input, select, button, summary, a')) return;
    if (bigKeys.has(key)) {
      event.preventDefault();
      bigPressed.delete(key);
      renderKeys();
      sendBig(true, null, bigPressed.size === 0);
      return;
    }
  });

  window.addEventListener('blur', () => killAll());
  document.addEventListener('visibilitychange', () => { if (document.hidden) killAll(); });
  window.addEventListener('pagehide', () => killAll());
  document.querySelector('#stop').addEventListener('click', () => killBig(true));
  document.querySelector('#kill-all').addEventListener('click', () => killAll(true));
  document.querySelector('#ramp-toggle').addEventListener('click', toggleRamp);
  speed.addEventListener('input', () => { speedValue.value = `${speed.value}%`; sendBig(true); });

  async function refreshStatus() {
    if (anyRobotMoving()) return;
    const requestStartedAt = Date.now();
    try {
      const response = await fetch('/api/status', {cache: 'no-store'});
      const data = await response.json();
      const responseReceivedAt = Date.now();
      if (Number.isFinite(data.server_time_ms)) {
        serverClockOffset = data.server_time_ms - ((requestStartedAt + responseReceivedAt) / 2);
      }
      const hardwareReady = data.gpio === 'hardware';
      renderActuatorStatus(data.actuators);
      const health = data.system_health || {};
      const temperature = Number.isFinite(health.temperature_c) ? `${health.temperature_c}°C` : 'n/a';
      const power = health.power_warning === true ? 'check supply' : health.power_warning === false ? 'stable' : 'n/a';
      const throttle = health.throttling_warning === true ? 'detected' : health.throttling_warning === false ? 'clear' : 'n/a';
      const disk = Number.isFinite(health.disk_free_mb) ? `${health.disk_free_mb} MB free` : 'checking';
      const cameraName = data.camera_name || 'USB camera';
      const cameraMode = `${data.camera_width}x${data.camera_height} @ ${data.camera_fps} FPS`;
      hubCameraModel.textContent = cameraName;
      hubCameraMode.textContent = data.camera_available ? `Automatic compatibility mode · ${cameraMode}` : 'Automatic detection is waiting for a camera';
      hubCameraLabel.textContent = `3TSahur · ${cameraName}`;
      document.querySelector('#health-panel').innerHTML = `<dt>Pi control</dt><dd>${hardwareReady ? 'ready' : 'simulation'}</dd><dt>Camera</dt><dd>${data.camera_available ? `${cameraName} · ${cameraMode}` : 'unavailable'} · ${data.camera_restart_count || 0} retries</dd><dt>Temperature</dt><dd>${temperature}</dd><dt>Power</dt><dd>${power}</dd><dt>Throttling</dt><dd>${throttle}</dd><dt>Storage</dt><dd>${disk}</dd><dt>Network</dt><dd>${location.host}</dd>`;
      const healthWarnings = [
        !hardwareReady,
        !data.camera_available,
        health.power_warning === true,
        health.throttling_warning === true,
        Number.isFinite(health.temperature_c) && health.temperature_c >= 80
      ].filter(Boolean).length;
      healthSummary.value = healthWarnings ? `${healthWarnings} alert${healthWarnings === 1 ? '' : 's'}` : 'Systems nominal';
      healthSummary.classList.toggle('warning', healthWarnings > 0);
      status.classList.toggle('offline', !hardwareReady);
      status.innerHTML = `<i></i> ${hardwareReady ? 'Pi controls ready' : 'GPIO unavailable - motors disabled'}`;
      host.textContent = `${data.hostname} / ${location.host}`;
      cameraMessage.classList.toggle('hidden', data.camera_available);
      cameraMessage.textContent = data.camera_error
        ? `Camera unavailable: ${data.camera_error}`
        : data.camera_device ? `Opening ${cameraName}…` : 'Looking for a Logitech USB camera…';
      if (!data.camera_available && data.camera_error && Date.now() - lastCameraRetryAt > 5000) {
        lastCameraRetryAt = Date.now();
        if (selectedCameras.has('3tsahur')) cameraImage.src = `${cameraImage.dataset.streamSrc}?retry=${lastCameraRetryAt}`;
      }
    } catch (_) {
      status.classList.add('offline');
      status.innerHTML = '<i></i> Disconnected';
      healthSummary.value = 'Connection lost';
      healthSummary.classList.add('warning');
    }
  }

  // These are safety heartbeats, not a request flood: each channel retains
  // only its latest command and never builds a queue.
  window.setInterval(() => { if (bigPressed.size) sendBig(true); }, 80);
  window.setInterval(refreshStatus, 3000);
  const deadman = document.querySelector('#deadman');
  let lastGamepadSignature = '';
  let lastGamepadSentAt = 0;
  function reportEvent(kind, source, message) { if (!anyRobotMoving()) fetch('/api/events', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({kind, source, message}), cache: 'no-store'}).catch(() => {}); }
  async function refreshEvents() { if (anyRobotMoving()) return; try { const data = await (await fetch('/api/events', {cache: 'no-store'})).json(); document.querySelector('#event-list').innerHTML = (data.events || []).slice(0, 8).map(e => `<li><time>${new Date(e.at_ms).toLocaleTimeString()}</time> ${e.message}</li>`).join('') || '<li>No mission events yet.</li>'; } catch (_) {} }
  async function takeSnapshot(source) { if (anyRobotMoving()) { showToast('Stop the robots before taking a snapshot'); return; } try { const response = await fetch(`/api/snapshots/${source}`, {method: 'POST', cache: 'no-store'}); const data = await response.json(); if (!response.ok) throw Error(data.error); window.open(data.url, '_blank', 'noopener'); showToast('Snapshot saved'); refreshEvents(); } catch (error) { showToast(error.message || 'Snapshot unavailable'); } }
  document.querySelectorAll('[data-snapshot]').forEach(button => button.addEventListener('click', () => takeSnapshot(button.dataset.snapshot)));
  deadman.addEventListener('change', () => { killAll(); reportEvent('safety', 'dashboard', `Dead-man mode ${deadman.checked ? 'enabled' : 'disabled'}`); });
  autoPriority.addEventListener('change', () => { if (!autoPriority.checked) controlPriorityUntil = 0; applyControlPriority(); reportEvent('network', 'dashboard', `Adaptive control priority ${autoPriority.checked ? 'enabled' : 'disabled'}`); });
  window.addEventListener('keydown', event => { if (deadman.checked && event.key === 'Shift') document.body.dataset.deadman = 'held'; });
  window.addEventListener('keyup', event => { if (deadman.checked && event.key === 'Shift') { delete document.body.dataset.deadman; killAll(); } });
  window.setInterval(refreshEvents, 2000);
  window.setInterval(applyControlPriority, 250);
  window.setInterval(() => { const pad = navigator.getGamepads?.()[0]; if (!pad) return; const held = Boolean(pad.buttons[0]?.pressed); if (deadman.checked && !held) { delete document.body.dataset.deadman; if (gamepadWasMoving) killBig(); gamepadWasMoving = false; lastGamepadSignature = ''; return; } if (deadman.checked) document.body.dataset.deadman = 'held'; const forward = Math.abs(pad.axes[1] || 0) > .18 ? -(pad.axes[1] || 0) : 0; const strafe = Math.abs(pad.axes[0] || 0) > .18 ? pad.axes[0] : 0; const rotate = Math.abs(pad.axes[2] || 0) > .18 ? pad.axes[2] : 0; const moving = Boolean(forward || strafe || rotate); const command = {forward, strafe, rotate, speed: Number(speed.value) / 100}; const signature = JSON.stringify(command); const now = performance.now(); if (moving && (signature !== lastGamepadSignature || now - lastGamepadSentAt >= 80)) { sendBig(true, command); lastGamepadSignature = signature; lastGamepadSentAt = now; } else if (!moving && gamepadWasMoving) { sendBig(true, {forward: 0, strafe: 0, rotate: 0, speed: 0}, true); lastGamepadSignature = ''; } gamepadWasMoving = moving; }, 100);
  renderCameraSelection();
  refreshStatus();
  refreshEvents();
})();
