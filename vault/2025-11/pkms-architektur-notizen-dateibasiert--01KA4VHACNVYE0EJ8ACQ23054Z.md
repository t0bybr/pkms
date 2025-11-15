---
date_created: 2025-11-15
language: de
title: PKMS – Architektur-Notizen (Dateibasiert)
---

# Leitplanken
- KISS: Möglichst wenig Technik, maximaler Nutzen
- Alles sind Dateien (Markdown, JSON, evtl. DuckDB als Index)
- Kein Vendor-Lock-In, keine proprietären Clouds

# Struktur-Idee
- `knowledge/notes/*.md` für Inhalt
- `knowledge/.schemas/*.json` für Formate
- `knowledge/.tools/` für kleine Helferskripte (search, validate, embed)

# Offene Punkte
- Link-Syntax (UUID im Dateinamen vs. WikiLinks)
- Frontmatter-Minimum vs. „Rich“ Frontmatter