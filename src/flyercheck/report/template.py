"""Jinja2 template for the self-contained HTML report (inline CSS/JS, no external resources)."""

REPORT_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FlyerCheck report — {{ filename }}</title>
<style>
:root{--fail:#d32f2f;--needs_review:#f59e0b;--error:#7e3ff2;--not_evaluable:#8a8f98;--pass:#2e9d4f;
--border:#e3e5e8;--muted:#5f6670;--bg:#f7f8fa;--fg:#1d2330}
*{box-sizing:border-box}
body{margin:0;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--fg)}
header,footer{padding:16px 24px;background:#fff;border-bottom:1px solid var(--border)}
footer{border-top:1px solid var(--border);border-bottom:0;color:var(--muted);font-size:12px}
h1{font-size:20px;margin:0 0 4px}
.meta{color:var(--muted);font-size:13px;display:flex;flex-wrap:wrap;gap:4px 16px}
.meta b{color:var(--fg);font-weight:600}
.chips{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}
.chip{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:600;color:#fff;white-space:nowrap}
.s-fail{background:var(--fail)}.s-needs_review{background:var(--needs_review)}.s-error{background:var(--error)}
.s-not_evaluable{background:var(--not_evaluable)}.s-pass{background:var(--pass)}
main{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:20px;padding:20px 24px}
@media (max-width:1000px){main{grid-template-columns:1fr;padding:16px}}
.panel{background:#fff;border:1px solid var(--border);border-radius:8px;padding:12px;min-width:0}
.panel.findings{overflow-x:auto}
.page{position:relative;margin-bottom:12px;line-height:0}
.page img{width:100%;height:auto;display:block}
.page svg{position:absolute;inset:0;width:100%;height:100%}
.placeholder{display:flex;align-items:center;justify-content:center;background:#eef0f3;color:var(--muted);
border:1px dashed #b9bec6;line-height:1.4;text-align:center;padding:12px;width:100%}
rect.box{stroke-width:2;vector-effect:non-scaling-stroke;cursor:pointer}
rect.box.st-fail{stroke:var(--fail);fill:rgba(211,47,47,.12)}
rect.box.st-needs_review{stroke:var(--needs_review);fill:rgba(245,158,11,.12)}
rect.box.st-error{stroke:var(--error);fill:rgba(126,63,242,.12)}
rect.box.st-not_evaluable{stroke:var(--not_evaluable);fill:rgba(138,143,152,.12)}
rect.box.st-pass{stroke:var(--pass);fill:rgba(46,157,79,.10);display:none}
body.show-passes rect.box.st-pass{display:inline}
body:not(.show-passes) tr.st-pass{display:none}
rect.box.hl{stroke-width:5;fill-opacity:.35}
.toolbar{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px;font-size:13px;color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;vertical-align:top;padding:6px 8px;border-bottom:1px solid var(--border)}
th{font-size:12px;color:var(--muted);font-weight:600;background:#fff}
tbody tr{cursor:pointer}
tbody tr:hover,tbody tr.hl{background:#fff7e0}
td.kv{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px;color:#333}
.arrow{color:var(--muted);margin:2px 0}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12px}
.sev{text-transform:uppercase;font-size:11px;font-weight:600;color:var(--muted)}
.sev-critical,.sev-high{color:var(--fail)}
.disclaimer{margin-top:8px;font-weight:600;color:var(--fg)}
</style>
</head>
<body>
<header>
  <h1>FlyerCheck report</h1>
  <div class="meta">
    <span>Document <b>{{ filename }}</b></span>
    <span>Run <b class="mono">{{ run.run_id }}</b></span>
    <span>Mode <b>{{ run.mode }}</b></span>
    <span>Model <b>{{ model }}</b></span>
    <span>Duration <b>{{ "%.1f"|format(run.duration_s) }} s</b></span>
    <span>Started <b>{{ run.started_at.strftime("%Y-%m-%d %H:%M:%S") }}</b></span>
    {% if run.llm_usage %}<span>LLM usage <b>{% for k, v in run.llm_usage.items() %}{{ k }}={{ v }}{% if not loop.last %}, {% endif %}{% endfor %}</b></span>{% endif %}
  </div>
  <div class="chips">
    {% for status, n in chips %}<span class="chip s-{{ status }}">{{ status|replace("_", " ") }}: {{ n }}</span>{% endfor %}
  </div>
</header>
<main>
  <section class="panel">
    {% for page in pages %}
    <div class="page" data-page="{{ page.number }}">
      {% if page.src %}
      <img src="{{ page.src }}" alt="Page {{ page.number }}" width="{{ page.width }}" height="{{ page.height }}">
      {% else %}
      <div class="placeholder" style="aspect-ratio:{{ page.width }}/{{ page.height }}">Page {{ page.number }} image not available<br>{{ page.path }}</div>
      {% endif %}
      <svg viewBox="0 0 1 1" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
        {% for r in page.rects %}<rect class="box st-{{ r.status }}" data-finding-id="{{ r.fid }}" x="{{ r.x }}" y="{{ r.y }}" width="{{ r.w }}" height="{{ r.h }}" vector-effect="non-scaling-stroke"><title>{{ r.title }}</title></rect>
        {% endfor %}
      </svg>
    </div>
    {% endfor %}
  </section>
  <section class="panel findings">
    <div class="toolbar">
      <span>{{ findings|length }} findings</span>
      <label><input type="checkbox" id="show-passes"> show passes</label>
    </div>
    <table>
      <thead><tr><th>Status</th><th>Severity</th><th>Check</th><th>Offer</th><th>Summary</th><th>Observed → expected</th><th>Conf.</th></tr></thead>
      <tbody>
      {% for f in findings %}
        <tr class="st-{{ f.status.value }}" data-finding-id="{{ f.id }}">
          <td><span class="chip s-{{ f.status.value }}">{{ f.status.value|replace("_", " ") }}</span></td>
          <td><span class="sev sev-{{ f.severity.value }}">{{ f.severity.value }}</span></td>
          <td class="mono">{{ f.check_id }}</td>
          <td>{{ f.offer_name or "document" }}</td>
          <td>{{ f.summary }}</td>
          <td class="kv">
            {% for k, v in f.observed.items() %}<div>{{ k }}: {{ v }}</div>{% endfor %}
            {% if f.expected %}<div class="arrow">→</div>{% for k, v in f.expected.items() %}<div>{{ k }}: {{ v }}</div>{% endfor %}{% endif %}
          </td>
          <td>{{ "%.2f"|format(f.confidence) }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>
  </section>
</main>
<footer>
  <div>Versions: {% for k, v in run.versions.items() %}<span class="mono">{{ k }}={{ v }}</span>{% if not loop.last %} · {% endif %}{% else %}—{% endfor %}
  · contract_version <span class="mono">{{ run.contract_version }}</span></div>
  <div class="disclaimer">No findings ≠ defect-free. Decision support only — a human approves publication.</div>
</footer>
<script>
(function () {
  var toggle = document.getElementById("show-passes");
  toggle.addEventListener("change", function () { document.body.classList.toggle("show-passes", toggle.checked); });
  function els(id) { return document.querySelectorAll('[data-finding-id="' + CSS.escape(id) + '"]'); }
  function setHl(id, on) { els(id).forEach(function (el) { el.classList.toggle("hl", on); }); }
  function reveal(id, tag) {
    var el = Array.prototype.find.call(els(id), function (e) { return e.tagName.toLowerCase() === tag; });
    if (el) el.scrollIntoView({behavior: "smooth", block: "center"});
  }
  document.querySelectorAll("tbody tr[data-finding-id], rect.box").forEach(function (el) {
    var id = el.getAttribute("data-finding-id");
    var isRow = el.tagName.toLowerCase() === "tr";
    el.addEventListener("mouseenter", function () { setHl(id, true); });
    el.addEventListener("mouseleave", function () { setHl(id, false); });
    el.addEventListener("click", function () {
      reveal(id, isRow ? "rect" : "tr");
      setHl(id, true); setTimeout(function () { setHl(id, false); }, 1500);
    });
  });
})();
</script>
</body>
</html>
"""
