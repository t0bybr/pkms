# Call‑Site‑Fix – Search‑Ergebnisse **Tuples → Dicts** (v2.6)

**Ziel:** Alle Stellen umstellen, die noch Tuple‑Ergebnisse aus `search_keyword`/`search_semantic` erwarten.
**Risiko bei Nicht‑Umstellung:** `ValueError: too many values to unpack`, falsche Index‑Zugriffe, kaputte Sortierung/Anzeige.

---

## 1) Finde alle Call‑Sites

```bash
# 1. direkte Aufrufe
rg -n --no-heading -g '!**/.pkms/**' "search_(keyword|semantic)\("

# 2. typische Tuple‑Unpacking‑Loops
rg -n --no-heading -g '!**/.pkms/**' "for\s*\([^)]*\)\s+in\s+search_(keyword|semantic)\("

# 3. Index‑Zugriffe auf Ergebnis‑Rows (heuristisch)
rg -n --no-heading -g '!**/.pkms/**' "\[[0-6]\]\s*(\)|,|\.|\])"
```

**Hinweis:** Test‑ und CLI‑Ordner nicht vergessen (z. B. `tests/`, `.pkms/lib/cli/`).

---

## 2) Mapping (neu → alt)

```text
Dict-Key          Früherer Tuple‑Index
-------------------------------------
chunk_id          [0]
note_id           [1]
note_title        [2]
text              [3]
path              [4]
section_heading   [5]
score (keyword)   [6]
distance (semant.)[6]
```

---

## 3) Mini‑Diffs (Before → After)

### A) Keyword‑Suche: Loop‑Unpacking
```diff
-for rid, note_id, title, text, path, section, score in search_keyword(q, top_k=5):
-    print(title, score, path)
+for r in search_keyword(q, top_k=5):
+    print(r['note_title'], r['score'], r['path'])
```

### B) Semantic‑Suche: Loop‑Unpacking
```diff
-for rid, note_id, title, text, path, section, dist in search_semantic(q, 10):
-    items.append((title, dist))
+for r in search_semantic(q, 10):
+    items.append((r['note_title'], r['distance']))
```

### C) Index‑Zugriffe auf die erste Zeile
```diff
-rows = search_keyword(q)
-first_title = rows[0][2]
+rows = search_keyword(q)
+first_title = rows[0]['note_title']
```

### D) Sortierungen/Keys
```diff
-rows = sorted(search_keyword(q), key=lambda r: r[6], reverse=True)
+rows = sorted(search_keyword(q), key=lambda r: r['score'], reverse=True)

-rows = sorted(search_semantic(q), key=lambda r: r[6])
+rows = sorted(search_semantic(q), key=lambda r: r['distance'])
```

### E) CLI‑Ausgabe
```diff
-for i, (rid, note_id, title, text, path, section, score) in enumerate(search_keyword(q), 1):
-    click.echo(f"{i}. {title} [{score:.3f}]\n   {path}\n   {text[:150]}…\n")
+for i, r in enumerate(search_keyword(q), 1):
+    click.echo(f"{i}. {r['note_title']} [{r['score']:.3f}]\n   {r['path']}\n   {r['text'][:150]}…\n")
```

---

## 4) Quick‑Checks (nach dem Refactor)

```bash
# 1) Lint/Type‑Check (falls im Projekt vorhanden)
ruff .  # oder flake8 / mypy

# 2) E2E
python .pkms/init_db.py
python .pkms/testing/test_e2e.py

# 3) Smoke‑Run der CLI
python -m pkms.lib.cli.commands ksearch "stichwort" --k 3
python -m pkms.lib.cli.commands ssearch "stichwort" --k 3
```

---

## 5) Optional: Übergangs‑Shim (nur falls Zeitdruck)

> Nicht empfohlen langfristig, aber reduziert kurzfristig das Risiko.

```python
# .pkms/lib/search/compat.py
from .search import search_keyword as _kw, search_semantic as _sem

def search_keyword_tuples(*args, **kwargs):
    m = _kw(*args, **kwargs)
    return [
        (r['chunk_id'], r['note_id'], r['note_title'], r['text'], r['path'], r['section_heading'], r['score'])
        for r in m
    ]

def search_semantic_tuples(*args, **kwargs):
    m = _sem(*args, **kwargs)
    return [
        (r['chunk_id'], r['note_id'], r['note_title'], r['text'], r['path'], r['section_heading'], r['distance'])
        for r in m
    ]
```

> Nutzung: Alte Call‑Sites temporär auf `from ..search.compat import search_keyword_tuples as search_keyword` umbiegen. Danach sukzessive entfernen.

---

## 6) Checkliste (kurz)

- [ ] Alle `for (… ) in search_keyword/semantic(` auf `for r in …` umgestellt.
- [ ] Alle `row[i]`‑Zugriffe ersetzt durch Dict‑Keys (Mapping oben).
- [ ] Sortier‑Keys/Format‑Strings angepasst (`score` vs. `distance`).
- [ ] CLI/Tests laufen grün (E2E/Smoke).

