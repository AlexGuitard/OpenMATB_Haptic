import subprocess
import sys
import threading

import pyglet.canvas
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import Signal, QObject, Slot, QThread
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtWidgets import QApplication, QMainWindow, QLabel
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
        self.response.setStyleSheet("margin-left:50px; margin-top: 7px")
        response_layout.addWidget(self.response)

        self.text_response = QLabel('')
        self.text_response.setFont(QFont("Helvetica", 35))
        response_layout.addWidget(self.text_response)

        response_value_layout.addLayout(response_layout)

        self.value = QLabel('Correct Answer :')
        self.value.setFont(QFont("Helvetica", 20))
        self.value.setStyleSheet("margin-top: 7px")
        value_layout.addWidget(self.value)

        self.text_value = QLabel('')
        self.text_value.setFont(QFont("Helvetica", 35))
        self.text_value.setStyleSheet("margin-left: 15px")
        value_layout.addWidget(self.text_value)

        response_value_layout.addLayout(value_layout)

        self.label_practice = QLabel('')
        self.label_practice.setFont(QFont("Helvetica", 25))
        self.label_practice.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)

        layout.addWidget(self.label_practice)
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
        self.label_practice.setVisible(False)

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
                self.text_response.setStyleSheet("margin-left: 15px; color: green;")
            else:
                self.text_response.setStyleSheet("margin-left: 15px; color: red;")

    def showHints(self):
        self.value.setVisible(True)
        self.text_value.setVisible(True)
        self.response.setVisible(True)
        self.text_response.setVisible(True)
        self.label_practice.setVisible(True)

    def hideHints(self):
        self.value.setVisible(False)
        self.text_value.setVisible(False)
        self.response.setVisible(False)
        self.text_response.setVisible(False)
        self.label_practice.setVisible(False)

    def clearValues(self):
        self.text_response.setText('')
        self.text_value.setText('')

    def init_practice_mode(self, address, *args):
        if address == '/condition':
            condition = args[0]
            location = args[1]
            if condition == 'practice':
                self.show_hints_signal.emit()
                self.label_practice.setText(condition + ' ' + 'on' + ' ' + location)
            else:
                self.hideHints()

    def minimize_window(self, address, *args):
        if address == "/minimize":
            minimize = args[0]
            if minimize:
                pyside_window.hide()
            else:
                pyside_window.show()

    def start_server(self):
        print("Starting Server OpenMATB-Tactilient")
        dispatcher = Dispatcher()
        dispatcher.map("/value", self.update_trial)
        dispatcher.map("/condition", self.init_practice_mode)
        dispatcher.map("/minimize", self.minimize_window)
        self.server = osc_server.ThreadingOSCUDPServer(("127.0.0.3", 5001), dispatcher)
        print("OpenMATB-Tactilient serving on {}".format(self.server.server_address))
        thread = threading.Thread(target=self.server.serve_forever)
        thread.start()

    def stop_server(self):
        print("Stopping Server OpenMATB-Tactilient")
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None
            print("Server OpenMATB-Tactilient stopped")
        else:
            print("Server is not running")


class SignalHandler(QObject):
    close_signal = Signal()
    window_closed = False

    @Slot()
    def close_window(self):
        if not self.window_closed:
            self.window_closed = True
            pyside_window.close()
            pyside_window.stop_server()
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


class ProcessThread(QThread):
    def run(self):
        process = subprocess.Popen(["python", "main.py"])
        process.wait()


if __name__ == "__main__":
    app = QApplication([])
    pyside_window = Tactilient()
    pyside_window.show()
    pyside_window.start_server()

    signal_handler = SignalHandler()
    process_thread = ProcessThread()

    signal_handler.close_signal.connect(pyside_window.stop_server)
    signal_handler.close_signal.connect(app.quit)
    signal_handler.close_signal.connect(process_thread.quit)
    signal_handler.close_signal.connect(process_thread.wait)
    
    process_thread.finished.connect(signal_handler.close_window)
    process_thread.start()

    sys.exit(app.exec())
