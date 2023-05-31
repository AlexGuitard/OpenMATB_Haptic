import subprocess
import sys
import win32con
import win32gui
import  os

from PySide6 import QtCore, QtGui
from PySide6.QtCore import QDir, Signal, QObject, Slot, QThread
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
from PySide6.QtMultimedia import QMediaDevices


class SignalHandler(QObject):
    close_signal = Signal()

    @Slot()
    def close_window(self):
        pyside_window.close()
        app.quit()


class ProcessWatcher(QObject):
    process_finished = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.process = None

    @Slot()
    def start_process(self):
        self.process = subprocess.Popen(["python", "main.py"])
        self.process.wait()
        self.process_finished.emit()

print(os.getcwd())

app = QApplication([])

pyside_window = QMainWindow()
pyside_window.setWindowTitle("Test")

pixmap = QPixmap('/includes/img/stimulus_sheet.png')
#pixmap = pixmap.scaled(100, 100)
if not pixmap.isNull():
    label = QLabel(pyside_window)
    label.setPixmap(pixmap)
else:
    print("Impossible de charger l'image")

pyside_window.setCentralWidget(label)
#pyside_window.setWindowFlags(Qt.FramelessWindowHint)
pyside_window.resize(800, 455)
pyside_window.move(0, 54)

pyside_window.show()

signal_handler = SignalHandler()
process_watcher = ProcessWatcher()
signal_handler.close_signal.connect(signal_handler.close_window)
process_watcher.process_finished.connect(signal_handler.close_window)

process_watcher_thread = QThread()
process_watcher.moveToThread(process_watcher_thread)
process_watcher_thread.started.connect(process_watcher.start_process)
process_watcher_thread.start()

# Récupérer le handle de la fenêtre PySide6
hwnd = pyside_window.winId()

# Modifier le style de la fenêtre pour la maintenir au premier plan
win32gui.SetWindowPos(hwnd, win32con.HWND_TOPMOST, 0, 0, 0, 0, win32con.SWP_NOMOVE | win32con.SWP_NOSIZE)

app.aboutToQuit.connect(signal_handler.close_window)

sys.exit(app.exec())
