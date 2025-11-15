PKMS – System Baseline (v0.3, 2025-11-14)

Ziel: Ein versioniertes, agentenkompatibles Wissenssystem mit

Markdown-Dateien als Source of Truth,

JSON-Metadaten als strukturierte Wahrheit,

Typesense als Such-/Indexschicht,

deterministischem Chunking + Embeddings,

Konsolidierung & Vergessen (Wissensstoffwechsel),

und voller Reproduzierbarkeit via Git.



---

1. Systemstruktur

📁 Verzeichnisaufbau

pkms/
├── notes/                      # Markdown-Quellen (SoT)
├── data/
│   ├── records/                # JSON-Metadaten (1:1 zu notes/)
│   ├── chunks/                 # NDJSON pro Dokument (1 Zeile = 1 Chunk)
│   └── embeddings/             # Embedding-Vektoren (pro Modell + Chunk-Hash)
│       ├── text-3-large-2025-06/    # {chunk_hash}.npy
│       └── clip-vit-large/          # optional: Bild-Embeddings
├── taxonomy/                   # kontrollierte Vokabulare
├── schema/                     # JSON-Schemas (→ Pydantic Code-Gen)
├── pkms/                       # Core-Library & Tools
│   ├── lib/
│   └── tools/
├── docker/                     # Deployment (Typesense etc.)
├── policy/                     # Relevance- & Memory-Regeln
├── Makefile
└── .env

🧠 Scripts (Toolchain)

Script	Aufgabe

ingest.py	Markdown → JSON (Records), Auto-Detection Language/Dates
link.py	Wikilinks erkennen, validieren & bidirektional tracken
chunk.py	Hybrid Chunking (hierarchisch + semantisch), Content-Hash IDs
embed.py	Incremental Embedding (nur neue/geänderte Chunks)
index_rebuild.py	Reindex in Typesense (Blue-Green)
search.py	Hybrid Search (BM25 + ANN via Typesense), MMR + Exploration
relevance.py	Formel-basiertes Scoring (Recency + Links + Quality + User)
synth.py	Konsolidierung via Git-Branches (Agent → PR → Merge)
archive.py	Policy-gesteuertes Archivieren (ohne Löschen)



---

2. Datenstrukturen

🧾 Record (Markdown-Metadaten)

{
  "id": "01HAR6DP2M7G1KQ3Y3VQ8C0Q",
  "slug": "pizza-knusprig",
  "path": "notes/pizza-knusprig--01HAR6DP2M7G1KQ3Y3VQ8C0Q.md",
  "title": "Pizza – knusprig bei 300°C",
  "tags": ["kochen", "ofen"],
  "categories": ["Kochen"],
  "language": "de",  // aus Frontmatter (auto-detect, überschreibbar)
  "created": "2025-01-10T14:22:31Z",
  "updated": "2025-11-13T09:03:00Z",
  "date_semantic": "2025-01-09T18:00:00Z",  // aus Frontmatter
  "full_text": "...",
  "links": [
    {"raw": "[[kochen]]", "type": "slug", "target": "01HAR999", "resolved": true}
  ],
  "backlinks": [  // Bidirektional!
    {"from": "01HAR888", "context": "...siehe [[pizza-knusprig]]..."}
  ],
  "content_hash": "sha256:...",
  "file_hash": "sha256:...",
  "status": {
    "relevance_score": 0.82,
    "archived": false,
    "consolidated_into": null  // ULID der Synthese, falls konsolidiert
  },
  "agent": {"id": "linker", "confidence": 0.94, "reviewed": false},
  "embedding_meta": {
    "text": {
      "model": "text-3-large-2025-06",
      "dim": 3072,
      "updated_at": "2025-11-14T08:10:01Z",
      "chunk_hashes": ["a3f2bc1d", "f9e1a2b3", "c4d5e6f7"]  // Welche Chunks embedded
    }
  },
  "source": {"repo": "github.com/you/pkms", "commit": "84ac…f2"}
}

🧩 Chunk (Textabschnitt)

