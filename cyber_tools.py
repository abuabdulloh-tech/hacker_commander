import os
import zipfile
import fnmatch
import time
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QCheckBox, QProgressBar, QMessageBox,
    QTextEdit, QGridLayout
)
from translator import tr

class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(tr("f1_help_title"))
        self.resize(600, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #060606;
                color: #00ff00;
                border: 2px solid #00ff00;
            }
            QTextEdit {
                background-color: #030303;
                color: #00ff00;
                border: 1px solid #00bb00;
                font-family: 'Consolas', monospace;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00aa00;
                font-family: 'Consolas', monospace;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #00aa00;
                color: #000;
            }
        """)

        layout = QVBoxLayout(self)

        self.text_area = QTextEdit()
        self.text_area.setReadOnly(True)
        
        help_content = (
            f"{tr('cs_fkeys')}\n"
            "  F1          - Open Help Guide.\n"
            "  F2          - Reread / Refresh active folder.\n"
            "  F3          - Quick View file in Lister Hex mode.\n"
            "  F4          - Edit file in built-in Text Editor.\n"
            "  F5          - Copy selected file/folder to opposite pane.\n"
            "  F6          - Move selected file/folder to opposite pane.\n"
            "  F7          - Create new directory (Mkdir).\n"
            "  F8 / Del    - Move selected files/folders to Recycle Bin.\n\n"
            f"{tr('cs_alt')}\n"
            "  Alt + F1    - Change Left Pane drive mapping.\n"
            "  Alt + F2    - Change Right Pane drive mapping.\n"
            "  Alt + F4    - Exit application immediately.\n"
            "  Alt + F5    - Pack selected items into a ZIP archive.\n"
            "  Alt + F6    - Unpack selected ZIP archives.\n"
            "  Alt + F7    - Search directories for files or text.\n"
            "  Alt + Enter - View metadata properties of selected item.\n"
            "  Alt + Left  - Navigate to previous folder in history.\n"
            "  Alt + Right - Navigate to next folder in history.\n"
            "  Alt + Down  - Open folder history dropdown log.\n\n"
            f"{tr('cs_ctrl')}\n"
            "  Ctrl + A    - Highlight all items in active pane.\n"
            "  Ctrl + B    - Toggle Flat List View (recursive files list).\n"
            "  Ctrl + D    - Bookmarks Sector Hotlist menu.\n"
            "  Ctrl + M    - Multi-Rename Sequencer tool.\n"
            "  Ctrl + Q    - Toggle Quick View Live Preview in opposite pane.\n"
            "  Ctrl + T    - Open new tab in active pane.\n"
            "  Ctrl + U    - Swap Left and Right active directory paths.\n"
            "  Ctrl + PgUp - Go up to parent directory.\n"
            "  Ctrl + F3   - Sort items by Name.\n"
            "  Ctrl + F4   - Sort items by Extension/Type.\n"
            "  Ctrl + F5   - Sort items by Date Modified.\n"
            "  Ctrl + F6   - Sort items by Size.\n\n"
            f"{tr('cs_shift')}\n"
            "  Shift + F4  - Generate new text file and edit.\n"
            "  Shift + F5  - Copy file into current directory under new name.\n"
            "  Shift + F6  - Trigger inline renaming on selected item.\n"
            "  Shift + Del - Shred and delete permanently (bypass Recycle Bin).\n"
        )
        self.text_area.setPlainText(help_content)
        layout.addWidget(self.text_area)

        self.btn_close = QPushButton(tr("btn_close"))
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)

class PropertiesDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(tr("prop_title"))
        self.resize(500, 250)
        self.setStyleSheet("""
            QDialog {
                background-color: #060606;
                color: #00ffff;
                border: 2px solid #00ffff;
            }
            QLabel {
                color: #00ffff;
                font-family: 'Consolas', monospace;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #111;
                color: #00ffff;
                border: 1px solid #00aaaa;
                font-family: 'Consolas', monospace;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #00ffff;
                color: #000;
            }
        """)

        layout = QVBoxLayout(self)
        grid = QGridLayout()

        name = os.path.basename(self.file_path)
        is_dir = os.path.isdir(self.file_path)
        size_bytes = 0
        created = ""
        modified = ""

        try:
            stat = os.stat(self.file_path)
            size_bytes = stat.st_size
            created = time.ctime(stat.st_ctime)
            modified = time.ctime(stat.st_mtime)
        except Exception:
            pass

        grid.addWidget(QLabel("Node Name:"), 0, 0)
        grid.addWidget(QLabel(name), 0, 1)

        grid.addWidget(QLabel(tr("prop_path")), 1, 0)
        grid.addWidget(QLabel(self.file_path), 1, 1)

        grid.addWidget(QLabel(tr("prop_type")), 2, 0)
        grid.addWidget(QLabel("Directory" if is_dir else "File"), 2, 1)

        grid.addWidget(QLabel(tr("prop_size")), 3, 0)
        grid.addWidget(QLabel(f"{size_bytes} bytes"), 3, 1)

        grid.addWidget(QLabel(tr("prop_created")), 4, 0)
        grid.addWidget(QLabel(created), 4, 1)

        grid.addWidget(QLabel(tr("prop_modified")), 5, 0)
        grid.addWidget(QLabel(modified), 5, 1)

        layout.addLayout(grid)

        self.btn_close = QPushButton(tr("btn_close"))
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)

class TextEditorDialog(QDialog):
    def __init__(self, file_path, parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.init_ui()
        self.load_file()

    def init_ui(self):
        self.setWindowTitle(f"{tr('editor_title')} - {os.path.basename(self.file_path)}")
        self.resize(700, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #060606;
                color: #00ff00;
                border: 2px solid #00ff00;
            }
            QTextEdit {
                background-color: #030303;
                color: #00ff00;
                border: 1px solid #00bb00;
                font-family: 'Consolas', monospace;
                font-size: 10pt;
            }
            QPushButton {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00aa00;
                font-family: 'Consolas', monospace;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: #00ff00;
                color: #000;
            }
        """)

        layout = QVBoxLayout(self)

        self.editor = QTextEdit()
        layout.addWidget(self.editor)

        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton(tr("editor_save"))
        self.btn_save.clicked.connect(self.save_file)
        btn_layout.addWidget(self.btn_save)

        self.btn_close = QPushButton(tr("btn_close"))
        self.btn_close.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_close)

        layout.addLayout(btn_layout)

    def load_file(self):
        if os.path.exists(self.file_path) and os.path.isfile(self.file_path):
            try:
                with open(self.file_path, "r", encoding="utf-8", errors="ignore") as f:
                    self.editor.setPlainText(f.read())
            except Exception as e:
                QMessageBox.critical(self, tr("sys_err"), f"{tr('error_occurred')}{str(e)}")

    def save_file(self):
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                f.write(self.editor.toPlainText())
            QMessageBox.information(self, "SUCCESS", tr("editor_saved"))
        except Exception as e:
            QMessageBox.critical(self, tr("sys_err"), f"{tr('error_occurred')}{str(e)}")

