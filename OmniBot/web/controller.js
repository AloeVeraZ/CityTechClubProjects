(() => {
  const session = globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
  const pressed = new Set();
  const servoPressed = new Set();
  const enableButton = document.querySelector('#enable');
  const stopButton = document.querySelector('#stop');
  const servoCenterButton = document.querySelector('#servo-center');
  const title = document.querySelector('#status-title');
  const link = document.querySelector('#link');
  const source = document.querySelector('#source');
  const telemetry = document.querySelector('#telemetry');
  const servo = document.querySelector('#servo');
  const direction = document.querySelector('#direction');
  const dot = document.querySelector('#stick-dot');
  const toast = document.querySelector('#toast');
  let enabled = false;
  let sequence = 0;
  let serverClockOffset = 0;
  let activeRequest = null;
  let pendingCommand = null;
  let centerServo = false;
  let gamepadVector = null;
  let gamepadWasMoving = false;

  function showToast(message) {
    toast.textContent = message;
    toast.classList.add('visible');
    clearTimeout(showToast.timer);
    showToast.timer = setTimeout(() => toast.classList.remove('visible'), 2200);
  }

  function keyboardVector() {
    return {
      forward: (pressed.has('forward') ? 1 : 0) - (pressed.has('back') ? 1 : 0),
      strafe: (pressed.has('left') ? 1 : 0) - (pressed.has('right') ? 1 : 0),
      turn: (pressed.has('turn-left') ? 1 : 0) - (pressed.has('turn-right') ? 1 : 0),
      left_trigger: servoPressed.has('left') ? 1 : 0,
      right_trigger: servoPressed.has('right') ? 1 : 0,
    };
  }

  function currentVector() {
    const keys = keyboardVector();
    if (pressed.size || servoPressed.size || !gamepadVector) return keys;
    return gamepadVector;
  }

  function isActive(vector = currentVector()) {
    return Boolean(vector.forward || vector.strafe || vector.turn || vector.left_trigger || vector.right_trigger);
  }

  async function pump() {
    if (activeRequest || !pendingCommand) return;
    const command = pendingCommand;
    pendingCommand = null;
    const controller = new AbortController();
    activeRequest = controller;
    const timeout = setTimeout(() => controller.abort(), 180);
    try {
      const response = await fetch('/api/drive', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(command),
        cache: 'no-store',
        signal: controller.signal,
      });
      if (response.status === 409) {
        const data = await response.json().catch(() => ({}));
        if (data.disabled || data.session_mismatch || data.expired) enabled = false;
      } else if (!response.ok) {
        throw new Error(`control request failed (${response.status})`);
      }
    } catch (error) {
      if (error.name !== 'AbortError') showToast('Command link interrupted — robot watchdog will stop');
    } finally {
      clearTimeout(timeout);
      if (activeRequest === controller) activeRequest = null;
      pump();
    }
  }

  function queueDrive(urgent = false, override = null) {
    if (!enabled && !override) return;
    const vector = override || currentVector();
    pendingCommand = {
      ...vector,
      center_servo: centerServo,
      session,
      sequence: ++sequence,
      expires_at_ms: Math.round(Date.now() + serverClockOffset + 300),
    };
    centerServo = false;
    if (urgent && activeRequest) {
      activeRequest.abort();
      activeRequest = null;
    }
    updateInputDisplay(vector);
    pump();
  }

  async function enable() {
    try {
      const response = await fetch('/api/enable', {
        method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({session}), cache: 'no-store',
      });
      if (!response.ok) throw new Error();
      const data = await response.json();
      if (Number.isFinite(Number(data.server_time_ms))) {
        serverClockOffset = Number(data.server_time_ms) - Date.now();
      }
      enabled = true;
      sequence = 0;
      queueDrive(true, {forward: 0, strafe: 0, turn: 0, left_trigger: 0, right_trigger: 0});
      showToast('Wi-Fi control enabled — controls must be neutral briefly');
    } catch (_) {
      showToast('Could not enable Wi-Fi control');
    }
  }

  function stop(notify = false) {
    enabled = false;
    pressed.clear();
    servoPressed.clear();
    gamepadVector = null;
    updateButtons();
    updateInputDisplay({forward: 0, strafe: 0, turn: 0});
    if (activeRequest) activeRequest.abort();
    activeRequest = null;
    pendingCommand = null;
    fetch('/api/stop', {method: 'POST', keepalive: true, cache: 'no-store'}).catch(() => {});
    if (notify) showToast('Robot stopped and Wi-Fi control disabled');
  }

  const keyActions = {w: 'forward', a: 'left', s: 'back', d: 'right', q: 'turn-left', e: 'turn-right'};
  window.addEventListener('keydown', event => {
    if (event.repeat) return;
    const key = event.key.toLowerCase();
    if (key === 'enter') { event.preventDefault(); enable(); return; }
    if (key === ' ' || key === 'escape') { event.preventDefault(); stop(true); return; }
    if (key === 'x') { centerServo = true; queueDrive(true); return; }
    if (key === '[' || key === ']') {
      servoPressed.add(key === '[' ? 'left' : 'right');
      event.preventDefault(); updateButtons(); queueDrive(true); return;
    }
    if (keyActions[key]) {
      pressed.add(keyActions[key]);
      event.preventDefault(); updateButtons(); queueDrive(true);
    }
  });
  window.addEventListener('keyup', event => {
    const key = event.key.toLowerCase();
    if (key === '[' || key === ']') {
      servoPressed.delete(key === '[' ? 'left' : 'right');
      updateButtons(); queueDrive(true); return;
    }
    if (keyActions[key]) {
      pressed.delete(keyActions[key]);
      updateButtons(); queueDrive(true);
    }
  });

  function bindHold(button, collection, value) {
    const press = event => {
      event.preventDefault();
      collection.add(value);
      button.setPointerCapture?.(event.pointerId);
      updateButtons(); queueDrive(true);
    };
    const release = event => {
      event.preventDefault();
      collection.delete(value);
      updateButtons(); queueDrive(true);
    };
    button.addEventListener('pointerdown', press);
    button.addEventListener('pointerup', release);
    button.addEventListener('pointercancel', release);
    button.addEventListener('lostpointercapture', release);
  }
  document.querySelectorAll('[data-drive]').forEach(button => bindHold(button, pressed, button.dataset.drive));
  document.querySelectorAll('[data-servo]').forEach(button => bindHold(button, servoPressed, button.dataset.servo));
  enableButton.addEventListener('click', enable);
  stopButton.addEventListener('click', () => stop(true));
  servoCenterButton.addEventListener('click', () => { centerServo = true; queueDrive(true); });

  function updateButtons() {
    document.querySelectorAll('[data-drive]').forEach(button => button.classList.toggle('active', pressed.has(button.dataset.drive)));
    document.querySelectorAll('[data-servo]').forEach(button => button.classList.toggle('active', servoPressed.has(button.dataset.servo)));
  }

  function updateInputDisplay(vector) {
    const x = Math.max(-1, Math.min(1, -(vector.strafe || 0))) * 78;
    const y = Math.max(-1, Math.min(1, -(vector.forward || 0))) * 78;
    dot.style.transform = `translate(${x}px, ${y}px)`;
    if (vector.forward > 0) direction.textContent = 'Moving forward';
    else if (vector.forward < 0) direction.textContent = 'Moving backward';
    else if (vector.strafe > 0) direction.textContent = 'Strafing left';
    else if (vector.strafe < 0) direction.textContent = 'Strafing right';
    else if (vector.turn > 0) direction.textContent = 'Rotating left';
    else if (vector.turn < 0) direction.textContent = 'Rotating right';
    else direction.textContent = 'Standing by';
  }

  function readGamepad() {
    const pad = navigator.getGamepads?.()[0];
    if (!pad) {
      gamepadVector = null;
      const needsStop = gamepadWasMoving;
      gamepadWasMoving = false;
      return needsStop;
    }
    const deadzone = value => Math.abs(value || 0) > .15 ? value : 0;
    gamepadVector = {
      strafe: -deadzone(pad.axes[0]),
      forward: -deadzone(pad.axes[1]),
      turn: -deadzone(pad.axes[3] ?? pad.axes[2]),
      left_trigger: pad.buttons[6]?.value || 0,
      right_trigger: pad.buttons[7]?.value || 0,
    };
    const moving = isActive(gamepadVector);
    const needsCommand = moving || gamepadWasMoving;
    gamepadWasMoving = moving;
    return needsCommand;
  }

  async function refreshStatus() {
    try {
      const response = await fetch('/api/status', {cache: 'no-store'});
      if (!response.ok) throw new Error();
      const data = await response.json();
      serverClockOffset = Number(data.server_time_ms) - Date.now();
      enabled = Boolean(data.remote?.enabled && data.remote?.session === session);
      link.textContent = 'ONLINE'; link.className = 'pill online';
      source.textContent = `Control source: ${data.source || 'none'} · watchdog ${data.watchdog_ms} ms`;
      let label = data.enabled ? 'ENABLED' : 'DISABLED (Enable to drive)';
      if (data.enabled && !data.armed) label += ' — UNARMED (Center controls briefly)';
      title.textContent = `Status: ${label}`;
      const rows = Array.isArray(data.telemetry) ? data.telemetry : [];
      telemetry.replaceChildren(...(rows.length ? rows : ['Waiting for telemetry']).map(row => {
        const p = document.createElement('p'); p.textContent = row; return p;
      }));
      servo.textContent = data.servo || 'Servo 0 unavailable';
    } catch (_) {
      link.textContent = 'OFFLINE'; link.className = 'pill offline';
      title.textContent = 'Status: CONNECTION LOST — robot watchdog stopped drive';
    }
  }

  setInterval(() => {
    const gamepadNeedsCommand = readGamepad();
    if (enabled && (isActive() || gamepadNeedsCommand)) queueDrive(!isActive());
  }, 80);
  setInterval(refreshStatus, 250);
  window.addEventListener('blur', () => stop(false));
  window.addEventListener('pagehide', () => navigator.sendBeacon?.('/api/stop', new Blob([], {type: 'application/json'})));
  refreshStatus();
})();