{
  "doc_id": "01HAR6DP2M7G1KQ3Y3VQ8C0Q",
  "chunk_id": "01HAR6DP2M7G1KQ3Y3VQ8C0Q:a3f2bc1d",
  "chunk_hash": "a3f2bc1d",  // xxhash64(text)[:12] → Content-addressable
  "chunk_index": 7,
  "text": "...",
  "tokens": 472,
  "section": "Ofentemperatur",
  "language": "de"
}

🔢 Embedding (Filesystem-basiert)

# Storage: data/embeddings/{model}/{chunk_hash}.npy
# Beispiel: data/embeddings/text-3-large-2025-06/a3f2bc1d.npy

# File enthält nur: np.array([0.0123, -0.9876, ...], dtype=float32)
# Metadaten stehen im Record (embedding_meta) und Chunk (chunk_hash)
# Timestamp = File mtime

# Vorteile:
# - Content-addressable: gleicher Text → gleiche Datei
# - Deduplication über Docs hinweg
# - Incremental Updates: nur neue Hashes embedden
# - Modellwechsel: neuer Ordner, alte bleiben


---

2.1 Frontmatter vs JSON – Daten-Philosophie

**Frontmatter (Markdown-Header):**
- ✅ Manuell editierbare Felder
- ✅ LLM-generiert, aber überschreibbar
- ✅ Für Menschen + Obsidian/Markdown-Tools lesbar

**Beispiel:**
```yaml
---
title: Pizza perfekt
tags: [kochen, italienisch]
categories: [Rezepte]
language: de  # Auto-detected, aber überschreibbar
date_semantic: 2025-01-09  # "Wann war das Event?"
---
```

**JSON (data/records/):**
- ✅ Automatisch generierte Metadaten
- ✅ Nur für Tooling, nicht für manuelle Edits
- ✅ Abgeleitete Werte (Hashes, Links, Scores)

**Beispiel:**
```json
{
  "id": "01HAR6DP...",
  "slug": "pizza-perfekt",
  "created": "2025-11-14T10:22:31Z",  // File-Timestamp
  "updated": "2025-11-14T12:03:00Z",
  "content_hash": "sha256:...",
  "links": [...],  // Extrahiert aus [[wikilinks]]
  "backlinks": [...],  // Berechnet via link.py
  "status": {
    "relevance_score": 0.82,  // Berechnet via relevance.py
    "archived": false
  }
}
```

**Prinzip:**
> **Frontmatter** = Was Menschen/LLMs setzen sollen  
> **JSON** = Was Tools automatisch ableiten

**Workflow (ingest.py):**
1. Parse Frontmatter
2. Falls `language` fehlt → Auto-Detect & zurückschreiben
3. Generiere JSON mit abgeleiteten Feldern
4. Synchron halten via File-Hashes


---

2.2 Bidirektionales Link-Tracking

**Forward Links (im Source-Doc):**
```json
{
  "id": "01HAR6DP...",
  "links": [
    {
      "raw": "[[kochen]]",
      "type": "slug",  // slug|id|alias
      "target": "01HAR999",  // Resolved ULID
      "resolved": true,
      "context": "...bei 300°C [[kochen]]..."
    }
  ]
}
```

**Backlinks (im Target-Doc):**
```json
{
  "id": "01HAR999",  // kochen-Doc
  "backlinks": [
    {
      "from": "01HAR6DP",  // pizza-Doc
      "raw": "[[kochen]]",
      "context": "...bei 300°C [[kochen]]..."
    }
  ]
}
```

**Workflow (link.py):**
1. Extrahiere alle `[[wikilinks]]` aus Markdown
2. Resolve via Slug/ID/Alias → ULID
3. Schreibe `links` in Source-Record
4. Schreibe `backlinks` in Target-Record
5. Validierung: Warne bei broken links (target=null)

**Use Cases:**
- **Orphan Detection**: Docs ohne Backlinks
- **Graph Analysis**: PageRank für Relevance-Scoring
- **Cluster Detection**: Hohe Link-Dichte → Synth-Kandidaten
- **Archive Warnings**: "Doc hat 12 Backlinks, wirklich archivieren?"

