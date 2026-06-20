import os
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QPlainTextEdit, QPushButton, QHBoxLayout, QLabel
from PyQt6.QtGui import QFont
from translator import tr

class HexViewer(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.chunk_size = 1024
        self.current_offset = 0
        self.init_ui()
        self.load_file_data()

    def init_ui(self):
        self.setWindowTitle(f"{tr('hex_viewer_title')} - {os.path.basename(self.file_path)}")
        self.resize(750, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #0d0d0d;
                color: #00ff00;
                border: 2px solid #00ff00;
            }
            QLabel {
                color: #00ffff;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11pt;
            }
            QPlainTextEdit {
                background-color: #050505;
                color: #00ff00;
                border: 1px solid #00bb00;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00ff00;
                padding: 6px 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #00ff00;
                color: #000;
            }
            QPushButton:pressed {
                background-color: #00aa00;
            }
        """)

        layout = QVBoxLayout(self)
        
        self.info_label = QLabel(f"{tr('target_file')}{self.file_path}")
        layout.addWidget(self.info_label)

        self.text_area = QPlainTextEdit()
        self.text_area.setReadOnly(True)
        layout.addWidget(self.text_area)

        nav_layout = QHBoxLayout()
        self.btn_prev = QPushButton(tr("prev_page"))
        self.btn_prev.clicked.connect(self.prev_page)
        nav_layout.addWidget(self.btn_prev)

        self.offset_label = QLabel(f"{tr('offset')}0x00000000")
        nav_layout.addWidget(self.offset_label)

        self.btn_next = QPushButton(tr("next_page"))
        self.btn_next.clicked.connect(self.next_page)
        nav_layout.addWidget(self.btn_next)

        layout.addLayout(nav_layout)

        self.btn_close = QPushButton(tr("btn_close"))
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)

    def load_file_data(self):
        if not os.path.exists(self.file_path):
            self.text_area.setPlainText(tr("lbl_shredding_miss"))
            return

        try:
            file_size = os.path.getsize(self.file_path)
            with open(self.file_path, "rb") as f:
                f.seek(self.current_offset)
                data = f.read(self.chunk_size)

            if not data:
                self.text_area.setPlainText("--- END OF FILE DATA ---")
                return

            lines = []
            for i in range(0, len(data), 16):
                chunk = data[i:i+16]
                offset_str = f"{(self.current_offset + i):08X}"
                
                hex_parts = []
                for b in chunk:
                    hex_parts.append(f"{b:02X}")
                
                hex_str1 = " ".join(hex_parts[:8])
                hex_str2 = " ".join(hex_parts[8:])
                hex_str = f"{hex_str1:<23}  {hex_str2:<23}"

                ascii_parts = []
                for b in chunk:
                    if 32 <= b <= 126:
                        ascii_parts.append(chr(b))
                    else:
                        ascii_parts.append(".")
                ascii_str = "".join(ascii_parts)

                lines.append(f"{offset_str}  {hex_str}  |{ascii_str}|")

            self.text_area.setPlainText("\n".join(lines))
            self.offset_label.setText(f"{tr('offset')}0x{self.current_offset:08X} / 0x{file_size:08X}")
            
            self.btn_prev.setEnabled(self.current_offset > 0)
            self.btn_next.setEnabled(self.current_offset + self.chunk_size < file_size)

        except Exception as e:
            self.text_area.setPlainText(f"{tr('error_occurred')}{str(e)}")

    def next_page(self):
        self.current_offset += self.chunk_size
        self.load_file_data()

    def prev_page(self):
        self.current_offset = max(0, self.current_offset - self.chunk_size)
        self.load_file_data()
