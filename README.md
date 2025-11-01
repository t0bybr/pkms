# PKMS RAG Monorepo (Local, CPU-first)

Siehe `INSTALLATION.md` für die Schritt-für-Schritt-Anleitung.
Dieses Repo enthält: OCR (Qwen-VL), Layout (YOLO/DocLayNet), CLIP-Embeddings,
Speech-to-Text (Whisper), LanceDB, Hybrid Retrieval (Dense+BM25), Redis Cache,
eine RAG-API und ein Dashboard sowie tägliche lokale Backups (restic).

**Admin-Endpoints:** `POST /cache/flush`, `POST /bm25/rebuild` (mit `X-API-Key`).

**Achtung:** Beim ersten Start Egress für Modell-Container kurz erlauben, damit Weights geladen werden.
