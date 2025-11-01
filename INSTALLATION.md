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
- `http://127.0.0.1:8080/docs` (OpenAPI/Swagger)
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

### Migration: image_v1 → image_v2 (CLIP → embedding)
Falls ältere Bild-Embeddings noch in `clip_embedding` gespeichert sind:
```bash
docker compose exec ingest-worker python services/ingest_worker/scripts/migrate_image_v2.py
# Podman:
podman compose exec ingest-worker python services/ingest_worker/scripts/migrate_image_v2.py
```

## 5) Backups
- laufen täglich, Ziel: `/pkms/backups/pkms`. Restore siehe README.

## 6) Optionen
- `RATE_LIMIT_PER_MIN`: einfache IP-Rate-Limitierung für `/query` (Default: 60)
- `LOG_LEVEL`: `DEBUG|INFO|WARN|ERROR` für alle Services (Default: INFO)
- `REDIS_PASSWORD`: optionales Passwort für Redis (Compose setzt `--requirepass` wenn gesetzt)
- `MAX_UPLOAD_MB`: Upload-Größenlimit in MB (Default: 10)
- `MAX_IMAGE_PIXELS`: Limit für Bildgröße (Pillow) (Default: 178956970)
- `MIN_FREE_MB`: Mindest-freier Speicher vor großen Writes (Default: 100)
