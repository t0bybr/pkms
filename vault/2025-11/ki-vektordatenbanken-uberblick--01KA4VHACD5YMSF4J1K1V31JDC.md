---
date_created: 2025-11-15
language: de
title: KI & Vektordatenbanken – Überblick
---

# Begriffe
- Embeddings = Zahlenvektoren für Texte/Bilder
- Vektordatenbank = effiziente Suche in diesen Vektoren
- BM25 = klassische Stichwortsuche (lexikalisch)

# Erkenntnisse
- Für mein Setup reicht oft: Filesystem + DuckDB + HNSW
- Semantische Suche ergänzt, ersetzt aber nicht BM25
- RRF (Reciprocal Rank Fusion) als einfache Kombination

# Offene Fragen
- Wie viel bringt Multimodalität in der Praxis?
- Welche Modelle lokal sinnvoll (Ollama + AMD)?