from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QDial
import pyqtgraph as pg
import sys

class mainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("demoTVCgui.ui", self)
        self.presDial.actionTriggered.connect(self.setPres)
        self.tempDial.actionTriggered.connect(self.setTemp)
        self.logButton.pressed.connect(self.logData)
        
        self.presLog = []
        self.tempLog = []
        
        self.currentPres = 0
        self.currentTemp = 0
        
    def setPres(self):
        self.currentPres = self.presDial.value()
        self.currentPresDisp.setText(str(self.currentPres))
        
    def setTemp(self):
        self.currentTemp = self.tempDial.value()
        self.currentTempDisp.setText(str(self.currentTemp))
        
    def logData(self):
        self.presLog.append(self.currentPres)
        self.tempLog.append(self.currentTemp)
        self.plotData()
        
    def plotData(self):
        self.presPlot.plot(self.presLog, pen="r")
        self.tempPlot.plot(self.tempLog, pen="b")

if __name__ == '__main__':
    app = QApplication([])
    
    mainApp = mainApp()
    mainApp.show()
    
    sys.exit(app.exec())