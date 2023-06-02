import subprocess
import sys
import threading

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import Signal, QObject, Slot, QThread
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel, QGridLayout
from pythonosc import osc_server
from pythonosc.dispatcher import Dispatcher

file = "./includes/img/Stimulus_Sansfond.png"


class Tactilient(QMainWindow):

    show_hints_signal = QtCore.Signal()

    def __init__(self):
        super(Tactilient, self).__init__()

        self.pixmap = QPixmap(file)
        self.pixmap = self.pixmap.scaled(780, 320)

        layout = QtWidgets.QVBoxLayout()
        self.label = QLabel(self)
        self.label.setPixmap(self.pixmap)
        self.setStyleSheet("background-color: #f0f0f0;")
        self.label.setStyleSheet("margin-top: 10px;margin-left: 5px;")
        self.label.setAlignment(QtCore.Qt.AlignTop)
        layout.addWidget(self.label)

        response_value_layout = QtWidgets.QHBoxLayout()
        response_layout = QtWidgets.QHBoxLayout()
        value_layout = QtWidgets.QHBoxLayout()

        self.response = QLabel('Your Answer :')
        self.response.setFont(QFont("Helvetica", 20))
        self.response.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom)
        self.response.setStyleSheet("margin-bottom: 30px")
        response_layout.addWidget(self.response)

        self.text_response = QLabel('')
        self.text_response.setFont(QFont("Helvetica", 40))
        self.text_response.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom)
        self.text_response.setStyleSheet("margin-bottom: 17px")
        response_layout.addWidget(self.text_response)

        response_value_layout.addLayout(response_layout)

        self.value = QLabel('Correct Answer :')
        self.value.setFont(QFont("Helvetica", 20))
        self.value.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom)
        self.value.setStyleSheet("margin-bottom: 30px")
        value_layout.addWidget(self.value)

        self.text_value = QLabel('')
        self.text_value.setFont(QFont("Helvetica", 40))
        self.text_value.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignBottom)
        self.text_value.setStyleSheet("margin-bottom: 17px")
        value_layout.addWidget(self.text_value)

        response_value_layout.addLayout(value_layout)

        #space_between_labels = QtWidgets.QSpacerItem(100, 20, QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Minimum)
        #response_value_layout.addItem(space_between_labels)

        layout.addLayout(response_value_layout)
        container = QtWidgets.QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.resize(803, 486)
        self.move(0, 54)
        self.setCursor(QtCore.Qt.BlankCursor)
        self.setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False)
        self.setWindowFlag(QtCore.Qt.WindowMaximizeButtonHint, False)
        self.setWindowFlag(QtCore.Qt.WindowMinimizeButtonHint, False)
        self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint | QtCore.Qt.FramelessWindowHint)

        self.value.setVisible(False)
        self.text_value.setVisible(False)
        self.response.setVisible(False)
        self.text_response.setVisible(False)

        self.server = None

        self.show_hints_signal.connect(self.showHints)

    def update_trial(self, address, *args):
        if address == "/value":
            value = str(args[0])
            response = args[1]
            if response == -1:
                response = '?'
            else:
                response = str(response)

            self.text_value.setText(value)
            self.text_response.setText(response)

            if response == value:
                self.text_response.setStyleSheet("margin-bottom: 17px; color: green;")
            else:
                self.text_response.setStyleSheet("margin-bottom: 17px; color: red;")

    def showHints(self):
        self.value.setVisible(True)
        self.text_value.setVisible(True)
        self.response.setVisible(True)
        self.text_response.setVisible(True)

    def hideHints(self):
        self.value.setVisible(False)
        self.text_value.setVisible(False)
        self.response.setVisible(False)
        self.text_response.setVisible(False)

    def clearValues(self):
        self.text_response.setText('')
        self.text_value.setText('')

    def init_practice_mode(self, address, *args):
        if address == '/condition':
            condition = args[0]
            print(condition)
            if condition == 'practice':
                self.show_hints_signal.emit()
            else:
                self.hideHints()

    def start_server(self):
        print("Starting Server")
        dispatcher = Dispatcher()
        dispatcher.map("/value", self.update_trial)
        dispatcher.map("/condition", self.init_practice_mode)
        self.server = osc_server.ThreadingOSCUDPServer(("127.0.0.3", 5001), dispatcher)
        print("Serving on {}".format(self.server.server_address))
        thread = threading.Thread(target=self.server.serve_forever)
        thread.start()

    def stop_server(self):
        print("Stopping Server")
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            print("Server stopped")
        else:
            print("Server is not running")


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


app = QApplication([])
pyside_window = Tactilient()
pyside_window.show()
pyside_window.start_server()

signal_handler = SignalHandler()
process_watcher = ProcessWatcher()
signal_handler.close_signal.connect(signal_handler.close_window)
process_watcher.process_finished.connect(signal_handler.close_window)

process_watcher_thread = QThread()
process_watcher.moveToThread(process_watcher_thread)
process_watcher_thread.started.connect(process_watcher.start_process)
process_watcher_thread.start()

app.aboutToQuit.connect(signal_handler.close_window)

sys.exit(app.exec())
