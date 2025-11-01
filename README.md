## Architektur

* **ollama** – lokales LLM (z. B. Llama 3.1 8B) für Antworten.
* **qwen-vl-ocr** – OCR/Caption mit Qwen2.5-VL.
* **layout-detector** – YOLO/DocLayNet für Dokument-Layout.
* **clip-embed** – OpenCLIP-Image-Embeddings (für Skizzen/Diagramme).
* **speech-to-text** – Whisper (ffmpeg) für Audio → Text.
* **ingest-worker** – Watcher + Pipelines (text/code/vision/audio) + Domains (Finanzamt).
* **lancedb** – Vektor- & Metadaten-Store (dateibasiert).
* **rag-api** – Retrieval (Dense + BM25) + Fusion (RRF) + Antwort.
* **redis** – Cache (Queries, BM25).
* **dashboard** – Statisches UI (Status, Query-Tester).
* **backup** – tägliches lokales restic-Backup.

## Datenpfade (empfohlen: 3× NVMe)

* `/pkms/data`  – Rohdaten, Notes, Thumbs, tmp, Inbox
* `/pkms/index` – LanceDB, Logs, State (SQLite)
* `/pkms/models` – Modelle/Weights
* `/pkms/backups` – Restic-Repo

## Setup (Kurzform)

```bash
sudo mkdir -p /pkms/{data,index,models,backups}
sudo mkdir -p /pkms/data/{inbox,notes,thumbs,tmp}
sudo mkdir -p /pkms/index/{text,code,image,cache,logs}
sudo chown -R 1000:1000 /pkms
cp .env.example .env
```

## Start

```bash
# Docker
docker compose build && docker compose up -d
# Podman
podman compose build && podman compose up -d
```

* Dashboard: `http://127.0.0.1:3000`
* API-Health: `curl -H 'X-API-Key: change_me_local_only' http://127.0.0.1:8080/health`
* OpenAPI/Swagger: `http://127.0.0.1:8080/docs`

## Ingest – so fließt es

1. **PDF/JPG/PNG** nach `/pkms/data/inbox/` → `pdf2image` → `layout-detector` → `qwen-vl-ocr` → Skizzencrops → `clip-embed` → Markdown + Index.
2. **Audio (wav/mp3/m4a)** nach `/pkms/data/inbox/` → Whisper → Markdown + Index.
3. **.md / Code** direkt in Pipelines → Chunking → `bge-m3` Embeddings → LanceDB.
4. **Query** → Dense + BM25 → RRF → LLM-Antwort + Treffer.

## Retrieval

* **Dense** mit `BAAI/bge-m3`.
* **Sparse** mit **BM25** (Token‑Cache: `/tmp/bm25_tokens.json`, wird bei Bedarf neu aufgebaut).
* **Fusion** via Reciprocal Rank Fusion (RRF).
* **Bildtreffer** optional (Heuristik: Query enthält „skizze/diagramm/ablauf/schema/block“).

## Admin-Endpoints (API-Key zwingend)

* `POST /cache/flush` – leert Redis.
* `POST /bm25/rebuild` – baut BM25 neu (nach viel neuem Text).
* `GET  /ingest/status` – verarbeitet/retries/deadletters.
* `GET  /metrics` – P50/P95, Query-Zähler.
* `GET  /health` – Liveness.

## Sicherheit

* **rag-api** bindet nur `127.0.0.1:8080`, API-Key-Header `X-API-Key`.
* **Rate Limit**: einfache IP‑Begrenzung über `RATE_LIMIT_PER_MIN` (Default 60/min).
* **OCR/Layout/CLIP/STT**: nur `127.0.0.1` und API‑Key erforderlich (`X-API-Key`).
* Modell-Container können **ohne Egress** laufen (Netz nur zum Download der Weights kurz zulassen).
* PII: Domain-Parser (z. B. Finanzamt) maskieren IBAN/Steuernummer; erweitere bei Bedarf.

## Idempotenz & Migration

* LanceDB-Tabellen mit **Metadaten**: `schema_version`, `embedding_model_id`, `embedding_dim`.
* **Dual-Index**-Strategie: aktuelle Tabellen `*_v1`; für Modellwechsel `*_v2` parallel befüllen, RAG liest beide → Umschalten ohne Downtime.
* **Incremental Indexing** via SHA256 + SQLite (`ingest_state.sqlite`).

## Zuverlässigkeit

* **Batch-Embeddings** (Text/Code) reduzieren Overhead.
* **Retry + Dead-Letter**: `_retry` (max 3), dann `_deadletter`.
* Reprocess-Script:
  `docker compose exec ingest-worker python services/ingest_worker/scripts/reprocess_deadletter.py`
  (mit Podman: `podman compose exec ingest-worker python services/ingest_worker/scripts/reprocess_deadletter.py`)

## Backups (lokal)

* Service `backup` sichert täglich `/pkms/data` & `/pkms/index` nach `/pkms/backups/pkms` (restic).
* Restore-Beispiel:

```bash
docker run --rm -e RESTIC_PASSWORD=change_me -v /pkms/backups:/backups -v /restore:/restore alpine:3.20 \
  sh -lc 'apk add --no-cache restic && restic -r /backups/pkms snapshots && restic -r /backups/pkms restore latest --target /restore'
```

## Häufige Stolpersteine

* **Erster Start dauert**, weil Modelle geladen werden.
* **Healthcheck-Binary**: `rag-api` enthält jetzt `curl` für Healthcheck.
* **GPU**: Nicht nötig für Start; später via `--gpus`/NVIDIA Runtime nachrüstbar.
