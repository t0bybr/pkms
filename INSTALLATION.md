# INSTALLATION.md (Schritt-für-Schritt)

## 0) Voraussetzungen
Docker & Docker Compose, Linux x86_64, Pfade:
- `/pkms/data`, `/pkms/index`, `/pkms/models`, `/pkms/backups` (per `.env` anpassbar)

```bash
sudo mkdir -p /pkms/{data,index,models,backups}
sudo mkdir -p /pkms/data/{inbox,notes,thumbs,tmp}
sudo mkdir -p /pkms/index/{text,code,image,cache,logs}
sudo chown -R 1000:1000 /pkms
cp .env.example .env
```

## 1) Modelle
- Leg `doclaynet.pt` nach `MODELS/layout/`.
- Qwen2.5‑VL (per `QWEN_MODEL`, Default: `Qwen/Qwen2.5-VL-7B-Instruct`) und OpenCLIP laden beim ersten Start (temporär Egress erlauben).
- Ollama Modelle via `ollama pull` landen in `MODELS/llm`.

## 2) Build & Start

**Wichtig**: Das System nutzt ein **Shared Base-Image** mit PyTorch & gemeinsamen Dependencies. Beim ersten Build wird das Base-Image zuerst gebaut (~10-15 Min), danach sind alle weiteren Builds viel schneller!

```bash
# mit Docker:
# 1. Base-Image bauen (nur beim ersten Mal lang)
docker compose build base
# 2. Alle Services bauen
docker compose build
# 3. Starten
docker compose up -d

# oder mit Podman:
podman compose build base
podman compose build
podman compose up -d
```

**Build-Zeiten**:
- Erster Build (Base-Image + Services): ~15-20 Min
- Spätere Rebuilds (nur Code-Änderungen): ~30 Sekunden
- PyTorch wird nur 1x heruntergeladen (~4GB statt 24GB)

**GPU-Support**: Das Base-Image enthält bereits CUDA-PyTorch. Für GPU-Nutzung später einfach `--gpus` bzw. NVIDIA Container Runtime konfigurieren.

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
- laufen täglich, Ziel: `${BACKUPS}/pkms` (Default: `/pkms/backups/pkms`).
- Pfad lässt sich via `.env` mit `BACKUPS=/anderer/mountpunkt` anpassen.
- Restore siehe README.

## 6) Optionen
- `RATE_LIMIT_PER_MIN`: einfache IP-Rate-Limitierung für `/query` (Default: 60)
- `LOG_LEVEL`: `DEBUG|INFO|WARN|ERROR` für alle Services (Default: INFO)
- `REDIS_PASSWORD`: optionales Passwort für Redis (Compose setzt `--requirepass` wenn gesetzt)
- `MAX_UPLOAD_MB`: Upload-Größenlimit in MB (Default: 10)
- `MAX_IMAGE_PIXELS`: Limit für Bildgröße (Pillow) (Default: 178956970)
- `MIN_FREE_MB`: Mindest-freier Speicher vor großen Writes (Default: 100)
- `IMAGE_EMBED_MODEL_ID`: Metadatenfeld für Bild‑Embeddings (Default: open_clip/ViT-L-14@openai)
- `IMAGE_EMBED_DIM`: Dimensionalität der Bild‑Embeddings (Default: 768)
- `BACKUPS`: Host‑Pfad für das Backup‑Volume (Default: `/pkms/backups`)
- `QWEN_MODEL`: Modell-ID für OCR/Caption (Default: `Qwen/Qwen2.5-VL-7B-Instruct`)

## 7) Performance-Tuning

### Build-Cache optimieren
Das System nutzt pip's Download-Cache (kein `--no-cache-dir`). Bei häufigen Rebuilds spart das massiv Zeit:
- PyTorch, Transformers, etc. werden aus `/root/.cache/pip` geladen
- Änderungen an `requirements.txt` triggern Rebuild des entsprechenden Layers
- Code-Änderungen (`.py` Files) nutzen gecachte pip-Layer

### Podman rootless Permissions
Das System nutzt Podman's `:U` Volume-Flag für automatisches UID-Mapping:
- Container laufen als `user: 1000:1000`
- Volumes werden automatisch auf die gemappte UID gechownt
- Funktioniert mit Podman's subordinate UID/GID Ranges (`/etc/subuid`, `/etc/subgid`)

### GPU aktivieren (zukünftig)
CUDA ist bereits im Base-Image enthalten. Für GPU-Nutzung:

```yaml
# In docker-compose.yml für GPU-Services hinzufügen:
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          count: 1
          capabilities: [gpu]
```

Kein Rebuild nötig - einfach Compose-Datei anpassen und Services neustarten!