**Visualisierung:**
```python
# Generiere Graph: docs → nodes, links → edges
# Export: Graphviz DOT, D3.js JSON, Obsidian Graph
```


---

3. Betrieb und Konsistenz

🌀 Blue-Green Deployment für Typesense

Indexiere in versionierte Collections: kb_chunks_v17, kb_docs_v17.

Suche läuft über Alias: kb_chunks, kb_docs.

Neuer Index → neue Version (_v18) → Alias-Swap nach Abschluss.

Rücksprung per Alias, kein Downtime.


🧩 Embedding-Migration & Modellwechsel

**Filesystem-basierte Migration:**
- Neues Modell → neuer Ordner: `data/embeddings/text-4-large-2026-01/`
- Alte Embeddings bleiben: `data/embeddings/text-3-large-2025-06/`
- Record-JSON trackt aktuelles Modell in `embedding_meta.text.model`

**Migration-Workflow:**
```python
# embed.py --model text-4-large-2026-01 --migrate
# → Re-embedded alle Chunks in neuen Ordner
# → Updated alle Records: embedding_meta.text.model
# → Alte .npy Files bleiben (Rollback-fähig)
```

**Query-Zeit:**
- Policy wählt Modell: `search --embedding-model text-4-large-2026-01`
- Fallback auf altes Modell wenn neue Embeddings fehlen
- Typesense-Collection pro Modell (Blue-Green)

**Garbage Collection:**
```bash
# Lösche altes Modell nach erfolgreicher Migration
rm -rf data/embeddings/text-3-large-2025-06/
```


⚙️ Relevanzsteuerung & Serendipität

Zeit-Decay mit Mindestschwelle (z. B. 0.15).

Zufällige Exploration (ε‑Exploration, 5 – 10 %).

Diversität durch MMR-Re-Ranking.

Regelmäßiger Zufalls-Recall alter, hochqualitativer Einträge.


🧱 Chunking-Qualität

Overlap: 10–20 % zwischen Chunks.

Hierarchisch: Segmentierung nach Headings + Länge.

Speichere section / subsection / page für Gruppierung.


💾 Embedding-Speicherstrategie

**Storage-Format:**
- `data/embeddings/{model}/{chunk_hash}.npy` (NumPy array, float32)
- Eine Datei pro Chunk-Hash (Content-addressable)
- Metadaten in Record-JSON (`embedding_meta`)

**Größe-Management:**

| Größe | Storage | Git-Strategie |
|-------|---------|---------------|
| Klein (<100MB) | `.npy` Files | Direkter Commit |
| Mittel (<1GB) | `.npy` Files | Git-LFS |
| Groß (>1GB) | Parquet + S3 | Commit-Pin in .env |

**Vorteile:**
- Incremental Updates: Nur neue Hashes embedden
- Deduplication: Gleicher Text in mehreren Docs = ein Embedding
- Modellwechsel: Neuer Ordner, alte bleiben
- Garbage Collection: Lösche `.npy` wenn kein Doc referenziert

**SoT-Hierarchie:**
- NDJSON (Chunks) = Quelle
- `.npy` Files (Embeddings) = Abgeleitete Artefakte
- Typesense = Cache


---

4. Wissensstoffwechsel: Konsolidierung & Vergessen

Ziel: Wissen bewertet, verdichtet und altert kontrolliert – analog zu einem organischen Gedächtnis.

🎯 Kernmechanismen

Konsolidierung: Synth-Agent verdichtet redundante Notizen zu stabilen Synthesen.

Vergessen: Alte, irrelevante Daten werden archiviert oder deaktiviert.

Relevanzsteuerung: Nutzung, Vernetzung und Alter bestimmen Gewicht.


⚙️ Prozesse

Relevance-Job (``): Score-Berechnung & Archivierung.

Synth-Agent (``): Themencluster erkennen, Synthesen generieren.

Archive-Skript (``): Policy-gesteuertes Altern & Verschieben.

Index-Gate: Nur archived:false & relevance_score>0.3 aktiv.


🧮 Umsetzung

Schritt	Beschreibung

