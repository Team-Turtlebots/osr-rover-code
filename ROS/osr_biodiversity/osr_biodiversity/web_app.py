"""Phone web page for Marpy: live camera view, Identify button, phone photo
upload, and the recent observations list.

create_app() takes plain callables instead of a ROS node, so the whole app can
be tested with Flask's test client and fakes (see test/test_web_app.py).
web_node.py supplies the real camera frames.
"""
import time

from flask import Flask, Response, jsonify, request, send_file

from .plantnet import ORGANS, PlantNetError

MAX_UPLOAD_BYTES = 25 * 1024 * 1024   # phone photos are usually 2-8 MB


def default_normalize_upload(data, max_side=2048, quality=90):
    """Decode an uploaded photo, shrink it so the longest side is max_side,
    and re-encode as JPEG. Raises ValueError if it isn't a readable image."""
    import cv2
    import numpy as np

    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("The rover couldn't read that file as a photo. Send a JPEG or PNG.")
    h, w = img.shape[:2]
    longest = max(h, w)
    if longest > max_side:
        scale = max_side / longest
        img = cv2.resize(img, (round(w * scale), round(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, quality])
    if not ok:
        raise ValueError("The rover couldn't save that photo.")
    return buf.tobytes()


def create_app(get_jpeg, store, identifier=None, get_status=None,
               stream_width=640, stream_fps=10.0, stream_quality=70,
               normalize_upload=default_normalize_upload):
    """
    get_jpeg(max_width=None, quality=None) -> bytes or None
        Latest camera frame as JPEG; None if no frame has arrived yet.
    store
        an observations.ObservationStore
    identifier(jpeg_bytes, organ) -> list of matches, or None if no API key
        Raises plantnet.PlantNetError on failure.
    get_status() -> dict
        Extra status fields (camera frame age, ...) for /api/status.
    """
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = MAX_UPLOAD_BYTES

    def requested_organ():
        organ = (request.form.get('organ') or 'auto').lower()
        return organ if organ in ORGANS else 'auto'

    def run_identification(row, jpeg):
        if identifier is None:
            return {'observation': row, 'results': [],
                    'message': 'Photo saved. No Pl@ntNet API key is set up on the rover, '
                               'so it is waiting to be identified.'}
        try:
            results = identifier(jpeg, row['organ'])
        except PlantNetError as e:
            row = store.update(row['id'], notes=str(e))
            return {'observation': row, 'results': [],
                    'message': f'Photo saved, not identified yet. {e}'}
        row = store.apply_results(row['id'], results)
        message = ('Identified.' if results else
                   'No match. Try a closer photo, or choose which plant part is in view.')
        return {'observation': row, 'results': results, 'message': message}

    @app.get('/')
    def index():
        return Response(PAGE_HTML, mimetype='text/html')

    @app.get('/stream')
    def stream():
        def frames():
            period = 1.0 / max(stream_fps, 0.5)
            while True:
                jpeg = get_jpeg(max_width=stream_width, quality=stream_quality)
                if jpeg:
                    yield (b'--frame\r\nContent-Type: image/jpeg\r\n'
                           b'Content-Length: ' + str(len(jpeg)).encode() + b'\r\n\r\n'
                           + jpeg + b'\r\n')
                time.sleep(period)
        return Response(frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

    @app.get('/snapshot.jpg')
    def snapshot():
        jpeg = get_jpeg(max_width=stream_width, quality=stream_quality)
        if not jpeg:
            return jsonify(error='No camera image yet.'), 503
        return Response(jpeg, mimetype='image/jpeg', headers={'Cache-Control': 'no-store'})

    @app.post('/api/identify')
    def identify_from_camera():
        jpeg = get_jpeg()          # full resolution
        if not jpeg:
            return jsonify(error='No camera image yet. Check the camera is plugged in '
                                 'and the camera node is running.'), 503
        row = store.add_photo(jpeg, source='rover', organ=requested_organ())
        return jsonify(run_identification(row, jpeg))

    @app.post('/api/upload')
    def identify_from_upload():
        upload = request.files.get('photo')
        if upload is None or not upload.filename:
            return jsonify(error='No photo was attached.'), 400
        try:
            jpeg = normalize_upload(upload.read())
        except ValueError as e:
            return jsonify(error=str(e)), 400
        row = store.add_photo(jpeg, source='phone', organ=requested_organ())
        return jsonify(run_identification(row, jpeg))

    @app.post('/api/retry')
    def retry_pending():
        pending = store.pending()
        identified = 0
        last_message = ''
        for row in pending:
            try:
                jpeg = store.read_photo(row['photo'])
            except (OSError, ValueError) as e:
                store.update(row['id'], notes=f'photo missing: {e}')
                continue
            outcome = run_identification(row, jpeg)
            last_message = outcome['message']
            if outcome['observation']['status'] != 'pending':
                identified += 1
        still_pending = len(store.pending())
        if not pending:
            message = 'Nothing is waiting to be identified.'
        elif still_pending:
            message = f'Identified {identified} of {len(pending)}. {last_message}'
        else:
            message = f'Identified all {len(pending)} waiting photos.'
        return jsonify(retried=len(pending), identified=identified,
                       still_pending=still_pending, message=message)

    @app.get('/api/observations')
    def observations():
        try:
            limit = max(0, min(int(request.args.get('limit', 20)), 500))
        except ValueError:
            limit = 20
        return jsonify(observations=store.recent(limit))

    @app.get('/api/status')
    def status():
        info = {'plantnet_ready': identifier is not None,
                'pending': len(store.pending())}
        if get_status:
            info.update(get_status())
        return jsonify(info)

    @app.get('/photos/<path:rel_path>')
    def photo(rel_path):
        try:
            path = store.photo_path(rel_path)
        except ValueError:
            return jsonify(error='Not found.'), 404
        try:
            return send_file(path, mimetype='image/jpeg')
        except FileNotFoundError:
            return jsonify(error='Not found.'), 404

    @app.get('/observations.csv')
    def observations_csv():
        return send_file(store.csv_path, mimetype='text/csv', as_attachment=True,
                         download_name='marpy_observations.csv')

    return app


PAGE_HTML = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Marpy Field Station</title>
<style>
:root { --bg:#f3f5f1; --card:#ffffff; --fg:#1a231c; --muted:#5b685e; --line:#d6dcd3;
        --accent:#2e7a4d; --accent-fg:#ffffff; --warn:#9a5d14; --err:#b23a2d; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#111612; --card:#1a211c; --fg:#e3eae4; --muted:#9aa79c; --line:#2b352e;
          --accent:#5dbd85; --accent-fg:#0c1a11; --warn:#e2a95b; --err:#f07d6d; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
       font: 16px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 720px; margin: 0 auto; padding: 12px 16px 48px;
       display:flex; flex-direction:column; gap:14px; }
header { display:flex; align-items:baseline; justify-content:space-between; gap:12px; flex-wrap:wrap; }
h1 { margin:0; font-size:26px; letter-spacing:.01em; }
h2 { margin:0; font-size:18px; }
.muted { color:var(--muted); font-size:14px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:14px;
        display:flex; flex-direction:column; gap:10px; }
#live { width:100%; aspect-ratio: 4 / 3; object-fit: contain; background:#000; border-radius:8px; }
.label { font-size:13px; text-transform:uppercase; letter-spacing:.06em; color:var(--muted); }
.organs { display:flex; flex-wrap:wrap; gap:8px; }
button, .button { font:inherit; border:1px solid var(--line); background:var(--bg); color:var(--fg);
                  border-radius:999px; padding:9px 14px; cursor:pointer; text-decoration:none;
                  display:inline-flex; align-items:center; justify-content:center; }
button[aria-pressed="true"] { background:var(--accent); color:var(--accent-fg); border-color:var(--accent); }
.primary { background:var(--accent); color:var(--accent-fg); border-color:var(--accent);
           font-weight:600; padding:13px 18px; border-radius:10px; }
.actions { display:grid; grid-template-columns: 1fr 1fr; gap:10px; }
.actions > * { border-radius:10px; padding:13px 12px; }
button:disabled { opacity:.55; cursor:wait; }
button:focus-visible, .button:focus-visible { outline:3px solid var(--accent); outline-offset:2px; }
#message.err { color:var(--err); } #message.warn { color:var(--warn); }
.match { display:flex; justify-content:space-between; gap:10px; padding:8px 0; border-top:1px solid var(--line); }
.match:first-of-type { border-top:0; }
.sci { font-style:italic; font-weight:600; }
.score { font-variant-numeric: tabular-nums; font-weight:600; white-space:nowrap; }
.row { display:flex; justify-content:space-between; align-items:center; gap:10px; flex-wrap:wrap; }
ul { list-style:none; margin:0; padding:0; display:flex; flex-direction:column; gap:10px; }
li { display:grid; grid-template-columns: 64px 1fr; gap:10px; align-items:center; }
li img { width:64px; height:64px; object-fit:cover; border-radius:8px; background:var(--line); }
.pill { font-size:12px; border-radius:999px; padding:2px 8px; border:1px solid var(--line); }
.pill.pending { color:var(--warn); border-color:var(--warn); }
.pill.no_match { color:var(--muted); }
.pill.identified { color:var(--accent); border-color:var(--accent); }
.result-photo { width:100%; border-radius:8px; }
</style>
</head>
<body>
<main>
  <header>
    <h1>Marpy Field Station</h1>
    <span id="status" class="muted">Connecting to rover…</span>
  </header>

  <section class="card">
    <img id="live" src="/stream" alt="Live view from the rover camera">
    <span id="liveNote" class="muted"></span>
  </section>

  <section class="card">
    <span class="label">Plant part in view</span>
    <div class="organs" id="organs">
      <button type="button" data-organ="auto" aria-pressed="true">Not sure</button>
      <button type="button" data-organ="leaf" aria-pressed="false">Leaf</button>
      <button type="button" data-organ="flower" aria-pressed="false">Flower</button>
      <button type="button" data-organ="fruit" aria-pressed="false">Fruit</button>
      <button type="button" data-organ="bark" aria-pressed="false">Bark</button>
    </div>
    <div class="actions">
      <button type="button" id="identify" class="primary">Identify from rover</button>
      <label class="button" for="upload" id="uploadLabel">Use phone photo</label>
      <input id="upload" type="file" accept="image/*" capture="environment" hidden>
    </div>
    <span id="message" class="muted" role="status"></span>
  </section>

  <section class="card" id="result" hidden></section>

  <section class="card">
    <div class="row">
      <h2>Recent observations</h2>
      <div class="row">
        <button type="button" id="retry">Retry waiting</button>
        <a class="button" href="/observations.csv">Download CSV</a>
      </div>
    </div>
    <ul id="recent"><li class="muted" style="display:block">No observations yet. Point the camera at a plant and tap Identify.</li></ul>
  </section>
</main>
<script>
const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const pct = s => (s === '' || s == null) ? '' : Math.round(parseFloat(s) * 100) + '%';
let organ = 'auto';

document.querySelectorAll('[data-organ]').forEach(btn => btn.addEventListener('click', () => {
  organ = btn.dataset.organ;
  document.querySelectorAll('[data-organ]').forEach(b => b.setAttribute('aria-pressed', String(b === btn)));
}));

function say(text, kind) { const m = $('message'); m.textContent = text; m.className = kind || 'muted'; }

async function post(url, body) {
  const r = await fetch(url, { method: 'POST', body });
  const j = await r.json().catch(() => ({ error: 'The rover sent an unexpected reply.' }));
  if (!r.ok) throw new Error(j.error || ('Request failed (' + r.status + ')'));
  return j;
}

function showResult(j) {
  const o = j.observation, box = $('result');
  const matches = (j.results || []).map(r => `
    <div class="match"><div><div class="sci">${esc(r.scientific_name)}</div>
    <div class="muted">${esc(r.common_name)}${r.family ? ' · ' + esc(r.family) : ''}</div></div>
    <div class="score">${pct(r.score)}</div></div>`).join('');
  box.innerHTML = `
    <div class="row"><h2>Observation #${esc(o.id)}</h2><span class="pill ${esc(o.status)}">${esc(o.status.replace('_', ' '))}</span></div>
    <img class="result-photo" src="/photos/${esc(o.photo)}" alt="Photo for observation ${esc(o.id)}">
    ${matches || '<span class="muted">' + esc(j.message) + '</span>'}
    <a class="button" href="/photos/${esc(o.photo)}" download="marpy_${esc(o.id)}.jpg">Save photo to phone</a>`;
  box.hidden = false;
  say(j.message, o.status === 'pending' ? 'warn' : 'muted');
}

async function run(button, url, body) {
  button.disabled = true; say('Identifying…');
  try { showResult(await post(url, body)); }
  catch (e) { say(e.message, 'err'); }
  finally { button.disabled = false; loadRecent(); loadStatus(); }
}

$('identify').addEventListener('click', () => {
  const fd = new FormData(); fd.append('organ', organ);
  run($('identify'), '/api/identify', fd);
});

$('upload').addEventListener('change', () => {
  const file = $('upload').files[0]; if (!file) return;
  const fd = new FormData(); fd.append('organ', organ); fd.append('photo', file);
  run($('identify'), '/api/upload', fd);
  $('upload').value = '';
});

$('retry').addEventListener('click', async () => {
  $('retry').disabled = true; say('Retrying waiting photos…');
  try { const j = await post('/api/retry', new FormData()); say(j.message, j.still_pending ? 'warn' : 'muted'); }
  catch (e) { say(e.message, 'err'); }
  finally { $('retry').disabled = false; loadRecent(); loadStatus(); }
});

async function loadRecent() {
  try {
    const j = await (await fetch('/api/observations?limit=15')).json();
    if (!j.observations.length) return;
    $('recent').innerHTML = j.observations.map(o => `
      <li><a href="/photos/${esc(o.photo)}"><img src="/photos/${esc(o.photo)}" alt="Observation ${esc(o.id)}" loading="lazy"></a>
      <div><div class="row"><span class="sci">${esc(o.scientific_name || 'Not identified yet')}</span>
      <span class="score">${pct(o.score)}</span></div>
      <div class="muted">${esc(o.common_name)}${o.common_name ? ' · ' : ''}#${esc(o.id)} · ${esc(o.source)} · ${esc(o.time.replace('T', ' '))}
      <span class="pill ${esc(o.status)}">${esc(o.status.replace('_', ' '))}</span></div></div></li>`).join('');
  } catch (e) { /* keep the old list */ }
}

async function loadStatus() {
  try {
    const s = await (await fetch('/api/status')).json();
    const parts = [];
    parts.push(s.camera_ok ? 'Camera live' : 'No camera image');
    parts.push(s.plantnet_ready ? 'Pl@ntNet ready' : 'No Pl@ntNet key');
    if (s.pending) parts.push(s.pending + ' waiting');
    $('status').textContent = parts.join(' · ');
  } catch (e) { $('status').textContent = 'Rover not reachable'; }
}

// Some browsers drop MJPEG streams; fall back to refreshing a snapshot.
let polling = false;
$('live').addEventListener('error', () => {
  if (polling) return; polling = true;
  $('liveNote').textContent = 'Showing snapshots (live stream unavailable).';
  setInterval(() => { $('live').src = '/snapshot.jpg?t=' + Date.now(); }, 700);
});

loadStatus(); loadRecent();
setInterval(loadStatus, 5000);
</script>
</body>
</html>
"""
