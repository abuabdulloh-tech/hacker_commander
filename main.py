import os
import sys
import json
import hashlib
import shutil
import ctypes
try:
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("mycompany.cybercommander.1.0")
except Exception:
    pass
from PyQt6.QtCore import Qt, QDir, QModelIndex, pyqtSignal, QUrl
from PyQt6.QtGui import QFileSystemModel, QAction, QIcon, QPixmap, QPainter, QColor
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeView, QLineEdit, QPushButton, QLabel,
    QInputDialog, QMessageBox, QDialog, QStatusBar, QTabWidget,
    QListWidget, QMenu, QPlainTextEdit, QFrame, QTextEdit
)

from hex_viewer import HexViewer
from shredder import ShredderDialog
from file_operations import FileOperationDialog
from terminal import CyberTerminal
from translator import tr
from cyber_tools import (
    SearchDialog, MultiRenameDialog, ZipDialog, HotlistDialog,
    HelpDialog, PropertiesDialog, TextEditorDialog
)

class CyberTreeView(QTreeView):
    drop_received = pyqtSignal(list, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeView.DragDropMode.DragDrop)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        parent_pane = self.parentWidget()
        while parent_pane and not hasattr(parent_pane, "set_focus_active"):
            parent_pane = parent_pane.parentWidget()
        if parent_pane:
            parent_pane.set_focus_active()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() or event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.setDropAction(Qt.DropAction.CopyAction)
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.DropAction.CopyAction)
            paths = [url.toLocalFile() for url in event.mimeData().urls() if url.toLocalFile()]
            index = self.indexAt(event.position().toPoint())
            model = self.model()
            
            if index.isValid():
                path = model.filePath(index)
                if os.path.isdir(path):
                    target_dir = path
                else:
                    target_dir = os.path.dirname(path)
            else:
                target_dir = model.filePath(self.rootIndex())
                
            self.drop_received.emit(paths, target_dir)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

class CyberListWidget(QListWidget):
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        parent_pane = self.parentWidget()
        while parent_pane and not hasattr(parent_pane, "set_focus_active"):
            parent_pane = parent_pane.parentWidget()
        if parent_pane:
            parent_pane.set_focus_active()

