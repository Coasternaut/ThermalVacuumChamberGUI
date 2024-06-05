from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QDial
from PyQt6.QtCore import QTimer, QThread
import pyqtgraph as pg
import sys, time, datetime, random
import numpy as np

class mainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("TVC-GUI-UI.ui", self)
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
        self.plotData()
        
    def plotData(self):
        self.presPlot.plot(self.elapsedTimeLog, self.presLog, pen="r")
        self.tempPlot.plot(self.elapsedTimeLog, self.tempLog, pen="b")
        
    def startLogging(self):
        self.getTempThread = getTemp()
        self.getTempThread.start()
    
    def stopLogging(self):
        print("stopping thread")
        self.getTempThread.quit()
        
class getTemp(QThread):
    def run(self):
        self.timeSent = None
        self.timeRecieved = None
        while self.isRunning:
            if (self.timeSent == None or time.time() - self.timeSent >= 1):
                self.timeSent = time.time()
                # TODO send request for temp packet
                
                # TEST
                randomFloat = random.uniform(0, 100)
                print(randomFloat)
                
                np.append(tempTimeLog, datetime.datetime.now())
                np.append(temp1Log, randomFloat)
                time.sleep(0.1)
        
    

if __name__ == '__main__':
    
    #numpy arrays to store data logs
    tempTimeLog = np.array([])
    temp1Log = np.array([])
    
    app = QApplication([])
    
    mainApp = mainApp()
    mainApp.show()
    
    sys.exit(app.exec())