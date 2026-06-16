# -*- coding: utf-8 -*-
"""实时光谱与趋势图表（pyqtgraph + 模拟数据）"""
import logging
import math
import random
import pyqtgraph as pg
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import QTimer, Qt, pyqtSignal
from color_scheme import ColorScheme, hex_to_rgba

logger = logging.getLogger(__name__)


def _apply_pg_theme():
    pg.setConfigOption("background", ColorScheme.DARK)
    pg.setConfigOption("foreground", ColorScheme.TEXT)
    pg.setConfigOption("antialias", False)
    pg.setConfigOptions(useOpenGL=False, leftButtonPan=False)


class DraggableLabel(QLabel):
    """可拖动+可缩放的标签，位置或大小变化结束后发出 pos_changed(x, y, w, h) 信号"""
    pos_changed = pyqtSignal(int, int, int, int)

    def __init__(self, text: str, color: str, parent=None):
        super().__init__(text, parent)
        self._dragging = False
        self._resizing = False
        self._offset = None
        self._color = color
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)
        self.setMinimumSize(40, 20)
        self._apply_style()

    def set_color(self, color: str):
        self._color = color
        self._apply_style()

    def _px_size(self, height: int) -> int:
        return max(8, int(height * 0.72))

    def _apply_style(self):
        """应用样式表（含当前高计算出的字号）"""
        h = self.height()
        px = self._px_size(h)
        self.setStyleSheet(
            "QLabel {"
            "background-color: rgba(%d, %d, %d, %s);"
            "color: %s;"
            "padding: 2px 6px;"
            "border: 1px solid %s;"
            "border-radius: 3px;"
            "font-size: %dpx;"
            "}"
            % (
                int(ColorScheme.LIGHT[1:3], 16),
                int(ColorScheme.LIGHT[3:5], 16),
                int(ColorScheme.LIGHT[5:7], 16),
                str(int(ColorScheme.LABEL_ALPHA, 16)),
                self._color,
                ColorScheme.LINE,
                px,
            )
        )
        logger.debug("label style: size=%dx%d, font=%dpx", self.width(), h, px)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            pos = event.pos()
            # 右下角 20x20 区域 = 缩放拖拽
            if pos.x() >= self.width() - 20 and pos.y() >= self.height() - 20:
                self._resizing = True
                self._offset = event.pos()
                event.accept()
                return
            # 其余区域 = 移动
            self._dragging = True
            self._offset = event.pos()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing and event.buttons() & Qt.LeftButton:
            w, h = max(40, event.pos().x()), max(20, event.pos().y())
            self.resize(w, h)
            self._apply_style()
            event.accept()
        elif self._dragging and event.buttons() & Qt.LeftButton:
            pos = self.mapToParent(event.pos() - self._offset)
            self.move(pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._resizing and event.button() == Qt.LeftButton:
            self._resizing = False
            self.pos_changed.emit(self.x(), self.y(), self.width(), self.height())
            event.accept()
        elif self._dragging and event.button() == Qt.LeftButton:
            self._dragging = False
            self.pos_changed.emit(self.x(), self.y(), self.width(), self.height())
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class SpectrumChart(pg.PlotWidget):
    """图 1 — 光谱曲线 + 同色半透明填充"""

    def __init__(self):
        super().__init__()
        self.setLabel("bottom", "Wavelength (nm)")
        self.setLabel("left", "Intensity")
        self.showGrid(x=True, y=True, alpha=0.4)
        self._curve = self.plot([], [], pen=pg.mkPen(ColorScheme.SPECTRUM, width=2.2))
        self._label = DraggableLabel("Spectrum", ColorScheme.SPECTRUM, self)
        self._apply_axis_font()
        self.enableAutoRange()

    def _apply_axis_font(self):
        sz = ColorScheme.AXIS_LABEL_SIZE
        font = pg.QtGui.QFont("", sz)
        for axis in ("left", "bottom"):
            ax = self.getAxis(axis)
            ax.tickFont = font
            ax.label.setFont(font)

    def set_label_pos(self, x: int, y: int):
        self._label.move(x, y)

    def _apply_fill(self):
        c = ColorScheme.SPECTRUM
        r, g, b, a = hex_to_rgba(c, 60)
        self._curve.setFillBrush(pg.mkBrush(r, g, b, a))
        self._curve.setFillLevel(0)

    def refresh_color(self):
        self._curve.setPen(pg.mkPen(ColorScheme.SPECTRUM, width=2.2))
        self._apply_fill()
        self._label.set_color(ColorScheme.SPECTRUM)
        self._label._apply_style()
        self._apply_axis_font()

    def update_spectrum(self, wl, spec):
        self._curve.setData(wl, spec)
        self._apply_fill()
        self.autoRange()


class TrendChart(pg.PlotWidget):
    """图 2 — 波段强度趋势（可链接 X 轴）"""

    MAX_POINTS = 1000

    def __init__(self):
        super().__init__()
        self.setLabel("bottom", "Time (s)")
        self.setLabel("left", "Intensity")
        self.showGrid(x=True, y=True, alpha=0.4)
        self._curve = self.plot(
            [], [], pen=pg.mkPen(ColorScheme.TREND, width=2),
            symbol="o", symbolSize=3,
            symbolBrush=ColorScheme.TREND, symbolPen=pg.mkPen(None),
        )
        self._label = DraggableLabel("Band Intensity", ColorScheme.TREND, self)
        self._apply_axis_font()
        self.enableAutoRange()

    def _apply_axis_font(self):
        sz = ColorScheme.AXIS_LABEL_SIZE
        font = pg.QtGui.QFont("", sz)
        for axis in ("left", "bottom"):
            ax = self.getAxis(axis)
            ax.tickFont = font
            ax.label.setFont(font)

    def set_label_pos(self, x: int, y: int):
        self._label.move(x, y)

    def refresh_color(self):
        c = ColorScheme.TREND
        self._curve.setPen(pg.mkPen(c, width=2))
        self._curve.setSymbolBrush(c)
        self._label.set_color(c)
        self._label._apply_style()
        self._apply_axis_font()

    def update_data(self, times, values):
        self._curve.setData(times, values)


class SourceMeterChart(pg.PlotWidget):
    """图 3 — 电阻（可链接 X 轴）"""

    MAX_POINTS = 1000

    def __init__(self):
        super().__init__()
        self.setLabel("bottom", "Time (s)")
        self.setLabel("left", "Resistance (Ω)")
        self.showGrid(x=True, y=True, alpha=0.4)
        self._r = self.plot(
            [], [], pen=pg.mkPen(ColorScheme.RESISTANCE, width=2.2),
            name="Resistance (Ω)", connect="finite",
        )
        self._label = DraggableLabel("SourceMeter", ColorScheme.RESISTANCE, self)
        self._apply_axis_font()
        self.enableAutoRange()

    def _apply_axis_font(self):
        sz = ColorScheme.AXIS_LABEL_SIZE
        font = pg.QtGui.QFont("", sz)
        for axis in ("left", "bottom"):
            ax = self.getAxis(axis)
            ax.tickFont = font
            ax.label.setFont(font)

    def set_label_pos(self, x: int, y: int):
        self._label.move(x, y)

    def refresh_color(self):
        self._r.setPen(pg.mkPen(ColorScheme.RESISTANCE, width=2.2))
        self._label.set_color(ColorScheme.RESISTANCE)
        self._label._apply_style()
        self._apply_axis_font()

    def update_data(self, times, r):
        self._r.setData(times, r)


class DataSimulator:
    @staticmethod
    def spectrum(wavelengths=None):
        if wavelengths is None:
            wavelengths = [300 + i * 0.5 for i in range(1400)]
        spec = []
        for wl in wavelengths:
            val = (800 * math.exp(-0.5 * ((wl - 450) / 30) ** 2) +
                   500 * math.exp(-0.5 * ((wl - 550) / 25) ** 2) +
                   300 * math.exp(-0.5 * ((wl - 680) / 20) ** 2) +
                   random.gauss(0, 15))
            spec.append(max(0, val))
        return wavelengths, spec

    @staticmethod
    def trend(n_points):
        times = [i * 0.1 for i in range(n_points)]
        values = []
        for t in times:
            v = 500 + 200 * math.sin(t * 0.5) * math.exp(-t * 0.01)
            values.append(v + random.gauss(0, 10))
        return times, values

    @staticmethod
    def sourcemeter(n_points):
        times = [i * 0.05 for i in range(n_points)]
        r = []
        for t in times:
            vt = 5.0 + 0.1 * math.sin(t * 2)
            ct = 0.003 + 0.0002 * math.cos(t * 3)
            r.append(vt / ct if ct != 0 else float("nan"))
        return times, r


class ChartPanel(QWidget):
    """包含三个图表的容器，垂直堆叠。Trend 和 SourceMeter 共 X 轴"""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = pg.QtWidgets.QSplitter(pg.QtCore.Qt.Vertical)
        self.spectrum = SpectrumChart()
        self.trend = TrendChart()
        self.sourcemeter = SourceMeterChart()
        splitter.addWidget(self.spectrum)
        splitter.addWidget(self.trend)
        splitter.addWidget(self.sourcemeter)
        layout.addWidget(splitter)

        # Trend 和 SourceMeter 共 X 轴：Trend 底部轴完全隐藏
        self.trend.setXLink(self.sourcemeter)
        self.trend.hideAxis("bottom")

        # 所有 Y 轴标签对齐：延迟到首次绘制后统一宽度
        self._align_y_axes_once = True

        self._data_counter = 0
        self._wl_cache = None
        self._times, self._trend_vals = [], []
        self._t2, self._r = [], []

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(500)

    def showEvent(self, event):
        super().showEvent(event)
        if self._align_y_axes_once:
            self._align_y_axes_once = False
            QTimer.singleShot(0, self._align_y_axes)

    def _align_y_axes(self):
        """统一所有图表左 Y 轴宽度，使 plot 区域对齐"""
        charts = [self.spectrum, self.trend, self.sourcemeter]
        max_width = 0
        for ch in charts:
            w = ch.getAxis("left").width()
            if w > max_width:
                max_width = w
        logger.debug("align y-axes: max_width=%d", max_width)
        for ch in charts:
            ch.getAxis("left").setWidth(max_width)

    def apply_label_positions(self, positions: dict):
        """从保存的设置恢复标签位置和大小"""
        if "spectrum" in positions:
            p = positions["spectrum"]
            self.spectrum._label.move(p["x"], p["y"])
            if "w" in p and "h" in p:
                self.spectrum._label.resize(p["w"], p["h"])
                self.spectrum._label._apply_style()
        if "trend" in positions:
            p = positions["trend"]
            self.trend._label.move(p["x"], p["y"])
            if "w" in p and "h" in p:
                self.trend._label.resize(p["w"], p["h"])
                self.trend._label._apply_style()
        if "sourcemeter" in positions:
            p = positions["sourcemeter"]
            self.sourcemeter._label.move(p["x"], p["y"])
            if "w" in p and "h" in p:
                self.sourcemeter._label.resize(p["w"], p["h"])
                self.sourcemeter._label._apply_style()

    def _tick(self):
        self._data_counter += 1
        start_t = self._data_counter * 0.5

        # 光谱 — 首帧立即显示，之后每 5 帧 (~2.5s) 更新
        if self._data_counter <= 1 or self._data_counter % 5 == 0:
            wl, spec = DataSimulator.spectrum(self._wl_cache)
            if self._wl_cache is None:
                self._wl_cache = wl
            self.spectrum.update_spectrum(self._wl_cache, spec)

        # 趋势 — 加 2 点
        t, v = DataSimulator.trend(2)
        for i in range(2):
            self._times.append(start_t + t[i])
            self._trend_vals.append(v[i])
        if len(self._times) > self.trend.MAX_POINTS:
            cut = len(self._times) - self.trend.MAX_POINTS
            self._times = self._times[cut:]
            self._trend_vals = self._trend_vals[cut:]
        self.trend.update_data(self._times, self._trend_vals)
        if self._times:
            self.sourcemeter.setXRange(max(0, self._times[-1] - 60), self._times[-1] + 5)

        # 源表 — 加 2 点
        t2, rt = DataSimulator.sourcemeter(2)
        for i in range(2):
            self._t2.append(start_t + t2[i])
            self._r.append(rt[i])
        if len(self._t2) > self.sourcemeter.MAX_POINTS:
            cut = len(self._t2) - self.sourcemeter.MAX_POINTS
            self._t2 = self._t2[cut:]
            self._r = self._r[cut:]
        self.sourcemeter.update_data(self._t2, self._r)

    def refresh_colors(self):
        _apply_pg_theme()
        for ch in [self.spectrum, self.trend, self.sourcemeter]:
            ch.setBackground(ColorScheme.DARK)
        self.spectrum.refresh_color()
        self.trend.refresh_color()
        self.sourcemeter.refresh_color()