Schema-Erweiterung	status.*-Felder für Relevanz & Archivierung
Policy-Datei	/policy/memory.yaml für Relevance-Regeln
Synth-Agent	Konsolidierung thematisch verwandter Notes
Archive-Skript	Archivierung veralteter Records
Index-Gate	Filter auf aktive & relevante Inhalte


💡 Prinzipien

Bewahren statt Löschen: alles versioniert.

Transparenz: jede Entscheidung erzeugt Traces.

Determinismus: gleiche Eingabe → gleiche Bewertung.

Serendipität: kontrollierte Zufallswiedervorlage.



---

5. Synth-Review-Prozess (Git-basiert)

🔄 Workflow

**1. Agent erstellt Feature-Branch**
```bash
git checkout -b synth/pizza-consolidated-01HAR789
```

**2. Agent schreibt Synthese + aktualisiert Quellen**
- Neue Note: `notes/pizza-perfekt--01HAR789.md`
- Neue Record: `data/records/pizza-perfekt--01HAR789.json`
- Update Quell-Records: `status.consolidated_into = "01HAR789"`
- Optional: `status.archived = true`

**3. Agent committed mit Trace**
```bash
git commit -m "synth: Consolidate 5 pizza recipes

Sources: 01HAR111, 01HAR222, 01HAR333
Synthesis: 01HAR789
Agent: synth-v1.2.0
Confidence: 0.89"
```

**4. Human Review**
- Via GitHub PR oder `git diff main..synth/pizza-consolidated-01HAR789`
- Prüft: Inhalt, Links, Claim-Check, Länge

**5a. Approved → Merge**
```bash
git checkout main
git merge --no-ff synth/pizza-consolidated-01HAR789
```

**5b. Rejected → Branch löschen oder manuell fixen**
```bash
git branch -D synth/pizza-consolidated-01HAR789  # oder
git checkout synth/pizza-consolidated-01HAR789
# ... manual edits ...
git commit -m "human: Refined synthesis"
```

**6. Rollback**
```bash
git revert <merge-commit>
```

**Vorteile:**
- ✅ Locking via Git (keine parallelen Synths auf selben Docs)
- ✅ Review-UI vorhanden (GitHub/GitLab)
- ✅ Traces = Commit-History
- ✅ Kein Custom-Staging-Filesystem

✅ Review-Checkliste



---

6. Wirkung

Signalstärke: aktive, geprüfte Inhalte im Fokus.

Selbstreinigung: irrelevante Inhalte verblassen.

Erinnerungsfähigkeit: alte Ideen bleiben rekonstruierbar.

Kognitive Effizienz: Agents arbeiten auf kuratiertem Wissen.


> Das System erinnert, verdichtet, vergisst – wie ein organisches Gedächtnis.




---

7. Facets & Mapping-Registry

Ziel: Einheitliche, kuratierte Facets im Index – ohne das SoT aufzublähen. Facets werden nur für real genutzte Filter/Aggregationen angelegt (niedrige–mittlere Kardinalität).

7.1 Facet-Policy (global)

Immer facet: doc_id (grouping), doc_type, tags[], categories[], language, status.archived, agent.reviewed

Optional facet (falls nötig): project, content_type, source.repo

Nicht facet: aliases[], freie Entities ohne Normalisierung, Pfade, Commits (hohe Kardinalität)

Zeit-Felder: als int64 ms (filter/sort), keine Facets: updated_ms, date_semantic_ms


7.2 Type-spezifische Facets (flattened)

Im Record bleiben type-spezifische Felder namespaced unter facets.<type>.*. Der Index erhält eine abgeflachte Auswahl pro doc_type.

Beispiel Record (Ausschnitt):

{
  "doc_type": "invoice",
  "facets": {
    "invoice": { "amount": 1299.00, "currency": "EUR", "due_date": "2025-12-15" },
    "pdf": { "pages": 2, "author": "ACME Finance" }
  }
}

Mapping-Registry → Index (Beispiel):

INDEX_FACET_REGISTRY = {
  "invoice": {
    "inv_amount": ("facets.invoice.amount", "float"),
    "inv_currency": ("facets.invoice.currency", "string"),
    "inv_due_ms": ("facets.invoice.due_date", "date_ms")
  },
  "pdf": {
    "pdf_pages": ("facets.pdf.pages", "int32"),
    "pdf_author": ("facets.pdf.author", "string")
  }
}

