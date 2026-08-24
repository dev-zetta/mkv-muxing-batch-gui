from PySide6.QtCore import QPointF, QRectF, QSize, Signal, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QPushButton
from packages.Startup.Options import Options, save_options
from packages.Startup.MainApplication import apply_dark_mode, apply_light_mode


class ThemeButton(QPushButton):
    dark_mode_updated_signal = Signal()

    def __init__(self):
        super().__init__()
        self.setIconSize(QSize(18, 18))
        self.setText("")
        self.clicked.connect(self.theme_button_clicked)
        if Options.Dark_Mode:
            self.set_tool_tip_when_dark()
        else:
            self.set_tool_tip_when_light()

    def theme_button_clicked(self):
        if Options.Dark_Mode:
            apply_light_mode()
            self.set_tool_tip_when_light()
        else:
            apply_dark_mode()
            self.set_tool_tip_when_dark()
        Options.Dark_Mode = not Options.Dark_Mode
        save_options()
        self.dark_mode_updated_signal.emit()

    def set_tool_tip_when_dark(self):
        self.setIcon(self.make_theme_icon("sun", "#d9dde5"))
        self.setToolTip("Switch To Light Mode")
        self.setToolTipDuration(1500)

    def set_tool_tip_when_light(self):
        self.setIcon(self.make_theme_icon("moon", "#3e4652"))
        self.setToolTip("Switch To Dark Mode")
        self.setToolTipDuration(1500)

    @staticmethod
    def make_theme_icon(kind, color):
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor(color), 1.5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        if kind == "sun":
            painter.drawEllipse(QRectF(6, 6, 8, 8))
            for start, end in (
                ((10, 2), (10, 4)), ((10, 16), (10, 18)),
                ((2, 10), (4, 10)), ((16, 10), (18, 10)),
                ((4, 4), (5.5, 5.5)), ((14.5, 14.5), (16, 16)),
                ((16, 4), (14.5, 5.5)), ((5.5, 14.5), (4, 16)),
            ):
                painter.drawLine(QPointF(*start), QPointF(*end))
        else:
            painter.drawArc(QRectF(4, 3, 12, 14), 65 * 16, 250 * 16)
            painter.drawArc(QRectF(8, 2, 9, 13), 110 * 16, 180 * 16)
        painter.end()
        return QIcon(pixmap)
