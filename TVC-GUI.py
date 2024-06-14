from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QDial, QFileDialog
from PyQt6.QtCore import QTimer, QThread, QDateTime
import pyqtgraph as pg
import sys, time, datetime, random, sqlite3, serial
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
        self.displayTimeBox.currentTextChanged.connect(self.updateGraphRange)
        
        self.actionSave.triggered.connect(saveData)
        self.actionOpen.triggered.connect(self.openTempFile)
        
        self.elapsedTimeLog = []
        self.presLog = []
        self.tempLog = []
        
        self.currentPres = 0
        self.currentTemp = 0
        self.elapsedTime = 0
        
        self.dateTimeEditBegin.setDateTime(QDateTime.currentDateTime())
        self.dateTimeEditEnd.setDateTime(QDateTime.currentDateTime())

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
        global tempLog
        #self.presPlot.plot(self.elapsedTimeLog, self.presLog, pen="r")
        self.tempPlot.clear()
        self.tempPlot.setAxisItems(axisItems = {'bottom': pg.DateAxisItem()})
        # tempGraphTimestamps = []
        # for t in tempLog.index.values:
        #     print(type(t))
        self.tempPlot.plot(tempLog['timestamp'].values, tempLog['temp1'].values, pen="b")
        self.dateTimeEditEnd.setSecsSinceEpoch(tempLog.iloc[-1]['timestamp'])
        
        
    def startLogging(self):
        self.getTempThread.start()
        # self.updateGraphTimer.start()

    
    def stopLogging(self):
        print("stopping thread")
        self.getTempThread.quit()
        
    def openTempFile(self):
        global tempLog
        tempFile = QFileDialog.getOpenFileName(self, "Open CSV file", '', '*.csv')
        print(tempFile[0])
        tempLog = pd.read_csv(tempFile[0])
        self.plotData()
        
    def updateGraphRange(self):
        currentRange = self.displayTimeBox.currentIndex()
        print(currentRange)
        
        # Full time
        if (currentRange == 0):
            self.tempPlot.setXRange(0, tempLog['elapsedTime'].values)
            
        
class getTemp(QThread):
    def run(self):
        #global tempTimeLog
        #global temp1Log
        global tempLog
        timeSent = None
        timeRecieved = None
        
        tempSerial = serial.Serial('/dev/cu.usbmodem11301', 9600, timeout=1)
        
        
        startTime = time.time()
        while self.isRunning():
                input = tempSerial.readline().decode('ascii')
                
                # converts data string into list of floats
                tempValueStr = input.split(';')
                tempValueStr.pop()
                tempValues = [float(val) for val in tempValueStr]
                
                db.execute("INSERT INTO temp_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (time.time(), tempValues[0], tempValues[1], tempValues[2], tempValues[3], tempValues[4], tempValues[5], tempValues[6]))
                db.commit()
                
                
                elapsedTime = time.time() - startTime
                
                #tempTimeLog = np.append(tempTimeLog, time.time())
                #temp1Log = np.append(temp1Log, randomFloat)
                
                entry = pd.DataFrame({'timestamp': time.time(), 
                                      'tempA': tempValues[0], 
                                      'tempB': tempValues[1], 
                                      'tempC': tempValues[2], 
                                      'tempD': tempValues[3], 
                                      'tempE': tempValues[4], 
                                      'tempF': tempValues[5], 
                                      'tempG': tempValues[6]}, 
                                     index=[datetime.datetime.now()])
                #print(entry)
                if (tempLog.empty):
                    tempLog = entry
                else:
                    tempLog = pd.concat([tempLog, entry])
                    
                #saveData()
                
                #print(tempLog)
                time.sleep(0.1)
            
tempFileName = f"tempLog{datetime.datetime.now().strftime('%Y-%m-%d--%H-%M-%S')}.csv"
def saveData():
    tempLog.to_csv(tempFileName)
    
    

if __name__ == '__main__':
    
    #numpy arrays to store data logs
    #tempTimeLog = np.array([])
    #temp1Log = np.array([])
    
    tempLog = pd.DataFrame([])
    
    dbPath = f'log{datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")}.db'
    
    db = sqlite3.connect(dbPath, check_same_thread=False)
    db.execute("CREATE TABLE temp_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG)")
    
    app = QApplication([])
    
    mainApp = mainApp()
    mainApp.show()
    
    sys.exit(app.exec())