---
date_created: 2025-11-15
language: de
title: Lokale KI-Hardware – Überlegungen
---

# Rahmen
- Fokus: Datenschutz + Bastelspaß
- Budget limitiert, keine Enterprise-GPUs

# Notizen
- 4B-Modelle mit Vision brauchen schnell ~40–50 GB RAM/GPU
- 70B-Modelle in 4-Bit sind zwar theoretisch kleiner,
  brauchen aber trotzdem sehr viel VRAM + Bandbreite
- Realistische Zielklasse: 7B–14B mit guter Quantisierung

# TODO
- Konkrete Benchmarks mit Ollama + Vulkan
- Energieverbrauch vs. Nutzen abwägen