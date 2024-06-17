from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QDial, QFileDialog
from PyQt6.QtCore import QTimer, QThread, QDateTime
import pyqtgraph as pg
import sys, time, datetime, random, sqlite3, serial
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

        global currentTemps
        timeRecieved = None
        
        tempSerial = serial.Serial('/dev/ttyACM0', 9600, timeout=1)
        
        
        startTime = time.time()
        while self.isRunning():
                input = tempSerial.readline().decode('ascii')
                timeRecieved = time.time()
                elapsedTime = timeRecieved - startTime
                
                # converts data string into list of floats
                tempValuesStr = input.split(';')
                tempValuesStr.pop()
                
                currentTemps = {'tempA': float(tempValuesStr[0]), 
                                'tempB': float(tempValuesStr[1]), 
                                'tempC': float(tempValuesStr[2]), 
                                'tempD': float(tempValuesStr[3]), 
                                'tempE': float(tempValuesStr[4]), 
                                'tempF': float(tempValuesStr[5]), 
                                'tempG': float(tempValuesStr[6])}
                
                db.execute("INSERT INTO temp_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (timeRecieved, currentTemps['tempA'], currentTemps['tempB'], currentTemps['tempC'], currentTemps['tempD'], currentTemps['tempE'], currentTemps['tempF'], currentTemps['tempG']))
                db.commit()

                time.sleep(0.1)
                
class getChillerData(QThread):
    def run(self):
        global currentChillerValues
        
        chillerSerial = serial.Serial('/dev/ttyUSB0', 4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE, timeout=1, rtscts=True)
        lastUpdateTime = time.time() - .9 # makes loop run on first time
        while self.isRunning():
            if (time.time() > lastUpdateTime + 0.8):
                # get bath temp
                chillerSerial.write(bytes('in_pv_00\r', 'ascii'))
                currentChillerValues['bath_temp'] = float(chillerSerial.readline().decode('ascii'))
                
                # get pump pressure
                chillerSerial.write(bytes('in_pv_05\r', 'ascii'))
                currentChillerValues['pump_pres'] = float(chillerSerial.readline().decode('ascii'))
                
                # get temperature setpoint
                chillerSerial.write(bytes('in_sp_00\r', 'ascii'))
                currentChillerValues['temp_setpoint'] = float(chillerSerial.readline().decode('ascii'))

                lastUpdateTime = time.time()
                db.execute("INSERT INTO chiller_log(timestamp, bath_temp, pump_pres, temp_setpoint) VALUES (?, ?, ?, ?)", 
                           (lastUpdateTime, currentChillerValues['bath_temp'], currentChillerValues['pump_pres'], currentChillerValues['temp_setpoint']))
                db.commit()
                
            time.sleep(.1)

if __name__ == '__main__':
    
    dbPath = f'log{datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")}.db'
    
    db = sqlite3.connect(dbPath, check_same_thread=False)
    db.execute("CREATE TABLE temp_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG)")
    db.execute("CREATE TABLE chiller_log(timestamp, bath_temp, pump_pres, temp_setpoint)")
    
    # intilized data storage for live display
    currentTemps = {
        'tempA': 0.0,
        'tempB': 0.0,
        'tempC': 0.0,
        'tempD': 0.0,
        'tempE': 0.0,
        'tempF': 0.0,
        'tempG': 0.0,
    }
    
    currentChillerValues = {
        'bath_temp': 0.0,
        'pump_pres': 0.0,
        'temp_setpoint': 0.0
    }
    
    app = QApplication([])
    
    mainApp = mainApp()
    mainApp.show()
    
    sys.exit(app.exec())