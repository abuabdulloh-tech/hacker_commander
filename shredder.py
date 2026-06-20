import os
import random
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QTextEdit, QPushButton
from translator import tr

class ShredderWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool)

    def __init__(self, file_paths):
        super().__init__()
        self.file_paths = file_paths

    def run(self):
        try:
            total_files = len(self.file_paths)
            for idx, path in enumerate(self.file_paths):
                if not os.path.exists(path):
                    self.log.emit(f"{tr('lbl_shredding_miss')}{path}")
                    continue

                if os.path.isdir(path):
                    self.log.emit(f"{tr('lbl_shredding_skip')}{path}")
                    continue

                size = os.path.getsize(path)
                self.log.emit(f"{tr('target_file')}{os.path.basename(path)} ({size} bytes)")

                with open(path, "ba+", buffering=0) as f:
                    for pass_num in range(1, 4):
                        self.log.emit(tr("lbl_shredding_pass").format(pass_num))
                        f.seek(0)
                        
                        if pass_num == 1:
                            pattern = b'\x00'
                        elif pass_num == 2:
                            pattern = b'\xff'
                        else:
                            pattern = bytes([random.randint(0, 255)])
                            
                        chunk = pattern * 4096
                        written = 0
                        while written < size:
                            to_write = min(4096, size - written)
                            f.write(chunk[:to_write])
                            written += to_write
                            
                        os.fsync(f.fileno())

                with open(path, "w") as f:
                    f.truncate(0)
                    
                os.remove(path)
                self.log.emit(f"{tr('lbl_shredding_del')}{os.path.basename(path)}")
                
                percent = int(((idx + 1) / total_files) * 100)
                self.progress.emit(percent)

            self.finished.emit(True)
        except Exception as e:
            self.log.emit(f"{tr('error_occurred')}{str(e)}")
            self.finished.emit(False)

class ShredderDialog(QDialog):
    def __init__(self, file_paths, parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(tr("shredder_title"))
        self.resize(500, 350)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0b0b;
                color: #ff3333;
                border: 2px solid #ff3333;
            }
            QLabel {
                color: #ff3333;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 11pt;
            }
            QProgressBar {
                border: 1px solid #ff3333;
                background-color: #111;
                color: #fff;
                text-align: center;
                font-family: 'Consolas', monospace;
            }
            QProgressBar::chunk {
                background-color: #ff3333;
            }
            QTextEdit {
                background-color: #050505;
                color: #ff5555;
                border: 1px solid #aa0000;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
            }
            QPushButton {
                background-color: #111;
                color: #ff3333;
                border: 1px solid #ff3333;
                padding: 6px 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #ff3333;
                color: #000;
            }
            QPushButton:disabled {
                border-color: #552222;
                color: #552222;
            }
        """)

        layout = QVBoxLayout(self)

        self.status_label = QLabel(tr("lbl_shredding_init"))
        layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        self.btn_cancel = QPushButton(tr("btn_cancel"))
        self.btn_cancel.clicked.connect(self.cancel_shredding)
        layout.addWidget(self.btn_cancel)

        self.worker = ShredderWorker(self.file_paths)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.log_area.append)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def cancel_shredding(self):
        if self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
            self.log_area.append(f"\n!!! {tr('op_cancelled')} !!!")
            self.status_label.setText(tr("op_cancelled"))
            self.btn_cancel.setText(tr("btn_close"))
            self.btn_cancel.clicked.disconnect()
            self.btn_cancel.clicked.connect(self.close)
        else:
            self.close()

    def on_finished(self, success):
        if success:
            self.status_label.setText(tr("lbl_shredding_done"))
            self.log_area.append(f"\n[STATUS] {tr('lbl_shredding_done')}")
        else:
            self.status_label.setText(tr("lbl_shredding_fail"))
        self.btn_cancel.setText(tr("btn_close"))
        self.btn_cancel.clicked.disconnect()
        self.btn_cancel.clicked.connect(self.close)
