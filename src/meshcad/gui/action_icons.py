"""Small vector icons for canvas actions and dock-panel buttons."""

from PyQt5.QtCore import QPointF, QSize, Qt
from PyQt5.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap

ICON_SIZE = 24
BLUE = QColor("#2563EB")
DARK = QColor("#334155")
GREEN = QColor("#16A34A")
RED = QColor("#DC2626")
ORANGE = QColor("#F97316")


def action_icon(kind: str) -> QIcon:
    pixmap = QPixmap(ICON_SIZE, ICON_SIZE)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setPen(QPen(BLUE, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    painter.setBrush(Qt.NoBrush)

    if kind == "split":
        painter.drawLine(3, 12, 9, 12)
        painter.drawLine(15, 12, 21, 12)
        painter.setPen(QPen(ORANGE, 2.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(12, 5, 12, 19)
        painter.setBrush(BLUE)
        painter.drawEllipse(1, 10, 4, 4)
        painter.drawEllipse(19, 10, 4, 4)
    elif kind == "refresh":
        painter.drawArc(4, 4, 16, 16, 35 * 16, 290 * 16)
        painter.setPen(QPen(GREEN, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(GREEN)
        painter.drawPolygon(QPointF(16, 3), QPointF(22, 5), QPointF(17, 9))
    elif kind == "apply":
        painter.setPen(QPen(GREEN, 2.6, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        path = QPainterPath()
        path.moveTo(4, 12)
        path.lineTo(9, 17)
        path.lineTo(20, 6)
        painter.drawPath(path)
    elif kind in ("delete", "delete_block"):
        painter.setPen(QPen(RED, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(5, 7, 19, 7)
        painter.drawLine(8, 4, 16, 4)
        painter.drawLine(7, 8, 8, 20)
        painter.drawLine(17, 8, 16, 20)
        painter.drawLine(8, 20, 16, 20)
        painter.drawLine(10, 10, 10, 17)
        painter.drawLine(14, 10, 14, 17)
        if kind == "delete_block":
            painter.setPen(QPen(ORANGE, 2.0, Qt.SolidLine, Qt.RoundCap))
            painter.drawLine(17, 15, 22, 20)
            painter.drawLine(22, 15, 17, 20)
    elif kind == "split_click":
        painter.drawLine(2, 15, 9, 15)
        painter.drawLine(15, 15, 22, 15)
        painter.setPen(QPen(ORANGE, 2.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(12, 10, 12, 20)
        painter.setPen(QPen(DARK, 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.setBrush(Qt.white)
        painter.drawPolygon(
            QPointF(14, 2),
            QPointF(21, 10),
            QPointF(16, 9),
            QPointF(14, 14),
            QPointF(11, 12),
            QPointF(13, 8),
        )
    elif kind == "split_coordinates":
        painter.drawLine(2, 16, 10, 16)
        painter.drawLine(14, 16, 22, 16)
        painter.setPen(QPen(ORANGE, 2.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(12, 10, 12, 21)
        painter.setPen(QPen(BLUE, 1.8, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(5, 7, 5, 2)
        painter.drawLine(3, 4, 5, 2)
        painter.drawLine(7, 4, 5, 2)
        painter.drawLine(5, 7, 10, 7)
    elif kind == "new":
        painter.setPen(QPen(GREEN, 2.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawEllipse(3, 3, 18, 18)
        painter.drawLine(12, 7, 12, 17)
        painter.drawLine(7, 12, 17, 12)
    elif kind == "rename":
        painter.setPen(QPen(BLUE, 2.5, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(5, 18, 16, 7)
        painter.drawLine(4, 20, 8, 19)
        painter.setPen(QPen(ORANGE, 2.0, Qt.SolidLine, Qt.RoundCap))
        painter.drawLine(15, 6, 18, 9)
        painter.drawLine(18, 4, 20, 6)
    elif kind == "orthogonal":
        painter.setPen(QPen(BLUE, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(4, 19, 4, 5)
        painter.drawLine(4, 19, 19, 19)
        painter.setPen(QPen(GREEN, 2.4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawLine(8, 15, 8, 9)
        painter.drawLine(8, 9, 14, 9)
        painter.drawLine(14, 9, 14, 15)
        painter.drawLine(14, 15, 20, 15)
    elif kind in ("assign", "remove"):
        painter.setPen(QPen(BLUE, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawRoundedRect(2, 7, 10, 12, 2, 2)
        painter.setPen(
            QPen(
                GREEN if kind == "assign" else ORANGE, 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin
            )
        )
        if kind == "assign":
            painter.drawLine(10, 13, 21, 13)
            painter.drawLine(17, 9, 21, 13)
            painter.drawLine(17, 17, 21, 13)
        else:
            painter.drawLine(14, 13, 22, 13)
            painter.drawLine(14, 13, 18, 9)
            painter.drawLine(14, 13, 18, 17)

    painter.end()
    return QIcon(pixmap)


def configure_button(button, kind: str, tooltip: str) -> None:
    button.setIcon(action_icon(kind))
    button.setIconSize(QSize(18, 18))
    button.setToolTip(tooltip)