7.3 Chunk-Facets (multimodal)

Immer: doc_id (facet), modality (facet: text|caption|ocr|figure|table|asr|summary), language

Optional: section, subsection, page, t_start, t_end (für Filter/Range)



---

8. DB‑Agnostik & Hybrid Search

**Primäre Engine: Typesense**
- ✅ Hybrid Search (BM25 + Vector) in einem Query
- ✅ Native Grouping (`group_by=doc_id`, max 3 Chunks pro Doc)
- ✅ Faceting & Filtering out-of-the-box

**Prinzip: Engine-Agnostik**
- SoT bleibt Dateisystem (JSON/NDJSON)
- Such-/Vektor-Layer austauschbar via dünne Abstraktion
- Alternative Engines: Meilisearch, Qdrant, pgvector

8.1 Such-Interface

class SearchIndex:
    def upsert_docs(self, docs: list[dict]) -> None: ...
    def delete_docs(self, ids: list[str]) -> None: ...

    def bm25(self, q: str, filters: dict | None, top_k: int) -> list[dict]: ...
    def ann(self, vector: list[float], filters: dict | None, top_k: int, model: str | None = None) -> list[dict]: ...
    def hybrid(self, q: str, vector: list[float] | None, filters: dict | None, top_k: int) -> list[dict]: ...

Implementierungen:

index_typesense.py → BM25 + optional eingebaute Vektor-Suche, Grouping via group_by=doc_id

index_qdrant.py → reine ANN (payload-Filter), für Fusion genutzt

index_pgvector.py → SQL‑basiertes ANN für kleine–mittlere Skalen


8.2 Hybrid-Fusion (engine‑neutral)

Hole k1 BM25 (Typesense/Meili), k2 ANN (Qdrant/pgvector/Typesense)

Score‑Fusion (RRF oder gewichtete Summe), MMR für Diversität

Grouping: immer doc_id → max. N Chunks pro Dokument


Pseudocode (RRF):

from collections import defaultdict

def rrf_merge(bm25_hits, ann_hits, k=60):
    S = defaultdict(float)
    for r, h in enumerate(bm25_hits, 1): S[h["doc_id"]] += 1/(k+r)
    for r, h in enumerate(ann_hits, 1):  S[h["doc_id"]] += 1/(r)
    return sorted(S.items(), key=lambda x: -x[1])

8.3 Blue‑Green & Aliases (engine‑agnostisch)

Collections versionieren: kb_chunks_vN, kb_docs_vN

Aliases: kb_chunks, kb_docs → atomischer Swap nach Rebuild

Gilt identisch für Typesense, Meili, Qdrant (Collections/Aliases) und kann bei pgvector via Views/Schemata emuliert werden


8.4 Embedding‑Schienen

Text‑Space (Pflicht) + optionale Image/Audio‑Spaces

Felder pro Space: embedding_<space>, embedding_model_<space>, embedding_dim_<space>, embedding_at_<space>

Query wählt Space explizit; Fusion kombiniert Spaces (optional)



---

9. Aktualisierte Schema‑Ausschnitte (mit Facets & Multimodal)

9.1 Record (ergänzt)

{
  "id": "01HAR6...",
  "doc_type": "note",
  "tags": ["kochen", "ofen"],
  "categories": ["Kochen"],
  "language": "de",
  "date_semantic": "2025-01-09T18:00:00Z",
  "status": { "relevance_score": 0.8, "archived": false },
  "agent": { "id": "linker", "confidence": 0.94, "reviewed": false },
  "facets": { "pdf": { "pages": 2 } },
  "source": { "repo": "github.com/you/pkms", "commit": "84ac..." }
}

9.2 Chunk (ergänzt)

{
  "doc_id": "01HAR6...",
  "chunk_id": "01HAR6...:a3f2bc1d",
  "chunk_hash": "a3f2bc1d",  // xxhash64(text)[:12]
  "chunk_index": 7,
  "modality": "caption",  // text|caption|ocr|figure|table|asr|summary
  "section": "Ergebnisse",
  "language": "de",
  "text": "Abbildung zeigt ...",
  "tokens": 42
}

