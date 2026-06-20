import os
import shutil
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QTextEdit, QPushButton
from translator import tr

class FileOperationWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, sources, destination, operation="copy"):
        super().__init__()
        self.sources = sources
        self.destination = destination
        self.operation = operation
        self.is_cancelled = False

    def run(self):
        try:
            total_size = 0
            for src in self.sources:
                if os.path.isdir(src):
                    for root, _, files in os.walk(src):
                        for file in files:
                            p = os.path.join(root, file)
                            if os.path.exists(p):
                                total_size += os.path.getsize(p)
                elif os.path.isfile(src):
                    total_size += os.path.getsize(src)

            if total_size == 0:
                total_size = 1

            copied_size = 0
            for src in self.sources:
                if self.is_cancelled:
                    break

                name = os.path.basename(src)
                dest_path = os.path.join(self.destination, name)

                if os.path.isdir(src):
                    copied_size = self.copy_dir_recursive(src, dest_path, copied_size, total_size)
                else:
                    copied_size = self.copy_file_chunked(src, dest_path, copied_size, total_size)

            if self.is_cancelled:
                self.finished.emit(False, tr("op_cancelled"))
                return

            if self.operation == "move":
                for src in self.sources:
                    if os.path.isdir(src):
                        shutil.rmtree(src)
                    else:
                        os.remove(src)
                self.log.emit("Sources removed successfully.")

            self.finished.emit(True, tr("copied_status") if self.operation == "copy" else tr("moved_status"))
        except Exception as e:
            self.finished.emit(False, str(e))

    def copy_file_chunked(self, src, dest, copied_size, total_size):
        if self.is_cancelled:
            return copied_size

        self.log.emit(f"Processing: {os.path.basename(src)}")
        
        try:
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(src, 'rb') as fsrc:
                with open(dest, 'wb') as fdst:
                    while True:
                        if self.is_cancelled:
                            break
                        buf = fsrc.read(65536)
                        if not buf:
                            break
                        fdst.write(buf)
                        copied_size += len(buf)
                        percent = int((copied_size / total_size) * 100)
                        self.progress.emit(percent)
        except Exception as e:
            self.log.emit(f"Error: {str(e)}")
            
        return copied_size

    def copy_dir_recursive(self, src, dest, copied_size, total_size):
        if self.is_cancelled:
            return copied_size

        os.makedirs(dest, exist_ok=True)
        for item in os.listdir(src):
            if self.is_cancelled:
                break
            src_item = os.path.join(src, item)
            dest_item = os.path.join(dest, item)
            if os.path.isdir(src_item):
                copied_size = self.copy_dir_recursive(src_item, dest_item, copied_size, total_size)
            else:
                copied_size = self.copy_file_chunked(src_item, dest_item, copied_size, total_size)
        return copied_size

class FileOperationDialog(QDialog):
    def __init__(self, sources, destination, operation="copy", parent=None):
        super().__init__(parent)
        self.sources = sources
        self.destination = destination
        self.operation = operation
        self.init_ui()

    def init_ui(self):
        title = "CYBER COPY PROTOCOL" if self.operation == "copy" else "CYBER RELOCATION PROTOCOL"
        self.setWindowTitle(title)
        self.resize(500, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: #0c0c0c;
                color: #00ffff;
                border: 2px solid #00ffff;
            }
            QLabel {
                color: #00ffff;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
            QProgressBar {
                border: 1px solid #00ffff;
                background-color: #111;
                color: #fff;
                text-align: center;
                font-family: 'Consolas', monospace;
            }
            QProgressBar::chunk {
                background-color: #00ffff;
            }
            QTextEdit {
                background-color: #050505;
                color: #00ffff;
                border: 1px solid #00aaaa;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 9pt;
            }
            QPushButton {
                background-color: #111;
                color: #00ffff;
                border: 1px solid #00ffff;
                padding: 6px 12px;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
            QPushButton:hover {
                background-color: #00ffff;
                color: #000;
            }
        """)

        layout = QVBoxLayout(self)

        status_text = tr("lbl_status_copy") if self.operation == "copy" else tr("lbl_status_move")
        self.lbl_status = QLabel(status_text)
        layout.addWidget(self.lbl_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        self.btn_action = QPushButton(tr("btn_abort"))
        self.btn_action.clicked.connect(self.cancel_op)
        layout.addWidget(self.btn_action)

        self.worker = FileOperationWorker(self.sources, self.destination, self.operation)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.log_area.append)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def cancel_op(self):
        if self.worker.isRunning():
            self.worker.is_cancelled = True
            self.log_area.append(f"\n!!! {tr('op_cancelled')} !!!")
            self.btn_action.setText(tr("btn_close"))
            self.btn_action.clicked.disconnect()
            self.btn_action.clicked.connect(self.close)
        else:
            self.close()

    def on_finished(self, success, message):
        if success:
            self.lbl_status.setText("TRANSFER COMPLETED")
            self.log_area.append(f"\n[SUCCESS] {message}")
        else:
            self.lbl_status.setText("TRANSFER FAILED")
            self.log_area.append(f"\n[ERROR] {message}")
        
        self.btn_action.setText(tr("btn_close"))
        if success or not self.worker.isRunning():
            try:
                self.btn_action.clicked.disconnect()
            except Exception:
                pass
            self.btn_action.clicked.connect(self.close)
