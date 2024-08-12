from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtCore import QTimer, QThread, QDateTime
import pyqtgraph as pg
import sys, time, datetime, sqlite3
import serial, serial.serialutil, serial.tools, serial.tools.list_ports
from dataclasses import dataclass
import pandas as pd
import termios
import numpy as np

class mainApp(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("TVC-GUI-UI.ui", self)

        # config settings
        self.minYBorder = 2

        self.startButton.pressed.connect(self.startLogging)
        self.stopButton.pressed.connect(self.stopLogging)
        self.displayTimeBox.currentTextChanged.connect(self.updateTimeRangeMode)
        self.applyCustomRangeButton.pressed.connect(self.updatePlots)

        self.tempUnitBox.currentTextChanged.connect(self.updateYAxisUnits)
        self.presUnitBox.currentTextChanged.connect(self.updateYAxisUnits)
        
        self.renameButton.pressed.connect(self.saveLabels)
        
        self.exportCSVbutton.pressed.connect(self.exportData)
        self.openDBbutton.pressed.connect(self.openDatabaseFile)

        self.chillerSetButton.pressed.connect(self.setChillerSetpoint)
        self.startChillerButton.pressed.connect(self.startChiller)
        self.stopChillerButton.pressed.connect(self.stopChiller)
        
        # self.dateTimeEditBegin.setDateTime(QDateTime.currentDateTime())
        # self.dateTimeEditEnd.setDateTime(QDateTime.currentDateTime())
        
        self.liveUpdateLoopTimer = QTimer(self)
        self.liveUpdateLoopTimer.setInterval(1000)
        self.liveUpdateLoopTimer.timeout.connect(self.liveUpdateLoop)
        
        self.currentMode = 'live'

        self.startTime = None
        
        self.dataChannels = {'tempA': dataChannel('tempArd', 'tempA', 'Temp Sensor A', 'temp', self.tempAPlot, self.tempALabel, self.tempAValue, self.tempARename),
                            'tempB': dataChannel('tempArd', 'tempB', 'Temp Sensor B', 'temp', self.tempBPlot, self.tempBLabel, self.tempBValue, self.tempBRename),
                            'tempC': dataChannel('tempArd', 'tempC', 'Temp Sensor C', 'temp', self.tempCPlot, self.tempCLabel, self.tempCValue, self.tempCRename),
                            'tempD': dataChannel('tempArd', 'tempD', 'Temp Sensor D', 'temp', self.tempDPlot, self.tempDLabel, self.tempDValue, self.tempDRename),
                            'tempE': dataChannel('tempArd', 'tempE', 'Temp Sensor E', 'temp', self.tempEPlot, self.tempELabel, self.tempEValue, self.tempERename),
                            'tempF': dataChannel('tempArd', 'tempF', 'Temp Sensor F', 'temp', self.tempFPlot, self.tempFLabel, self.tempFValue, self.tempFRename),
                            'tempG': dataChannel('tempArd', 'tempG', 'Temp Sensor G', 'temp', self.tempGPlot, self.tempGLabel, self.tempGValue, self.tempGRename),
                            'bath_temp': dataChannel('chiller', 'bath_temp', 'Actual:', 'temp', self.chillerTempPlot, self.chillerActualTempLabel, self.chillerActualTempValue),
                            'temp_setpoint': dataChannel('chiller', 'temp_setpoint', 'Setpoint:', 'temp', self.chillerTempPlot, self.chillerSetpointTempLabel, self.chillerSetpointTempValue, None, False, 'g'),
                            'ion_pressure': dataChannel('pressure', 'ion_pressure', 'Ionization Pressure', 'pres', self.ionPlot, self.ionLabel, self.ionValue)
                            }
        
        # current display units for each dataCategory. Values set in updateYAxisUnits()
        self.currentUnits = {
            'temp': '',
            'pres': ''
        }
        
        # initializes graphs
        for channel in self.dataChannels.values():
            channel.plot.setAxisItems(axisItems = {'bottom': pg.DateAxisItem()})
            channel.plot.setLabel('bottom', 'Time')

        self.updateYAxisUnits()

        self.timeRangeMode = 'hours'
        self.serialDevices  = {
            'tempArd': serialDevice('tempArd', 'D12A5A1851544B5933202020FF080B15', serial.Serial(None, 9600, timeout=1)),
            'chiller': serialDevice('chiller', 'AL066BK6', serial.Serial(None, 4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE, timeout=.15, write_timeout=.1, rtscts=True)),
            'ionGauge': serialDevice('ionGauge', 'B001YA5C', serial.Serial(None, 19200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=.1, write_timeout=.05))
        }

        # reads from each device to initialize COM port
        for device in self.serialDevices.values():
            readSerialData(device)

    # loop called every second when in live logging mode
    def liveUpdateLoop(self):
        loopStartTime = time.time()

        self.getNewData()
        self.updateValueDisplays()
        self.updatePlots()
        
        self.totalTime.setText(str(round((time.time() - loopStartTime), 3)))

    def getNewData(self):
        self.currentTimestamp = time.time()
        # gets temp data
        tempData = requestSerialData(self.serialDevices['tempArd'], 'D', 36)
        
        # if temp data exists
        if tempData:
            # converts data string into list of floatsMin Length: {minByteLength}   Actual Length: {dataLen}'
            tempValuesStr = tempData.split(';')
            tempValuesStr.pop()
            
            for i, channel in zip(range(len(tempValuesStr)), self.dataChannels.values()):
                channel.currentValue = validateTemp(safeFloat(tempValuesStr[i]))
        else:
            for channel in list(self.dataChannels.values())[:7]:
                channel.currentValue = None

        self.tempTime.setText(str(round((time.time() - self.currentTimestamp), 3)))
        clock = time.time()
        
        # get bath temp
        self.dataChannels['bath_temp'].currentValue = safeFloat(requestSerialData(self.serialDevices['chiller'], 'in_pv_00\r', 4))
        
        # only gets setpoint if bath temp was valid
        if self.dataChannels['bath_temp'].currentValue != None:
            # get temperature setpoint
            self.dataChannels['temp_setpoint'].currentValue = safeFloat(requestSerialData(self.serialDevices['chiller'], 'in_sp_00\r', 4))
        else:
            self.dataChannels['temp_setpoint'].currentValue = None

        self.chillerTime.setText(str(round((time.time() - clock), 3)))
        clock = time.time()
        
        # get ionization gauge pressure
        ionData = requestSerialData(self.serialDevices['ionGauge'], '#01RD\r', 13)
        if ionData and ionData[:3] == '*01': # ensures valid return header
            if ionData[4:] != '9.99E+09': # checks for default return when gauge off
                ionData = safeFloat(ionData[4:]) # splits data from return header
            else:
                ionData = None
        else: 
            ionData = None
            
        self.dataChannels['ion_pressure'].currentValue = ionData

        self.ionTime.setText(str(round((time.time() - clock), 3)))

        clock = time.time()
        db.execute("""INSERT INTO data_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG, bath_temp, temp_setpoint, ion_pressure)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        self.currentValueTuple())

        db.commit()

        self.dbTime.setText(str(round((time.time() - clock), 3)))
    
    def updateValueDisplays(self):
        for channel in self.dataChannels.values():
            value = self.convertUnit(channel.currentValue, channel.dataCategory)
            if value:
                channel.currentValueDisplay.setText(f'{value} {self.currentUnits[channel.dataCategory]}')
                channel.currentValueDisplay.setStyleSheet('color: black; font-size: 16px')
            else:
                channel.currentValueDisplay.setText('No Data')
                channel.currentValueDisplay.setStyleSheet('color: red; font-size: 16px')
                
    def updatePlots(self):
        clock = time.time()

        # sets time ranges for plotting
        if self.currentMode == 'replay':
                self.startTime = self.dateTimeEditBegin.dateTime().toSecsSinceEpoch()
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
            self.endGraphTimestamp = currentTime
            self.beginGraphTimestamp = self.startTime
        # custom range
        elif(self.timeRangeMode == 'range'):
            self.endGraphTimestamp = self.dateTimeEditEnd.dateTime().toSecsSinceEpoch()
            self.beginGraphTimestamp = self.dateTimeEditBegin.dateTime().toSecsSinceEpoch()
        else:
            raise ValueError('No time range specified')
        

        cur = db.cursor()
        #plots data
        for channel in self.dataChannels.values():
            cur.execute(f"""SELECT timestamp, {channel.dbName} FROM data_log 
                            WHERE timestamp BETWEEN ? AND ?""",
                            (self.beginGraphTimestamp, self.endGraphTimestamp)) # TODO replace fstring
            data = cur.fetchall()

            #print(f'Reading from {channel.dbName} - Length Data: {len(data)}')

            xAxis = []
            yAxis = []

            for d in data:
                xAxis.append(d[0])
                yValue = self.convertUnit(d[1], channel.dataCategory)
                if yValue:
                    yAxis.append(yValue)
                else:
                    #print('Invalid data for graphing: ', d[1])
                    yAxis.append(np.nan)

            if channel.singlePlot:
                channel.plot.clear()
                channel.plot.setXRange(self.beginGraphTimestamp, self.endGraphTimestamp, update=False)

            if channel.device != 'chiller' and yAxis:
                yMin = min(yAxis)
                yMax = max(yAxis)

                yRangeMin = min(yMin * 0.95, yMin - self.minYBorder)
                yRangeMax = max(yMax * 1.05, yMax + self.minYBorder)

                if not (np.isnan(yRangeMin) or np.isnan(yRangeMax)):
                    #print(f'Updating Y range - Channel: {channel.dbName} Min: {yRangeMin}, Max: {yRangeMax}')
                    channel.plot.setYRange(yRangeMin, yRangeMax, update=False)

            channel.plot.plot(xAxis, yAxis, pen=channel.color, connect='finite')
        self.plottingTime.setText(str(round((time.time() - clock), 3)))
            
            
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
        
        db.execute("CREATE TABLE IF NOT EXISTS data_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG, bath_temp, temp_setpoint, ion_pressure)")
        
        # sets beginning of time range if 
        if not self.startTime:
            self.startTime = time.time()
            self.dateTimeEditBegin.setDateTime(QDateTime.currentDateTime())
        
        # starts threads to gather data and timer to refresh UI
        self.liveUpdateLoopTimer.start()
        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(True)

    # stops logging data
    def stopLogging(self):
        self.liveUpdateLoopTimer.stop()
        self.startButton.setEnabled(True)
        self.stopButton.setEnabled(False)
        
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
        
        self.updatePlots()

        self.startButton.setEnabled(False)
        self.stopButton.setEnabled(False)
    
    def saveLabels(self):
        global db
        
        if (not isDBOpen()):
            openDB()
            
        db.execute("CREATE TABLE IF NOT EXISTS labels(channel PRIMARY KEY, label)")
        
        for channel in self.dataChannels.values():
            if channel.renameLabel:
                if channel.renameLabel.text():
                    channel.label = channel.renameLabel.text()
                db.execute("REPLACE INTO labels(channel, label) VALUES (?, ?)", (channel.dbName, channel.label))
                db.commit()
                
                channel.labelDisplay.setText(channel.label)
                channel.renameLabel.clear()
                channel.renameLabel.setPlaceholderText(channel.label)
        
    def readDBLabels(self):
        global db
        
        cur = db.cursor()
        cur.row_factory = lambda cursor, row: row[0]
        
        for channel in self.dataChannels.values():
            if channel.renameLabel:
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
        #print('Selection index: ', selection)
        
        # Last # hours
        if (selection == 0):
            self.timeRangeMode = 'hours'
            
            self.hoursLabel.setEnabled(True)
            self.hoursBox.setEnabled(True)
            
            self.displayBeginningLabel.setEnabled(False)
            self.displayEndLabel.setEnabled(False)
            self.dateTimeEditBegin.setEnabled(False)
            self.dateTimeEditEnd.setEnabled(False)
            self.applyCustomRangeButton.setEnabled(False)
        # Full time
        if (selection == 1):
            self.timeRangeMode = 'full'
            
            self.hoursLabel.setEnabled(False)
            self.hoursBox.setEnabled(False)
            
            self.displayBeginningLabel.setEnabled(False)
            self.displayEndLabel.setEnabled(False)
            self.dateTimeEditBegin.setEnabled(False)
            self.dateTimeEditEnd.setEnabled(False)
            self.applyCustomRangeButton.setEnabled(False)
        # Custom range
        elif (selection == 2):
            self.timeRangeMode = 'range'
            
            self.hoursLabel.setEnabled(False)
            self.hoursBox.setEnabled(False)
            
            self.displayBeginningLabel.setEnabled(True)
            self.displayEndLabel.setEnabled(True)
            self.dateTimeEditBegin.setEnabled(True)
            self.dateTimeEditEnd.setEnabled(True)
            self.applyCustomRangeButton.setEnabled(True)

        #print('New mode: ', self.timeRangeMode)
        self.updatePlots()
        
    def exportData(self):    
        savePath = str(QFileDialog.getSaveFileName(self, 'Export CSV')[0])
        # print('Save path: ', savePath)

        if savePath.endswith('/'):
            savePath += f'{datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")}.csv'
        elif not savePath.endswith('.csv'):
            savePath += '.csv'

        # print('Final save path: ', savePath)
        df = pd.read_sql_query("SELECT * FROM data_log", db)
        
        labels = [channel.label for channel in self.dataChannels.values()]
        
        # sets temp sensor columns to given label
        for i in range(1, 8):
            df.rename(columns={df.columns[i]: labels[i - 1]}, inplace=True)
                
        df.to_csv(savePath)

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

    # returns the timestamp and all current values as a tuple
    def currentValueTuple(self):
        data = [self.currentTimestamp]
        
        for channel in self.dataChannels.values():
            data.append(channel.currentValue)
    
        return tuple(data)
    
    def updateYAxisUnits(self):
        self.currentUnits['temp'] = str(self.tempUnitBox.currentText())
        self.currentUnits['pres'] = str(self.presUnitBox.currentText())
        for channel in self.dataChannels.values():
            if channel.dataCategory == 'temp':
                channel.plot.setLabel('left', 'Temperature', units=self.currentUnits['temp'])
            if channel.dataCategory == 'pres':
                channel.plot.setLabel('left', 'Pressure', units=self.currentUnits['pres'])
    
    def convertUnit(self, value, dataCategory):
        if validNumber(value):
            if dataCategory == 'temp':
                if self.currentUnits['temp'] == '°C':
                    return value
                if self.currentUnits['temp'] == '°F':
                    return round((value * 1.8) + 32, 1)
                if self.currentUnits['temp'] == 'K':
                    return round(value + 273.15, 1)
            if dataCategory == 'pres':
                if self.currentUnits['pres'] == 'Torr':
                    return value
                if self.currentUnits['temp'] == 'Pa':
                    return round(value * 133.322, 2)
                if self.currentUnits['temp'] == 'inHg':
                    return round(value / 25.4, 2)
                if self.currentUnits['temp'] == 'Atm':
                    return round(value / 760.0, 2)
        return None
    
    def setChillerSetpoint(self):
        newValue = self.chillerSetInput.value()
        writeMessage = f'out_sp_00 {newValue}\r'
        print(f'Setting chiller setpoint to {newValue}. Output: ', writeSerialData(self.serialDevices['chiller'], writeMessage))

    def startChiller(self):
        print('Starting chiller')
        if writeSerialData(self.serialDevices['chiller'], 'out_mode_05 1\r'):
            self.startChillerButton.setEnabled(False)
            self.stopChillerButton.setEnabled(True)
            print('Chiller on')
        # print(startWriteStatus)
        # if startWriteStatus:
        #     requestedStatus = requestSerialData(self.serialDevices['chiller'], 'in_mode_05\r', 1)
        #     print(requestedStatus)
        #     print('Chiller on')

    def stopChiller(self):
        print('Stopping chiller')
        if writeSerialData(self.serialDevices['chiller'], 'out_mode_05 0\r'):
            self.startChillerButton.setEnabled(True)
            self.stopChillerButton.setEnabled(False)
            print('Chiller off')
            # if requestSerialData(self.serialDevices['chiller'], 'in_mode_05\r', 1) == 0:

# Converts a epoch timestamp (float) to a QDateTime object
def QDateTimeFromTimestamp(timestamp):
    dt = QDateTime(0,0,0,0,0) # placeholder
    dt.setSecsSinceEpoch(round(timestamp))
    return dt
        
                
@dataclass       
class dataChannel:
    device: str
    dbName: str
    label: str
    dataCategory: str
    plot: any
    labelDisplay: any
    currentValueDisplay: any
    renameLabel: any = None 
    singlePlot: bool = True
    color: str = 'r'
    currentValue: float = None
    
@dataclass
class serialDevice:
    name: str
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

def readSerialData(serialDevice):
    try:
        data = serialDevice.connectionObject.readline().decode('ascii')
    except (serial.serialutil.PortNotOpenError, serial.serialutil.SerialException):
        try:
            resetConnection(serialDevice)
            data = serialDevice.connectionObject.readline().decode('ascii')
        except serial.SerialException:
            return None
    if data:
        return data
    else:
        return None
        
# returns True if successful, False otherwise
def writeSerialData(serialDevice, dataString):
    try:
        serialDevice.connectionObject.write(bytes(dataString, 'ascii'))
        return True
    except (serial.serialutil.PortNotOpenError):
        try:
            resetConnection(serialDevice)
            print('Second data write: ', dataString)
            serialDevice.connectionObject.write(bytes(dataString, 'ascii'))
            return True
        except (serial.serialutil.SerialException, serial.serialutil.SerialTimeoutException, termios.error):
            print('Failed to reopen connection and write data')
            return False
    except (serial.serialutil.SerialException, serial.serialutil.SerialTimeoutException, termios.error):
        return False
        
def requestSerialData(serialDevice, requestString, minByteLength):
    data = None
    try:
        serialDevice.connectionObject.reset_input_buffer()
        # if serialDevice.name == 'chiller':
        #     print('buffer reset')
        serialDevice.connectionObject.write(bytes(requestString, 'ascii'))
        # if serialDevice.name == 'chiller':
        #     print(f'{datetime.datetime.now()}  Writing to {serialDevice.name}: {bytes(requestString, 'ascii')}')
        data = serialDevice.connectionObject.read_until(b'\r')
        dataLen = len(data)
        # print(f'Data: {data} - Data len: {dataLen}')
        if dataLen < minByteLength:
            # log if some data is read
            if dataLen != 0:
                print(f'{datetime.datetime.now()}  Return too short   Device: {serialDevice.name}   Data: {data}  Min Length: {minByteLength}   Actual Length: {dataLen}')
            return None
        # if serialDevice.name == 'chiller':
        #     print(f'{datetime.datetime.now()}  Reading from {serialDevice.name}: {data}')
        #     print(f'Bytes length - {serialDevice.name}: ', len(data))
        data = data.decode('ascii').strip()
        #print(f'Data - {serialDevice.name}: ', data)
    except (serial.serialutil.SerialTimeoutException) as e:
        #print(f'{datetime.datetime.now()}  Timeout device {serialDevice.name}: {type(e)} {e}')
        return None
    except (serial.serialutil.PortNotOpenError, serial.serialutil.SerialException, termios.error) as e:
        print(f'{datetime.datetime.now()}  Resetting device {serialDevice.name}: {type(e)} {e}')
        try:
            resetConnection(serialDevice)
            return None
        except serial.SerialException:
            return None
    if data:
        return data
    else:
        print(f'{datetime.datetime.now()}  Data not True   Device: {serialDevice.name}   Data: {data}')
        return None
        
def resetConnection(serialDevice):
    serialDevice.connectionObject.close()
    serialDevice.connectionObject.port = getDevicePath(serialDevice.serialNumber)
    serialDevice.connectionObject.open()

# converts a string to a float, returning None if the string is not a number
def safeFloat(string):
    if string:
        try:
            return float(string)
        except ValueError:
            return None
    #print('Safe Float - invalid string: ', string)
    return None

# returns None if temperature value is outside of the supported range for the sensor
def validateTemp(temp):
    if temp > -40 and temp < 125:
        return temp
    else:
        return None
    
# returns true if the input is a number, false otherwise
def validNumber(input):
    if type(input) == int or type(input) == float:
        return True
    #print(f'Invalid number - input: {input}; type: {type(input)}')
    return False



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