9.3 Embedding (Filesystem, multi‑space)

# File: data/embeddings/text-3-large-2025-06/a3f2bc1d.npy
# Content: np.array([0.0123, -0.9876, ...], dtype=float32)

# Optional: Für Image-Space
# File: data/embeddings/clip-vit-large/a3f2bc1d.npy

# Metadaten-Tracking im Record-JSON:
{
  "embedding_meta": {
    "text": {
      "model": "text-3-large-2025-06",
      "dim": 3072,
      "updated_at": "2025-11-14T08:10:01Z",
      "chunk_hashes": ["a3f2bc1d", "f9e1a2b3", ...]
    }
  }
}


---

10. Defaults für Index‑Schemas (Engine‑neutral)

Docs‑Collection (pro Dokument):

searchable: title, full_text

facets: doc_type, tags[], categories[], language, status.archived, agent.reviewed

filter/sort: date_semantic_ms, updated_ms, status.relevance_score


Chunks‑Collection (pro Chunk):

searchable: text, title

facets: doc_id, modality, language, (optional) section, page

vectors: embedding_text: float[] (optional: embedding_image[], embedding_audio[])

sort: updated_ms


> Hinweis: Die tatsächliche Felddefinition (Typesense/Meili/Qdrant/pgvector) wird in den jeweiligen Adapter‑Modulen abgebildet. Das SoT bleibt engine‑neutral.

---

11. Key Design Decisions (v0.3)

**Chunk-IDs: Content-Hash statt Index**
- ✅ `chunk_id = doc_id:xxhash64(text)[:12]`
- ✅ Deterministisch, dedup-fähig, embedding-cache-freundlich
- ❌ Sequenzielle IDs (brechen bei Re-Chunking)

**Embeddings: Filesystem statt NDJSON**
- ✅ `data/embeddings/{model}/{chunk_hash}.npy`
- ✅ Incremental updates, modell-agnostisch, garbage-collectable
- ❌ Embeddings in Chunk-NDJSON (schlecht für Tracking)

**Synth-Review: Git-Branches statt Staging**
- ✅ Feature-Branch → PR → Merge
- ✅ Native Git-Locking, Rollback, Review-UI
- ❌ Custom `staging/` Filesystem

**Link-Tracking: Bidirektional**
- ✅ Forward Links + Backlinks
- ✅ Graph-Analyse, Orphan-Detection, Archive-Warnings
- ❌ Nur Forward Links (verliert Kontext)

**Relevance-Scoring: Formel statt Agent**
- ✅ Deterministisch, nachvollziehbar, A/B-testbar
- ✅ `0.4*recency + 0.3*links + 0.2*quality + 0.1*user`
- ❌ LLM-basiertes Scoring (teuer, non-deterministisch)

**Chunking: Hybrid (Hierarchisch + Semantisch)**
- ✅ Markdown-Headings + Sentence-Embedding-Splits
- ✅ Respektiert Struktur + semantische Kohärenz
- ❌ Nur fix-size Chunks (ignoriert Semantik)

**Search: Typesense als Primary**
- ✅ Hybrid (BM25+Vector), Grouping, Faceting
- ✅ Engine-agnostisch via Abstraktion
- ❌ Meilisearch (kein natives Grouping)

**Frontmatter vs JSON: Separation of Concerns**
- ✅ Frontmatter = Manuell/LLM-editierbar
- ✅ JSON = Tool-generiert, abgeleitet
- ❌ Alles in Frontmatter (bläht Markdown auf)

**Schema: JSON-Schema → Pydantic**
- ✅ `schema/*.schema.json` → Code-Gen
- ✅ Single Source of Truth
- ❌ Code-First (Schema divergiert)

**Language: Frontmatter (auto-detect, überschreibbar)**
- ✅ In YAML-Header, damit manuell korrigierbar
- ✅ Auto-Detection via `langdetect` wenn leer
- ❌ Nur in JSON (nicht überschreibbar)
