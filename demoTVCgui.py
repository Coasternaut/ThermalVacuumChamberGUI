from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QDial
from PyQt6.QtCore import QTimer
import pyqtgraph as pg
import sys, sqlite3

class mainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("demoTVCgui.ui", self)
        self.presDial.actionTriggered.connect(self.setPres)
        self.tempDial.actionTriggered.connect(self.setTemp)
        self.startButton.pressed.connect(self.startLogging)
        self.stopButton.pressed.connect(self.stopLogging)
        
        self.elapsedTimeLog = []
        self.presLog = []
        self.tempLog = []
        
        self.currentPres = 0
        self.currentTemp = 0
        self.elapsedTime = 0
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.logData)
        
        self.refreshInterval = self.refreshBox.value()
        
        self.db = sqlite3.connect("log.db")
        self.cursor = self.db.cursor()
        
        self.cursor.execute("CREATE TABLE log(elapsed, pres, temp)")
        
    def setPres(self):
        self.currentPres = self.presDial.value()
        self.currentPresDisp.setText(str(self.currentPres))
        
    def setTemp(self):
        self.currentTemp = self.tempDial.value()
        self.currentTempDisp.setText(str(self.currentTemp))
        
    def logData(self):
        self.elapsedTime = round((self.refreshInterval / 1000.0) + self.elapsedTime, 3)
        self.elapsedTimeDisplay.setText(str(self.elapsedTime))
        
        self.elapsedTimeLog.append(self.elapsedTime)
        self.presLog.append(self.currentPres)
        self.tempLog.append(self.currentTemp)
        
        self.cursor.execute("INSERT INTO log(elapsed, pres, temp) VALUES (?, ?, ?)", (self.elapsedTime, self.currentPres, self.currentTemp))
        self.db.commit()
        
        self.plotData()
        
    def plotData(self):
        self.presPlot.plot(self.elapsedTimeLog, self.presLog, pen="r")
        self.tempPlot.plot(self.elapsedTimeLog, self.tempLog, pen="b")
        
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