---
date_created: 2025-11-15
language: de
title: PKMS – Dateinamen & UUID-Konzept
---

# Idee
- Format: `slug.uuid8.ext`
- Beispiel: `local-llm-setup.01HD3M7G8Z4ZN1YT4W6P1ZP6C9.md`

# Vorteile
- Menschlich lesbar + trotzdem eindeutig
- UUID Teil erlaubt stabile Referenzen in Embeddings, JSON, etc.
- Umbennenbar, solange UUID gleich bleibt

# ToDo
- Utilities: `rename_with_uuid.py`
- Tests mit vorhandenen Notizen