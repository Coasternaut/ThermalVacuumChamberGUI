from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtCore import QTimer, QThread, QDateTime
import pyqtgraph as pg
import sys, time, datetime, sqlite3, serial
from dataclasses import dataclass

class mainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("TVC-GUI-UI.ui", self)

        self.startButton.pressed.connect(self.startLogging)
        self.stopButton.pressed.connect(self.stopLogging)
        self.displayTimeBox.currentTextChanged.connect(self.updateUI)
        
        # self.actionSave.triggered.connect(saveData) TODO implement export function
        self.actionOpen.triggered.connect(self.openDatabaseFile)
        
        self.dateTimeEditBegin.setDateTime(QDateTime.currentDateTime())
        self.dateTimeEditEnd.setDateTime(QDateTime.currentDateTime())

        self.updateUITimer = QTimer(self)
        self.updateUITimer.setInterval(1000)
        self.updateUITimer.timeout.connect(self.updateUI)
        
        self.getTempThread = getTemp()
        self.getChillerDataThread = getChillerData()
        
        global tempChannels 
        tempChannels = [dataChannel('tempA', 'temp_log', 'Temp Sensor A', 0.0, self.tempAPlot, self.tempALabel, self.tempAValue),
                        dataChannel('tempB', 'temp_log', 'Temp Sensor B', 0.0, self.tempBPlot, self.tempBLabel, self.tempBValue),
                        dataChannel('tempC', 'temp_log', 'Temp Sensor C', 0.0, self.tempCPlot, self.tempCLabel, self.tempCValue),
                        dataChannel('tempD', 'temp_log', 'Temp Sensor D', 0.0, self.tempDPlot, self.tempDLabel, self.tempDValue),
                        dataChannel('tempE', 'temp_log', 'Temp Sensor E', 0.0, self.tempEPlot, self.tempELabel, self.tempEValue),
                        dataChannel('tempF', 'temp_log', 'Temp Sensor F', 0.0, self.tempFPlot, self.tempFLabel, self.tempFValue),
                        dataChannel('tempG', 'temp_log', 'Temp Sensor G', 0.0, self.tempGPlot, self.tempGLabel, self.tempGValue)]
        
        # initializes graphs
        for channel in tempChannels:
            channel.plot.setAxisItems(axisItems = {'bottom': pg.DateAxisItem()})

        self.chillerTempPlot.setAxisItems(axisItems = {'bottom': pg.DateAxisItem()})


    def updateUI(self):
         # calculates the time range displayed on the graphs TODO implement
         
        currentRangeSelection = self.displayTimeBox.currentIndex()
        
        # Full time
        if (currentRangeSelection == 0):
            endGraphTimestamp = 2**32 # a really big number
            beginGraphTimestamp = 0
        # last 30 mins
        elif (currentRangeSelection == 1):
            endGraphTimestamp = time.time()
            beginGraphTimestamp = time.time() - (30 * 60) 
        
        cur = db.cursor()
        cur.row_factory = lambda cursor, row: row[0]

        
        #plots temperatures
        cur.execute("SELECT timestamp FROM temp_log WHERE timestamp BETWEEN ? AND ?", (beginGraphTimestamp, endGraphTimestamp))
        tempTimestamps = cur.fetchall()
        
        for channel in tempChannels:
            cur.execute(f"SELECT {channel.dbName} FROM {channel.dbTable} WHERE timestamp BETWEEN ? AND ?", (beginGraphTimestamp, endGraphTimestamp)) # TODO replace fstring
            tempValues = cur.fetchall()
        
            channel.plot.clear()
            channel.plot.plot(tempTimestamps, tempValues, pen="r")
            
            channel.currentValueDisplay.setText(f'{channel.currentValue} C')
            
        # plots chiller temperature
        
        cur.execute("SELECT timestamp FROM chiller_log WHERE timestamp BETWEEN ? AND ?", (beginGraphTimestamp, endGraphTimestamp))
        chillerTimestamps = cur.fetchall()
        
        cur.execute("SELECT bath_temp FROM chiller_log WHERE timestamp BETWEEN ? AND ?", (beginGraphTimestamp, endGraphTimestamp))
        chillerBathTemps = cur.fetchall()
        
        cur.execute("SELECT temp_setpoint FROM chiller_log WHERE timestamp BETWEEN ? AND ?", (beginGraphTimestamp, endGraphTimestamp))
        chillerSetpointTemps = cur.fetchall()
        
        self.chillerTempPlot.clear()
    
        self.chillerTempPlot.plot(chillerTimestamps, chillerBathTemps, pen="r")
        self.chillerTempPlot.plot(chillerTimestamps, chillerSetpointTemps, pen="g")
        
        #updates end display time
        self.dateTimeEditBegin.setDateTime(QDateTimeFromTimestamp(tempTimestamps[0]))
        self.dateTimeEditEnd.setDateTime(QDateTimeFromTimestamp(tempTimestamps[-1]))
        
        
    # starts logging and graphing data
    def startLogging(self):
        global db
        
        openDB() # creates new database file
        
        db.execute("CREATE TABLE temp_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG)")
        db.execute("CREATE TABLE chiller_log(timestamp, bath_temp, pump_pres, temp_setpoint)")
        
        # starts threads to gather data and timer to refresh UI
        self.getTempThread.start()
        self.getChillerDataThread.start()
        self.updateUITimer.start()

    # stops logging data TODO make thread stop
    def stopLogging(self):
        print("stopping thread")
        self.getTempThread.quit()
        
    # imports stored data from a database file
    def openDatabaseFile(self): 
        openFilePath = QFileDialog.getOpenFileName(self, "Open Database file", '', '*.db')
        openDB(openFilePath)
        
        self.updateUI()
        
            
# Converts a epoch timestamp (float) to a QDateTime object
def QDateTimeFromTimestamp(timestamp):
    dt = QDateTime(0,0,0,0,0) # placeholder
    dt.setSecsSinceEpoch(round(timestamp))
    return dt
        
# gets temperature data from Arduino via USB serial and saves it to a database and dataframe to graph from
class getTemp(QThread):
    def run(self):

        global tempChannels
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
                
                for i in range(len(tempValuesStr)):
                    tempChannels[i].currentValue = float(tempValuesStr[i])
                
                db.execute("INSERT INTO temp_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                           (timeRecieved,
                            tempChannels[0].currentValue,
                            tempChannels[1].currentValue,
                            tempChannels[2].currentValue,
                            tempChannels[3].currentValue,
                            tempChannels[4].currentValue,
                            tempChannels[5].currentValue,
                            tempChannels[6].currentValue))
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
            
@dataclass       
class dataChannel:
    dbName: str
    dbTable: str
    label: str
    currentValue: float = 0.0
    plot: any = None
    labelDisplay: any = None
    currentValueDisplay: any = None
    
def openDB(filepath=f'logs/log{datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")}.db'):
    global db
    
    # closes database if one currently is open
    if (isDBOpen()):
        db.close()
        
    db = sqlite3.connect(filepath, check_same_thread=False)
    
# returns true if a database file is open, false otherwise
def isDBOpen():
    global db
    try:
        if (db):
            return True
        else:
            return False
    except NameError:
        return False


if __name__ == '__main__':
    
    currentChillerValues = {
        'bath_temp': 0.0,
        'pump_pres': 0.0,
        'temp_setpoint': 0.0
    }
    
    app = QApplication([])
    
    mainApp = mainApp()
    mainApp.show()
    
    sys.exit(app.exec())