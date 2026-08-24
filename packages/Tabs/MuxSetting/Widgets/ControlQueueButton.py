from PySide6 import QtCore
from PySide6.QtCore import QPointF, QRectF, QSize, Qt
from PySide6.QtGui import QIcon, QPaintEvent, QPainter, QPen, QPixmap, QPolygonF
from PySide6.QtWidgets import QPushButton

class ControlQueueButton(QPushButton):
    add_to_queue_clicked_signal = QtCore.Signal()
    start_multiplexing_clicked_signal = QtCore.Signal()
    pause_multiplexing_clicked_signal = QtCore.Signal()

    def __init__(self):
        super().__init__()
        self.setIconSize(QSize(18, 18))
        self.state = ""
        self.set_state_add_to_queue()
        self.clicked.connect(self.button_clicked)
        self.states = [" Add To Queue", " Start Muxing", " Pause", " Finishing Job", " Resume"]

    def set_state_add_to_queue(self):
        self.state = "ADD"
        self.setText(" Add To Queue")
        self.setIcon(self.make_icon("add"))
        self.setToolTip("")
        self.setDisabled(False)

    def set_state_start_multiplexing(self):
        self.state = "START"
        self.setText(" Start Muxing")
        self.setIcon(self.make_icon("play"))
        self.setToolTip("")
        self.setDisabled(False)

    def set_state_pause_multiplexing(self):
        self.state = "PAUSE"
        self.setText(" Pause")
        self.setIcon(self.make_icon("pause"))
        self.setToolTip("")
        self.setDisabled(False)

    def set_state_pausing_multiplexing(self):
        self.state = "PAUSING"
        self.setText(" Finishing Job")
        self.setIcon(self.make_icon("pause"))
        self.setToolTip("will pause muxing after current job finished")
        self.setDisabled(True)

    def set_state_resume_multiplexing(self):
        self.state = "RESUME"
        self.setText(" Resume")
        self.setIcon(self.make_icon("play"))
        self.setToolTip("")

    def paintEvent(self, event: QPaintEvent):
        width = 0
        for text in self.states:
            width = max(width, self.fontMetrics().boundingRect(text).width())
        width += 25
        self.setMinimumWidth(width)
        super().paintEvent(event)

    @staticmethod
    def make_icon(kind):
        pixmap = QPixmap(20, 20)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(Qt.GlobalColor.white, 1.8)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        if kind == "play":
            painter.setBrush(Qt.GlobalColor.white)
            painter.drawPolygon(QPolygonF([
                QPointF(6, 4), QPointF(6, 16), QPointF(15, 10)
            ]))
        elif kind == "pause":
            painter.setBrush(Qt.GlobalColor.white)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(QRectF(5, 4, 3.5, 12), 1, 1)
            painter.drawRoundedRect(QRectF(11.5, 4, 3.5, 12), 1, 1)
        else:
            painter.drawLine(QPointF(4, 6), QPointF(11, 6))
            painter.drawLine(QPointF(4, 10), QPointF(9, 10))
            painter.drawLine(QPointF(4, 14), QPointF(11, 14))
            painter.drawLine(QPointF(15, 9), QPointF(15, 15))
            painter.drawLine(QPointF(12, 12), QPointF(18, 12))
        painter.end()
        icon = QIcon(pixmap)
        return icon

    def button_clicked(self):
        if self.state == "ADD":
            self.add_to_queue_clicked_signal.emit()
        elif self.state == "START" or self.state == "RESUME":
            self.start_multiplexing_clicked_signal.emit()
        elif self.state == "PAUSE":
            self.pause_multiplexing_clicked_signal.emit()
