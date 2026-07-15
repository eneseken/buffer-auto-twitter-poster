from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify, render_template_string, request

import posts_store
import scheduler_core

app = Flask(__name__)

EDITABLE_FIELDS = ["datum", "uhrzeit", "plattform", "caption", "media_url", "hashtags", "status"]

PAGE = """
<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>Buffer Kuyruk Yöneticisi</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 1100px; margin: 40px auto; padding: 0 20px; }
  .toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 16px; }
  .toolbar input[type=number] { width: 60px; padding: 6px; }
  button { padding: 8px 14px; cursor: pointer; }
  table { width: 100%; border-collapse: collapse; user-select: none; }
  th, td { border: 1px solid #ddd; padding: 0; text-align: left; font-size: 14px; position: relative; }
  th { background: #f4f4f4; padding: 8px; }
  td.cell { position: relative; }
  td.cell input { width: 100%; box-sizing: border-box; border: none; padding: 8px; font-size: 14px; font-family: inherit; background: transparent; }
  td.cell input:focus { outline: 2px solid #4285f4; outline-offset: -2px; }
  td.id-col { padding: 8px; color: #888; }
  .fill-handle { position: absolute; width: 8px; height: 8px; background: #4285f4; right: -1px; bottom: -1px; cursor: crosshair; z-index: 2; }
  td.cell.highlight { background: #e8f0fe; }
  .status-pending input { color: #b8860b; }
  .status-queued input { color: #2e7d32; }
  .status-posted input { color: #888; }
  .del-btn { border: none; background: none; color: #c0392b; cursor: pointer; font-size: 16px; }
  .log { background: #f0f0f0; padding: 10px; margin-top: 20px; white-space: pre-wrap; font-family: monospace; font-size: 13px; }
  .hint { color: #888; font-size: 13px; margin-bottom: 10px; }
</style>
</head>
<body>
  <h1>Buffer Kuyruk Yöneticisi</h1>
  <p class="hint">Hücreye tıklayıp yaz, otomatik kaydedilir. Bir hücreyi seçince sağ alt köşesindeki mavi noktayı aşağı sürükleyerek değeri diğer satırlara kopyalayabilirsin (Sheets'teki gibi).</p>

  <div class="toolbar">
    <button id="addRowsBtn" type="button">+ Satır ekle</button>
    <input type="number" id="addRowsCount" value="5" min="1" max="100">
    <button id="runBtn" type="button">Kuyruğu şimdi doldur</button>
  </div>

  <div id="log" class="log" style="display:none;"></div>

  <table id="grid">
    <thead>
      <tr>
        <th>ID</th>
        <th>Datum</th><th>Uhrzeit</th><th>Plattform</th>
        <th>Caption</th><th>Media URL</th><th>Hashtags</th><th>Status</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {% for p in posts %}
      <tr data-id="{{ p.id }}" class="status-{{ p.status }}">
        <td class="id-col">{{ p.id }}</td>
        {% for field in fields %}
        <td class="cell" data-field="{{ field }}">
          <input class="cell-input" value="{{ p[field] }}">
          <div class="fill-handle"></div>
        </td>
        {% endfor %}
        <td><button class="del-btn" data-id="{{ p.id }}" title="Sil">✕</button></td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

<script>
const FIELDS = {{ fields|tojson }};

function saveCell(input) {
  const td = input.closest('td');
  const tr = input.closest('tr');
  const field = td.dataset.field;
  const id = tr.dataset.id;
  tr.className = tr.className.replace(/status-\\S+/, '') + ' status-' + (field === 'status' ? input.value.trim() : tr.dataset.status || '');
  fetch('/update_cell', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({id: id, field: field, value: input.value}),
  });
}

document.querySelectorAll('.cell-input').forEach(input => {
  input.addEventListener('change', () => saveCell(input));
});

// --- Fill handle (Sheets-style drag to copy a value down a column) ---
let fillState = null;

function cellsInColumn(field) {
  return Array.from(document.querySelectorAll(`td.cell[data-field="${field}"]`));
}

function clearHighlight() {
  document.querySelectorAll('td.cell.highlight').forEach(td => td.classList.remove('highlight'));
}

document.querySelectorAll('.fill-handle').forEach(handle => {
  handle.addEventListener('mousedown', (e) => {
    e.preventDefault();
    const td = handle.closest('td');
    const field = td.dataset.field;
    const input = td.querySelector('.cell-input');
    const cells = cellsInColumn(field);
    fillState = { field, value: input.value, cells, startIndex: cells.indexOf(td) };
  });
});

document.addEventListener('mousemove', (e) => {
  if (!fillState) return;
  const el = document.elementFromPoint(e.clientX, e.clientY);
  const td = el ? el.closest(`td.cell[data-field="${fillState.field}"]`) : null;
  clearHighlight();
  if (!td) return;
  const endIndex = fillState.cells.indexOf(td);
  if (endIndex === -1) return;
  const [lo, hi] = [Math.min(fillState.startIndex, endIndex), Math.max(fillState.startIndex, endIndex)];
  for (let i = lo; i <= hi; i++) fillState.cells[i].classList.add('highlight');
});

document.addEventListener('mouseup', (e) => {
  if (!fillState) return;
  const el = document.elementFromPoint(e.clientX, e.clientY);
  const td = el ? el.closest(`td.cell[data-field="${fillState.field}"]`) : null;
  if (td) {
    const endIndex = fillState.cells.indexOf(td);
    if (endIndex !== -1) {
      const [lo, hi] = [Math.min(fillState.startIndex, endIndex), Math.max(fillState.startIndex, endIndex)];
      for (let i = lo; i <= hi; i++) {
        const input = fillState.cells[i].querySelector('.cell-input');
        input.value = fillState.value;
        saveCell(input);
      }
    }
  }
  clearHighlight();
  fillState = null;
});

// --- Toolbar actions ---
document.getElementById('addRowsBtn').addEventListener('click', async () => {
  const count = parseInt(document.getElementById('addRowsCount').value, 10) || 1;
  await fetch('/add_rows', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({count}),
  });
  location.reload();
});

document.querySelectorAll('.del-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    await fetch('/delete_row', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({id: btn.dataset.id}),
    });
    location.reload();
  });
});

document.getElementById('runBtn').addEventListener('click', async () => {
  const btn = document.getElementById('runBtn');
  btn.disabled = true;
  btn.textContent = 'Çalışıyor...';
  const res = await fetch('/run', { method: 'POST' });
  const data = await res.json();
  const logEl = document.getElementById('log');
  logEl.style.display = 'block';
  logEl.textContent = data.log.join('\\n');
  btn.disabled = false;
  btn.textContent = 'Kuyruğu şimdi doldur';
});
</script>
</body>
</html>
"""


@app.route("/")
def index():
    posts = sorted(posts_store.all_posts(), key=lambda p: p["id"])
    return render_template_string(PAGE, posts=posts, fields=EDITABLE_FIELDS)


@app.route("/update_cell", methods=["POST"])
def update_cell():
    data = request.get_json()
    field = data["field"]
    if field not in EDITABLE_FIELDS:
        return jsonify({"ok": False, "error": "invalid field"}), 400
    posts_store.update_field(int(data["id"]), field, data["value"])
    return jsonify({"ok": True})


@app.route("/add_rows", methods=["POST"])
def add_rows():
    data = request.get_json(silent=True) or {}
    count = max(1, min(100, int(data.get("count", 1))))
    ids = posts_store.add_blank_rows(count)
    return jsonify({"ok": True, "ids": ids})


@app.route("/delete_row", methods=["POST"])
def delete_row():
    data = request.get_json()
    posts_store.delete_post(int(data["id"]))
    return jsonify({"ok": True})


@app.route("/run", methods=["POST"])
def run():
    log = scheduler_core.fill_queue()
    return jsonify({"log": log})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
