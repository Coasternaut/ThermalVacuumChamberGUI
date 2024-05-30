from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox
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
        msg = QMessageBox()
        msg.setWindowTitle("message")
        msg.setText("the message")
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Cancel|QMessageBox.Retry|QMessageBox.Ignore)
        msg.setDefaultButton(QMessageBox.Ignore)
        msg.setInformativeText("more info text")
        
        msg.setDetailedText("more detailed text")
        
        msg.buttonClicked.connect(self.popupButton)
        
        popup = msg.exec_()
        
    def popupButton(self, button):
        print(button.text())
            
        
        
    def update(self):
        self.label.adjustSize()


def app():
    app = QApplication(sys.argv)
    win = window()

    win.show()
    sys.exit(app.exec_())
    
app()