---
date_created: 2025-11-15
language: de
title: Trackball Firmware – ZMK + PIM447
---

# Problem
- ZMK-Treiber für PIM447 Trackball
- Symptom: Keyboard hängt, sobald Trackball berührt wird

# Hypothesen
- SPI-Konfiguration falsch (Mode, Clock)
- Interrupt-Pin nicht richtig deglitched
- Power-Management / Sleep-Mode vom Sensor?

# To Investigate
- Minimal-Firmware nur für Trackball auf Testboard
- Logic Analyzer an MOSI/MISO/CLK/CS hängen
- Vergleich mit Beispielcode von Pimoroni