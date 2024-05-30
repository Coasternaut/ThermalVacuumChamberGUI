from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow
import sys

def clicked():
    print("clicked")


def window():
    app = QApplication(sys.argv)
    win = QMainWindow()
    win.setGeometry(100, 200, 400, 200)
    win.setWindowTitle("Hello World")
    
    label = QtWidgets.QLabel(win)
    label.setText("Hello World")
    label.move(50, 50)
    
    b1 = QtWidgets.QPushButton(win)
    b1.setText("Click me")
    b1.clicked.connect(clicked)
    
    win.show()
    sys.exit(app.exec_())
    
window()