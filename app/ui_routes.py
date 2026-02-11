from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.auth import require_grant
from app.db import get_db
from app.models import Entity
from app.schemas import EntityOut

router = APIRouter()


@router.get("/ui", response_class=HTMLResponse)
def ui_page() -> str:
    return """<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Ontology Vault UI</title>
  <style>
    :root { color-scheme: light dark; }
    body {
      margin: 0;
      font-family: Inter, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
      background: #0b1020;
      color: #e6ecff;
    }
    .container { max-width: 1100px; margin: 0 auto; padding: 20px; }
    h1 { margin: 0 0 16px; font-size: 28px; }
    .panel {
      background: #111831;
      border: 1px solid #243054;
      border-radius: 10px;
      padding: 14px;
      margin-bottom: 14px;
    }
    label { font-size: 13px; display: block; margin-bottom: 6px; color: #a8b4d8; }
    input, select, textarea, button {
      width: 100%;
      box-sizing: border-box;
      border-radius: 8px;
      border: 1px solid #334573;
      background: #0f1730;
      color: #e6ecff;
      padding: 10px;
      font-size: 14px;
    }
    textarea { min-height: 140px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    button {
      background: #2d4cff;
      border: 0;
      cursor: pointer;
      width: auto;
      padding: 10px 14px;
    }
    button.secondary { background: #314165; }
    button:disabled { opacity: 0.6; cursor: not-allowed; }
    .row { display: grid; gap: 12px; }
    .row.two { grid-template-columns: 1fr 1fr; }
    .tabs { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; }
    .tab-btn { background: #1a2650; }
    .tab-btn.active { background: #2d4cff; }
    .tab { display: none; }
    .tab.active { display: block; }
    .muted { color: #9aa8cb; font-size: 13px; }
    pre {
      background: #0c142a;
      border: 1px solid #243054;
      border-radius: 8px;
      padding: 10px;
      overflow: auto;
      margin: 0;
    }
    .cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 10px; }
    .card {
      border: 1px solid #2a3864;
      background: #121b38;
      border-radius: 8px;
      padding: 10px;
    }
    table { width: 100%; border-collapse: collapse; }
    th, td { border-bottom: 1px solid #243054; text-align: left; padding: 8px; vertical-align: top; }
    .entity-list { max-height: 350px; overflow: auto; border: 1px solid #243054; border-radius: 8px; }
    .entity-item { padding: 10px; border-bottom: 1px solid #243054; cursor: pointer; }
    .entity-item:hover { background: #172448; }
    .ok { color: #8df0b0; }
    .err { color: #ff9a9a; }
    @media (max-width: 800px) { .row.two { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class=\"container\">
    <h1>Ontology Vault</h1>

    <div class=\"panel\">
      <div class=\"row two\">
        <div>
          <label for=\"token\">Bearer token</label>
          <input id=\"token\" placeholder=\"Paste token from /dev/grants\" />
        </div>
        <div style=\"display:flex;align-items:end;gap:8px;\">
          <button id=\"saveToken\">Save token</button>
          <button class=\"secondary\" id=\"clearToken\">Clear</button>
        </div>
      </div>
      <p id=\"tokenStatus\" class=\"muted\"></p>
    </div>

    <div class=\"tabs\">
      <button class=\"tab-btn active\" data-tab=\"entities\">Entities</button>
      <button class=\"tab-btn\" data-tab=\"claims\">Claims</button>
      <button class=\"tab-btn\" data-tab=\"write\">Write</button>
      <button class=\"tab-btn\" data-tab=\"query\">Query</button>
    </div>

    <div id=\"entities\" class=\"tab active panel\">
      <div class=\"row two\">
        <div>
          <label>Entity type (optional)</label>
          <input id=\"entitiesType\" placeholder=\"contact\" />
        </div>
        <div>
          <label>Limit / Offset</label>
          <div class=\"row two\">
            <input id=\"entitiesLimit\" type=\"number\" value=\"50\" />
            <input id=\"entitiesOffset\" type=\"number\" value=\"0\" />
          </div>
        </div>
      </div>
      <p><button id=\"loadEntities\">Load Entities</button></p>
      <div class=\"row two\">
        <div class=\"entity-list\" id=\"entityList\"></div>
        <pre id=\"entityDetail\">Select an entity…</pre>
      </div>
    </div>

    <div id=\"claims\" class=\"tab panel\">
      <p><button id=\"loadClaims\">Load Proposed Claims</button></p>
      <div id=\"claimsTableWrap\" class=\"muted\">No claims loaded.</div>
    </div>

    <div id=\"write\" class=\"tab panel\">
      <div class=\"row\">
        <div>
          <label>Entity Type</label>
          <select id=\"writeEntityType\">
            <option value=\"contact\">contact</option>
            <option value=\"preference\">preference</option>
            <option value=\"goal\">goal</option>
          </select>
        </div>
        <div class=\"row two\">
          <div>
            <label>Match JSON</label>
            <textarea id=\"writeMatch\">{\n  \"name\": \"Alice\"\n}</textarea>
          </div>
          <div>
            <label>Patch JSON</label>
            <textarea id=\"writePatch\">{\n  \"org\": \"OpenAI\",\n  \"email\": \"alice@example.com\"\n}</textarea>
          </div>
        </div>
      </div>
      <p><button id=\"submitWrite\">Submit Write</button></p>
      <div id=\"writeResult\" class=\"muted\">No write submitted yet.</div>
    </div>

    <div id=\"query\" class=\"tab panel\">
      <div class=\"row two\">
        <div>
          <label>q</label>
          <input id=\"queryQ\" placeholder=\"ali\" />
        </div>
        <div>
          <label>entity_type (optional)</label>
          <input id=\"queryType\" placeholder=\"contact\" />
        </div>
      </div>
      <p><button id=\"runQuery\">Run Query</button></p>
      <div id=\"queryResults\" class=\"cards\"></div>
    </div>
  </div>

  <script>
    const tokenInput = document.getElementById('token');
    const tokenStatus = document.getElementById('tokenStatus');

    const savedToken = localStorage.getItem('ontology_token') || '';
    tokenInput.value = savedToken;
    setTokenStatus();

    document.getElementById('saveToken').onclick = () => {
      localStorage.setItem('ontology_token', tokenInput.value.trim());
      setTokenStatus('Token saved.');
    };

    document.getElementById('clearToken').onclick = () => {
      localStorage.removeItem('ontology_token');
      tokenInput.value = '';
      setTokenStatus('Token cleared.');
    };

    function setTokenStatus(msg) {
      const has = !!(localStorage.getItem('ontology_token') || tokenInput.value.trim());
      tokenStatus.innerHTML = `${msg ? msg + ' ' : ''}${has ? '<span class="ok">Token ready.</span>' : '<span class="err">No token set.</span>'}`;
    }

    async function apiFetch(path, opts = {}) {
      const token = (localStorage.getItem('ontology_token') || tokenInput.value || '').trim();
      if (!token) throw new Error('Set bearer token first.');
      const headers = {
        'Authorization': `Bearer ${token}`,
        ...(opts.body ? {'Content-Type': 'application/json'} : {}),
        ...(opts.headers || {}),
      };
      const res = await fetch(path, {...opts, headers});
      if (!res.ok) {
        const text = await res.text();
        throw new Error(`${res.status} ${res.statusText}: ${text}`);
      }
      return res.json();
    }

    document.querySelectorAll('.tab-btn').forEach(btn => {
      btn.onclick = () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
      };
    });

    document.getElementById('loadEntities').onclick = async () => {
      const type = document.getElementById('entitiesType').value.trim();
      const limit = Number(document.getElementById('entitiesLimit').value || 50);
      const offset = Number(document.getElementById('entitiesOffset').value || 0);
      const qs = new URLSearchParams();
      if (type) qs.set('type', type);
      qs.set('limit', String(limit));
      qs.set('offset', String(offset));
      const entities = await apiFetch(`/api/entities?${qs.toString()}`);
      const list = document.getElementById('entityList');
      const detail = document.getElementById('entityDetail');
      list.innerHTML = '';
      detail.textContent = 'Select an entity…';

      if (!entities.length) {
        list.innerHTML = '<div class="entity-item muted">No entities found.</div>';
        return;
      }

      for (const e of entities) {
        const item = document.createElement('div');
        item.className = 'entity-item';
        item.textContent = `${e.type} · ${e.id}`;
        item.onclick = async () => {
          const one = await apiFetch(`/api/entity/${e.id}`);
          detail.textContent = JSON.stringify(one, null, 2);
        };
        list.appendChild(item);
      }
    };

    async function refreshClaims() {
      const wrap = document.getElementById('claimsTableWrap');
      const claims = await apiFetch('/claims?status_filter=proposed');
      if (!claims.length) {
        wrap.innerHTML = '<p class="muted">No proposed claims.</p>';
        return;
      }

      let html = '<table><thead><tr><th>ID</th><th>Entity</th><th>Field</th><th>Current</th><th>New</th><th></th></tr></thead><tbody>';
      for (const c of claims) {
        html += `<tr>
          <td><code>${c.id}</code></td>
          <td><code>${c.entity_id}</code><br/><span class="muted">${c.entity_type}</span></td>
          <td>${c.field}</td>
          <td><pre>${JSON.stringify(c.old_value, null, 2)}</pre></td>
          <td><pre>${JSON.stringify(c.new_value, null, 2)}</pre></td>
          <td><button data-confirm="${c.id}">Confirm</button></td>
        </tr>`;
      }
      html += '</tbody></table>';
      wrap.innerHTML = html;

      wrap.querySelectorAll('button[data-confirm]').forEach(btn => {
        btn.onclick = async () => {
          btn.disabled = true;
          try {
            await apiFetch(`/claims/${btn.dataset.confirm}/confirm`, {method: 'POST'});
            await refreshClaims();
          } catch (e) {
            alert(e.message);
            btn.disabled = false;
          }
        };
      });
    }

    document.getElementById('loadClaims').onclick = async () => {
      try {
        await refreshClaims();
      } catch (e) {
        document.getElementById('claimsTableWrap').innerHTML = `<p class=\"err\">${e.message}</p>`;
      }
    };

    document.getElementById('submitWrite').onclick = async () => {
      const out = document.getElementById('writeResult');
      try {
        const payload = {
          entity_type: document.getElementById('writeEntityType').value,
          match: JSON.parse(document.getElementById('writeMatch').value || '{}'),
          patch: JSON.parse(document.getElementById('writePatch').value || '{}'),
          confidence: 1.0,
        };
        const res = await apiFetch('/write', {method: 'POST', body: JSON.stringify(payload)});
        const proposedRows = (res.proposed || []).map(p =>
          `<tr><td>${p.field}</td><td><code>${p.claim_id}</code></td><td><pre>${JSON.stringify(p.current, null, 2)}</pre></td><td><pre>${JSON.stringify(p.new, null, 2)}</pre></td></tr>`
        ).join('');
        out.innerHTML = `
          <p><strong>Entity:</strong> <code>${res.entity_id}</code></p>
          <p><strong>Applied:</strong> ${(res.applied || []).join(', ') || 'None'}</p>
          <p><strong>Proposed:</strong> ${(res.proposed || []).length}</p>
          ${(res.proposed || []).length ? `<table><thead><tr><th>Field</th><th>Claim ID</th><th>Current</th><th>New</th></tr></thead><tbody>${proposedRows}</tbody></table>` : ''}
        `;
      } catch (e) {
        out.innerHTML = `<p class=\"err\">${e.message}</p>`;
      }
    };

    document.getElementById('runQuery').onclick = async () => {
      const q = document.getElementById('queryQ').value.trim();
      const entityType = document.getElementById('queryType').value.trim();
      const wrap = document.getElementById('queryResults');
      wrap.innerHTML = '';
      try {
        const payload = { q, max_results: 5 };
        if (entityType) payload.entity_type = entityType;
        const rows = await apiFetch('/query', {method: 'POST', body: JSON.stringify(payload)});
        if (!rows.length) {
          wrap.innerHTML = '<p class="muted">No results.</p>';
          return;
        }
        for (const r of rows) {
          const card = document.createElement('div');
          card.className = 'card';
          card.innerHTML = `<strong>${r.type}</strong><br/><span class="muted">${r.id}</span><pre>${JSON.stringify(r.data, null, 2)}</pre>`;
          wrap.appendChild(card);
        }
      } catch (e) {
        wrap.innerHTML = `<p class=\"err\">${e.message}</p>`;
      }
    };
  </script>
</body>
</html>"""


@router.get("/api/entities", response_model=list[EntityOut])
def list_entities(
    request: Request,
    type: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db),
    _grant=Depends(require_grant),
):
    query = db.query(Entity).filter(Entity.user_id == request.state.user_id)
    if type:
        query = query.filter(Entity.type == type)

    entities = query.order_by(Entity.updated_at.desc()).offset(max(offset, 0)).limit(min(max(limit, 1), 200)).all()
    return [EntityOut(id=e.id, type=e.type, data=e.data) for e in entities]


@router.get("/api/entity/{entity_id}", response_model=EntityOut)
def get_entity(
    entity_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    _grant=Depends(require_grant),
):
    entity = db.query(Entity).filter(Entity.id == entity_id, Entity.user_id == request.state.user_id).first()
    if not entity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entity not found")
    return EntityOut(id=entity.id, type=entity.type, data=entity.data)
