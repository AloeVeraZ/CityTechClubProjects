(() => {
  const bigPressed = new Set();
  const scoutPressed = {a: new Set(), b: new Set()};
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
  let activeRobotTab = '3tsahur';
  let actuatorState = {ramp: {state: 'closed', closed_angle: 0}};
  const scoutSequences = {a: 0, b: 0};
  const scoutStatusInFlight = {a: false, b: false};
  const visionEnabled = {'3tsahur': false, 'larp-a': false, 'larp-b': false};
  const visionInFlight = {'3tsahur': false, 'larp-a': false, 'larp-b': false};
  const landmarkEnabled = {'3tsahur': false, 'larp-a': false, 'larp-b': false};
  const controlLatencySamples = [];
  let controlPriorityUntil = 0;
  let cameraTrafficPaused = false;
  let gamepadWasMoving = false;
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
    return Boolean(bigPressed.size || scoutPressed.a.size || scoutPressed.b.size || gamepadWasMoving);
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
  const queueScouts = {
    a: createLatestChannel('/api/scouts/a/drive', () => {}, recordControlTiming),
    b: createLatestChannel('/api/scouts/b/drive', () => {}, recordControlTiming)
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

  function sendScout(id, motion, urgent = false) {
    if (document.querySelector('#deadman')?.checked && motion !== 'stop' && document.body.dataset.deadman !== 'held') return;
    const controls = document.querySelector(`[data-scout="${id}"]`);
    const vector = scoutMotion[motion] || scoutMotion.stop;
    const speedLimit = Number(controls.querySelector('input').value);
    queueScouts[id]({
      ...vector,
      speed: speedLimit,
      session,
      sequence: ++scoutSequences[id],
      ...commandTiming()
    }, urgent);
    applyControlPriority();
  }

  function renderScoutButtons(id, motion = activeScoutMotion(id)) {
    document.querySelectorAll(`[data-scout="${id}"] [data-motion]`).forEach(button => {
      button.classList.toggle('active', motion !== 'stop' && button.dataset.motion === motion);
    });
  }

  function killScout(id, show = false) {
    scoutPressed[id].clear();
    renderScoutButtons(id, 'stop');
    sendScout(id, 'stop', true);
  if (show) showToast(`LARP Scout ${id.toUpperCase()} kill switch activated`);
  }

  function killAll(show = false) {
    killBig(false);
    killScout('a');
    killScout('b');
    if (show) showToast('ALL ROBOTS STOPPED');
  }

  const cameraSelectors = [...document.querySelectorAll('[data-camera-select]')];
  const robotPanels = [...document.querySelectorAll('[data-robot-panel]')];
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

  function setActiveRobotContext(id) {
    if (!robotPanels.some(panel => panel.dataset.robotPanel === id)) return;
    robotPanels.forEach(panel => {
      panel.classList.toggle('active', panel.dataset.robotPanel === id);
    });
    activeRobotTab = id;
  }

  function renderCameraSelection() {
    if (!selectedCameras.size) selectedCameras.add('3tsahur');
    const selected = cameraFeeds.filter(feed => selectedCameras.has(feed.dataset.streamFor));
    const rowSpan = 6 / selected.length;
    cameraFeeds.forEach(feed => {
      const visibleIndex = selected.indexOf(feed);
      const stage = feed.closest('.video-stage');
      const visible = visibleIndex >= 0;
      stage.classList.toggle('camera-hidden', !visible);
      stage.style.gridRow = visible ? `${(visibleIndex * rowSpan) + 1} / span ${rowSpan}` : '';
      stage.style.gridColumn = visible ? '1' : '';
    });
    cameraSelectors.forEach(button => {
      const selected = selectedCameras.has(button.dataset.cameraSelect);
      button.classList.toggle('active', selected);
      button.setAttribute('aria-pressed', String(selected));
    });
    if (!selectedCameras.has(activeRobotTab)) setActiveRobotContext([...selectedCameras][0]);
    activateSelectedCameras();
  }

  robotPanels.forEach(panel => {
    const selectPanel = () => setActiveRobotContext(panel.dataset.robotPanel);
    panel.addEventListener('pointerdown', selectPanel);
    panel.addEventListener('focusin', selectPanel);
  });
  cameraSelectors.forEach(button => button.addEventListener('click', () => {
    const source = button.dataset.cameraSelect;
    if (selectedCameras.has(source)) selectedCameras.delete(source);
    else selectedCameras.add(source);
    setActiveRobotContext(source);
    renderCameraSelection();
  }));

  function clearVisionOverlay(source) {
    const canvas = document.querySelector(`[data-vision-overlay="${source}"]`);
    if (!canvas) return;
    const context = canvas.getContext('2d');
    context.clearRect(0, 0, canvas.width, canvas.height);
  }

  function renderVision(source, data) {
    const button = document.querySelector(`[data-vision-toggle="${source}"]`);
    const landmarkButton = document.querySelector(`[data-landmark-toggle="${source}"]`);
    const label = document.querySelector(`[data-vision-status="${source}"]`);
    const canvas = document.querySelector(`[data-vision-overlay="${source}"]`);
    const peopleOn = Boolean(data.enabled ?? visionEnabled[source]);
    const markersOn = Boolean(data.landmarks_enabled ?? landmarkEnabled[source]);
    visionEnabled[source] = peopleOn;
    landmarkEnabled[source] = markersOn;
    button.setAttribute('aria-pressed', String(peopleOn));
    button.textContent = `${peopleOn ? 'Vision on' : 'Vision off'} · C`;
    landmarkButton.setAttribute('aria-pressed', String(markersOn));
    landmarkButton.textContent = `${markersOn ? 'Markers on' : 'Markers off'} · L`;
    if (!peopleOn && !markersOn) {
      label.textContent = 'Analysis ready when enabled';
      clearVisionOverlay(source);
      return;
    }
    if (peopleOn && data.available === false && !markersOn) {
      label.textContent = data.error ? `Vision unavailable: ${data.error}` : 'Starting vision worker…';
      clearVisionOverlay(source);
      return;
    }
    const detections = data.detections || [];
    const landmarks = data.landmarks || [];
    const summaries = [];
    if (peopleOn) summaries.push(data.available === false ? 'Vision unavailable' : data.inference_skipped ? 'Motion gate idle' : detections.length ? `${detections.length} person${detections.length === 1 ? '' : 's'}` : 'No person');
    if (markersOn) summaries.push(data.landmark_skipped ? 'Marker gate idle' : data.landmarks_available === false ? 'Markers unavailable' : `${landmarks.length} marker${landmarks.length === 1 ? '' : 's'}`);
    label.textContent = summaries.join(' · ');
    const bounds = canvas.getBoundingClientRect();
    canvas.width = Math.max(1, Math.round(bounds.width));
    canvas.height = Math.max(1, Math.round(bounds.height));
    const context = canvas.getContext('2d');
    context.clearRect(0, 0, canvas.width, canvas.height);
    if (!data.frame_width || !data.frame_height) return;
    const scaleX = canvas.width / data.frame_width;
    const scaleY = canvas.height / data.frame_height;
    context.strokeStyle = '#b9ff38'; context.fillStyle = '#b9ff38'; context.lineWidth = 2;
    context.font = '700 12px ui-monospace, monospace';
    detections.forEach(box => {
      const x = box.x1 * scaleX, y = box.y1 * scaleY;
      const width = (box.x2 - box.x1) * scaleX, height = (box.y2 - box.y1) * scaleY;
      context.strokeRect(x, y, width, height);
      context.fillText(`PERSON ${Math.round(box.confidence * 100)}%`, x + 3, Math.max(13, y - 5));
    });
    context.strokeStyle = '#ffb547'; context.fillStyle = '#ffb547';
    landmarks.forEach(marker => {
      const x = marker.x1 * scaleX, y = marker.y1 * scaleY;
      const width = (marker.x2 - marker.x1) * scaleX, height = (marker.y2 - marker.y1) * scaleY;
      context.strokeRect(x, y, width, height);
      context.fillText(`MARKER ${marker.id}`, x + 3, Math.max(13, y - 5));
    });
  }

  async function refreshVision(source) {
    if (anyRobotMoving() || (!visionEnabled[source] && !landmarkEnabled[source]) || visionInFlight[source]) return;
    visionInFlight[source] = true;
    try {
      const response = await fetch(`/api/vision/${source}`, {cache: 'no-store'});
      renderVision(source, await response.json());
    } catch (_) {
      document.querySelector(`[data-vision-status="${source}"]`).textContent = 'Analysis status request failed';
    } finally {
      visionInFlight[source] = false;
    }
  }

  async function toggleVision(source) {
    const enabled = !visionEnabled[source];
    visionEnabled[source] = enabled;
    renderVision(source, {enabled, available: null, detections: []});
    try {
      const response = await fetch(`/api/vision/${source}`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({enabled}), cache: 'no-store'});
      if (!response.ok) throw new Error(`request failed: ${response.status}`);
      renderVision(source, await response.json());
      showToast(`${source === '3tsahur' ? '3TSahur' : source === 'larp-a' ? 'LARP Scout A' : 'LARP Scout B'} vision ${enabled ? 'enabled' : 'disabled'}`);
    } catch (_) {
      visionEnabled[source] = false;
      renderVision(source, {enabled: false, available: null, detections: []});
      showToast('Vision unavailable - robot controls remain active');
    }
  }

  async function toggleLandmarks(source) {
    const enabled = !landmarkEnabled[source];
    landmarkEnabled[source] = enabled;
    renderVision(source, {enabled: visionEnabled[source], landmarks_enabled: enabled});
    try {
      const response = await fetch(`/api/landmarks/${source}`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({enabled}), cache: 'no-store'});
      if (!response.ok) throw new Error(`request failed: ${response.status}`);
      renderVision(source, await response.json());
      showToast(`${source} landmark recognition ${enabled ? 'enabled' : 'disabled'}`);
    } catch (_) {
      landmarkEnabled[source] = false;
      renderVision(source, {enabled: visionEnabled[source], landmarks_enabled: false});
      showToast('Landmarks unavailable - robot controls remain active');
    }
  }

  function renderActuatorStatus(data = actuatorState) {
    actuatorState = data || actuatorState;
    const ramp = actuatorState.ramp || {state: "closed", closed_angle: 0};
    const isOpen = ramp.state === "open";
    const openLabel = Number.isFinite(Number(ramp.open_angle)) ? Number(ramp.open_angle) + "°" : "30°";
    document.querySelector("#ramp-readout").value = isOpen ? "Open · " + openLabel : "Closed · 0°";
    const toggle = document.querySelector("#ramp-toggle");
    toggle.textContent = (isOpen ? "Close" : "Open") + " ramp · R";
    toggle.setAttribute("aria-pressed", String(isOpen));
    document.querySelector("#actuator-status").value = actuatorState.configured
      ? "Ramp servos ready"
      : (actuatorState.reason || "Servo GPIO unavailable");
  }

  async function toggleRamp() {
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
    }
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
    if (event.target.closest?.('input, select, button, summary, a')) return;
    if (key === ' ') {
      event.preventDefault();
      killBig(true);
      return;
    }
    if (key === 'c' && !event.repeat) {
      event.preventDefault();
      toggleVision(activeRobotTab);
      return;
    }
    if (key === 'l' && !event.repeat && activeRobotTab !== 'larp-b') {
      event.preventDefault();
      toggleLandmarks(activeRobotTab);
      return;
    }
    if (activeRobotTab === '3tsahur' && key === 'r' && !event.repeat) {
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
    for (const id of ['a', 'b']) {
      const motion = keyMotion(event, id);
      if (!motion) continue;
      event.preventDefault();
      if (event.repeat) return;
      scoutPressed[id].add(motion);
      renderScoutButtons(id);
      sendScout(id, activeScoutMotion(id));
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
    for (const id of ['a', 'b']) {
      const motion = keyMotion(event, id);
      if (!motion) continue;
      event.preventDefault();
      scoutPressed[id].delete(motion);
      renderScoutButtons(id);
      const nextMotion = activeScoutMotion(id);
      sendScout(id, nextMotion, nextMotion === 'stop');
      return;
    }
  });

  window.addEventListener('blur', () => killAll());
  document.addEventListener('visibilitychange', () => { if (document.hidden) killAll(); });
  window.addEventListener('pagehide', () => killAll());
  document.querySelector('#stop').addEventListener('click', () => killBig(true));
  document.querySelector('#kill-all').addEventListener('click', () => killAll(true));
  document.querySelectorAll('[data-vision-toggle]').forEach(button => button.addEventListener('click', () => toggleVision(button.dataset.visionToggle)));
  document.querySelectorAll('[data-landmark-toggle]').forEach(button => button.addEventListener('click', () => toggleLandmarks(button.dataset.landmarkToggle)));
  document.querySelector('#ramp-toggle').addEventListener('click', toggleRamp);
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
        sendScout(id, activeScoutMotion(id));
      });
      ['pointerup', 'pointercancel', 'lostpointercapture'].forEach(type => button.addEventListener(type, () => {
        scoutPressed[id].delete(motion);
        renderScoutButtons(id);
        const nextMotion = activeScoutMotion(id);
        sendScout(id, nextMotion, nextMotion === 'stop');
      }));
    });
  });

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
      const evidence = data.evidence || {};
      const cameraName = data.camera_name || 'USB camera';
      const cameraMode = `${data.camera_width}x${data.camera_height} @ ${data.camera_fps} FPS`;
      hubCameraModel.textContent = cameraName;
      hubCameraMode.textContent = data.camera_available ? `Automatic compatibility mode · ${cameraMode}` : 'Automatic detection is waiting for a camera';
      hubCameraLabel.textContent = `3TSahur · ${cameraName}`;
      document.querySelector('#health-panel').innerHTML = `<dt>Pi control</dt><dd>${hardwareReady ? 'ready' : 'simulation'}</dd><dt>Camera</dt><dd>${data.camera_available ? `${cameraName} · ${cameraMode}` : 'unavailable'} · ${data.camera_restart_count || 0} retries</dd><dt>Temperature</dt><dd>${temperature}</dd><dt>Power</dt><dd>${power}</dd><dt>Throttling</dt><dd>${throttle}</dd><dt>Storage</dt><dd>${disk}</dd><dt>Evidence</dt><dd>${(evidence.items || []).length} saved · ${evidence.queue_depth || 0} queued</dd><dt>Network</dt><dd>${location.host}</dd>`;
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

  function renderCsiSensor(id, data, online) {
    const sensor = document.querySelector(`#scout-${id}-csi`);
    const state = document.querySelector(`#scout-${id}-csi-state`);
    const levelOutput = document.querySelector(`#scout-${id}-csi-level`);
    const meter = document.querySelector(`#scout-${id}-csi-meter`);
    const meterTrack = meter.parentElement;
    const level = Math.max(0, Math.min(100, Number(data.motion_level) || 0));
    const detected = online && Boolean(data.motion);
    sensor.classList.toggle('detected', detected);
    meter.style.width = `${level}%`;
    meterTrack.setAttribute('aria-valuenow', String(Math.round(level)));
    levelOutput.value = online ? `${Math.round(level)}%` : '--';
    state.textContent = !online
      ? 'Awaiting Scout telemetry'
      : detected ? 'Possible presence - check video' : 'No strong disturbance';
  }

  async function refreshScout(id) {
    // Status/CSI is auxiliary. Do not compete with a held drive command on the
    // scout's Wi-Fi radio or HTTP server; the watchdog remains independent.
    if (scoutPressed[id].size) return;
    if (anyRobotMoving()) return;
    if (scoutStatusInFlight[id]) return;
    scoutStatusInFlight[id] = true;
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
      connectionElement.textContent = connected ? 'LARP connected to 3TSahur-Swarm' : 'Waiting for LARP heartbeat';
      motionElement.textContent = data.online
        ? `${data.motion ? 'CSI disturbance' : 'CSI idle'} / ${Math.round(data.motion_level || 0)}%`
        : connected ? 'Heartbeat received' : 'Scout not connected';
      renderCsiSensor(id, data, Boolean(data.online));
      sampleCalibration(id, Math.max(0, Math.min(100, Number(data.motion_level) || 0)));
    } catch (_) {
      panel.classList.remove('scout-connected');
      statusElement.classList.add('offline');
      statusElement.innerHTML = '<i></i> Waiting';
      connectionElement.textContent = 'Waiting for LARP heartbeat';
      motionElement.textContent = 'Scout not connected';
      renderCsiSensor(id, {}, false);
    } finally {
      scoutStatusInFlight[id] = false;
    }
  }

  // These are safety heartbeats, not a request flood: each channel retains
  // only its latest command and never builds a queue.
  window.setInterval(() => { if (bigPressed.size) sendBig(true); }, 80);
  window.setInterval(() => {
    for (const id of ['a', 'b']) if (scoutPressed[id].size) sendScout(id, activeScoutMotion(id));
  }, 80);
  window.setInterval(refreshStatus, 3000);
  // Inactive scouts already advertise UDP heartbeats. Poll them slowly for
  // optional CSI/UI freshness, reserving hotspot airtime for drive traffic.
  window.setInterval(() => { refreshScout('a'); refreshScout('b'); }, 5000);
  window.setInterval(() => {
    const id = activeRobotTab === 'larp-a' ? 'a' : activeRobotTab === 'larp-b' ? 'b' : null;
    if (id) refreshScout(id);
  }, 1200);
  window.setInterval(() => selectedCameras.forEach(refreshVision), 500);
  const deadman = document.querySelector('#deadman');
  let lastGamepadSignature = '';
  let lastGamepadSentAt = 0;
  const calibration = {a: null, b: null};
  function reportEvent(kind, source, message) { if (!anyRobotMoving()) fetch('/api/events', {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({kind, source, message}), cache: 'no-store'}).catch(() => {}); }
  async function refreshEvents() { if (anyRobotMoving()) return; try { const data = await (await fetch('/api/events', {cache: 'no-store'})).json(); document.querySelector('#event-list').innerHTML = (data.events || []).slice(0, 8).map(e => `<li><time>${new Date(e.at_ms).toLocaleTimeString()}</time> ${e.message}</li>`).join('') || '<li>No mission events yet.</li>'; } catch (_) {} }
  async function takeSnapshot(source) { if (anyRobotMoving()) { showToast('Stop the robots before taking a snapshot'); return; } try { const response = await fetch(`/api/snapshots/${source}`, {method: 'POST', cache: 'no-store'}); const data = await response.json(); if (!response.ok) throw Error(data.error); window.open(data.url, '_blank', 'noopener'); showToast('Snapshot saved'); refreshEvents(); } catch (error) { showToast(error.message || 'Snapshot unavailable'); } }
  async function saveEvidence(source) { if (anyRobotMoving()) { showToast('Stop the robots before saving evidence'); return; } try { const response = await fetch(`/api/evidence/${source}`, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({note: 'Operator evidence capture'}), cache: 'no-store'}); const data = await response.json(); if (!response.ok) throw Error(data.error); showToast('Evidence bundle queued'); refreshEvents(); } catch (error) { showToast(error.message || 'Evidence unavailable'); } }
  function startCalibration(id) { calibration[id] = {until: Date.now() + 20000, values: []}; document.querySelector(`#scout-${id}-calibration`).value = 'Calibrating… keep area clear'; reportEvent('calibration', `larp-${id}`, 'CSI calibration started'); }
  function sampleCalibration(id, level) { const item = calibration[id]; if (!item) return; item.values.push(level); if (Date.now() < item.until) return; const baseline = item.values.reduce((a, b) => a + b, 0) / Math.max(1, item.values.length); document.querySelector(`#scout-${id}-calibration`).value = `Baseline ${Math.round(baseline)}% · suggested alert ${Math.min(100, Math.round(baseline + 15))}%`; calibration[id] = null; refreshEvents(); }
  document.querySelectorAll('[data-snapshot]').forEach(button => button.addEventListener('click', () => takeSnapshot(button.dataset.snapshot)));
  document.querySelectorAll('[data-evidence]').forEach(button => button.addEventListener('click', () => saveEvidence(button.dataset.evidence)));
  document.querySelectorAll('[data-calibrate]').forEach(button => button.addEventListener('click', () => startCalibration(button.dataset.calibrate)));
  deadman.addEventListener('change', () => { killAll(); reportEvent('safety', 'dashboard', `Dead-man mode ${deadman.checked ? 'enabled' : 'disabled'}`); });
  autoPriority.addEventListener('change', () => { if (!autoPriority.checked) controlPriorityUntil = 0; applyControlPriority(); reportEvent('network', 'dashboard', `Adaptive control priority ${autoPriority.checked ? 'enabled' : 'disabled'}`); });
  window.addEventListener('keydown', event => { if (deadman.checked && event.key === 'Shift') document.body.dataset.deadman = 'held'; });
  window.addEventListener('keyup', event => { if (deadman.checked && event.key === 'Shift') { delete document.body.dataset.deadman; killAll(); } });
  window.setInterval(refreshEvents, 2000);
  window.setInterval(applyControlPriority, 250);
  window.setInterval(() => { const pad = navigator.getGamepads?.()[0]; if (!pad) return; const held = Boolean(pad.buttons[0]?.pressed); if (deadman.checked && !held) { delete document.body.dataset.deadman; if (gamepadWasMoving) killBig(); gamepadWasMoving = false; lastGamepadSignature = ''; return; } if (deadman.checked) document.body.dataset.deadman = 'held'; const forward = Math.abs(pad.axes[1] || 0) > .18 ? -(pad.axes[1] || 0) : 0; const strafe = Math.abs(pad.axes[0] || 0) > .18 ? pad.axes[0] : 0; const rotate = Math.abs(pad.axes[2] || 0) > .18 ? pad.axes[2] : 0; const moving = Boolean(forward || strafe || rotate); const command = {forward, strafe, rotate, speed: Number(speed.value) / 100}; const signature = JSON.stringify(command); const now = performance.now(); if (moving && (signature !== lastGamepadSignature || now - lastGamepadSentAt >= 80)) { sendBig(true, command); lastGamepadSignature = signature; lastGamepadSentAt = now; } else if (!moving && gamepadWasMoving) { sendBig(true, {forward: 0, strafe: 0, rotate: 0, speed: 0}, true); lastGamepadSignature = ''; } gamepadWasMoving = moving; }, 100);
  renderCameraSelection();
  refreshStatus();
  refreshScout('a');
  refreshScout('b');
  refreshEvents();
})();
