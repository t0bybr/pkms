# PKMS JSON Schemas

JSON Schema definitions für alle PKMS-Datenstrukturen.

## Schemas

- **record.schema.json** - Haupt-Dokument-Metadaten (generiert aus Markdown + Frontmatter)
- **chunk.schema.json** - Text-Chunk mit Content-addressable ID
- **link.schema.json** - Wikilink-Struktur (Forward/Backlink)
- **status.schema.json** - Dokument-Status und Relevanz
- **embedding_meta.schema.json** - Embedding-Metadaten pro Space (text/image/audio)

## Pydantic Code-Generation

### Installation

```bash
pip install datamodel-code-generator
```

### Generierung

```bash
# Alle Schemas → Python-Modelle
datamodel-code-generator \
  --input schema/ \
  --input-file-type jsonschema \
  --output pkms/models/generated.py \
  --use-standard-collections \
  --use-schema-description \
  --field-constraints \
  --strict-types

# Einzelnes Schema
datamodel-code-generator \
  --input schema/record.schema.json \
  --input-file-type jsonschema \
  --output pkms/models/record.py
```

### Verwendung

```python
from pkms.models.generated import Record, Chunk, Link

# Validierung
record = Record(**json_data)

# Serialisierung
json_str = record.model_dump_json()
```

## Schema-Validierung

```bash
# Via jsonschema-cli
pip install check-jsonschema

check-jsonschema \
  --schemafile schema/record.schema.json \
  data/records/pizza--01HAR6DP.json
```

## Prinzipien

1. **Single Source of Truth** - Schemas sind führend, Code wird generiert
2. **Strict Typing** - Alle Felder validiert
3. **Versionierung** - Schemas sind Teil des Git-Repos
4. **Engine-Neutral** - Unabhängig von Typesense/Whoosh/etc.

## Schema-Referenzen

- `record.schema.json` referenziert:
  - `link.schema.json` (via `$ref`)
  - `status.schema.json`
  - `embedding_meta.schema.json`

- Relative `$ref` werden beim Code-Gen aufgelöst
