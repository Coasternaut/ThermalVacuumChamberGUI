from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtCore import QTimer, QThread, QDateTime
import pyqtgraph as pg
import sys, time, datetime, sqlite3
import serial, serial.serialutil, serial.tools, serial.tools.list_ports
from dataclasses import dataclass
import pandas as pd

class mainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("TVC-GUI-UI.ui", self)

        self.startButton.pressed.connect(self.startLogging)
        self.stopButton.pressed.connect(self.stopLogging)
        self.displayTimeBox.currentTextChanged.connect(self.updateTimeRangeMode)
        
        self.renameButton.pressed.connect(self.saveLabels)
        
        self.actionSave.triggered.connect(self.exportData)
        self.actionOpen.triggered.connect(self.openDatabaseFile)
        
        # self.dateTimeEditBegin.setDateTime(QDateTime.currentDateTime())
        # self.dateTimeEditEnd.setDateTime(QDateTime.currentDateTime())
        
        self.updateUITimer = QTimer(self)
        self.updateUITimer.setInterval(1000)
        self.updateUITimer.timeout.connect(self.updateUI)
        
        self.currentMode = 'live'
        
        global tempChannels 
        tempChannels = [dataChannel('tempA', 'temp_log', 'Temp Sensor A', 0.0, self.tempAPlot, self.tempALabel, self.tempAValue, self.tempARename),
                        dataChannel('tempB', 'temp_log', 'Temp Sensor B', 0.0, self.tempBPlot, self.tempBLabel, self.tempBValue, self.tempBRename),
                        dataChannel('tempC', 'temp_log', 'Temp Sensor C', 0.0, self.tempCPlot, self.tempCLabel, self.tempCValue, self.tempCRename),
                        dataChannel('tempD', 'temp_log', 'Temp Sensor D', 0.0, self.tempDPlot, self.tempDLabel, self.tempDValue, self.tempDRename),
                        dataChannel('tempE', 'temp_log', 'Temp Sensor E', 0.0, self.tempEPlot, self.tempELabel, self.tempEValue, self.tempERename),
                        dataChannel('tempF', 'temp_log', 'Temp Sensor F', 0.0, self.tempFPlot, self.tempFLabel, self.tempFValue, self.tempFRename),
                        dataChannel('tempG', 'temp_log', 'Temp Sensor G', 0.0, self.tempGPlot, self.tempGLabel, self.tempGValue, self.tempGRename)]
        
        # initializes graphs
        for channel in tempChannels:
            channel.plot.setAxisItems(axisItems = {'bottom': pg.DateAxisItem()})

        self.chillerTempPlot.setAxisItems(axisItems = {'bottom': pg.DateAxisItem()})
        
        self.timeRangeMode = 'hours'
        self.serialDevices  = {
            'temp': serialDevice('D12A5A1851544B5933202020FF080B15', serial.Serial(None, 9600, timeout=1)),
            'chiller': serialDevice('AL066BK6', serial.Serial(None, 4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE, timeout=1, rtscts=True))
        }

        # reads from each device to initialize COM port
        for device in self.serialDevices.values():
            getSerialData(device)

    # main loop to update 
    def updateUI(self):
        self.getNewData()
        self.updateValueDisplays()
        self.updateTimeRanges()
        self.updatePlots()

    def getNewData(self):
        timestamp = time.time()
        # gets temp data
        tempData = getSerialData(self.serialDevices['temp'])
        
        # if temp data exists
        if tempData:
            # converts data string into list of floats
            tempValuesStr = tempData.split(';')
            tempValuesStr.pop()
            
            for i in range(len(tempValuesStr)):
                tempChannels[i].currentValue = safeFloat(tempValuesStr[i])
        else:
            for channel in tempChannels:
                channel.currentValue = None
        
        # get bath temp
        if writeSerialData(self.serialDevices['chiller'],'in_pv_00\r'):
            bathTempInput = getSerialData(self.serialDevices['chiller'])
            currentChillerValues['bath_temp'] = safeFloat(bathTempInput)
        else:
            currentChillerValues['bath_temp'] = None
        
        # get pump pressure
        if writeSerialData(self.serialDevices['chiller'],'in_pv_05\r'):
            pumpPressureInput = getSerialData(self.serialDevices['chiller'])
            currentChillerValues['pump_pres'] = safeFloat(pumpPressureInput)
        else:
            currentChillerValues['pump_pres'] = None
        
        # get temperature setpoint
        if writeSerialData(self.serialDevices['chiller'],'in_sp_00\r'):
            tempSetpointInput = getSerialData(self.serialDevices['chiller'])
            currentChillerValues['temp_setpoint'] = safeFloat(tempSetpointInput)
        else:
            currentChillerValues['temp_setpoint'] = None

        db.execute("""INSERT INTO data_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG, bath_temp, pump_pres, temp_setpoint)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (timestamp,
                        tempChannels[0].currentValue,
                        tempChannels[1].currentValue,
                        tempChannels[2].currentValue,
                        tempChannels[3].currentValue,
                        tempChannels[4].currentValue,
                        tempChannels[5].currentValue,
                        tempChannels[6].currentValue,
                        currentChillerValues['bath_temp'], 
                        currentChillerValues['pump_pres'], 
                        currentChillerValues['temp_setpoint']))

        db.commit()
    
    def updateValueDisplays(self):
        for channel in tempChannels:
            if channel.currentValue:
                channel.currentValueDisplay.setText(f'{channel.currentValue} C')
            else:
                channel.currentValueDisplay.setText('No Data')
                
        if currentChillerValues['bath_temp']:
            self.chillerActualValue.setText(f"{currentChillerValues['bath_temp']} C")
        else:
            self.chillerActualValue.setText('No Data')
            
        if currentChillerValues['temp_setpoint']:
            self.chillerSetpointTempValue.setText(f"{currentChillerValues['temp_setpoint']} C")
        else:
            self.chillerSetpointTempValue.setText('No Data')
            
     # calculates the time range displayed on the graph
    def updateTimeRanges(self):
        
        if self.currentMode == 'replay':
                currentTime = self.dateTimeEditEnd.dateTime().toSecsSinceEpoch()
        else:
                currentTime = time.time()
                self.dateTimeEditEnd.setDateTime(QDateTime.currentDateTime())
        # last # hours
        if (self.timeRangeMode == 'hours'):
            self.endGraphTimestamp = currentTime
            self.beginGraphTimestamp = currentTime - (self.hoursBox.value() * 3600) # 3600 sec/hr
        # Full time
        elif (self.timeRangeMode == 'full'):
            self.endGraphTimestamp = 2**32 # a really big number
            self.beginGraphTimestamp = 0
        # custom range
        elif(self.timeRangeMode == 'range'):
            self.endGraphTimestamp = self.dateTimeEditBegin.dateTime().toSecsSinceEpoch()
            self.beginGraphTimestamp = self.dateTimeEditEnd.dateTime().toSecsSinceEpoch()
            
    def updatePlots(self):
        cur = db.cursor()
        #plots temperatures
        for channel in tempChannels:
            cur.execute(f"""SELECT timestamp, {channel.dbName} FROM data_log 
                            WHERE timestamp BETWEEN ? AND ? 
                            AND {channel.dbName} IS NOT NULL""",
                            (self.beginGraphTimestamp, self.endGraphTimestamp)) # TODO replace fstring
            data = cur.fetchall()
        
            channel.plot.clear()
            channel.plot.plot([d[0] for d in data], [d[1] for d in data], pen="r")
            
        # plots chiller temperature
        
        cur.execute("""SELECT timestamp, bath_temp, temp_setpoint FROM data_log 
                       WHERE timestamp BETWEEN ? AND ? 
                       AND bath_temp IS NOT NULL 
                       AND temp_setpoint IS NOT NULL""", (self.beginGraphTimestamp, self.endGraphTimestamp))
        data = cur.fetchall()
        chillerTimestamps = [d[0] for d in data]
        
        self.chillerTempPlot.clear()
    
        self.chillerTempPlot.plot(chillerTimestamps, [d[1] for d in data], pen="r")
        self.chillerTempPlot.plot(chillerTimestamps, [d[2] for d in data], pen="g")
        
    # sets the time begin and end boxes based on the first and last entry in the database
    def readDateRange(self):
        cur = db.cursor()
        cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM data_log")
        data = cur.fetchall()
        self.dateTimeEditBegin.setDateTime(QDateTimeFromTimestamp(data[0][0]))
        self.dateTimeEditEnd.setDateTime(QDateTimeFromTimestamp(data[0][1]))

    # starts logging and graphing data
    def startLogging(self):
        global db
        
        openDB() # creates new database file
        
        db.execute("CREATE TABLE data_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG, bath_temp, pump_pres, temp_setpoint)")
        
        # sets beginning of time range if 
        if self.dateTimeEditBegin.dateTime().toSecsSinceEpoch() == 946702800: # default datetime number
            self.dateTimeEditBegin.setDateTime(QDateTime.currentDateTime())
        
        # starts threads to gather data and timer to refresh UI
        self.updateUITimer.start()

    # stops logging data
    def stopLogging(self):
        self.updateUITimer.stop()
        
    # imports stored data from a database file
    def openDatabaseFile(self): 
        self.setMode('replay')
        
        openFilePath = QFileDialog.getOpenFileName(self, "Open Database file", '', '*.db')
        openDB(openFilePath[0])
        
        # reads labels and date range from database
        self.readDBLabels()
        self.readDateRange()

        # displays full range
        self.displayTimeBox.setCurrentIndex(1)
        
        # updates UI with new data
        self.updateTimeRangeMode()
        self.updateTimeRanges()
        self.updatePlots()
    
    def saveLabels(self):
        global db
        
        if (not isDBOpen()):
            openDB()
            
        db.execute("CREATE TABLE IF NOT EXISTS labels(channel PRIMARY KEY, label)")
        
        for channel in tempChannels:
            if channel.renameLabel.text():
                channel.label = channel.renameLabel.text()
            db.execute("REPLACE INTO labels(channel, label) VALUES (?, ?)", (channel.dbName, channel.label))
            db.commit()
            
            channel.labelDisplay.setText(channel.label)
            channel.renameLabel.clear()
            channel.renameLabel.setPlaceholderText(channel.label)
        
    def readDBLabels(self):
        global db
        
        for channel in tempChannels:
            
            cur = db.cursor()
            cur.row_factory = lambda cursor, row: row[0]
            
            try:
                cur.execute("SELECT label FROM labels WHERE channel = ?", (channel.dbName,))
            except sqlite3.OperationalError as e:
                if str(e) != "no such table: labels":
                    print('An error occured reading labels from the database')
                    raise
                else:
                    readLabel = cur.fetchone()
                    if readLabel:
                        channel.label = readLabel

                        channel.labelDisplay.setText(channel.label)
                        channel.renameLabel.setPlaceholderText(channel.label)
                
    def updateTimeRangeMode(self):
        selection = self.displayTimeBox.currentIndex()
        
        # Last # hours
        if (selection == 0):
            self.timeRangeMode = 'hours'
            
            self.hoursLabel.setEnabled(True)
            self.hoursBox.setEnabled(True)
            
            self.displayBeginningLabel.setEnabled(False)
            self.displayEndLabel.setEnabled(False)
            self.dateTimeEditBegin.setEnabled(False)
            self.dateTimeEditEnd.setEnabled(False)
        # Full time
        if (selection == 1):
            self.timeRangeMode = 'full'
            
            self.hoursLabel.setEnabled(False)
            self.hoursBox.setEnabled(False)
            
            self.displayBeginningLabel.setEnabled(False)
            self.displayEndLabel.setEnabled(False)
            self.dateTimeEditBegin.setEnabled(False)
            self.dateTimeEditEnd.setEnabled(False)
        # Custom range
        elif (selection == 2):
            self.timeRangeMode = 'range'
            
            self.hoursLabel.setEnabled(False)
            self.hoursBox.setEnabled(False)
            
            self.displayBeginningLabel.setEnabled(True)
            self.displayEndLabel.setEnabled(True)
            self.dateTimeEditBegin.setEnabled(True)
            self.dateTimeEditEnd.setEnabled(True)
        
    def exportData(self):    
        df = pd.read_sql_query("SELECT * FROM data_log", db)
        
        labels = [channel.label for channel in tempChannels]
        
        # sets temp sensor columns to given label
        for i in range(1, 8):
            df.rename(columns={df.columns[i]: labels[i - 1]}, inplace=True)
                
        df.to_csv(f'exports/export{datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")}.csv')

    # adjusts UI elements based on new mode
    def setMode(self, newMode: str):
        self.currentMode = newMode
        if newMode == 'replay':
            self.startButton.setEnabled(False)
            self.stopButton.setEnabled(False)
            self.renameButton.setEnabled(False)
        if newMode == 'live':
            self.startButton.setEnabled(True)
            self.stopButton.setEnabled(True)
            self.renameButton.setEnabled(True)
            
            
# Converts a epoch timestamp (float) to a QDateTime object
def QDateTimeFromTimestamp(timestamp):
    dt = QDateTime(0,0,0,0,0) # placeholder
    dt.setSecsSinceEpoch(round(timestamp))
    return dt
        
                
@dataclass       
class dataChannel:
    dbName: str
    dbTable: str
    label: str
    currentValue: float = 0.0
    plot: any = None
    labelDisplay: any = None
    currentValueDisplay: any = None
    renameLabel: any = None
    
@dataclass
class serialDevice:
    serialNumber: str
    connectionObject: serial.Serial
    
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
    
def getDevicePath(serialNumber):
    for port in serial.tools.list_ports.comports():
        if port.serial_number == serialNumber:
            return port.device
    
    return None

def getSerialData(serialDevice):
    try:
        data = serialDevice.connectionObject.readline().decode('ascii')
        if data:
            return data
        else:
            return None
    except (serial.serialutil.PortNotOpenError, serial.serialutil.SerialException):
        try:
                serialDevice.connectionObject.close()
                serialDevice.connectionObject.port = getDevicePath(serialDevice.serialNumber)
                serialDevice.connectionObject.open()
        except serial.SerialException:
            return None
        
# returns True if successful, False otherwise
def writeSerialData(serialDevice, dataString):
    try:
        serialDevice.connectionObject.write(bytes(dataString, 'ascii'))
        return True
    except (serial.serialutil.PortNotOpenError, serial.serialutil.SerialException):
        try:
                serialDevice.connectionObject.close()
                serialDevice.connectionObject.port = getDevicePath(serialDevice.serialNumber)
                serialDevice.connectionObject.open()
                serialDevice.connectionObject.write(bytes(dataString, 'ascii'))
        except serial.SerialException:
            # print('Failed to reopen connection and write data')
            return False

# converts a string to a float, returning None if the string is not a number
def safeFloat(string):
    if string:
        try:
            return float(string)
        except ValueError:
            return None
    return None

if __name__ == '__main__':
    
    currentChillerValues = {
        'bath_temp': None,
        'pump_pres': None,
        'temp_setpoint': None
    }
    
    app = QApplication([])
    
    mainApp = mainApp()
    mainApp.show()
    
    sys.exit(app.exec())