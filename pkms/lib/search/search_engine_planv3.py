# pkms/lib/search/search_engine_planv3.py
"""
Plan v0.3 compliant search engine:
- Chunk-based (not document-based)
- Content-hash chunk IDs
- .npy embedding files
- RRF fusion (BM25 + Semantic)
- Whoosh for BM25 (later: Typesense)
"""

import os
import json
from typing import Callable, List, Dict, Optional, Tuple
from pathlib import Path

import numpy as np
from whoosh.index import create_in, open_dir, exists_in
from whoosh.fields import Schema, TEXT, ID, STORED
from whoosh.qparser import MultifieldParser


# ------------------------------------------------------------
# Schema
# ------------------------------------------------------------

def _get_schema() -> Schema:
    """
    Whoosh-Schema für Chunks.

    Fields:
    - chunk_id: unique identifier (doc_id:chunk_hash)
    - doc_id: parent document ULID (for grouping)
    - text: chunk content (indexed, not stored)
    - section: heading/section name (stored for display)
    - chunk_index: for ordering within doc
    """
    return Schema(
        chunk_id=ID(stored=True, unique=True),
        doc_id=ID(stored=True),  # for grouping
        text=TEXT(stored=False),  # indexed but not stored (save space)
        section=STORED(),  # for display
        chunk_index=STORED(),  # for ordering
    )


# ------------------------------------------------------------
# Cosine Similarity
# ------------------------------------------------------------

def _cosine_similarity(query_vec: np.ndarray, doc_mat_normed: np.ndarray) -> np.ndarray:
    """
    Kosinus-Ähnlichkeit zwischen Query-Vektor und normalisierten Chunk-Vektoren.
    doc_mat_normed: (N, dim), Zeilen bereits normiert.
    """
    if doc_mat_normed.size == 0:
        return np.zeros((0,), dtype=np.float32)

    q = np.asarray(query_vec, dtype=np.float32)
    q_norm = np.linalg.norm(q)
    if q_norm == 0:
        return np.zeros((doc_mat_normed.shape[0],), dtype=np.float32)

    q_normed = q / q_norm
    return doc_mat_normed @ q_normed


# ------------------------------------------------------------
# Index-Aufbau (Whoosh) für Chunks
# ------------------------------------------------------------

def _build_or_open_chunk_index(chunks_dir: str, index_dir: str):
    """
    Öffnet existierenden Chunk-Index oder erstellt ihn neu.

    Liest NDJSON-Dateien aus chunks_dir:
      data/chunks/{doc_id}.ndjson

    Jede Zeile: {"chunk_id": "01HAR:a3f2bc", "doc_id": "01HAR", "text": "...", ...}
    """
    if not os.path.exists(index_dir):
        os.makedirs(index_dir)

    if exists_in(index_dir):
        ix = open_dir(index_dir)
    else:
        schema = _get_schema()
        ix = create_in(index_dir, schema)
        writer = ix.writer()

        chunks_path = Path(chunks_dir)
        if chunks_path.exists():
            for ndjson_file in chunks_path.glob("*.ndjson"):
                try:
                    with open(ndjson_file, "r", encoding="utf-8") as f:
                        for line_num, line in enumerate(f, 1):
                            if not line.strip():
                                continue
                            try:
                                chunk = json.loads(line)
                                writer.add_document(
                                    chunk_id=chunk["chunk_id"],
                                    doc_id=chunk["doc_id"],
                                    text=chunk["text"],
                                    section=chunk.get("section", ""),
                                    chunk_index=chunk.get("chunk_index", 0),
                                )
                            except (json.JSONDecodeError, KeyError) as e:
                                print(f"[chunk_index] WARN: {ndjson_file}:{line_num} - {e}")
                except Exception as e:
                    print(f"[chunk_index] WARN: Could not read {ndjson_file}: {e}")

        writer.commit()

    return ix


