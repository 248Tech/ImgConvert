/* ImgConvert online demo: converts images locally with the Canvas API. Nothing is uploaded. */
(function () {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const drop = $('#drop'), fileIn = $('#file'), list = $('#list'), results = $('#results');
  const fmt = $('#fmt'), q = $('#q'), qv = $('#qv'), maxSel = $('#max'), go = $('#go'), zipBtn = $('#zip'), bar = $('#bar'), summary = $('#summary');
  const EXT = { jpeg: '.jpg', png: '.png', webp: '.webp' }, MIME = { jpeg: 'image/jpeg', png: 'image/png', webp: 'image/webp' };
  let items = [], seq = 0, busy = false;

  /* theme */
  const root = document.documentElement, themeBtn = $('#theme');
  const safe = { get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }, set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* ignore */ } } };
  function setTheme(t) { root.dataset.theme = t; themeBtn.textContent = t === 'light' ? '☾ Dark mode' : '☀ Light mode'; safe.set('imgconvert-theme', t); }
  setTheme(safe.get('imgconvert-theme') || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'));
  themeBtn.addEventListener('click', () => setTheme(root.dataset.theme === 'light' ? 'dark' : 'light'));

  const human = (n) => (n < 1024 ? n + ' B' : n < 1048576 ? (n / 1024).toFixed(1) + ' KB' : (n / 1048576).toFixed(2) + ' MB');
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  function sync() {
    $('#qwrap').style.display = fmt.value === 'png' ? 'none' : '';
    qv.textContent = q.value;
    go.disabled = busy || !items.length;
    zipBtn.disabled = !items.some((i) => i.blob);
    results.hidden = !items.length;
    const done = items.filter((i) => i.blob).length, fail = items.filter((i) => i.err).length;
    summary.textContent = items.length ? `${items.length} file${items.length === 1 ? '' : 's'} · ${done} converted${fail ? ' · ' + fail + ' failed' : ''}` : '';
  }
  function render() {
    list.innerHTML = '';
    for (const it of items) {
      const li = document.createElement('li');
      const saved = it.blob ? Math.round((1 - it.blob.size / it.file.size) * 100) : null;
      li.innerHTML = `<img alt="" src="${it.thumb}"><div><div class="n">${esc(it.file.name)}</div><div class="m">${human(it.file.size)}${it.blob ? ` → <strong>${human(it.blob.size)}</strong> <span class="${saved >= 0 ? 'ok' : 'muted'}">(${saved >= 0 ? '−' + saved : '+' + Math.abs(saved)}%)</span> · ${it.w}×${it.h}` : ''}</div>${it.err ? `<div class="m bad">${esc(it.err)}</div>` : ''}</div><div></div>`;
      if (it.blob) { const a = document.createElement('a'); a.className = 'btn'; a.textContent = 'Download'; a.href = it.url; a.download = it.outName; li.lastChild.appendChild(a); }
      list.appendChild(li);
    }
    sync();
  }

  async function addFiles(files) {
    for (const f of files) {
      if (!(f.type.startsWith('image/') || /\.(heic|heif|tiff?|avif|bmp|gif|webp|png|jpe?g)$/i.test(f.name))) continue;
      items.push({ id: ++seq, file: f, thumb: URL.createObjectURL(f), blob: null, err: '' });
    }
    render();
  }
  function collect(dt) {
    const out = [], walk = (entry) => new Promise((res) => {
      if (entry.isFile) entry.file((f) => { out.push(f); res(); }, res);
      else if (entry.isDirectory) entry.createReader().readEntries((es) => Promise.all(es.map(walk)).then(res), res);
      else res();
    });
    const entries = [...dt.items].map((i) => (i.webkitGetAsEntry ? i.webkitGetAsEntry() : null)).filter(Boolean);
    if (!entries.length) return Promise.resolve([...dt.files]);
    return Promise.all(entries.map(walk)).then(() => out);
  }

  drop.addEventListener('click', () => fileIn.click());
  drop.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileIn.click(); } });
  fileIn.addEventListener('change', () => { addFiles([...fileIn.files]); fileIn.value = ''; });
  ['dragenter', 'dragover'].forEach((ev) => drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add('over'); }));
  ['dragleave', 'drop'].forEach((ev) => drop.addEventListener(ev, () => drop.classList.remove('over')));
  drop.addEventListener('drop', (e) => { e.preventDefault(); collect(e.dataTransfer).then(addFiles); });
  $('#clear').addEventListener('click', () => { items.forEach((i) => { URL.revokeObjectURL(i.thumb); if (i.url) URL.revokeObjectURL(i.url); }); items = []; bar.style.width = '0'; render(); });
  q.addEventListener('input', sync); fmt.addEventListener('change', sync);

  async function convertOne(it) {
    if (it.url) { URL.revokeObjectURL(it.url); it.url = null; }
    it.blob = null; it.err = '';
    try {
      const bmp = await createImageBitmap(it.file); // honours EXIF orientation in modern browsers
      let w = bmp.width, h = bmp.height; const max = +maxSel.value;
      if (max && Math.max(w, h) > max) { const s = max / Math.max(w, h); w = Math.round(w * s); h = Math.round(h * s); }
      const c = document.createElement('canvas'); c.width = w; c.height = h; const g = c.getContext('2d');
      if (fmt.value === 'jpeg') { g.fillStyle = '#fff'; g.fillRect(0, 0, w, h); }
      g.imageSmoothingQuality = 'high'; g.drawImage(bmp, 0, 0, w, h); bmp.close && bmp.close();
      const blob = await new Promise((res) => c.toBlob(res, MIME[fmt.value], fmt.value === 'png' ? undefined : q.value / 100));
      if (!blob || blob.type !== MIME[fmt.value]) throw new Error('This browser cannot encode ' + fmt.value.toUpperCase() + '.');
      it.blob = blob; it.w = w; it.h = h; it.url = URL.createObjectURL(blob);
      it.outName = it.file.name.replace(/\.[^.]+$/, '') + EXT[fmt.value];
    } catch (e) {
      it.err = /decode|source|InvalidState|could not be/i.test(e.message || '') || e.name === 'InvalidStateError' ? 'Could not decode this file in the browser (HEIC/TIFF need the Windows app).' : (e.message || 'Conversion failed.');
    }
  }
  go.addEventListener('click', async () => {
    busy = true; sync(); bar.style.width = '0';
    const seen = {};
    for (let i = 0; i < items.length; i++) {
      await convertOne(items[i]);
      const it = items[i]; if (it.outName) { const k = it.outName.toLowerCase(); if (seen[k]) { const n = ++seen[k]; it.outName = it.outName.replace(/(\.[^.]+)$/, `-${n}$1`); } else seen[k] = 1; }
      bar.style.width = ((i + 1) / items.length) * 100 + '%'; render();
      await new Promise((r) => setTimeout(r, 0));
    }
    busy = false; sync();
  });

  /* minimal store-only ZIP writer */
  const CRC = (() => { const t = []; for (let n = 0; n < 256; n++) { let c = n; for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1; t[n] = c >>> 0; } return t; })();
  const crc32 = (u8) => { let c = 0xffffffff; for (let i = 0; i < u8.length; i++) c = CRC[(c ^ u8[i]) & 255] ^ (c >>> 8); return (c ^ 0xffffffff) >>> 0; };
  async function makeZip(files) {
    const enc = new TextEncoder(), parts = [], central = []; let offset = 0;
    for (const f of files) {
      const data = new Uint8Array(await f.blob.arrayBuffer()), name = enc.encode(f.name), crc = crc32(data);
      const lh = new DataView(new ArrayBuffer(30)); lh.setUint32(0, 0x04034b50, true); lh.setUint16(4, 20, true); lh.setUint16(6, 0x0800, true); lh.setUint32(14, crc, true); lh.setUint32(18, data.length, true); lh.setUint32(22, data.length, true); lh.setUint16(26, name.length, true);
      parts.push(lh.buffer, name, data);
      const ch = new DataView(new ArrayBuffer(46)); ch.setUint32(0, 0x02014b50, true); ch.setUint16(4, 20, true); ch.setUint16(6, 20, true); ch.setUint16(8, 0x0800, true); ch.setUint32(16, crc, true); ch.setUint32(20, data.length, true); ch.setUint32(24, data.length, true); ch.setUint16(28, name.length, true); ch.setUint32(42, offset, true);
      central.push(ch.buffer, name); offset += 30 + name.length + data.length;
    }
    const csize = central.reduce((s, b) => s + (b.byteLength !== undefined ? b.byteLength : b.length), 0);
    const end = new DataView(new ArrayBuffer(22)); end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true); end.setUint32(12, csize, true); end.setUint32(16, offset, true);
    return new Blob([...parts, ...central, end.buffer], { type: 'application/zip' });
  }
  zipBtn.addEventListener('click', async () => {
    const done = items.filter((i) => i.blob).map((i) => ({ name: i.outName, blob: i.blob }));
    const blob = await makeZip(done), a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'imgconvert-output.zip'; document.body.appendChild(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(a.href), 4000);
  });
  sync();
})();
