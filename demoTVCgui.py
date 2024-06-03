from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QDial
from PyQt6.QtCore import QTimer
import pyqtgraph as pg
import sys, datetime

import pandas as pd

class mainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("demoTVCgui.ui", self)
        self.presDial.actionTriggered.connect(self.setPres)
        self.tempDial.actionTriggered.connect(self.setTemp)
        self.startButton.pressed.connect(self.startLogging)
        self.stopButton.pressed.connect(self.stopLogging)
        
        self.log = pd.DataFrame({
            "Timestamp": [pd.Timestamp(datetime.datetime.now())],
            "Elapsed Time": 0,
            "Pres": 0,
            "Temp": 0
        })
        
        self.log.set_index("Timestamp")
        
        self.currentPres = 0
        self.currentTemp = 0
        self.elapsedTime = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.logData)
        
        self.refreshInterval = self.refreshBox.value()
        
    def setPres(self):
        self.currentPres = self.presDial.value()
        self.currentPresDisp.setText(str(self.currentPres))
        
    def setTemp(self):
        self.currentTemp = self.tempDial.value()
        self.currentTempDisp.setText(str(self.currentTemp))
        
    def logData(self):
        self.elapsedTime += self.refreshInterval
        self.elapsedTimeDisplay.setText(str(self.elapsedTime))
        
        newLog = pd.DataFrame({
            "Timestamp": pd.Timestamp(datetime.datetime.now()),
            "Elapsed Time": self.elapsedTime,
            "Pres": self.currentPres,
            "Temp": self.currentTemp
            })
        newLog.set_index("Timestamp")
        
        pd.concat([self.log, newLog])
        # self.presLog.append(self.currentPres)
        # self.tempLog.append(self.currentTemp)
        # self.plotData()
        
        print(self.log)
        
    def plotData(self):
        self.presPlot.plot(self.presLog, pen="r")
        self.tempPlot.plot(self.tempLog, pen="b")
        
    def startLogging(self):
        self.refreshInterval = self.refreshBox.value()
        self.timer.start(self.refreshInterval)
    
    def stopLogging(self):
        self.timer.stop()

if __name__ == '__main__':
    app = QApplication([])
    
    mainApp = mainApp()
    mainApp.show()
    
    sys.exit(app.exec())