class SearchDialog(QDialog):
    def __init__(self, start_dir, parent=None):
        super().__init__(parent)
        self.start_dir = start_dir
        self.selected_path = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(tr("search_title"))
        self.resize(600, 400)
        self.setStyleSheet("""
            QDialog {
                background-color: #050505;
                color: #00ff00;
                border: 2px solid #00ff00;
            }
            QLabel {
                color: #00ff00;
                font-family: 'Consolas', monospace;
                font-size: 10pt;
            }
            QLineEdit {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00aa00;
                font-family: 'Consolas', monospace;
                padding: 4px;
            }
            QPushButton {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00aa00;
                font-family: 'Consolas', monospace;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #00aa00;
                color: #000;
            }
            QListWidget {
                background-color: #080808;
                color: #00ff00;
                border: 1px solid #00aa00;
                font-family: 'Consolas', monospace;
            }
        """)

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(tr("search_pattern")))
        self.pattern_input = QLineEdit("*.txt")
        layout.addWidget(self.pattern_input)

        layout.addWidget(QLabel(tr("search_content")))
        self.content_input = QLineEdit()
        layout.addWidget(self.content_input)

        self.btn_search = QPushButton(tr("search_btn"))
        self.btn_search.clicked.connect(self.perform_search)
        layout.addWidget(self.btn_search)

        self.results_list = QListWidget()
        self.results_list.doubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.results_list)

        self.btn_close = QPushButton(tr("btn_close"))
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_close)

    def perform_search(self):
        self.results_list.clear()
        pattern = self.pattern_input.text().strip()
        content = self.content_input.text().strip()

        if not pattern:
            pattern = "*"

        for root, _, files in os.walk(self.start_dir):
            for file in files:
                if fnmatch.fnmatch(file, pattern):
                    full_path = os.path.join(root, file)
                    if content:
                        try:
                            with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                                if content in f.read():
                                    self.results_list.addItem(full_path)
                        except Exception:
                            pass
                    else:
                        self.results_list.addItem(full_path)

    def on_item_double_clicked(self, index):
        self.selected_path = self.results_list.currentItem().text()
        self.accept()

