# UI_palette — Dynamic 4-Color Theme System for PyQt5

A reusable, user-customizable color theme framework for PyQt5 applications. The entire UI palette is derived from just **4 base colors** — each independently adjustable via HEX input or system color picker.

## Quick Start

```bash
git clone https://github.com/YoukoSaint/UI_palette.git
cd UI_palette
pip install pyqt5 pyqtgraph
python main_window.py
```

## For Agents / AI Tools

> **Read [`REPRODUCE.md`](REPRODUCE.md) first.** It contains the full architecture breakdown, step-by-step integration guide, performance checklist, and design rationale needed to reproduce or extend this system in any PyQt5 project.

## Files

| File | Role |
|------|------|
| `color_scheme.py` | Color state + QSS generator (no PyQt deps) |
| `color_panel.py` | Compact color picker UI widget |
| `main_window.py` | Host window with toggle button + demo charts |
| `plot_widgets.py` | pyqtgraph charts consuming dynamic colors |
| `settings_manager.py` | JSON persistence for colors + params |
| `REPRODUCE.md` | Full architecture & integration guide |
| `README.md` | This file |

## How It Works

```
┌─────────────────────────────────┐
│         color_scheme.py          │  Single source of truth
│  ColorScheme (4 base + extras)  │
│  get_stylesheet() → full QSS    │
└────────────┬────────────────────┘
             │
   ┌─────────┼─────────┐
   ▼         ▼         ▼
main_window  color     plot_widgets
 (QSS)      _panel    (chart pens)
```

**4 base colors** control the entire look:

| Role | Controls |
|------|----------|
| **TEXT** | All text/foreground colors |
| **LIGHT** | Panel, card, surface backgrounds |
| **DARK** | Main window, chart plot backgrounds |
| **LINE** | Borders, splitters, separators |

Additional chart curve colors (Spectrum, Trend, Resistance) are also user-adjustable.

## Features

- **4-color base palette** — entire UI derived from TEXT / LIGHT / DARK / LINE
- **HEX input + system color picker** per color
- **Real-time preview** — changes apply instantly to all widgets
- **Collapsible panel** — toggle button on the right edge
- **Settings persistence** — auto-save/load to `settings.json`
- **Simulated data** — 3 live-updating pyqtgraph charts for demo
- **Fullscreen** — F10 to enter, Esc to exit
