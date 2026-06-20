import os
import sys
import random
from PyQt6.QtCore import QProcess, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit, QLineEdit, QLabel
from translator import tr

class CyberTerminal(QWidget):
    command_executed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None
        self.simulation_timer = None
        self.sim_lines = []
        self.sim_index = 0
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        self.setStyleSheet("""
            QWidget {
                background-color: #050505;
                border-top: 2px solid #00ff00;
            }
            QPlainTextEdit {
                background-color: #030303;
                color: #00ff00;
                border: none;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
            }
            QLineEdit {
                background-color: #030303;
                color: #00ffff;
                border: 1px solid #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                padding: 4px;
            }
            QLabel {
                color: #00ff00;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                border: none;
            }
        """)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)

        input_layout = QHBoxLayout()
        self.prompt_lbl = QLabel(tr("prompt_lbl"))
        input_layout.addWidget(self.prompt_lbl)

        self.input_line = QLineEdit()
        self.input_line.returnPressed.connect(self.execute_command)
        input_layout.addWidget(self.input_line)
        layout.addLayout(input_layout)

        self.print_welcome()

    def print_welcome(self):
        self.console.appendPlainText(tr("welcome_terminal"))

    def execute_command(self):
        cmd = self.input_line.text().strip()
        self.input_line.clear()
        if not cmd:
            return

        self.console.appendPlainText(f"\n{tr('prompt_lbl')} {cmd}")
        self.command_executed.emit(cmd)

        parts = cmd.split()
        base_cmd = parts[0].lower()

        if base_cmd == "help":
            self.show_help()
        elif base_cmd == "clear":
            self.console.clear()
        elif base_cmd == "matrix":
            self.run_matrix_simulation()
        elif base_cmd == "scan":
            self.run_port_scan()
        elif base_cmd == "decrypt":
            target = parts[1] if len(parts) > 1 else "SYSTEM_LOG"
            self.run_decryption_simulation(target)
        else:
            self.run_system_command(cmd)

    def show_help(self):
        self.console.appendPlainText(tr("help_txt"))

    def run_matrix_simulation(self):
        self.sim_lines = []
        for _ in range(50):
            line = "".join(random.choice("0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ@#$%&*()+-=") for _ in range(60))
            self.sim_lines.append(line)
        self.sim_index = 0
        
        self.simulation_timer = QTimer(self)
        self.simulation_timer.timeout.connect(self.print_matrix_step)
        self.simulation_timer.start(50)

    def print_matrix_step(self):
        if self.sim_index < len(self.sim_lines):
            self.console.appendPlainText(self.sim_lines[self.sim_index])
            self.sim_index += 1
        else:
            self.simulation_timer.stop()
            self.console.appendPlainText(tr("matrix_done"))

    def run_port_scan(self):
        self.sim_lines = [
            "CONNECTING TO NETWORK HUB...",
            "RESOLVING HOSTS IN THE SECURE SUBNET...",
        ]
        for ip in range(1, 10):
            ip_str = f"192.168.1.{random.randint(1, 254)}"
            self.sim_lines.append(f"TARGET IP: {ip_str} - TESTING PORTS...")
            for port in [21, 22, 80, 443, 8080]:
                status = "OPEN" if random.random() > 0.7 else "CLOSED"
                self.sim_lines.append(f"  PORT {port:<5} : {status}")
        self.sim_lines.append(tr("scan_done"))
        self.sim_index = 0

        self.simulation_timer = QTimer(self)
        self.simulation_timer.timeout.connect(self.print_generic_simulation_step)
        self.simulation_timer.start(100)

    def run_decryption_simulation(self, target):
        self.sim_lines = [
            f"ACCESSING KEYSTORE FOR: {target}...",
            "RUNNING BRUTEFORCE CRYPTO ATTACK [SEED: 0x9F4E5A]..."
        ]
        for percent in range(0, 101, 10):
            hash_str = f"MD5: {random.randint(100000,999999):08X}"
            self.sim_lines.append(f"  [ATTEMPT] Progress: {percent:>3}% | {hash_str}")
        self.sim_lines.append(tr("decrypt_done"))
        self.sim_lines.append(f"SUCCESS: Decrypted {target} to raw output stream.")
        self.sim_index = 0

        self.simulation_timer = QTimer(self)
        self.simulation_timer.timeout.connect(self.print_generic_simulation_step)
        self.simulation_timer.start(150)

    def print_generic_simulation_step(self):
        if self.sim_index < len(self.sim_lines):
            self.console.appendPlainText(self.sim_lines[self.sim_index])
            self.sim_index += 1
        else:
            self.simulation_timer.stop()

    def run_system_command(self, cmd):
        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.finished.connect(self.handle_finished)

        if sys.platform == "win32":
            self.process.start("cmd.exe", ["/c", cmd])
        else:
            self.process.start("/bin/sh", ["-c", cmd])

    def handle_stdout(self):
        data = self.process.readAllStandardOutput()
        stdout = bytes(data).decode("utf-8", errors="replace")
        self.console.appendPlainText(stdout.strip())

    def handle_finished(self):
        self.process = None
