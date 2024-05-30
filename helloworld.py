from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow
import sys

class window(QMainWindow):
    def __init__(self):
        super(window, self).__init__()
        self.setGeometry(100, 200, 400, 200)
        self.setWindowTitle("Hello World")
        self.initUI()
        
    
    def initUI(self):
        self.label = QtWidgets.QLabel(self)
        self.label.setText("Hello World")
        self.label.move(50, 50)

        self.b1 = QtWidgets.QPushButton(self)
        self.b1.setText("Click me")
        self.b1.clicked.connect(self.clicked)
        
    def clicked(self):
        self.label.setText("you pressed the button")
        self.update()
        
    def update(self):
        self.label.adjustSize()


def clicked():
    print("clicked")


def app():
    app = QApplication(sys.argv)
    win = window()

    win.show()
    sys.exit(app.exec_())
    
app()