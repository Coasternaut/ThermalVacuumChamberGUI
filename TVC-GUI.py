from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtCore import QTimer, QThread, QDateTime
import pyqtgraph as pg
import sys, time, datetime, sqlite3
import serial, serial.serialutil, serial.tools, serial.tools.list_ports
from dataclasses import dataclass

class mainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("TVC-GUI-UI.ui", self)

        self.startButton.pressed.connect(self.startLogging)
        self.stopButton.pressed.connect(self.stopLogging)
        self.displayTimeBox.currentTextChanged.connect(self.updateTimeRangeMode)
        
        self.renameButton.pressed.connect(self.saveLabels)
        
        # self.actionSave.triggered.connect(saveData) TODO implement export function
        self.actionOpen.triggered.connect(self.openDatabaseFile)
        
        self.dateTimeEditBegin.setDateTime(QDateTime.currentDateTime())
        self.dateTimeEditEnd.setDateTime(QDateTime.currentDateTime())

        self.updateUITimer = QTimer(self)
        self.updateUITimer.setInterval(1000)
        self.updateUITimer.timeout.connect(self.updateUI)
        
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

    def updateUI(self):
        timestamp = time.time()
        # gets temp data
        tempData = getSerialData(self.serialDevices['temp'])
        
        # if temp data exists
        if tempData:
            # converts data string into list of floats
            tempValuesStr = tempData.split(';')
            tempValuesStr.pop()
            
            for i in range(len(tempValuesStr)):
                tempChannels[i].currentValue = float(tempValuesStr[i])
        else:
            for channel in tempChannels:
                channel.currentValue = None
        
        # get bath temp
        if writeSerialData(self.serialDevices['chiller'],'in_pv_00\r'):
            bathTempInput = getSerialData(self.serialDevices['chiller'])
            if bathTempInput:
                currentChillerValues['bath_temp'] = float(bathTempInput)
        else:
            currentChillerValues['bath_temp'] = None
        
        # get pump pressure
        if writeSerialData(self.serialDevices['chiller'],'in_pv_05\r'):
            pumpPressureInput = getSerialData(self.serialDevices['chiller'])
            if pumpPressureInput:
                currentChillerValues['pump_pres'] = float(pumpPressureInput)
        else:
            currentChillerValues['pump_pres'] = None
        
        # get temperature setpoint
        if writeSerialData(self.serialDevices['chiller'],'in_sp_00\r'):
            tempSetpointInput = getSerialData(self.serialDevices['chiller'])
            if tempSetpointInput:
                currentChillerValues['temp_setpoint'] = float(tempSetpointInput)
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
         # calculates the time range displayed on the graph
        
        # last # hours
        if (self.timeRangeMode == 'hours'):
            endGraphTimestamp = time.time()
            beginGraphTimestamp = time.time() - (self.hoursBox.value() * 3600) # 3600 sec/hr
        # Full time
        elif (self.timeRangeMode == 'full'):
            endGraphTimestamp = 2**32 # a really big number
            beginGraphTimestamp = 0
        # custom range
        elif(self.timeRangeMode == 'range'):
            endGraphTimestamp = self.dateTimeEditBegin.dateTime().toSecsSinceEpoch()
            beginGraphTimestamp = self.dateTimeEditEnd.dateTime().toSecsSinceEpoch()
         
        
        cur = db.cursor()
        #cur.row_factory = lambda cursor, row: row[0]

        
        #plots temperatures
        for channel in tempChannels:
            cur.execute(f"""SELECT timestamp, {channel.dbName} FROM data_log 
                            WHERE timestamp BETWEEN ? AND ? 
                            AND {channel.dbName} IS NOT NULL""",
                            (beginGraphTimestamp, endGraphTimestamp)) # TODO replace fstring
            data = cur.fetchall()
        
            channel.plot.clear()
            channel.plot.plot([d[0] for d in data], [d[1] for d in data], pen="r")
            
            if channel.currentValue:
                channel.currentValueDisplay.setText(f'{channel.currentValue} C')
            else:
                channel.currentValueDisplay.setText('No Data')
            
        # plots chiller temperature
        
        cur.execute("""SELECT timestamp, bath_temp, temp_setpoint FROM data_log 
                       WHERE timestamp BETWEEN ? AND ? 
                       AND bath_temp IS NOT NULL 
                       AND temp_setpoint IS NOT NULL""", (beginGraphTimestamp, endGraphTimestamp))
        data = cur.fetchall()
        chillerTimestamps = [d[0] for d in data]
        
        self.chillerTempPlot.clear()
    
        self.chillerTempPlot.plot(chillerTimestamps, [d[1] for d in data], pen="r")
        self.chillerTempPlot.plot(chillerTimestamps, [d[2] for d in data], pen="g")
        
        if currentChillerValues['bath_temp']:
            self.chillerActualValue.setText(f'{currentChillerValues['bath_temp']} C')
        else:
            self.chillerActualValue.setText('No Data')
            
        if currentChillerValues['temp_setpoint']:
            self.chillerSetpointTemp.setText(f'{currentChillerValues['temp_setpoint']} C')
        else:
            self.chillerSetpointTemp.setText('No Data')
        
        #updates end display time
        
        cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM data_log")
        data = cur.fetchall()
        self.dateTimeEditBegin.setDateTime(QDateTimeFromTimestamp(data[0][0]))
        self.dateTimeEditEnd.setDateTime(QDateTimeFromTimestamp(data[0][1]))
        
        
    # starts logging and graphing data
    def startLogging(self):
        global db
        
        openDB() # creates new database file
        
        db.execute("CREATE TABLE data_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG, bath_temp, pump_pres, temp_setpoint)")
        
        # starts threads to gather data and timer to refresh UI
        self.updateUITimer.start()

    # stops logging data TODO make thread stop
    def stopLogging(self):
        print("stopping thread")
        self.getTempThread.quit()
        
    # imports stored data from a database file
    def openDatabaseFile(self): 
        openFilePath = QFileDialog.getOpenFileName(self, "Open Database file", '', '*.db')
        openDB(openFilePath[0])

        self.updateLabels()

        # displays full range
        self.displayTimeBox.setCurrentIndex(1)
        self.updateTimeRangeMode() # also calls updateUI
    
    def saveLabels(self):
        global db
        
        if (not isDBOpen()):
            openDB()
            
        db.execute("CREATE TABLE IF NOT EXISTS labels(channel PRIMARY KEY, label)")
        
        for channel in tempChannels:
            if (channel.renameLabel.text()):
                db.execute("REPLACE INTO labels(channel, label) VALUES (?, ?)", (channel.dbName, channel.renameLabel.text()))
                db.commit()

        self.updateLabels()
        
    def updateLabels(self):
        global db
        
        if (isDBOpen()):
            for channel in tempChannels:
                
                cur = db.cursor()
                cur.row_factory = lambda cursor, row: row[0]
                
                try:
                    cur.execute("SELECT label FROM labels WHERE channel = ?", (channel.dbName,))
                except sqlite3.OperationalError as e:
                    if str(e) != "no such table: labels":
                        raise
                    else:
                        channel.label = cur.fetchone()

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
        
        self.updateUI()
            
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