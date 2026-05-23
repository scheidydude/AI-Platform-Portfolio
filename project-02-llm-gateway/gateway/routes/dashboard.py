from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LLM Gateway</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#f0f2f5;color:#1e293b}
header{background:#1e293b;color:#e2e8f0;padding:.875rem 2rem;display:flex;align-items:center;gap:.75rem}
header h1{font-size:1rem;font-weight:700;letter-spacing:.02em}
#month-tag{font-size:.75rem;background:#334155;padding:.125rem .5rem;border-radius:9999px;opacity:.9}
#refresh-tag{margin-left:auto;font-size:.7rem;opacity:.4}
.wrap{max-width:1120px;margin:0 auto;padding:1.5rem}
/* auth */
.auth-box{max-width:380px;margin:5rem auto;background:#fff;border-radius:10px;padding:2rem;
  box-shadow:0 1px 4px rgba(0,0,0,.1)}
.auth-box h2{font-size:.875rem;color:#64748b;margin-bottom:1rem}
.auth-box input{width:100%;padding:.5rem .75rem;border:1px solid #e2e8f0;border-radius:6px;
  font-size:.875rem;margin-bottom:.75rem;outline:none}
.auth-box input:focus{border-color:#6366f1}
.auth-box button{width:100%;padding:.5rem;background:#6366f1;color:#fff;border:none;
  border-radius:6px;cursor:pointer;font-size:.875rem;font-weight:600}
.auth-box button:hover{background:#4f46e5}
.err{color:#ef4444;font-size:.78rem;margin-top:.5rem}
/* cards */
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:1rem;margin-bottom:1.5rem}
.card{background:#fff;border-radius:10px;padding:1.25rem;box-shadow:0 1px 3px rgba(0,0,0,.07);
  border-left:4px solid #94a3b8}
.card.ok{border-color:#10b981}.card.warn{border-color:#f59e0b}.card.crit{border-color:#ef4444}
.card-team{font-size:.7rem;text-transform:uppercase;letter-spacing:.08em;color:#94a3b8;margin-bottom:.375rem}
.card-pct{font-size:2.25rem;font-weight:800;line-height:1}
.card.ok .card-pct{color:#10b981}.card.warn .card-pct{color:#f59e0b}.card.crit .card-pct{color:#ef4444}
.card-sub{font-size:.72rem;color:#94a3b8;margin-top:.25rem}
.bar{height:4px;background:#e2e8f0;border-radius:2px;margin-top:.875rem;overflow:hidden}
.bar-fill{height:100%;border-radius:2px}
.card.ok .bar-fill{background:#10b981}.card.warn .bar-fill{background:#f59e0b}.card.crit .bar-fill{background:#ef4444}
/* sections */
.section{background:#fff;border-radius:10px;padding:1.5rem;box-shadow:0 1px 3px rgba(0,0,0,.07);margin-bottom:1.25rem}
.section-title{font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
  color:#94a3b8;margin-bottom:1.25rem}
.chart-wrap{height:180px;position:relative}
/* table */
table{width:100%;border-collapse:collapse;font-size:.8rem}
th{text-align:left;padding:.4rem .75rem;color:#94a3b8;font-weight:600;font-size:.68rem;
  text-transform:uppercase;letter-spacing:.06em;border-bottom:1px solid #f1f5f9}
td{padding:.55rem .75rem;border-bottom:1px solid #f8fafc}
tr:last-child td{border:none}
.badge{display:inline-block;padding:.1rem .45rem;border-radius:9999px;font-size:.65rem;font-weight:700}
.badge-hard{background:#fee2e2;color:#991b1b}
.badge-soft{background:#fef3c7;color:#92400e}
.badge-downgrade{background:#dbeafe;color:#1e40af}
</style>
</head>
<body>
<header>
  <h1>LLM Gateway</h1>
  <span id="month-tag"></span>
  <span id="refresh-tag"></span>
</header>

<div id="auth-view" class="wrap">
  <div class="auth-box">
    <h2>Admin key required</h2>
    <input id="key-input" type="password" placeholder="Admin key"
      onkeydown="if(event.key==='Enter')connect()"/>
    <button onclick="connect()">Connect</button>
    <div class="err" id="auth-err"></div>
  </div>
</div>

<div id="dash-view" class="wrap" style="display:none">
  <div class="cards" id="quota-cards"></div>
  <div class="section">
    <div class="section-title">Monthly Tokens by Team</div>
    <div class="chart-wrap"><canvas id="c-tokens"></canvas></div>
  </div>
  <div class="section">
    <div class="section-title">Daily Token Trend</div>
    <div class="chart-wrap"><canvas id="c-daily"></canvas></div>
  </div>
  <div class="section">
    <div class="section-title">Cost &amp; Quota Breakdown</div>
    <table>
      <thead>
        <tr><th>Team</th><th>Tokens Used</th><th>Budget</th><th>% Used</th>
            <th>Cost (USD)</th><th>Mode</th></tr>
      </thead>
      <tbody id="cost-tbody"></tbody>
    </table>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<script>
let key = sessionStorage.getItem('gw_admin') || '';
let charts = {};
if (key) load();

async function connect() {
  key = document.getElementById('key-input').value.trim();
  document.getElementById('auth-err').textContent = '';
  try {
    const r = await fetch('/admin/quota', {headers: {'X-Admin-Key': key}});
    if (!r.ok) throw new Error('bad key');
    sessionStorage.setItem('gw_admin', key);
    load();
  } catch {
    document.getElementById('auth-err').textContent = 'Invalid admin key';
  }
}

async function api(p) {
  const r = await fetch(p, {headers: {'X-Admin-Key': key}});
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

async function load() {
  try {
    const [quota, daily] = await Promise.all([api('/admin/quota'), api('/admin/daily')]);
    document.getElementById('auth-view').style.display = 'none';
    document.getElementById('dash-view').style.display = '';
    document.getElementById('month-tag').textContent = quota.month;
    document.getElementById('refresh-tag').textContent = 'refreshed ' + new Date().toLocaleTimeString();
    renderCards(quota.teams);
    renderTokensChart(quota.teams);
    renderDailyChart(daily.daily);
    renderTable(quota.teams);
  } catch(e) {
    document.getElementById('auth-err').textContent = String(e);
    document.getElementById('auth-view').style.display = '';
    document.getElementById('dash-view').style.display = 'none';
    sessionStorage.removeItem('gw_admin');
  }
}

function sev(pct) { return pct >= 90 ? 'crit' : pct >= 75 ? 'warn' : 'ok'; }
function fmt(n) { return n >= 1e6 ? (n/1e6).toFixed(2)+'M' : n >= 1e3 ? (n/1e3).toFixed(1)+'K' : n; }

function renderCards(teams) {
  document.getElementById('quota-cards').innerHTML = teams.map(t => {
    const cls = sev(t.pct_used);
    return `<div class="card ${cls}">
      <div class="card-team">${t.team}</div>
      <div class="card-pct">${t.pct_used}%</div>
      <div class="card-sub">${fmt(t.tokens_used)} / ${fmt(t.tokens_budget)} &nbsp;·&nbsp; ${fmt(t.tokens_remaining)} left</div>
      <div class="bar"><div class="bar-fill" style="width:${Math.min(t.pct_used,100)}%"></div></div>
    </div>`;
  }).join('');
}

function renderTokensChart(teams) {
  const ctx = document.getElementById('c-tokens').getContext('2d');
  if (charts.tokens) charts.tokens.destroy();
  charts.tokens = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: teams.map(t => t.team),
      datasets: [
        {label:'Used', data: teams.map(t => t.tokens_used), backgroundColor:'#6366f1', borderRadius:4},
        {label:'Remaining', data: teams.map(t => t.tokens_remaining), backgroundColor:'#e2e8f0', borderRadius:4},
      ]
    },
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins:{legend:{position:'top', labels:{font:{size:11}}}},
      scales:{x:{stacked:true},y:{stacked:true, ticks:{callback:v=>fmt(v)}}},
    }
  });
}

function renderDailyChart(daily) {
  const ctx = document.getElementById('c-daily').getContext('2d');
  if (charts.daily) charts.daily.destroy();
  charts.daily = new Chart(ctx, {
    type: 'line',
    data: {
      labels: daily.map(d => d.date.slice(5)),
      datasets: [{
        label:'Tokens', data: daily.map(d => d.tokens),
        borderColor:'#6366f1', backgroundColor:'rgba(99,102,241,.08)',
        fill:true, tension:.3, pointRadius:3, pointHoverRadius:5,
      }]
    },
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins:{legend:{display:false}},
      scales:{y:{ticks:{callback:v=>fmt(v)}}},
    }
  });
}

function renderTable(teams) {
  const bc = {hard:'badge-hard', soft:'badge-soft', downgrade:'badge-downgrade'};
  document.getElementById('cost-tbody').innerHTML = teams.map(t => `
    <tr>
      <td><strong>${t.team}</strong></td>
      <td>${t.tokens_used.toLocaleString()}</td>
      <td>${t.tokens_budget.toLocaleString()}</td>
      <td>${t.pct_used}%</td>
      <td>$${(t.cost_usd||0).toFixed(4)}</td>
      <td><span class="badge ${bc[t.enforcement_mode]||''}">${t.enforcement_mode}</span></td>
    </tr>`).join('');
}

setInterval(load, 30000);
</script>
</body>
</html>"""


@router.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
async def dashboard() -> str:
    return _HTML