class MultiRenameDialog(QDialog):
    def __init__(self, file_paths, parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.rename_log = []
        self.init_ui()
        self.update_preview()

    def init_ui(self):
        self.setWindowTitle(tr("multi_rename_title"))
        self.resize(700, 450)
        self.setStyleSheet("""
            QDialog {
                background-color: #060606;
                color: #00ff00;
                border: 2px solid #00ff00;
            }
            QLabel {
                color: #00ff00;
                font-family: 'Consolas', monospace;
            }
            QLineEdit {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00aa00;
                font-family: 'Consolas', monospace;
                padding: 4px;
            }
            QCheckBox {
                color: #00ff00;
                font-family: 'Consolas', monospace;
            }
            QPushButton {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00aa00;
                font-family: 'Consolas', monospace;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #00aa00;
                color: #000;
            }
            QListWidget {
                background-color: #080808;
                color: #00ff00;
                border: 1px solid #00aa00;
                font-family: 'Consolas', monospace;
            }
        """)

        layout = QVBoxLayout(self)

        inputs_layout = QHBoxLayout()

        col1 = QVBoxLayout()
        col1.addWidget(QLabel(tr("mr_prefix")))
        self.prefix_input = QLineEdit()
        self.prefix_input.textChanged.connect(self.update_preview)
        col1.addWidget(self.prefix_input)

        col1.addWidget(QLabel(tr("mr_suffix")))
        self.suffix_input = QLineEdit()
        self.suffix_input.textChanged.connect(self.update_preview)
        col1.addWidget(self.suffix_input)

        inputs_layout.addLayout(col1)

        col2 = QVBoxLayout()
        col2.addWidget(QLabel(tr("mr_replace_src")))
        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self.update_preview)
        col2.addWidget(self.search_input)

        col2.addWidget(QLabel(tr("mr_replace_dst")))
        self.replace_input = QLineEdit()
        self.replace_input.textChanged.connect(self.update_preview)
        col2.addWidget(self.replace_input)

        inputs_layout.addLayout(col2)
        layout.addLayout(inputs_layout)

        self.counter_checkbox = QCheckBox(tr("mr_counter"))
        self.counter_checkbox.stateChanged.connect(self.update_preview)
        layout.addWidget(self.counter_checkbox)

        self.preview_list = QListWidget()
        layout.addWidget(self.preview_list)

        btn_layout = QHBoxLayout()
        self.btn_execute = QPushButton(tr("mr_btn"))
        self.btn_execute.clicked.connect(self.execute_rename)
        btn_layout.addWidget(self.btn_execute)

        self.btn_cancel = QPushButton(tr("btn_cancel"))
        self.btn_cancel.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_cancel)

        layout.addLayout(btn_layout)

    def get_new_name(self, idx, path):
        directory = os.path.dirname(path)
        base = os.path.basename(path)
        name, ext = os.path.splitext(base)

        search_txt = self.search_input.text()
        replace_txt = self.replace_input.text()

        if search_txt:
            name = name.replace(search_txt, replace_txt)

        prefix = self.prefix_input.text()
        suffix = self.suffix_input.text()

        counter_str = ""
        if self.counter_checkbox.isChecked():
            counter_str = f"_{idx+1}"

        new_base = f"{prefix}{name}{suffix}{counter_str}{ext}"
        return os.path.join(directory, new_base)

    def update_preview(self):
        self.preview_list.clear()
        for idx, path in enumerate(self.file_paths):
            new_path = self.get_new_name(idx, path)
            self.preview_list.addItem(f"{os.path.basename(path)}  ->  {os.path.basename(new_path)}")

    def execute_rename(self):
        self.rename_log = []
        for idx, path in enumerate(self.file_paths):
            new_path = self.get_new_name(idx, path)
            if path != new_path:
                try:
                    os.rename(path, new_path)
                    self.rename_log.append((path, new_path))
                except Exception as e:
                    QMessageBox.critical(self, tr("sys_err"), f"{tr('error_occurred')}{str(e)}")
        self.accept()

