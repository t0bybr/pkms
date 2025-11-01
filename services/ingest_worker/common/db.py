import os, lancedb
INDEX_DIR=os.environ.get('INDEX_DIR','/app/index')
DB = lancedb.connect(INDEX_DIR)

TEXT_META = {
    "schema_version": 1,
    "embedding_model_id": "BAAI/bge-m3",
    "embedding_dim": 1024
}

CODE_META = TEXT_META.copy()

# Image embeddings come from OpenCLIP (default ViT-L-14 @ openai)
IMAGE_EMBED_MODEL_ID = os.environ.get('IMAGE_EMBED_MODEL_ID', 'open_clip/ViT-L-14@openai')
IMAGE_EMBED_DIM = int(os.environ.get('IMAGE_EMBED_DIM', '768'))
IMAGE_META = {
    "schema_version": 1,
    "embedding_model_id": IMAGE_EMBED_MODEL_ID,
    "embedding_dim": IMAGE_EMBED_DIM
}

def table(name: str, schema: dict=None):
    if name in DB.table_names():
        return DB.open_table(name)
    return DB.create_table(name, data=[], schema=schema or None)

TEXT = table('text_v1')
CODE = table('code_v1')
IMAGE= table('image_v1')

__all__=["DB","TEXT","CODE","IMAGE","TEXT_META","CODE_META","IMAGE_META","table"]
