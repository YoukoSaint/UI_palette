# -*- coding: utf-8 -*-
"""OptoSync UI — 展示用主窗口 + 4 色动态主题 + 模拟数据图表"""
import sys
import logging
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QApplication,
    QPlainTextEdit, QLabel, QStatusBar, QPushButton,
    QGroupBox, QFormLayout, QDoubleSpinBox, QSpinBox, QComboBox,
)
from PyQt5.QtCore import Qt, QObject, pyqtSignal
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtGui import QFont

from color_scheme import get_stylesheet, ColorScheme
from color_panel import ColorPanel
from plot_widgets import ChartPanel
from settings_manager import load_settings, save_settings


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OptoSync — Synchronized Acquisition System")
        self.resize(1440, 920)
        self.setMinimumSize(1100, 700)

        self._settings = load_settings()
        self._apply_loaded_colors()

        self._color_panel = ColorPanel()
        self._color_panel.color_changed.connect(self._on_color_changed)
        self._color_panel_visible = True

        self._setup_ui()
        self._apply_loaded_params()
        self._connect_param_signals()
        self._setup_status_bar()

        # Apply QSS LAST — after all widgets exist, nothing overrides it
        QApplication.instance().setStyleSheet(get_stylesheet())
        self._charts.refresh_colors()

        # 恢复面板折叠状态
        panels = self._settings.get("panels", {})
        if not panels.get("left", True):
            self._toggle_left_panel()
        if not panels.get("right", True):
            self._toggle_right_panel()
        if not panels.get("log", True):
            self._toggle_log_panel()

    def _apply_loaded_colors(self):
        for role, color in self._settings["colors"].items():
            ColorScheme.set_color(role, color)

    def _apply_loaded_params(self):
        p = self._settings["params"]
        self._si.setValue(p["integration_ms"])
        self._sa.setValue(p["averages"])
        self._sw.setValue(p["monitor_wl"])
        self._mc.setCurrentIndex(p["source_type"])
        self._mv.setValue(p["source_value"])
        self._mn.setValue(p["nplc"])
        self._sr.setValue(p["sample_rate"])

    def _connect_param_signals(self):
        """Connect parameter widgets to auto-save on every change.

        Connected AFTER ``_apply_loaded_params()`` so that loading saved
        values does not trigger a redundant first write.
        """
        self._si.valueChanged.connect(self._save)
        self._sa.valueChanged.connect(self._save)
        self._sw.valueChanged.connect(self._save)
        self._mc.currentIndexChanged.connect(self._save)
        self._mv.valueChanged.connect(self._save)
        self._mn.valueChanged.connect(self._save)
        self._sr.valueChanged.connect(self._save)

    def _save_chart_labels(self, x: int, y: int, w: int, h: int):
        sender = self.sender()
        if sender is self._charts.spectrum._label:
            key = "spectrum"
        elif sender is self._charts.trend._label:
            key = "trend"
        elif sender is self._charts.sourcemeter._label:
            key = "sourcemeter"
        else:
            return
        self._settings.setdefault("chart_labels", {})[key] = {"x": x, "y": y, "w": w, "h": h}
        self._save()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(4, 4, 4, 4)

        content = QHBoxLayout()
        content.setSpacing(0)
        main.addLayout(content, stretch=1)

        # ── 左: 参数面板 (可折叠) ──
        self._left_panel = self._build_param_panel()
        self._left_panel.setFixedWidth(300)
        content.addWidget(self._left_panel)

        self._left_toggle = self._make_edge_btn("◀", "Hide param panel")
        self._left_toggle.clicked.connect(self._toggle_left_panel)
        content.addWidget(self._left_toggle)

        # ── 中: 图表 + 日志 ──
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)

        self._charts = ChartPanel()
        rl.addWidget(self._charts, stretch=1)
        self._charts.apply_label_positions(self._settings.get("chart_labels", {}))

        # 标签拖动时自动保存位置
        self._charts.spectrum._label.pos_changed.connect(self._save_chart_labels)
        self._charts.trend._label.pos_changed.connect(self._save_chart_labels)
        self._charts.sourcemeter._label.pos_changed.connect(self._save_chart_labels)

        # ── 日志面板 (可折叠) ──
        log_bar = QHBoxLayout()
        log_bar.setContentsMargins(0, 0, 0, 0)
        log_bar.setSpacing(0)
        self._log_toggle = self._make_edge_btn("▼", "Hide log panel")
        self._log_toggle.clicked.connect(self._toggle_log_panel)
        log_bar.addWidget(self._log_toggle, alignment=Qt.AlignLeft)
        log_bar.addStretch()
        rl.addLayout(log_bar)

        self._log_panel = QPlainTextEdit()
        self._log_panel.setReadOnly(True)
        self._log_panel.setMaximumBlockCount(500)
        self._log_panel.setPlaceholderText("Log output — demo mode")
        self._log_panel.setFixedHeight(150)
        rl.addWidget(self._log_panel)

        content.addWidget(right, stretch=1)

        # ── 右: 配色面板折叠按钮 + 配色面板 ──
        self._right_toggle = self._make_edge_btn("▶", "Hide color panel")
        self._right_toggle.clicked.connect(self._toggle_right_panel)
        content.addWidget(self._right_toggle)
        content.addWidget(self._color_panel)

        # 恢复上次的折叠状态
        self._color_panel_visible = True
        self._left_panel_visible = True
        self._log_panel_visible = True

    def _make_edge_btn(self, text, tooltip):
        """生成瘦窄的折叠按钮"""
        b = QPushButton(text)
        b.setFixedSize(12, 30)
        b.setToolTip(tooltip)
        b.setCursor(Qt.PointingHandCursor)
        b.setStyleSheet("""
            QPushButton {background:transparent; border:none; font-size:7px; color:#606060; padding:0; margin:0;}
            QPushButton:hover {color:#c0c0c0;}
        """)
        return b

    def _build_param_panel(self) -> QWidget:
        w = QWidget()
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)

        g = QGroupBox("Parameter Settings")
        gl = QVBoxLayout(g)

        sg = QGroupBox("Spectrometer")
        sf = QFormLayout(sg)
        self._si = QDoubleSpinBox(); self._si.setRange(1, 60000); self._si.setValue(10); self._si.setSuffix(" ms")
        self._sa = QSpinBox(); self._sa.setRange(2, 100); self._sa.setValue(2)
        self._sw = QDoubleSpinBox(); self._sw.setRange(0, 10000); self._sw.setValue(632); self._sw.setSuffix(" nm")
        sf.addRow("Integration:", self._si)
        sf.addRow("Averages:", self._sa)
        sf.addRow("Monitor WL:", self._sw)
        gl.addWidget(sg)

        mg = QGroupBox("SourceMeter")
        mf = QFormLayout(mg)
        self._mc = QComboBox(); self._mc.addItems(["Voltage", "Current"])
        self._mv = QDoubleSpinBox(); self._mv.setRange(-100, 100); self._mv.setDecimals(4); self._mv.setValue(0.003)
        self._mn = QDoubleSpinBox(); self._mn.setRange(0.01, 10); self._mn.setValue(1.0)
        mf.addRow("Source:", self._mc)
        mf.addRow("Value:", self._mv)
        mf.addRow("NPLC:", self._mn)
        gl.addWidget(mg)

        ag = QGroupBox("Acquisition")
        af = QFormLayout(ag)
        self._sr = QDoubleSpinBox(); self._sr.setRange(0.01, 1000); self._sr.setValue(5); self._sr.setSuffix(" Hz")
        af.addRow("Sample Rate:", self._sr)
        gl.addWidget(ag)

        bl = QHBoxLayout()
        for t, o in [("Start", "btn_start"), ("Stop", "btn_stop"), ("Save", "btn_save")]:
            b = QPushButton(t); b.setObjectName(o)
            b.setStyleSheet("padding:6px 10px;")
            bl.addWidget(b)
        gl.addLayout(bl)
        gl.addStretch()
        l.addWidget(g)
        return w

    def _toggle_left_panel(self):
        if self._left_panel_visible:
            self._left_panel.hide()
            self._left_toggle.setText("▶")
            self._left_toggle.setToolTip("Show param panel")
        else:
            self._left_panel.show()
            self._left_toggle.setText("◀")
            self._left_toggle.setToolTip("Hide param panel")
        self._left_panel_visible = not self._left_panel_visible
        self._save()

    def _toggle_right_panel(self):
        if self._color_panel_visible:
            self._color_panel.hide()
            self._right_toggle.setText("◀")
            self._right_toggle.setToolTip("Show color panel")
        else:
            self._color_panel.show()
            self._right_toggle.setText("▶")
            self._right_toggle.setToolTip("Hide color panel")
        self._color_panel_visible = not self._color_panel_visible
        self._save()

    def _toggle_log_panel(self):
        if self._log_panel_visible:
            self._log_panel.hide()
            self._log_toggle.setText("▲")
            self._log_toggle.setToolTip("Show log panel")
        else:
            self._log_panel.show()
            self._log_toggle.setText("▼")
            self._log_toggle.setToolTip("Hide log panel")
        self._log_panel_visible = not self._log_panel_visible
        self._save()

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() == Qt.Key_F10:
            self.showFullScreen()
        elif event.key() == Qt.Key_Escape:
            self.showNormal()

    def _on_color_changed(self, role: str, color: str):
        QApplication.instance().setStyleSheet(get_stylesheet())
        self._charts.refresh_colors()
        self._save()

    def _save(self):
        self._settings["colors"] = {r: getattr(ColorScheme, r) for r in [
            "TEXT", "LIGHT", "DARK", "LINE", "BTN", "SPECTRUM", "TREND", "RESISTANCE", "GRID", "AXIS"]}
        self._settings["params"] = {
            "integration_ms": self._si.value(),
            "averages": self._sa.value(),
            "monitor_wl": self._sw.value(),
            "source_type": self._mc.currentIndex(),
            "source_value": self._mv.value(),
            "nplc": self._mn.value(),
            "sample_rate": self._sr.value(),
        }
        self._settings.setdefault("panels", {})["left"] = self._left_panel_visible
        self._settings.setdefault("panels", {})["right"] = self._color_panel_visible
        self._settings.setdefault("panels", {})["log"] = self._log_panel_visible
        save_settings(self._settings)

    def closeEvent(self, event):
        self._save()
        event.accept()

    def _setup_status_bar(self):
        sb = QStatusBar()
        self.setStatusBar(sb)
        sb.showMessage("Ready — Demo Mode | Simulated data")

    def _append_log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self._log_panel.appendPlainText(f"{ts} {msg}")
        sb = self._log_panel.verticalScrollBar()
        sb.setValue(sb.maximum())


if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec_())
