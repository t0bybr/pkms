---
date_created: 2025-11-15
language: de
title: Home Assistant – Jalousie-Blueprint Gedanken
---

# Features
- Kurz-/Langdruck Taster
- Tilt-Modus (2x Hoch zum Umschalten)
- State Machine:
  - `IDLE`
  - `MOVING_UP`
  - `MOVING_DOWN`
  - `TILT_ACTIVE`

# Anforderungen
- Logo/MQTT sauber entkoppeln
- Tilt deaktivieren, wenn andere Fahrt endet