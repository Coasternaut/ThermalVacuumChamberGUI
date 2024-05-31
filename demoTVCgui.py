from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QDial
import sys

class mainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("demoTVCgui.ui", self)
        self.presDial.actionTriggered.connect(self.setPres)
        self.tempDial.actionTriggered.connect(self.setTemp)
        
    def setPres(self):
        currentPres = self.presDial.value()
        self.currentPres.setText(str(currentPres))
        
    def setTemp(self):
        currentTemp = self.tempDial.value()
        self.currentTemp.setText(str(currentTemp))

if __name__ == '__main__':
    app = QApplication([])
    
    mainApp = mainApp()
    mainApp.show()
    
    sys.exit(app.exec())