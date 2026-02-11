# Ontology Vault (v1)

Minimal FastAPI + PostgreSQL service for user-scoped ontology entities with safe write behavior:
- auto-write if field is empty/missing
- propose overwrite claim if existing value differs
- apply overwrite only after explicit confirmation

## 1) Run Postgres with Docker

```bash
docker run --name ontology-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=ontology \
  -p 5432:5432 \
  -d postgres:16
```

## 2) Configure environment

```bash
cp .env.example .env
# edit .env if needed
```

`DATABASE_URL` should look like:

```env
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/ontology
```

## 3) Install and run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Server: `http://127.0.0.1:8000`

## 4) Example curl workflow

Set a reusable variable:

```bash
BASE=http://127.0.0.1:8000
```

### Create a dev grant token

```bash
curl -s -X POST "$BASE/dev/grants" \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "11111111-1111-1111-1111-111111111111",
    "client_id": "assistant-client",
    "scopes": ["read","write"]
  }'
```

Copy `token` from the response:

```bash
TOKEN='<paste_token_here>'
```

### Write data (/write)

```bash
curl -s -X POST "$BASE/write" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{
    "entity_type": "contact",
    "match": {"name": "Alice"},
    "patch": {"org": "OpenAI", "email": "alice@example.com"},
    "confidence": 1.0
  }'
```

### Query entities (/query)

```bash
curl -s -X POST "$BASE/query" \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"q":"ali","entity_type":"contact","max_results":5}'
```

### List claims (/claims)

```bash
curl -s "$BASE/claims?status_filter=proposed" \
  -H "Authorization: Bearer $TOKEN"
```

### Confirm a proposed claim

```bash
CLAIM_ID='<claim_id_here>'
curl -s -X POST "$BASE/claims/$CLAIM_ID/confirm" \
  -H "Authorization: Bearer $TOKEN"
```

## Notes
- Tables are created automatically on startup.
- No Alembic migrations in v1.


## 5) Built-in Web UI

1. Start the server:

```bash
uvicorn app.main:app --reload
```

2. Create a token via `/dev/grants` (see example above).
3. Open `http://127.0.0.1:8000/ui` in your browser.
4. Paste the token once in the Bearer token box and click **Save token**.
5. Use tabs:
   - **Entities**: list entities and inspect one entity JSON
   - **Claims**: view proposed claims and confirm them
   - **Write**: submit `entity_type`, `match` JSON, and `patch` JSON
   - **Query**: run search and view card results

Additional secured API routes used by the UI:
- `GET /api/entities?type=&limit=50&offset=0`
- `GET /api/entity/{entity_id}`
