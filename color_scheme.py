# -*- coding: utf-8 -*-
"""
4 色动态配色方案 + QSS 生成 + 图表颜色
基础 4 色: TEXT(文字), LIGHT(浅色), DARK(深色), LINE(线条)
图表 3 色: 全部可自定义
"""
import re

HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")

ROLES_BASE = ["TEXT", "LIGHT", "DARK", "LINE"]
ROLES_CHART = ["SPECTRUM", "TREND", "RESISTANCE"]


class ColorScheme:
    """动态配色方案"""

    # 基础 4 色 — 驱动整套 QSS
    TEXT = "#c0caf5"     # 文字色
    LIGHT = "#1e1f2e"    # 浅色区 (面板/卡片)
    DARK = "#1a1b26"     # 深色区 (主背景)
    LINE = "#3b3d56"     # 线条/边框

    # 图表曲线色 — 每条曲线一个用户可管理色
    SPECTRUM = "#0db9d7"   # 光谱曲线
    TREND = "#bb9af7"      # 波段趋势
    RESISTANCE = "#f7768e" # 电阻

    # 图表内标签字号（可调）
    LABEL_SIZE = 14        # 图表内部标签字体大小
    LABEL_ALPHA = "ff"     # 标签背景透明度（00=完全透明, ff=完全不透明）
    AXIS_LABEL_SIZE = 13   # 图表坐标轴标签字号

    # 固定辅助色 (不暴露给用户)
    GRID = "#2c2d3f"
    AXIS = "#565f89"

    @classmethod
    def set_color(cls, role: str, hex_color: str) -> bool:
        if not HEX_PATTERN.match(hex_color):
            return False
        if hasattr(cls, role.upper()):
            setattr(cls, role.upper(), hex_color.upper())
            return True
        return False


def _adjust(hex_color: str, amount: int) -> str:
    hex_color = hex_color.lstrip('#')
    r = max(0, min(255, int(hex_color[0:2], 16) + amount))
    g = max(0, min(255, int(hex_color[2:4], 16) + amount))
    b = max(0, min(255, int(hex_color[4:6], 16) + amount))
    return f"#{r:02x}{g:02x}{b:02x}"


def hex_to_rgba(hex_color: str, alpha: int) -> tuple:
    """HEX → (r,g,b,a)"""
    hex_color = hex_color.lstrip('#')
    return (
        int(hex_color[0:2], 16),
        int(hex_color[2:4], 16),
        int(hex_color[4:6], 16),
        alpha,
    )


def get_stylesheet() -> str:
    text = ColorScheme.TEXT
    light = ColorScheme.LIGHT
    dark = ColorScheme.DARK
    line = ColorScheme.LINE

    text2 = _adjust(text, -30)
    text3 = _adjust(text, -50)
    dark2 = _adjust(dark, -6)
    light2 = _adjust(light, 10)
    accent = _adjust(light, 30)

    return f"""
QWidget {{
    background-color: {dark};
    color: {text};
    font-family: "Segoe UI", "Microsoft YaHei", sans-serif;
    font-size: 13px;
}}
QMainWindow {{ background-color: {dark2}; }}
QLabel {{ background-color: transparent; color: {text2}; border: none; }}

QGroupBox {{
    background-color: {light};
    border: 1px solid {line};
    border-radius: 8px;
    margin-top: 16px;
    padding: 16px 12px 12px 12px;
    font-weight: bold;
    font-size: 13px;
    color: {accent};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 14px; top: 2px;
    padding: 2px 8px;
    background-color: {light};
    border-radius: 4px;
    color: {accent};
}}

QPushButton {{
    background-color: {line};
    color: {text};
    border: 1px solid {line};
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: bold;
    font-size: 13px;
}}
QPushButton:hover {{ background-color: {light2}; border-color: {accent}; }}
QPushButton:pressed {{ background-color: {dark}; }}
QPushButton:disabled {{ background-color: {light}; color: {text3}; }}

QPushButton#btn_start {{ background-color:#1a6b3c; color:#9ece6a; border-color:#2f9e54; }}
QPushButton#btn_start:hover {{ background-color:#228b4a; }}
QPushButton#btn_stop {{ background-color:#6b1a1a; color:#f28b82; border-color:#9e2f2f; }}
QPushButton#btn_stop:hover {{ background-color:#8b2222; }}
QPushButton#btn_save {{ background-color:#1a4a6b; color:#7dcfff; border-color:#2f6f9e; }}
QPushButton#btn_save:hover {{ background-color:#225f8b; }}

QLineEdit {{
    background-color: {dark2};
    color: {text};
    border: 1px solid {line};
    border-radius: 5px;
    padding: 5px 8px;
}}
QLineEdit:focus {{ border-color: {accent}; }}

QSpinBox, QDoubleSpinBox {{
    background-color: {dark2};
    color: {text};
    border: 1px solid {line};
    border-radius: 5px;
    padding: 4px 6px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {accent}; }}

QComboBox {{
    background-color: {dark2};
    color: {text};
    border: 1px solid {line};
    border-radius: 5px;
    padding: 4px 8px;
}}
QComboBox:focus {{ border-color: {accent}; }}
QComboBox QAbstractItemView {{
    background-color: {light};
    color: {text};
    border: 1px solid {line};
    border-radius: 4px;
    selection-background-color: {accent};
    outline: none;
}}

QSplitter::handle {{ background-color: {line}; margin:1px; }}
QSplitter::handle:horizontal {{ width:3px; }}
QSplitter::handle:vertical {{ height:3px; }}
QSplitter::handle:hover {{ background-color: {accent}; }}

QPlainTextEdit {{
    background-color: {dark2};
    color: {text2};
    border: 1px solid {line};
    border-radius: 6px;
    padding: 8px;
    font-family: "Consolas", "Courier New", monospace;
    font-size: 12px;
}}

QStatusBar {{
    background-color: {dark2};
    color: {text2};
    border-top: 1px solid {line};
    padding: 2px 8px;
    font-size: 12px;
}}

QScrollBar:vertical {{ background-color:{dark2}; width:10px; border-radius:5px; }}
QScrollBar::handle:vertical {{ background-color:{line}; border-radius:5px; min-height:30px; }}
QScrollBar::handle:vertical:hover {{ background-color:{accent}; }}
QScrollBar:horizontal {{ background-color:{dark2}; height:10px; border-radius:5px; }}
QScrollBar::handle:horizontal {{ background-color:{line}; border-radius:5px; min-width:30px; }}
QScrollBar::handle:horizontal:hover {{ background-color:{accent}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height:0; border:none; }}
"""
