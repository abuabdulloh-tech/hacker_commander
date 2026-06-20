import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QPainter, QColor
from PyQt6.QtCore import Qt

def main():
    app = QApplication(sys.argv)
    pixmap = QPixmap(256, 256)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setBrush(QColor(10, 10, 10))
    painter.setPen(QColor(0, 255, 0))
    painter.drawRect(8, 8, 240, 240)
    font = painter.font()
    font.setPointSize(80)
    font.setFamily("Consolas")
    font.setBold(True)
    painter.setFont(font)
    painter.drawText(65, 160, "CC")
    painter.end()
    pixmap.save("icon.ico", "ICO")

if __name__ == "__main__":
    main()