# ------------------------------------------------------------
# Embedding-Laden (.npy Files)
# ------------------------------------------------------------

def _load_chunk_embeddings(emb_dir: str) -> Tuple[List[str], np.ndarray]:
    """
    Lädt Chunk-Embeddings aus .npy-Dateien:
      data/embeddings/{model}/{chunk_hash}.npy

    Erwartet:
    - Dateiname = chunk_hash (12 hex chars)
    - Inhalt = np.array([...], dtype=float32)

    Rückgabe:
    - chunk_hashes: list[str] (ohne .npy extension)
    - embeddings_normed: np.ndarray (N, dim), already normalized
    """
    emb_path = Path(emb_dir)
    if not emb_path.exists():
        return [], np.zeros((0, 0), dtype=np.float32)

    chunk_hashes = []
    vectors = []

    for npy_file in emb_path.glob("*.npy"):
        chunk_hash = npy_file.stem  # remove .npy
        try:
            vec = np.load(npy_file)
            if vec.ndim != 1:
                print(f"[embeddings] WARN: {npy_file} has wrong shape {vec.shape}, expected 1D")
                continue
            chunk_hashes.append(chunk_hash)
            vectors.append(vec)
        except Exception as e:
            print(f"[embeddings] WARN: Could not load {npy_file}: {e}")

    if not vectors:
        return [], np.zeros((0, 0), dtype=np.float32)

    mat = np.stack(vectors, axis=0).astype(np.float32)

    # Normalize rows
    norms = np.linalg.norm(mat, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    mat_normed = mat / norms

    return chunk_hashes, mat_normed


# ------------------------------------------------------------
# Chunk-Hash ↔ Chunk-ID Mapping
# ------------------------------------------------------------

def _build_hash_to_chunkid_map(chunks_dir: str) -> Dict[str, str]:
    """
    Baut Mapping: chunk_hash → chunk_id (doc_id:chunk_hash)

    Liest alle .ndjson Files und extrahiert (chunk_hash, chunk_id) Paare.
    """
    hash_map = {}
    chunks_path = Path(chunks_dir)

    if not chunks_path.exists():
        return hash_map

    for ndjson_file in chunks_path.glob("*.ndjson"):
        try:
            with open(ndjson_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        chunk = json.loads(line)
                        chunk_hash = chunk.get("chunk_hash")
                        chunk_id = chunk.get("chunk_id")
                        if chunk_hash and chunk_id:
                            hash_map[chunk_hash] = chunk_id
                    except (json.JSONDecodeError, KeyError):
                        continue
        except Exception:
            continue

    return hash_map


# ------------------------------------------------------------
# SearchEngine (Chunk-basiert)
# ------------------------------------------------------------

class SearchEngine:
    """
    Plan v0.3 compliant search engine:

    - Keyword-Suche über Chunks (Whoosh BM25)
    - Semantische Suche über Chunk-Embeddings (Kosinus)
    - RRF-Fusion
    - Grouping: max N Chunks pro doc_id
    """

    def __init__(
        self,
        chunks_dir: str,
        emb_dir: str,
        index_dir: str,
        embed_fn: Optional[Callable[[str], np.ndarray]] = None,
        max_keyword_hits: int = 50,
        max_semantic_hits: int = 50,
        rrf_k: int = 60,
        group_limit: int = 3,
    ):
        """
        :param chunks_dir: Directory with chunk NDJSON files (data/chunks/)
        :param emb_dir: Directory with .npy embedding files (data/embeddings/{model}/)
        :param index_dir: Whoosh index directory (cache)
        :param embed_fn: Function: text -> np.ndarray (embedding)
        :param max_keyword_hits: BM25 hits for RRF
        :param max_semantic_hits: Semantic hits for RRF
        :param rrf_k: RRF parameter (usually 60)
        :param group_limit: Max chunks per doc_id in results
        """
        self.chunks_dir = chunks_dir
        self.emb_dir = emb_dir
        self.index_dir = index_dir
        self.embed_fn = embed_fn
        self.max_keyword_hits = max_keyword_hits
        self.max_semantic_hits = max_semantic_hits
        self.rrf_k = rrf_k
        self.group_limit = group_limit

        # Build caches
        self.ix = _build_or_open_chunk_index(chunks_dir, index_dir)
        self.chunk_hashes, self.embeddings_normed = _load_chunk_embeddings(emb_dir)
        self.hash_to_chunkid = _build_hash_to_chunkid_map(chunks_dir)

        print(f"[SearchEngine] Initialized:")
        print(f"  - {len(self.chunk_hashes)} embeddings loaded")
        print(f"  - Whoosh index: {index_dir}")

    # ---------- Keyword Search (BM25 via Whoosh) ----------

    def _keyword_search(self, query_text: str, limit: int) -> List[Dict]:
        """BM25-Suche über Chunks."""
        results_list = []
        with self.ix.searcher() as searcher:
            parser = MultifieldParser(["text"], self.ix.schema)
            query = parser.parse(query_text)
            whoosh_results = searcher.search(query, limit=limit)
            for hit in whoosh_results:
                results_list.append({
                    "chunk_id": hit["chunk_id"],
                    "doc_id": hit["doc_id"],
                    "section": hit.get("section", ""),
                    "chunk_index": hit.get("chunk_index", 0),
                    "score": float(hit.score),
                })
        return results_list

    # ---------- Semantic Search (Cosine via Embeddings) ----------

    def _semantic_search(self, query_vec: np.ndarray, limit: int) -> List[Dict]:
        """Semantische Suche über Chunk-Embeddings."""
        if self.embeddings_normed.size == 0:
            return []

        sims = _cosine_similarity(query_vec, self.embeddings_normed)
        top_idx = np.argsort(sims)[::-1][:limit]

        results = []
        for idx in top_idx:
            chunk_hash = self.chunk_hashes[idx]
            chunk_id = self.hash_to_chunkid.get(chunk_hash)
            if not chunk_id:
                continue

            # Extract doc_id from chunk_id (format: "doc_id:chunk_hash")
            doc_id = chunk_id.split(":", 1)[0] if ":" in chunk_id else chunk_id

            results.append({
                "chunk_id": chunk_id,
                "doc_id": doc_id,
                "chunk_hash": chunk_hash,
                "score": float(sims[idx]),
            })

        return results

    # ---------- RRF Fusion ----------

    def _rrf_fusion(
        self,
        results_lists: List[List[Dict]],
        top_k: int,
    ) -> List[Tuple[str, float]]:
        """
        Reciprocal Rank Fusion über chunk_id.
        """
        scores: Dict[str, float] = {}

        for results in results_lists:
            for rank, r in enumerate(results):
                chunk_id = r["chunk_id"]
                contrib = 1.0 / (self.rrf_k + rank + 1)
                scores[chunk_id] = scores.get(chunk_id, 0.0) + contrib

        sorted_chunks = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_chunks[:top_k]

    # ---------- Grouping (max N chunks per doc_id) ----------

    def _apply_grouping(
        self,
        fused_pairs: List[Tuple[str, float]],
        kw_dict: Dict[str, Dict],
        sem_dict: Dict[str, Dict],
    ) -> List[Dict]:
        """
        Gruppiert Chunks nach doc_id, max group_limit Chunks pro Doc.
        """
        doc_groups: Dict[str, List[Tuple[str, float]]] = {}

        for chunk_id, rrf_score in fused_pairs:
            # Get doc_id from metadata
            doc_id = kw_dict.get(chunk_id, {}).get("doc_id") or \
                     sem_dict.get(chunk_id, {}).get("doc_id")

            if not doc_id:
                # Fallback: extract from chunk_id
                doc_id = chunk_id.split(":", 1)[0] if ":" in chunk_id else chunk_id

            if doc_id not in doc_groups:
                doc_groups[doc_id] = []

            if len(doc_groups[doc_id]) < self.group_limit:
                doc_groups[doc_id].append((chunk_id, rrf_score))

        # Flatten grouped results
        final_results = []
        for doc_id, chunks in doc_groups.items():
            for chunk_id, rrf_score in chunks:
                kw_meta = kw_dict.get(chunk_id, {})
                sem_meta = sem_dict.get(chunk_id, {})

                bm25 = kw_meta.get("score")
                semantic = sem_meta.get("score")

                if bm25 is not None and semantic is not None:
                    source = "hybrid"
                elif bm25 is not None:
                    source = "keyword"
                else:
                    source = "semantic"

                final_results.append({
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "rrf_score": rrf_score,
                    "bm25": bm25,
                    "semantic": semantic,
                    "source": source,
                    "section": kw_meta.get("section", ""),
                    "chunk_index": kw_meta.get("chunk_index", 0),
                })

        return final_results

    # ---------- Public API ----------

    def search(self, query_text: str, k: int = 10) -> List[Dict]:
        """
        Hybrid search with RRF fusion and grouping.

        Returns:
          [
            {
              "chunk_id": "01HAR6DP:a3f2bc1d",
              "doc_id": "01HAR6DP",
              "rrf_score": 0.123,
              "bm25": 5.67 or None,
              "semantic": 0.89 or None,
              "source": "keyword"|"semantic"|"hybrid",
              "section": "Ofentemperatur",
              "chunk_index": 7
            },
            ...
          ]
        """
        # 1) Keyword search
        kw_results = self._keyword_search(query_text, limit=self.max_keyword_hits)
        kw_dict = {r["chunk_id"]: r for r in kw_results}

        # 2) Semantic search (if embed_fn available)
        if self.embed_fn is None or self.embeddings_normed.size == 0:
            # Keyword-only fallback
            return [
                {
                    "chunk_id": r["chunk_id"],
                    "doc_id": r["doc_id"],
                    "rrf_score": None,
                    "bm25": r["score"],
                    "semantic": None,
                    "source": "keyword",
                    "section": r.get("section", ""),
                    "chunk_index": r.get("chunk_index", 0),
                }
                for r in kw_results[:k]
            ]

        query_vec = self.embed_fn(query_text)
        sem_results = self._semantic_search(query_vec, limit=self.max_semantic_hits)
        sem_dict = {r["chunk_id"]: r for r in sem_results}

        # 3) RRF fusion
        fused_pairs = self._rrf_fusion(
            results_lists=[kw_results, sem_results],
            top_k=k * 5,  # Get more candidates for grouping
        )

        # 4) Grouping (max N chunks per doc)
        final_results = self._apply_grouping(fused_pairs, kw_dict, sem_dict)

        return final_results[:k]


# ------------------------------------------------------------
# Example Usage
# ------------------------------------------------------------

if __name__ == "__main__":
    # Dummy embedding function for testing
    def dummy_embed(text: str) -> np.ndarray:
        return np.random.rand(384).astype(np.float32)

    CHUNKS_DIR = "data/chunks"
    EMB_DIR = "data/embeddings/nomic-embed-text"
    INDEX_DIR = "data/whoosh_index"

    engine = SearchEngine(
        chunks_dir=CHUNKS_DIR,
        emb_dir=EMB_DIR,
        index_dir=INDEX_DIR,
        embed_fn=dummy_embed,
        group_limit=3,
    )

    results = engine.search("pizza ofen temperatur", k=10)
    for r in results:
        print(
            f"{r['chunk_id']:40} "
            f"doc={r['doc_id']:26} "
            f"rrf={r['rrf_score']:.4f} "
            f"(bm25={r['bm25']}, sem={r['semantic']}) "
            f"[{r['source']}] "
            f"§{r['section']}"
        )
