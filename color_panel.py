# -*- coding: utf-8 -*-
"""紧凑型配色面板 — 基础 4 色 + 图表 5 色，带折叠按钮"""
import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QLabel, QFrame, QColorDialog, QScrollArea,
)
from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtGui import QFont, QColor

from color_scheme import ColorScheme

HEX_PATTERN = re.compile(r"^#[0-9A-Fa-f]{6}$")


class ColorPickerRow(QWidget):
    """单行：色块 + 标签 + HEX + 调色盘"""
    color_changed = pyqtSignal(str)

    def __init__(self, role: str, label: str, color: str, show_label=True):
        super().__init__()
        self.role = role
        self.color = color
        layout = QHBoxLayout(self)
        layout.setSpacing(3)
        layout.setContentsMargins(0, 0, 0, 0)

        swatch = QFrame()
        swatch.setFixedSize(10, 10)
        swatch.setStyleSheet(f"background:{color}; border:1px solid #555; border-radius:1px;")
        self._swatch = swatch

        lbl = QLabel(label if show_label else "")
        lbl.setFixedWidth(28 if show_label else 0)
        lbl.setStyleSheet("font-size:10px;")

        hex_input = QLineEdit()
        hex_input.setText(color)
        hex_input.setFixedWidth(64)
        hex_input.setFont(QFont("Consolas", 7))
        hex_input.setAlignment(Qt.AlignCenter)
        hex_input.setStyleSheet("padding:1px; font-size:10px;")
        hex_input.editingFinished.connect(self._on_hex)
        self._hex = hex_input

        btn = QPushButton("🎨")
        btn.setFixedWidth(18)
        btn.setStyleSheet("padding:0; font-size:8px;")
        btn.clicked.connect(self._on_picker)

        layout.addWidget(swatch)
        layout.addWidget(lbl)
        layout.addWidget(hex_input)
        layout.addWidget(btn)
        layout.addStretch()

    def _on_picker(self):
        c = QColorDialog.getColor(QColor(self.color), self)
        if c.isValid():
            self.set_color(c.name())

    def _on_hex(self):
        t = self._hex.text().strip()
        if HEX_PATTERN.match(t):
            self.set_color(t)
        else:
            self._hex.setStyleSheet("padding:1px; font-size:10px; border:1px solid red;")
            self._hex.setText(self.color)

    def set_color(self, c: str):
        self.color = c.upper()
        self._swatch.setStyleSheet(f"background:{self.color}; border:1px solid #555; border-radius:1px;")
        self._hex.setText(self.color)
        self._hex.setStyleSheet("padding:1px; font-size:10px;")
        self.color_changed.emit(self.color)


class ColorPanel(QWidget):
    """配色面板 + 图表颜色"""
    color_changed = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.setFixedWidth(170)
        self._pickers = {}
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(3)
        layout.setContentsMargins(4, 4, 4, 4)

        # Base 4 colors
        base = QLabel("Base Colors")
        base.setStyleSheet("font-weight:bold; font-size:10px;")
        layout.addWidget(base)

        for r, l in [("TEXT","Text"), ("LIGHT","Light"), ("DARK","Dark"), ("LINE","Line")]:
            row = ColorPickerRow(r, l, getattr(ColorScheme, r))
            row.color_changed.connect(lambda c, r=r: self._on_change(r, c))
            self._pickers[r] = row
            layout.addWidget(row)

        # Chart curve colors
        layout.addSpacing(4)
        chart_lbl = QLabel("Chart Curves")
        chart_lbl.setStyleSheet("font-weight:bold; font-size:10px;")
        layout.addWidget(chart_lbl)

        for r, l in [("SPECTRUM","Spectrum"), ("TREND","Trend"), ("RESISTANCE","R")]:
            row = ColorPickerRow(r, l, getattr(ColorScheme, r))
            row.color_changed.connect(lambda c, r=r: self._on_change(r, c))
            self._pickers[r] = row
            layout.addWidget(row)

        layout.addStretch()
        reset = QPushButton("↺ Reset")
        reset.setStyleSheet("padding:2px; font-size:10px;")
        reset.clicked.connect(self._reset)
        layout.addWidget(reset)

    def _on_change(self, role, color):
        ColorScheme.set_color(role, color)
        self.color_changed.emit(role, color)

    def _reset(self):
        defaults = {
            "TEXT":"#c0caf5","LIGHT":"#1e1f2e","DARK":"#1a1b26","LINE":"#3b3d56",
            "SPECTRUM":"#0db9d7","TREND":"#bb9af7","VOLTAGE":"#7aa2f7",
            "CURRENT":"#9ece6a","RESISTANCE":"#f7768e",
        }
        for r, c in defaults.items():
            ColorScheme.set_color(r, c)
            self._pickers[r].set_color(c)
            self.color_changed.emit(r, c)
