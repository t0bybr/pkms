from sentence_transformers import SentenceTransformer
_EMB=None
def get_text_embedder():
    global _EMB
    if _EMB is None:
        _EMB = SentenceTransformer("BAAI/bge-m3"); _EMB.max_seq_length=512
    return _EMB
def embed_texts(texts):
    emb = get_text_embedder()
    return emb.encode(texts, normalize_embeddings=True).tolist()
