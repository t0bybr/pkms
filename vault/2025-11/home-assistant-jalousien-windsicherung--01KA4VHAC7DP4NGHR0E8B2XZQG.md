---
date_created: 2025-11-15
language: de
title: Home Assistant – Jalousien Windsicherung
---

# Ziel
- Bei starkem Wind alle Jalousien in Sicherheitsposition fahren
- Automationen sollen lokale Taster weiterhin erlauben, aber mit Limit

# Notizen
- Winddaten aktuell über Shelly + Logo → MQTT → Home Assistant
- Schwellenwert z. B. 40 km/h Böen
- State Machine im Blueprint:
  - `NORMAL`
  - `WIND_PROTECT`
  - `MANUAL_OVERRIDE`

# TODO
- Hysterese für Windschwelle, damit es nicht flackert
- Visualisierung im Dashboard (Icon + Textstatus)