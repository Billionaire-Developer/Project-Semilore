(function () {
  'use strict';

  const config = window.AUDIT_SCANNER_CONFIG || {};
  const sessionId = config.sessionId;
  const verifyUrl = config.verifyUrl;
  const csrfToken = config.csrfToken;
  const lookupUrl = config.lookupUrl;

  const queueKey = `audit_queue_${sessionId}`;
  const offlineBanner = document.getElementById('offline-banner');
  const lastScanEl = document.getElementById('last-scan');
  const progressBar = document.getElementById('audit-progress-bar');
  const progressText = document.getElementById('audit-progress-text');
  const manualUidForm = document.getElementById('manual-uid-form');

  function getQueue() {
    try {
      return JSON.parse(localStorage.getItem(queueKey) || '[]');
    } catch (e) {
      return [];
    }
  }

  function saveQueue(queue) {
    localStorage.setItem(queueKey, JSON.stringify(queue));
  }

  function updateOfflineBanner() {
    if (!offlineBanner) return;
    offlineBanner.classList.toggle('show', !navigator.onLine || getQueue().length > 0);
    if (!navigator.onLine) {
      offlineBanner.textContent = 'Offline — scans will retry when reconnected';
    } else if (getQueue().length > 0) {
      offlineBanner.textContent = `Retrying ${getQueue().length} pending verification(s)…`;
    }
  }

  function updateProgress(data) {
    if (!data || !data.progress) return;
    const pct = data.progress.pct || 0;
    if (progressBar) {
      progressBar.style.width = pct + '%';
      progressBar.textContent = pct + '%';
    }
    if (progressText) {
      progressText.textContent = `${data.progress.verified} / ${data.progress.expected} verified`;
    }
  }

  function showLastScan(item, ok, message) {
    if (!lastScanEl) return;
    const cls = ok ? 'text-success' : 'text-danger';
    lastScanEl.innerHTML = `<span class="${cls}">${message || (ok ? '✓' : '✗')} ${item ? item.uid + ' — ' + item.name : ''}</span>`;
  }

  async function postVerify(payload) {
    const body = new FormData();
    Object.entries(payload).forEach(([k, v]) => body.append(k, v));
    const resp = await fetch(verifyUrl, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken },
      body,
      credentials: 'same-origin',
    });
    const data = await resp.json();
    if (!resp.ok || !data.ok) {
      throw new Error(data.error || data.detail || 'Verification failed');
    }
    return data;
  }

  async function verifyItem(itemUuid, scanMethod) {
    const payload = {
      item_uuid: itemUuid,
      status: 'verified',
      scan_method: scanMethod || 'qr_scan',
    };

    if (!navigator.onLine) {
      const queue = getQueue();
      queue.push(payload);
      saveQueue(queue);
      updateOfflineBanner();
      showLastScan({ uid: itemUuid.slice(0, 8) + '…' }, false, 'Queued (offline)');
      return;
    }

    try {
      const data = await postVerify(payload);
      showLastScan(data.item, true, '✓');
      updateProgress(data);
    } catch (err) {
      const queue = getQueue();
      queue.push(payload);
      saveQueue(queue);
      updateOfflineBanner();
      showLastScan(null, false, err.message);
    }
  }

  async function flushQueue() {
    if (!navigator.onLine) return;
    let queue = getQueue();
    if (!queue.length) {
      updateOfflineBanner();
      return;
    }
    updateOfflineBanner();
    const remaining = [];
    for (const payload of queue) {
      try {
        const data = await postVerify(payload);
        showLastScan(data.item, true, '✓ (synced)');
        updateProgress(data);
      } catch (err) {
        remaining.push(payload);
      }
    }
    saveQueue(remaining);
    updateOfflineBanner();
  }

  function extractUuidFromScan(decodedText) {
    const uuidRe = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
    const match = decodedText.match(uuidRe);
    if (match) return match[0];
    return decodedText.trim();
  }

  function initScanner() {
    const readerEl = document.getElementById('qr-reader');
    if (!readerEl || typeof Html5Qrcode === 'undefined') return;

    const scanner = new Html5Qrcode('qr-reader');
    const configScan = { fps: 10, qrbox: { width: 250, height: 250 } };

    scanner.start(
      { facingMode: 'environment' },
      configScan,
      (decodedText) => {
        const uuid = extractUuidFromScan(decodedText);
        verifyItem(uuid, 'qr_scan');
      },
      () => {}
    ).catch((err) => {
      readerEl.innerHTML = `<div class="alert alert-warning">Camera unavailable: ${err}. Use manual UID entry.</div>`;
    });
  }

  if (manualUidForm) {
    manualUidForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const uid = document.getElementById('manual-uid-input').value.trim();
      if (!uid) return;
      try {
        const resp = await fetch(`${lookupUrl}?uid=${encodeURIComponent(uid)}`, { credentials: 'same-origin' });
        const data = await resp.json();
        if (!data.ok) throw new Error(data.error || 'Not found');
        await verifyItem(data.item.uuid, 'manual_uid');
      } catch (err) {
        showLastScan(null, false, err.message);
      }
    });
  }

  window.addEventListener('online', flushQueue);
  document.addEventListener('DOMContentLoaded', () => {
    updateOfflineBanner();
    flushQueue();
    initScanner();
  });
})();