class ZipWorker(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, paths, zip_dest, mode="pack"):
        super().__init__()
        self.paths = paths
        self.zip_dest = zip_dest
        self.mode = mode

    def run(self):
        try:
            if self.mode == "pack":
                with zipfile.ZipFile(self.zip_dest, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    total = len(self.paths)
                    for idx, path in enumerate(self.paths):
                        name = os.path.basename(path)
                        self.log.emit(f"Adding: {name}")
                        if os.path.isdir(path):
                            for root, _, files in os.walk(path):
                                for file in files:
                                    full_p = os.path.join(root, file)
                                    rel_p = os.path.relpath(full_p, os.path.dirname(path))
                                    zipf.write(full_p, rel_p)
                        else:
                            zipf.write(path, name)
                        percent = int(((idx + 1) / total) * 100)
                        self.progress.emit(percent)
                self.finished.emit(True, tr("copied_status"))
            else:
                total = len(self.paths)
                for idx, path in enumerate(self.paths):
                    self.log.emit(f"Extracting: {os.path.basename(path)}")
                    with zipfile.ZipFile(path, 'r') as zipf:
                        zipf.extractall(self.zip_dest)
                    percent = int(((idx + 1) / total) * 100)
                    self.progress.emit(percent)
                self.finished.emit(True, tr("moved_status"))
        except Exception as e:
            self.finished.emit(False, str(e))

class ZipDialog(QDialog):
    def __init__(self, paths, zip_dest, mode="pack", parent=None):
        super().__init__(parent)
        self.paths = paths
        self.zip_dest = zip_dest
        self.mode = mode
        self.init_ui()

    def init_ui(self):
        title = tr("zip_pack_title") if self.mode == "pack" else tr("zip_unpack_title")
        self.setWindowTitle(title)
        self.resize(500, 280)
        self.setStyleSheet("""
            QDialog {
                background-color: #080808;
                color: #00ffff;
                border: 2px solid #00ffff;
            }
            QLabel {
                color: #00ffff;
                font-family: 'Consolas', monospace;
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
            QListWidget {
                background-color: #050505;
                color: #00ffff;
                border: 1px solid #00aaaa;
                font-family: 'Consolas', monospace;
            }
            QPushButton {
                background-color: #111;
                color: #00ffff;
                border: 1px solid #00ffff;
                padding: 6px;
                font-family: 'Consolas', monospace;
            }
            QPushButton:hover {
                background-color: #00ffff;
                color: #000;
            }
        """)

        layout = QVBoxLayout(self)

        self.status_lbl = QLabel(tr("zip_working"))
        layout.addWidget(self.status_lbl)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.log_list = QListWidget()
        layout.addWidget(self.log_list)

        self.btn_close = QPushButton(tr("btn_abort"))
        self.btn_close.clicked.connect(self.abort_worker)
        layout.addWidget(self.btn_close)

        self.worker = ZipWorker(self.paths, self.zip_dest, self.mode)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.log.connect(self.log_list.addItem)
        self.worker.finished.connect(self.on_finished)
        self.worker.start()

    def abort_worker(self):
        if self.worker.isRunning():
            self.worker.terminate()
            self.worker.wait()
        self.close()

    def on_finished(self, success, message):
        if success:
            self.status_lbl.setText("PROTOCOL SUCCESS")
            self.log_list.addItem("[STATUS] Operations compiled.")
        else:
            self.status_lbl.setText("PROTOCOL FAILED")
            self.log_list.addItem(f"[ERROR] {message}")
        self.btn_close.setText(tr("btn_close"))
        self.btn_close.clicked.disconnect()
        self.btn_close.clicked.connect(self.close)

class HotlistDialog(QDialog):
    def __init__(self, current_path, parent=None):
        super().__init__(parent)
        self.current_path = current_path
        self.selected_path = None
        self.bookmarks_file = "bookmarks.json"
        self.load_bookmarks()
        self.init_ui()

    def load_bookmarks(self):
        self.bookmarks = []
        if os.path.exists(self.bookmarks_file):
            try:
                with open(self.bookmarks_file, "r") as f:
                    self.bookmarks = json.load(f)
            except Exception:
                pass

    def save_bookmarks(self):
        try:
            with open(self.bookmarks_file, "w") as f:
                json.dump(self.bookmarks, f, indent=2)
        except Exception:
            pass

    def init_ui(self):
        self.setWindowTitle(tr("bookmarks_title"))
        self.resize(400, 300)
        self.setStyleSheet("""
            QDialog {
                background-color: #050505;
                color: #00ff00;
                border: 2px solid #00ff00;
            }
            QPushButton {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00aa00;
                font-family: 'Consolas', monospace;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #00aa00;
                color: #000;
            }
            QListWidget {
                background-color: #080808;
                color: #00ff00;
                border: 1px solid #00aa00;
                font-family: 'Consolas', monospace;
            }
        """)

        layout = QVBoxLayout(self)

        self.btn_add = QPushButton(tr("btn_add_bookmark"))
        self.btn_add.clicked.connect(self.add_current)
        layout.addWidget(self.btn_add)

        self.list_widget = QListWidget()
        for bookmark in self.bookmarks:
            self.list_widget.addItem(bookmark)
        self.list_widget.doubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.list_widget)

        btn_layout = QHBoxLayout()
        self.btn_select = QPushButton("SELECT")
        self.btn_select.clicked.connect(self.on_select_clicked)
        btn_layout.addWidget(self.btn_select)

        self.btn_delete = QPushButton("DELETE")
        self.btn_delete.clicked.connect(self.delete_bookmark)
        btn_layout.addWidget(self.btn_delete)

        layout.addLayout(btn_layout)

    def add_current(self):
        if self.current_path not in self.bookmarks:
            self.bookmarks.append(self.current_path)
            self.list_widget.addItem(self.current_path)
            self.save_bookmarks()

    def delete_bookmark(self):
        item = self.list_widget.currentItem()
        if item:
            self.bookmarks.remove(item.text())
            self.save_bookmarks()
            self.list_widget.takeItem(self.list_widget.row(item))

    def on_select_clicked(self):
        item = self.list_widget.currentItem()
        if item:
            self.selected_path = item.text()
            self.accept()

    def on_item_double_clicked(self, index):
        self.selected_path = self.list_widget.currentItem().text()
        self.accept()

import json
