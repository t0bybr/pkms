import os, lancedb
from lancedb import vector
import pyarrow as pa
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

def _to_pa_type(t):
    if isinstance(t, pa.DataType):
        return t
    if t is str:
        return pa.string()
    if t is int:
        return pa.int64()
    if t is float:
        return pa.float64()
    # lancedb.vector(...) returns a valid Arrow extension type
    return t

def _to_pa_schema(d: dict) -> pa.Schema:
    # d maps field_name -> python types, pyarrow types, or lancedb.vector types
    return pa.schema([pa.field(k, _to_pa_type(v)) for k, v in d.items()])

def table(name: str, schema: dict=None):
    names = DB.table_names()
    if name in names:
        return DB.open_table(name)
    if schema is None:
        raise ValueError(f"Schema required to create table '{name}'")
    pa_schema = _to_pa_schema(schema) if isinstance(schema, dict) else schema
    return DB.create_table(name, schema=pa_schema)

# Schemas
_TEXT_DIM = TEXT_META.get("embedding_dim", 1024)
TEXT_SCHEMA = {
    "path": str,
    "title": str,
    "text": str,
    "embedding": vector(_TEXT_DIM)
}

_CODE_DIM = CODE_META.get("embedding_dim", 1024)
CODE_SCHEMA = {
    "path": str,
    "code": str,
    "embedding": vector(_CODE_DIM)
}

_IMG_DIM = IMAGE_META.get("embedding_dim", 768)
IMAGE_SCHEMA = {
    "path_crop": str,
    "bbox": pa.list_(pa.float32()),
    "page_sha": str,
    "primary_text_id": str,
    "nearest_heading": str,
    "embedding": vector(_IMG_DIM)
}

TEXT = table('text_v1', TEXT_SCHEMA)
CODE = table('code_v1', CODE_SCHEMA)
IMAGE= table('image_v1', IMAGE_SCHEMA)

__all__=["DB","TEXT","CODE","IMAGE","TEXT_META","CODE_META","IMAGE_META","table"]