class FilePane(QWidget):
    pane_focused = pyqtSignal(object)

    def __init__(self, start_path, partner_pane=None, parent=None):
        super().__init__(parent)
        self.partner_pane = partner_pane
        self.current_dir = start_path
        self.history = [start_path]
        self.history_idx = 0
        self.is_flat_view = False
        self.is_preview_mode = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self.setStyleSheet("""
            QLineEdit {
                background-color: #0b0b0b;
                color: #00ff00;
                border: 1px solid #008800;
                font-family: 'Consolas', monospace;
                font-size: 10pt;
                padding: 3px;
            }
            QPushButton {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00aa00;
                font-family: 'Consolas', monospace;
                font-size: 9pt;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #00aa00;
                color: #000;
            }
            QTreeView, QListWidget, QPlainTextEdit {
                background-color: #050505;
                color: #00ff00;
                border: 1px solid #008800;
                font-family: 'Consolas', monospace;
                font-size: 9pt;
            }
            QTreeView::item:selected, QListWidget::item:selected {
                background-color: #003300;
                color: #00ff00;
                border: 1px solid #00ff00;
            }
            QTreeView::item:hover, QListWidget::item:hover {
                background-color: #002200;
                color: #00ff00;
            }
            QHeaderView::section {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00aa00;
                padding: 4px;
                font-family: 'Consolas', monospace;
                font-size: 9pt;
            }
            QLabel {
                color: #00ff00;
                font-family: 'Consolas', monospace;
                font-size: 9pt;
            }
        """)

        top_layout = QHBoxLayout()
        
        self.drives_layout = QHBoxLayout()
        self.load_drives()
        top_layout.addLayout(self.drives_layout)
        
        self.btn_up = QPushButton("[ .. ]")
        self.btn_up.clicked.connect(lambda: (self.set_focus_active(), self.go_up()))
        top_layout.addWidget(self.btn_up)
        
        layout.addLayout(top_layout)

        self.path_input = QLineEdit(self.current_dir)
        self.path_input.returnPressed.connect(lambda: (self.set_focus_active(), self.navigate_to_input_path()))
        layout.addWidget(self.path_input)

        self.model = QFileSystemModel()
        self.model.setRootPath(self.current_dir)
        self.model.setFilter(QDir.Filter.AllEntries | QDir.Filter.NoDotAndDotDot)
        self.model.directoryLoaded.connect(self.update_stats)

        self.tree = CyberTreeView()
        self.tree.setModel(self.model)
        self.tree.setRootIndex(self.model.index(self.current_dir))
        self.tree.setSelectionMode(QTreeView.SelectionMode.ExtendedSelection)
        self.tree.setAlternatingRowColors(False)
        self.tree.setColumnWidth(0, 250)
        self.tree.setSortingEnabled(True)
        self.tree.doubleClicked.connect(self.on_item_double_clicked)
        self.tree.clicked.connect(self.set_focus_active)
        self.tree.selectionModel().selectionChanged.connect(self.update_stats)
        self.tree.drop_received.connect(self.handle_drag_drop)
        layout.addWidget(self.tree)

        self.flat_list = CyberListWidget()
        self.flat_list.doubleClicked.connect(self.on_flat_double_clicked)
        self.flat_list.clicked.connect(self.set_focus_active)
        self.flat_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.flat_list.hide()
        layout.addWidget(self.flat_list)

        self.preview_text = QPlainTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.hide()
        layout.addWidget(self.preview_text)

        self.stats_lbl = QLabel()
        layout.addWidget(self.stats_lbl)
        self.update_stats()

    def load_drives(self):
        while self.drives_layout.count():
            item = self.drives_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        drives = []
        for d in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
            path = f"{d}:\\"
            if os.path.exists(path):
                drives.append(path)

        for drive in drives:
            btn = QPushButton(drive[:2])
            btn.setMaximumWidth(40)
            btn.clicked.connect(lambda checked, p=drive: (self.set_focus_active(), self.navigate(p)))
            self.drives_layout.addWidget(btn)

        home_btn = QPushButton("~")
        home_btn.setMaximumWidth(30)
        home_btn.clicked.connect(lambda: (self.set_focus_active(), self.navigate(os.path.expanduser("~"))))
        self.drives_layout.addWidget(home_btn)

    def set_focus_active(self):
        if self.is_flat_view:
            self.flat_list.setFocus()
        else:
            self.tree.setFocus()
        self.pane_focused.emit(self)

    def navigate(self, path, add_history=True):
        if os.path.exists(path) and os.path.isdir(path):
            self.current_dir = path
            self.path_input.setText(path)
            self.model.setRootPath(path)
            self.tree.setRootIndex(self.model.index(path))
            
            if add_history:
                if self.history_idx < len(self.history) - 1:
                    self.history = self.history[:self.history_idx + 1]
                self.history.append(path)
                self.history_idx = len(self.history) - 1

            if self.is_flat_view:
                self.populate_flat_view()
            self.update_stats()
            
            parent_tab_widget = self.parentWidget()
            while parent_tab_widget and not isinstance(parent_tab_widget, QTabWidget):
                parent_tab_widget = parent_tab_widget.parentWidget()
            if parent_tab_widget:
                idx = parent_tab_widget.indexOf(self)
                if idx != -1:
                    parent_tab_widget.setTabText(idx, os.path.basename(path) or path[:3])

    def history_back(self):
        if self.history_idx > 0:
            self.history_idx -= 1
            self.navigate(self.history[self.history_idx], add_history=False)

    def history_forward(self):
        if self.history_idx < len(self.history) - 1:
            self.history_idx += 1
            self.navigate(self.history[self.history_idx], add_history=False)

    def show_history_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0b0b0b;
                color: #00ff00;
                border: 1px solid #00ff00;
            }
            QMenu::item:selected {
                background-color: #003300;
            }
        """)
        for path in reversed(self.history):
            action = QAction(path, self)
            action.triggered.connect(lambda checked, p=path: self.navigate(p))
            menu.addAction(action)
        menu.exec(self.path_input.mapToGlobal(self.path_input.rect().bottomLeft()))

    def navigate_to_input_path(self):
        path = self.path_input.text().strip()
        if os.path.exists(path) and os.path.isdir(path):
            self.navigate(path)
        else:
            self.path_input.setText(self.current_dir)

    def go_up(self):
        parent_dir = os.path.dirname(self.current_dir)
        if parent_dir and parent_dir != self.current_dir:
            self.navigate(parent_dir)

    def on_item_double_clicked(self, index):
        path = self.model.filePath(index)
        if os.path.isdir(path):
            self.navigate(path)
        else:
            self.open_file_in_viewer(path)

    def on_flat_double_clicked(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            if os.path.isdir(path):
                self.toggle_flat_view()
                self.navigate(path)
            else:
                self.open_file_in_viewer(path)

    def open_file_in_viewer(self, path):
        viewer = HexViewer(path, self)
        viewer.exec()

    def get_selected_paths(self):
        if self.is_flat_view:
            items = self.flat_list.selectedItems()
            paths = [i.data(Qt.ItemDataRole.UserRole) for i in items if i.data(Qt.ItemDataRole.UserRole)]
            if not paths and self.flat_list.currentItem():
                paths.append(self.flat_list.currentItem().data(Qt.ItemDataRole.UserRole))
            return paths
        
        indexes = self.tree.selectionModel().selectedRows()
        paths = []
        for index in indexes:
            paths.append(self.model.filePath(index))
        if not paths:
            cur_index = self.tree.currentIndex()
            if cur_index.isValid():
                paths.append(self.model.filePath(cur_index))
        return paths

    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1048576:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1073741824:
            return f"{size_bytes / 1048576:.1f} MB"
        else:
            return f"{size_bytes / 1073741824:.1f} GB"

    def update_stats(self):
        if self.is_flat_view:
            total_count = self.flat_list.count()
            selected_count = len(self.flat_list.selectedItems())
            total_size = 0
            selected_size = 0
            for i in range(total_count):
                item = self.flat_list.item(i)
                p = item.data(Qt.ItemDataRole.UserRole)
                if p and os.path.isfile(p):
                    try:
                        total_size += os.path.getsize(p)
                    except Exception:
                        pass
            for item in self.flat_list.selectedItems():
                p = item.data(Qt.ItemDataRole.UserRole)
                if p and os.path.isfile(p):
                    try:
                        selected_size += os.path.getsize(p)
                    except Exception:
                        pass
            total_size_str = self.format_size(total_size)
            selected_size_str = self.format_size(selected_size)
            self.stats_lbl.setText(tr("pane_stats").format(
                selected_count, total_count, selected_size_str, total_size_str
            ))
            return

        try:
            files = os.listdir(self.current_dir)
        except Exception:
            files = []

        total_count = len(files)
        total_size = 0
        for f in files:
            fp = os.path.join(self.current_dir, f)
            if os.path.isfile(fp):
                try:
                    total_size += os.path.getsize(fp)
                except Exception:
                    pass

        selected_indexes = self.tree.selectionModel().selectedRows()
        selected_count = len(selected_indexes)
        selected_size = 0
        for index in selected_indexes:
            path = self.model.filePath(index)
            if os.path.isfile(path):
                try:
                    selected_size += os.path.getsize(path)
                except Exception:
                    pass

        total_size_str = self.format_size(total_size)
        selected_size_str = self.format_size(selected_size)

        self.stats_lbl.setText(tr("pane_stats").format(
            selected_count, total_count, selected_size_str, total_size_str
        ))

        if self.partner_pane and hasattr(self.partner_pane, "is_preview_mode") and self.partner_pane.is_preview_mode:
            self.partner_pane.update_preview_content(self.get_selected_paths())

    def toggle_flat_view(self):
        self.is_flat_view = not self.is_flat_view
        if self.is_flat_view:
            self.tree.hide()
            self.flat_list.show()
            self.populate_flat_view()
        else:
            self.flat_list.hide()
            self.tree.show()
            self.update_stats()

    def populate_flat_view(self):
        self.flat_list.clear()
        for root, _, files in os.walk(self.current_dir):
            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, self.current_dir)
                from PyQt6.QtWidgets import QListWidgetItem
                list_item = QListWidgetItem(rel_path)
                list_item.setData(Qt.ItemDataRole.UserRole, full_path)
                self.flat_list.addItem(list_item)
        self.update_stats()

    def toggle_preview_mode(self):
        self.is_preview_mode = not self.is_preview_mode
        if self.is_preview_mode:
            self.tree.hide()
            self.flat_list.hide()
            self.preview_text.show()
        else:
            self.preview_text.hide()
            if self.is_flat_view:
                self.flat_list.show()
            else:
                self.tree.show()

    def update_preview_content(self, selected_paths):
        if not self.is_preview_mode:
            return
        if not selected_paths:
            self.preview_text.setPlainText("--- NO SELECTION ---")
            return
        
        path = selected_paths[0]
        if os.path.isdir(path):
            self.preview_text.setPlainText(f"Directory: {path}")
            return

        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(5000)
            self.preview_text.setPlainText(content)
        except Exception as e:
            self.preview_text.setPlainText(f"PREVIEW ERROR:\n{str(e)}")

    def handle_drag_drop(self, paths, target_dir):
        dialog = FileOperationDialog(paths, target_dir, "copy", self)
        dialog.exec()
        main_win = self.window()
        if main_win and hasattr(main_win, "undo_stack"):
            main_win.undo_stack.append({
                "type": "copy",
                "items": [os.path.join(target_dir, os.path.basename(p)) for p in paths]
            })
        self.refresh()
        if self.partner_pane:
            self.partner_pane.refresh()

    def toggle_hidden_files(self):
        filters = self.model.filter()
        if filters & QDir.Filter.Hidden:
            self.model.setFilter(filters & ~QDir.Filter.Hidden)
        else:
            self.model.setFilter(filters | QDir.Filter.Hidden)
        self.refresh()

    def refresh(self):
        self.model.setRootPath(self.current_dir)
        self.tree.setRootIndex(self.model.index(self.current_dir))
        if self.is_flat_view:
            self.populate_flat_view()
        self.update_stats()

class CyberCommander(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_file = "config.json"
        self.undo_stack = []
        self.load_settings()
        self.init_ui()

    def load_settings(self):
        self.left_path = "C:\\"
        self.right_path = "C:\\"
        self.window_width = 1100
        self.window_height = 700

        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    cfg = json.load(f)
                    self.left_path = cfg.get("left_path", "C:\\")
                    self.right_path = cfg.get("right_path", "C:\\")
                    self.window_width = cfg.get("window_width", 1100)
                    self.window_height = cfg.get("window_height", 700)
            except Exception:
                pass

        if not os.path.exists(self.left_path):
            self.left_path = os.path.expanduser("~")
        if not os.path.exists(self.right_path):
            self.right_path = os.path.expanduser("~")

    def save_settings(self):
        cfg = {
            "left_path": self.left_pane.current_dir,
            "right_path": self.right_pane.current_dir,
            "window_width": self.width(),
            "window_height": self.height()
        }
        try:
            with open(self.config_file, "w") as f:
                json.dump(cfg, f, indent=2)
            try:
                ctypes.windll.kernel32.SetFileAttributesW(self.config_file, 2)
            except Exception:
                pass
        except Exception:
            pass

    def init_ui(self):
        self.setWindowTitle("CYBERCOMMANDER")
        self.resize(self.window_width, self.window_height)
        
        if os.path.exists("icon.ico"):
            self.setWindowIcon(QIcon("icon.ico"))
        else:
            pixmap = QPixmap(64, 64)
            pixmap.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QColor(10, 10, 10))
            painter.setPen(QColor(0, 255, 0))
            painter.drawRect(2, 2, 60, 60)
            painter.drawText(20, 36, "CC")
            painter.end()
            self.setWindowIcon(QIcon(pixmap))
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #060606;
                color: #00ff00;
            }
            QStatusBar {
                background-color: #0b0b0b;
                color: #00ffff;
                border-top: 1px solid #00bb00;
                font-family: 'Consolas', monospace;
                font-size: 9pt;
            }
            QMessageBox {
                background-color: #080808;
                color: #00ff00;
                border: 2px solid #00ff00;
            }
            QMessageBox QLabel {
                color: #00ff00;
                font-family: 'Consolas', monospace;
            }
            QMessageBox QPushButton {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00ff00;
                padding: 4px 10px;
                font-family: 'Consolas', monospace;
            }
            QTabWidget::pane {
                border: 1px solid #005500;
                background: #050505;
            }
            QTabBar::tab {
                background: #111;
                color: #008800;
                border: 1px solid #005500;
                padding: 6px;
                font-family: 'Consolas', monospace;
            }
            QTabBar::tab:selected {
                background: #050505;
                color: #00ff00;
                border-color: #00ff00;
                border-bottom-color: #050505;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)

        left_and_right_layout = QVBoxLayout()
        
        pane_splitter = QSplitter(Qt.Orientation.Horizontal)

        self.left_tabs = QTabWidget()
        self.left_tabs.setTabsClosable(True)
        self.left_tabs.tabCloseRequested.connect(lambda idx: self.close_tab(self.left_tabs, idx))

        self.right_tabs = QTabWidget()
        self.right_tabs.setTabsClosable(True)
        self.right_tabs.tabCloseRequested.connect(lambda idx: self.close_tab(self.right_tabs, idx))

        self.left_pane = FilePane(self.left_path, parent=self)
        self.right_pane = FilePane(self.right_path, parent=self)

        self.left_pane.partner_pane = self.right_pane
        self.right_pane.partner_pane = self.left_pane

        self.left_pane.pane_focused.connect(self.set_active_pane)
        self.right_pane.pane_focused.connect(self.set_active_pane)

        self.left_tabs.addTab(self.left_pane, os.path.basename(self.left_path) or self.left_path[:3])
        self.right_tabs.addTab(self.right_pane, os.path.basename(self.right_path) or self.right_path[:3])

        pane_splitter.addWidget(self.left_tabs)
        pane_splitter.addWidget(self.right_tabs)
        left_and_right_layout.addWidget(pane_splitter, stretch=3)

        self.active_pane = self.left_pane
        self.active_pane_group = self.left_tabs

        self.terminal_widget = CyberTerminal()
        left_and_right_layout.addWidget(self.terminal_widget, stretch=1)

        fkeys_layout = QHBoxLayout()
        fkeys_layout.setSpacing(2)

        self.btn_f3 = QPushButton(tr("f3_view_btn"))
        self.btn_f3.clicked.connect(self.trigger_f3)
        fkeys_layout.addWidget(self.btn_f3)

        self.btn_f4 = QPushButton(tr("f4_hash"))
        self.btn_f4.clicked.connect(self.trigger_f4)
        fkeys_layout.addWidget(self.btn_f4)

        self.btn_f5 = QPushButton(tr("f5_copy"))
        self.btn_f5.clicked.connect(self.trigger_f5)
        fkeys_layout.addWidget(self.btn_f5)

        self.btn_f6 = QPushButton(tr("f6_move"))
        self.btn_f6.clicked.connect(self.trigger_f6)
        fkeys_layout.addWidget(self.btn_f6)

        self.btn_f7 = QPushButton(tr("f7_mkdir"))
        self.btn_f7.clicked.connect(self.trigger_f7)
        fkeys_layout.addWidget(self.btn_f7)

        self.btn_f8 = QPushButton(tr("f8_shred"))
        self.btn_f8.clicked.connect(self.trigger_f8)
        fkeys_layout.addWidget(self.btn_f8)

        self.style_fkeys()
        left_and_right_layout.addLayout(fkeys_layout)

        main_layout.addLayout(left_and_right_layout, stretch=4)

        self.cheatsheet_frame = QFrame()
        self.cheatsheet_frame.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Plain)
        self.cheatsheet_frame.setStyleSheet("""
            QFrame {
                background-color: #0a0a0a;
                color: #00ff00;
                border: 1px solid #00bb00;
                max-width: 250px;
            }
            QLabel {
                font-family: 'Consolas', monospace;
                font-size: 8pt;
                color: #00ff00;
                border: none;
            }
            QPushButton {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00aa00;
                font-family: 'Consolas', monospace;
                font-size: 9pt;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #00aa00;
                color: #000;
            }
        """)
        
        cs_layout = QVBoxLayout(self.cheatsheet_frame)
        self.lbl_cs_title = QLabel(tr("cheatsheet_title"))
        self.lbl_cs_title.setStyleSheet("font-weight: bold; font-size: 9pt; color: #00ffff;")
        cs_layout.addWidget(self.lbl_cs_title)

        self.cheatsheet_text = QTextEdit()
        self.cheatsheet_text.setReadOnly(True)
        self.cheatsheet_text.setStyleSheet("border: none; background: transparent;")
        cs_layout.addWidget(self.cheatsheet_text)
        
        self.btn_toggle_cs = QPushButton(tr("btn_close"))
        self.btn_toggle_cs.clicked.connect(self.toggle_cheatsheet)
        cs_layout.addWidget(self.btn_toggle_cs)
        
        main_layout.addWidget(self.cheatsheet_frame, stretch=1)
        self.update_cheatsheet_content()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(tr("active_left"))

        self.left_tabs.currentChanged.connect(lambda idx: self.tab_changed(self.left_tabs, idx))
        self.right_tabs.currentChanged.connect(lambda idx: self.tab_changed(self.right_tabs, idx))

    def update_cheatsheet_content(self):
        text = (
            f"F1: Help Guide\n"
            f"F2: Reread Directory\n"
            f"F3: Hex View (Lister)\n"
            f"F4: built-in Editor\n"
            f"F5: Copy selected items\n"
            f"F6: Move selected items\n"
            f"F7: New Folder (Mkdir)\n"
            f"F8: Delete File/Folder\n\n"
            f"Alt+F1: Left Drive select\n"
            f"Alt+F2: Right Drive select\n"
            f"Alt+F4: Exit program\n"
            f"Alt+F5: Pack (ZIP)\n"
            f"Alt+F6: Unpack (ZIP)\n"
            f"Alt+F7: Search Dialog\n"
            f"Alt+Enter: Properties\n"
            f"Alt+Left/Right: Back/Fwd\n"
            f"Alt+Down: History menu\n\n"
            f"Ctrl+A: Select All items\n"
            f"Ctrl+B: Toggle Flat view\n"
            f"Ctrl+D: Folder Bookmarks\n"
            f"Ctrl+M: Multi-Rename\n"
            f"Ctrl+Q: Quick View toggle\n"
            f"Ctrl+T: Open new Tab\n"
            f"Ctrl+U: Swap directories\n"
            f"Ctrl+PgUp/Backspace: Up\n"
            f"Ctrl+F3: Sort by Name\n"
            f"Ctrl+F4: Sort by Type\n"
            f"Ctrl+F5: Sort by Date\n"
            f"Ctrl+F6: Sort by Size\n\n"
            f"Shift+F4: New empty text\n"
            f"Shift+F5: Copy as (Local)\n"
            f"Shift+F6: Rename active item\n"
            f"Shift+Delete: Shred deletion\n\n"
            f"Backspace: Go Up folder\n"
            f"Enter: Navigate into folder\n"
            f"Ctrl+Z: Undo last action"
        )
        self.cheatsheet_text.setPlainText(text)

    def toggle_cheatsheet(self):
        if self.cheatsheet_frame.isVisible():
            self.cheatsheet_frame.hide()
        else:
            self.cheatsheet_frame.show()

    def style_fkeys(self):
        style = """
            QPushButton {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00aa00;
                font-family: 'Consolas', monospace;
                font-weight: bold;
                font-size: 10pt;
                padding: 6px;
            }
            QPushButton:hover {
                background-color: #00ff00;
                color: #000;
            }
        """
        self.btn_f3.setStyleSheet(style)
        self.btn_f4.setStyleSheet(style)
        self.btn_f5.setStyleSheet(style)
        self.btn_f6.setStyleSheet(style)
        self.btn_f7.setStyleSheet(style)
        
        shred_style = style.replace("#00ff00", "#ff3333").replace("#00aa00", "#aa0000")
        self.btn_f8.setStyleSheet(shred_style)

    def set_active_pane(self, pane):
        self.active_pane = pane
        self.active_pane_group = self.left_tabs if self.left_tabs.indexOf(pane) != -1 else self.right_tabs
        
        if self.active_pane_group == self.left_tabs:
            self.left_pane.setStyleSheet(self.left_pane.styleSheet().split("\nQTreeView")[0] + "\nQTreeView { border: 2px solid #00ff00; }")
            self.right_pane.setStyleSheet(self.right_pane.styleSheet().split("\nQTreeView")[0] + "\nQTreeView { border: 1px solid #005500; }")
            self.status_bar.showMessage(tr("active_left"))
        else:
            self.right_pane.setStyleSheet(self.right_pane.styleSheet().split("\nQTreeView")[0] + "\nQTreeView { border: 2px solid #00ff00; }")
            self.left_pane.setStyleSheet(self.left_pane.styleSheet().split("\nQTreeView")[0] + "\nQTreeView { border: 1px solid #005500; }")
            self.status_bar.showMessage(tr("active_right"))

    def add_tab(self, tab_widget, path):
        partner = self.right_pane if tab_widget == self.left_tabs else self.left_pane
        new_pane = FilePane(path, partner, self)
        new_pane.pane_focused.connect(self.set_active_pane)
        new_pane.partner_pane = partner
        tab_widget.addTab(new_pane, os.path.basename(path) or path[:3])
        tab_widget.setCurrentWidget(new_pane)
        new_pane.set_focus_active()
        self.status_bar.showMessage(tr("tab_opened"))

    def close_tab(self, tab_widget, idx):
        if tab_widget.count() > 1:
            widget = tab_widget.widget(idx)
            tab_widget.removeTab(idx)
            widget.deleteLater()
            self.status_bar.showMessage(tr("tab_closed"))

    def tab_changed(self, tab_widget, idx):
        widget = tab_widget.widget(idx)
        if widget:
            widget.set_focus_active()

    def keyPressEvent(self, event):
        modifiers = event.modifiers()
        key = event.key()

        if key == Qt.Key.Key_Tab:
            if self.active_pane_group == self.left_tabs:
                pane = self.right_tabs.currentWidget()
            else:
                pane = self.left_tabs.currentWidget()
            if pane:
                pane.set_focus_active()
            event.accept()
        elif key == Qt.Key.Key_Backspace:
            self.active_pane.go_up()
            event.accept()
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            if self.active_pane.tree.hasFocus():
                idx = self.active_pane.tree.currentIndex()
                path = self.active_pane.model.filePath(idx)
                if os.path.isdir(path):
                    self.active_pane.navigate(path)
                else:
                    self.trigger_f3()
                event.accept()
            elif self.active_pane.flat_list.hasFocus():
                item = self.active_pane.flat_list.currentItem()
                if item:
                    path = item.data(Qt.ItemDataRole.UserRole)
                    if os.path.isdir(path):
                        self.active_pane.toggle_flat_view()
                        self.active_pane.navigate(path)
                    else:
                        self.active_pane.open_file_in_viewer(path)
                event.accept()
        elif modifiers == Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_F1:
            self.left_tabs.currentWidget().navigate("C:\\")
            event.accept()
        elif modifiers == Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_F2:
            self.right_tabs.currentWidget().navigate("C:\\")
            event.accept()
        elif modifiers == Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_F4:
            self.close()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_F5:
            self.trigger_alt_f5()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_F6:
            self.trigger_alt_f9()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_F7:
            self.trigger_alt_f7()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_Enter:
            self.trigger_alt_enter()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_Left:
            self.active_pane.history_back()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_Right:
            self.active_pane.history_forward()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.AltModifier and key == Qt.Key.Key_Down:
            self.active_pane.show_history_menu()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_A:
            if self.active_pane.is_flat_view:
                self.active_pane.flat_list.selectAll()
            else:
                self.active_pane.tree.selectAll()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_B:
            self.active_pane.toggle_flat_view()
            self.status_bar.showMessage(tr("flat_toggled"))
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_D:
            self.trigger_ctrl_d()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_M:
            self.trigger_ctrl_m()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Q:
            self.active_pane.partner_pane.toggle_preview_mode()
            self.active_pane.partner_pane.update_preview_content(self.active_pane.get_selected_paths())
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_T:
            self.add_tab(self.active_pane_group, self.active_pane.current_dir)
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_U:
            left_p = self.left_tabs.currentWidget().current_dir
            right_p = self.right_tabs.currentWidget().current_dir
            self.left_tabs.currentWidget().navigate(right_p)
            self.right_tabs.currentWidget().navigate(left_p)
            self.status_bar.showMessage(tr("swap_panes"))
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_PageUp:
            self.active_pane.go_up()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_F3:
            self.active_pane.tree.sortByColumn(0, Qt.SortOrder.AscendingOrder)
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_F4:
            self.active_pane.tree.sortByColumn(2, Qt.SortOrder.AscendingOrder)
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_F5:
            self.active_pane.tree.sortByColumn(3, Qt.SortOrder.AscendingOrder)
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_F6:
            self.active_pane.tree.sortByColumn(1, Qt.SortOrder.AscendingOrder)
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_H:
            self.active_pane.toggle_hidden_files()
            self.status_bar.showMessage(tr("hidden_toggled"))
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ControlModifier and key == Qt.Key.Key_Z:
            self.trigger_undo()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ShiftModifier and key == Qt.Key.Key_F4:
            self.trigger_shift_f4()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ShiftModifier and key == Qt.Key.Key_F5:
            self.trigger_shift_f5()
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ShiftModifier and key == Qt.Key.Key_F6:
            self.active_pane.tree.edit(self.active_pane.tree.currentIndex())
            event.accept()
        elif modifiers == Qt.KeyboardModifier.ShiftModifier and key == Qt.Key.Key_Delete:
            self.trigger_shift_delete()
            event.accept()
        elif key == Qt.Key.Key_F1:
            dialog = HelpDialog(self)
            dialog.exec()
            event.accept()
        elif key == Qt.Key.Key_F2:
            self.active_pane.refresh()
            event.accept()
        elif key == Qt.Key.Key_F3:
            self.trigger_f3()
            event.accept()
        elif key == Qt.Key.Key_F4:
            self.trigger_f4()
            event.accept()
        elif key == Qt.Key.Key_F5:
            self.trigger_f5()
            event.accept()
        elif key == Qt.Key.Key_F6:
            self.trigger_f6()
            event.accept()
        elif key == Qt.Key.Key_F7:
            self.trigger_f7()
            event.accept()
        elif key == Qt.Key.Key_F8 or key == Qt.Key.Key_Delete:
            self.trigger_f8()
            event.accept()
        else:
            super().keyPressEvent(event)

    def trigger_f3(self):
        paths = self.active_pane.get_selected_paths()
        if not paths:
            return
        path = paths[0]
        if os.path.exists(path) and os.path.isfile(path):
            viewer = HexViewer(path, self)
            viewer.exec()

    def trigger_f4(self):
        paths = self.active_pane.get_selected_paths()
        if not paths:
            return
        path = paths[0]
        if os.path.exists(path) and os.path.isfile(path):
            dialog = TextEditorDialog(path, self)
            dialog.exec()
            self.active_pane.refresh()

    def trigger_f5(self):
        paths = self.active_pane.get_selected_paths()
        if not paths:
            return
        dest = self.active_pane.partner_pane.current_dir
        dialog = FileOperationDialog(paths, dest, "copy", self)
        dialog.exec()
        self.undo_stack.append({
            "type": "copy",
            "items": [os.path.join(dest, os.path.basename(p)) for p in paths]
        })
        self.left_tabs.currentWidget().refresh()
        self.right_tabs.currentWidget().refresh()

    def trigger_f6(self):
        paths = self.active_pane.get_selected_paths()
        if not paths:
            return
        dest = self.active_pane.partner_pane.current_dir
        dialog = FileOperationDialog(paths, dest, "move", self)
        dialog.exec()
        self.undo_stack.append({
            "type": "move",
            "mapping": {os.path.join(dest, os.path.basename(p)): p for p in paths}
        })
        self.left_tabs.currentWidget().refresh()
        self.right_tabs.currentWidget().refresh()

    def trigger_f7(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle(tr("input_folder_title"))
        dialog.setLabelText(tr("enter_folder"))
        dialog.setStyleSheet("""
            QInputDialog {
                background-color: #0b0b0b;
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
                border: 1px solid #00ff00;
                font-family: 'Consolas', monospace;
            }
            QPushButton {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00ff00;
                padding: 4px 10px;
                font-family: 'Consolas', monospace;
            }
        """)
        if dialog.exec() == QInputDialog.DialogCode.Accepted:
            name = dialog.textValue().strip()
            if name:
                new_path = os.path.join(self.active_pane.current_dir, name)
                try:
                    os.makedirs(new_path, exist_ok=True)
                    self.undo_stack.append({
                        "type": "mkdir",
                        "path": new_path
                    })
                except Exception as e:
                    QMessageBox.critical(self, tr("sys_err"), f"{tr('error_occurred')}{str(e)}")
                self.active_pane.refresh()

    def trigger_f8(self):
        paths = self.active_pane.get_selected_paths()
        if not paths:
            return
        filenames = "\n".join([os.path.basename(p) for p in paths])
        confirm = QMessageBox.question(
            self,
            tr("confirm_title"),
            f"{tr('shred_confirm')}{filenames}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            dialog = ShredderDialog(paths, self)
            dialog.exec()
            self.left_tabs.currentWidget().refresh()
            self.right_tabs.currentWidget().refresh()

    def trigger_alt_f7(self):
        dialog = SearchDialog(self.active_pane.current_dir, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_path:
            target_p = dialog.selected_path
            if os.path.isdir(target_p):
                self.active_pane.navigate(target_p)
            else:
                self.active_pane.navigate(os.path.dirname(target_p))

    def trigger_alt_f5(self):
        paths = self.active_pane.get_selected_paths()
        if not paths:
            return
        dialog = QInputDialog(self)
        dialog.setWindowTitle(tr("zip_pack_title"))
        dialog.setLabelText(tr("zip_target"))
        dialog.setTextValue("archive.zip")
        dialog.setStyleSheet("""
            QInputDialog {
                background-color: #080808;
                color: #00ffff;
                border: 2px solid #00ffff;
            }
            QLabel {
                color: #00ffff;
                font-family: 'Consolas', monospace;
            }
            QLineEdit {
                background-color: #111;
                color: #00ffff;
                border: 1px solid #00ffff;
                font-family: 'Consolas', monospace;
            }
            QPushButton {
                background-color: #111;
                color: #00ffff;
                border: 1px solid #00ffff;
                padding: 4px 10px;
                font-family: 'Consolas', monospace;
            }
        """)
        if dialog.exec() == QInputDialog.DialogCode.Accepted:
            zip_name = dialog.textValue().strip()
            if zip_name:
                if not zip_name.lower().endswith(".zip"):
                    zip_name += ".zip"
                dest_zip = os.path.join(self.active_pane.partner_pane.current_dir, zip_name)
                zip_dlg = ZipDialog(paths, dest_zip, "pack", self)
                zip_dlg.exec()
                self.undo_stack.append({
                    "type": "copy",
                    "items": [dest_zip]
                })
                self.left_tabs.currentWidget().refresh()
                self.right_tabs.currentWidget().refresh()

    def trigger_alt_f9(self):
        paths = self.active_pane.get_selected_paths()
        zips = [p for p in paths if p.lower().endswith(".zip")]
        if not zips:
            return
        dest = self.active_pane.partner_pane.current_dir
        zip_dlg = ZipDialog(zips, dest, "unpack", self)
        zip_dlg.exec()
        self.left_tabs.currentWidget().refresh()
        self.right_tabs.currentWidget().refresh()

    def trigger_alt_enter(self):
        paths = self.active_pane.get_selected_paths()
        if paths:
            dialog = PropertiesDialog(paths[0], self)
            dialog.exec()

    def trigger_ctrl_d(self):
        dialog = HotlistDialog(self.active_pane.current_dir, self)
        if dialog.exec() == QDialog.DialogCode.Accepted and dialog.selected_path:
            self.active_pane.navigate(dialog.selected_path)

    def trigger_ctrl_m(self):
        paths = self.active_pane.get_selected_paths()
        if not paths:
            return
        dialog = MultiRenameDialog(paths, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.rename_log:
                self.undo_stack.append({
                    "type": "rename",
                    "rename_log": dialog.rename_log
                })
            self.left_tabs.currentWidget().refresh()
            self.right_tabs.currentWidget().refresh()

    def trigger_shift_f4(self):
        dialog = QInputDialog(self)
        dialog.setWindowTitle("GENERATE NODE")
        dialog.setLabelText(tr("create_file_prompt"))
        dialog.setStyleSheet("""
            QInputDialog {
                background-color: #0b0b0b;
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
                border: 1px solid #00ff00;
                font-family: 'Consolas', monospace;
            }
            QPushButton {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00ff00;
                padding: 4px 10px;
                font-family: 'Consolas', monospace;
            }
        """)
        if dialog.exec() == QInputDialog.DialogCode.Accepted:
            name = dialog.textValue().strip()
            if name:
                new_file = os.path.join(self.active_pane.current_dir, name)
                try:
                    with open(new_file, "w") as f:
                        pass
                    self.undo_stack.append({
                        "type": "create_file",
                        "path": new_file
                    })
                    self.active_pane.refresh()
                    editor = TextEditorDialog(new_file, self)
                    editor.exec()
                    self.active_pane.refresh()
                except Exception as e:
                    QMessageBox.critical(self, tr("sys_err"), f"{tr('error_occurred')}{str(e)}")

    def trigger_shift_f5(self):
        paths = self.active_pane.get_selected_paths()
        if not paths:
            return
        src = paths[0]
        dialog = QInputDialog(self)
        dialog.setWindowTitle("COPY LOCAL")
        dialog.setLabelText("Enter new name:")
        dialog.setTextValue(os.path.basename(src))
        dialog.setStyleSheet("""
            QInputDialog {
                background-color: #0b0b0b;
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
                border: 1px solid #00ff00;
                font-family: 'Consolas', monospace;
            }
            QPushButton {
                background-color: #111;
                color: #00ff00;
                border: 1px solid #00ff00;
                padding: 4px 10px;
                font-family: 'Consolas', monospace;
            }
        """)
        if dialog.exec() == QInputDialog.DialogCode.Accepted:
            new_name = dialog.textValue().strip()
            if new_name:
                dest = os.path.join(self.active_pane.current_dir, new_name)
                try:
                    if os.path.isdir(src):
                        shutil.copytree(src, dest)
                    else:
                        shutil.copy2(src, dest)
                    self.undo_stack.append({
                        "type": "copy",
                        "items": [dest]
                    })
                    self.active_pane.refresh()
                except Exception as e:
                    QMessageBox.critical(self, tr("sys_err"), f"{tr('error_occurred')}{str(e)}")

    def trigger_shift_delete(self):
        paths = self.active_pane.get_selected_paths()
        if not paths:
            return
        filenames = "\n".join([os.path.basename(p) for p in paths])
        confirm = QMessageBox.question(
            self,
            "SECURE PURGE",
            f"{tr('delete_confirm')}{filenames}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            for p in paths:
                try:
                    if os.path.isdir(p):
                        shutil.rmtree(p)
                    else:
                        os.remove(p)
                except Exception as e:
                    QMessageBox.critical(self, tr("sys_err"), f"{tr('error_occurred')}{str(e)}")
            self.active_pane.refresh()

    def trigger_undo(self):
        if not self.undo_stack:
            self.status_bar.showMessage("Undo stack empty.")
            return

        action = self.undo_stack.pop()
        action_type = action.get("type")

        try:
            if action_type == "copy":
                items = action.get("items", [])
                for item in items:
                    if os.path.exists(item):
                        if os.path.isdir(item):
                            shutil.rmtree(item)
                        else:
                            os.remove(item)
                self.status_bar.showMessage("Undo copy completed.")

            elif action_type == "move":
                mapping = action.get("mapping", {})
                for current_path, original_path in mapping.items():
                    if os.path.exists(current_path):
                        shutil.move(current_path, original_path)
                self.status_bar.showMessage("Undo move completed.")

            elif action_type == "mkdir":
                path = action.get("path")
                if os.path.exists(path) and os.path.isdir(path):
                    shutil.rmtree(path)
                self.status_bar.showMessage("Undo directory creation completed.")

            elif action_type == "create_file":
                path = action.get("path")
                if os.path.exists(path) and os.path.isfile(path):
                    os.remove(path)
                self.status_bar.showMessage("Undo create file completed.")

            elif action_type == "rename":
                rename_log = action.get("rename_log", [])
                for old_path, new_path in reversed(rename_log):
                    if os.path.exists(new_path):
                        os.rename(new_path, old_path)
                self.status_bar.showMessage("Undo rename completed.")

            self.left_tabs.currentWidget().refresh()
            self.right_tabs.currentWidget().refresh()
        except Exception as e:
            self.status_bar.showMessage(f"Undo failed: {str(e)}")

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CyberCommander()
    window.show()
    sys.exit(app.exec())
