import os, lancedb
INDEX_DIR=os.environ.get('INDEX_DIR','/app/index')
DB = lancedb.connect(INDEX_DIR)

META = {
    "schema_version": 1,
    "embedding_model_id": "BAAI/bge-m3",
    "embedding_dim": 1024
}

def table(name: str, schema: dict=None):
    if name in DB.table_names():
        return DB.open_table(name)
    return DB.create_table(name, data=[], schema=schema or None)

TEXT = table('text_v1')
CODE = table('code_v1')
IMAGE= table('image_v1')

__all__=["DB","TEXT","CODE","IMAGE","META","table"]

