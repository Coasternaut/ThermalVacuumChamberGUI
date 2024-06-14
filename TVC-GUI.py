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

        self.startButton.pressed.connect(self.startLogging)
        self.stopButton.pressed.connect(self.stopLogging)
        self.displayTimeBox.currentTextChanged.connect(self.updateGraphRange)
        
        # self.actionSave.triggered.connect(saveData) TODO implement export function
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
        self.getChillerDataThread = getChillerData()

        
    def plotData(self):
        global tempLog

        #plots tempA
        self.tempPlot.clear()
        self.tempPlot.setAxisItems(axisItems = {'bottom': pg.DateAxisItem()})
        self.tempPlot.plot(tempLog['timestamp'].values, tempLog['tempA'].values, pen="b")
        
        #updates end display time
        self.dateTimeEditEnd.setSecsSinceEpoch(tempLog.iloc[-1]['timestamp'])
        
        
    # starts logging and graphing data
    def startLogging(self):
        self.getTempThread.start()
        self.getChillerDataThread.start()
        self.updateGraphTimer.start()

    # stops logging data TODO make thread stop
    def stopLogging(self):
        print("stopping thread")
        self.getTempThread.quit()
        
    # imports temperature data from file
    def openTempFile(self):
        global tempLog
        tempFile = QFileDialog.getOpenFileName(self, "Open CSV file", '', '*.csv')
        print(tempFile[0])
        tempLog = pd.read_csv(tempFile[0])
        self.plotData()
        
    # updates the time range displayed on the graphs TODO implement
    def updateGraphRange(self):
        currentRange = self.displayTimeBox.currentIndex()
        print(currentRange)
        
        # Full time
        if (currentRange == 0):
            self.tempPlot.setXRange(0, tempLog['elapsedTime'].values)
            
        
# gets temperature data from Arduino via USB serial and saves it to a database and dataframe to graph from
class getTemp(QThread):
    def run(self):

        global tempLog
        timeRecieved = None
        
        tempSerial = serial.Serial('/dev/cu.usbmodem11301', 9600, timeout=1)
        
        
        startTime = time.time()
        while self.isRunning():
                input = tempSerial.readline().decode('ascii')
                timeRecieved = time.time()
                elapsedTime = timeRecieved - startTime
                
                # converts data string into list of floats
                tempValueStr = input.split(';')
                tempValueStr.pop()
                tempValues = [float(val) for val in tempValueStr]
                
                db.execute("INSERT INTO temp_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (timeRecieved, tempValues[0], tempValues[1], tempValues[2], tempValues[3], tempValues[4], tempValues[5], tempValues[6]))
                db.commit()
                
                
                entry = pd.DataFrame({'timestamp': timeRecieved, 
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

                time.sleep(0.1)
                
class getChillerData(QThread):
    def run(self):
        chillerSerial = serial.Serial('/dev/ttyUSB0', 4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE, timeout=1, rtscts=True)
        while self.isRunning():
            # get bath temp
            chillerSerial.write(bytes('in_pv_00\r', 'ascii'))
            bathTemp = float(chillerSerial.readline().decode('ascii'))
            
            # get pump pressure
            chillerSerial.write(bytes('in_pv_05\r', 'ascii'))
            pumpPres = float(chillerSerial.readline().decode('ascii'))
            
            # get temperature setpoint
            chillerSerial.write(bytes('in_sp_00\r', 'ascii'))
            setpoint = float(chillerSerial.readline().decode('ascii'))
            
            db.execute("INSERT INTO chiller_log(timestamp, bath_temp, pump_pres, setpoint) VALUES (?, ?, ?, ?)", (time.time(), bathTemp, pumpPres, setpoint))
            db.commit()
            
            time.sleep(1)

if __name__ == '__main__':
    
    #numpy arrays to store data logs
    #tempTimeLog = np.array([])
    #temp1Log = np.array([])
    
    tempLog = pd.DataFrame([])
    
    dbPath = f'log{datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")}.db'
    
    db = sqlite3.connect(dbPath, check_same_thread=False)
    db.execute("CREATE TABLE temp_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG)")
    db.execute("CREATE TABLE chiller_log(timestamp, bath_temp, pump_pres, setpoint)")
    
    app = QApplication([])
    
    mainApp = mainApp()
    mainApp.show()
    
    sys.exit(app.exec())