from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QDial
from PyQt6.QtCore import QTimer, QThread
import pyqtgraph as pg
import sys, time, datetime, random
#import numpy as np
import pandas as pd

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
        
        self.updateGraphTimer = QTimer(self)
        self.updateGraphTimer.setInterval(1000)
        self.updateGraphTimer.timeout.connect(self.plotData)
        
        self.getTempThread = getTemp()
        
        #self.refreshInterval = self.refreshBox.value()
        
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
        #self.presPlot.plot(self.elapsedTimeLog, self.presLog, pen="r")
        self.tempPlot.clear()
        #self.tempPlot.setAxisItems(axisItems = {'bottom': pg.DateAxisItem()})
        # tempGraphTimestamps = []
        # for t in tempLog.index.values:
        #     print(type(t))
        self.tempPlot.plot(tempLog['elapsedTime'].values, tempLog['temp1'].values, pen="b")
        
    def startLogging(self):
        self.getTempThread.start()
        self.updateGraphTimer.start()

    
    def stopLogging(self):
        print("stopping thread")
        self.getTempThread.quit()
        
class getTemp(QThread):
    def run(self):
        #global tempTimeLog
        #global temp1Log
        global tempLog
        timeSent = None
        timeRecieved = None
        
        startTime = time.time()
        while self.isRunning():
            if (timeSent == None or time.time() - timeSent >= 1):
                timeSent = time.time()
                # TODO send request for temp packet
                
                # TEST
                randomFloat = random.uniform(0, 100)
                randomFloat2 = random.uniform(100, 200)
                elapsedTime = time.time() - startTime
                
                #tempTimeLog = np.append(tempTimeLog, time.time())
                #temp1Log = np.append(temp1Log, randomFloat)
                
                entry = pd.DataFrame({'elapsedTime': elapsedTime, 'temp1': randomFloat, 'temp2': randomFloat2}, index=[datetime.datetime.now().time])
                #print(entry)
                if (tempLog.empty):
                    tempLog = entry
                else:
                    tempLog = pd.concat([tempLog, entry])
                
                #print(tempLog)
                time.sleep(0.1)
        
            
    

if __name__ == '__main__':
    
    #numpy arrays to store data logs
    #tempTimeLog = np.array([])
    #temp1Log = np.array([])
    
    tempLog = pd.DataFrame([])
    
    app = QApplication([])
    
    mainApp = mainApp()
    mainApp.show()
    
    sys.exit(app.exec())