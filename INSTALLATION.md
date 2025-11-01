# INSTALLATION.md (Schritt-für-Schritt)

## 0) Voraussetzungen
Docker & Docker Compose, Linux x86_64, Pfade:
- `/pkms/data`, `/pkms/index`, `/pkms/models`, `/pkms/backups`

```bash
sudo mkdir -p /pkms/{data,index,models,backups}
sudo mkdir -p /pkms/data/{inbox,notes,thumbs,tmp}
sudo mkdir -p /pkms/index/{text,code,image,cache,logs}
sudo chown -R 1000:1000 /pkms
cp .env.example .env
```

## 1) Modelle
- Leg `doclaynet.pt` nach `/pkms/models/layout/`.
- Qwen2.5-VL und OpenCLIP laden beim ersten Start (temporär Egress erlauben).

## 2) Build & Start
```bash
# mit Docker:
docker compose build && docker compose up -d
# oder mit Podman:
podman compose build && podman compose up -d
```

## 3) Smoke-Tests
- `http://127.0.0.1:3000` (Dashboard)
- `curl -H 'X-API-Key: change_me_local_only' 'http://127.0.0.1:8080/health'`
- Drop: PDF/JPG/WAV nach `/pkms/data/inbox/` → check `/pkms/data/notes/`

## 4) Admin
- Cache flush: `POST /cache/flush` (mit API-Key)
- BM25 rebuild: `POST /bm25/rebuild`
- Reprocess Dead-Letter:
```bash
docker compose exec ingest-worker python services/ingest_worker/scripts/reprocess_deadletter.py
# mit Podman entsprechend:
podman compose exec ingest-worker python services/ingest_worker/scripts/reprocess_deadletter.py
```

## 6) Optionen
- `RATE_LIMIT_PER_MIN`: einfache IP-Rate-Limitierung für `/query` (Default: 60)
- `LOG_LEVEL`: `DEBUG|INFO|WARN|ERROR` für alle Services (Default: INFO)

## 5) Backups
- laufen täglich, Ziel: `/pkms/backups/pkms`. Restore siehe README.
