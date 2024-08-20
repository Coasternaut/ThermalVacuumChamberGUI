from PyQt6 import uic
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from PyQt6.QtCore import QTimer, QDateTime
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
        self.resetLabelsButton.pressed.connect(self.readDBLabels)
        
        self.exportCSVbutton.pressed.connect(self.exportData)
        self.importCSVbutton.pressed.connect(self.importData)
        self.openDBbutton.pressed.connect(self.openDatabaseFile)
        self.closeDBbutton.pressed.connect(self.closeDatabaseFile)

        self.chillerSetButton.pressed.connect(self.setChillerSetpoint)
        self.startChillerButton.pressed.connect(self.startChiller)
        self.stopChillerButton.pressed.connect(self.stopChiller)

        self.ionOnButton.pressed.connect(self.ionOn)
        self.ionOffButton.pressed.connect(self.ionOff)
        self.getStatusButton.pressed.connect(self.getStatus)
        
        self.liveUpdateLoopTimer = QTimer(self)
        self.liveUpdateLoopTimer.setInterval(1000)
        self.liveUpdateLoopTimer.timeout.connect(self.liveUpdateLoop)
        
        self.setMode('startup')

        self.startTime = None

        self.db = None

        self.configDB = sqlite3.connect('config.db')
        
        self.dataChannels = {'tempA': dataChannel('tempArd', 'tempA', 'Temp Sensor A', 'temp', self.tempAPlot, self.tempAEnable, self.tempAValue, self.tempARename),
                            'tempB': dataChannel('tempArd', 'tempB', 'Temp Sensor B', 'temp', self.tempBPlot, self.tempBEnable, self.tempBValue, self.tempBRename),
                            'tempC': dataChannel('tempArd', 'tempC', 'Temp Sensor C', 'temp', self.tempCPlot, self.tempCEnable, self.tempCValue, self.tempCRename),
                            'tempD': dataChannel('tempArd', 'tempD', 'Temp Sensor D', 'temp', self.tempDPlot, self.tempDEnable, self.tempDValue, self.tempDRename),
                            'tempE': dataChannel('tempArd', 'tempE', 'Temp Sensor E', 'temp', self.tempEPlot, self.tempEEnable, self.tempEValue, self.tempERename),
                            'tempF': dataChannel('tempArd', 'tempF', 'Temp Sensor F', 'temp', self.tempFPlot, self.tempFEnable, self.tempFValue, self.tempFRename),
                            'tempG': dataChannel('tempArd', 'tempG', 'Temp Sensor G', 'temp', self.tempGPlot, self.tempGEnable, self.tempGValue, self.tempGRename),
                            'bath_temp': dataChannel('chiller', 'bath_temp', 'Chiller Temp', 'temp', self.chillerTempPlot, self.chillerTempEnable, self.chillerActualTempValue),
                            'temp_setpoint': dataChannel('chiller', 'temp_setpoint', 'Chiller Setpoint', 'temp', self.chillerTempPlot, self.chillerTempEnable, self.chillerSetpointTempValue, None, False, 'g'),
                            'ion_pressure': dataChannel('ionGauge', 'ion_pressure', 'Ionization Pressure', 'pres', self.ionPlot, self.ionEnable, self.ionValue, color='m'),
                            'CG1': dataChannel('ionGauge', 'CG1', 'Scroll Pump Pressure (CG1)', 'pres', self.CG1Plot, self.CG1Enable, self.CG1Value, color='m'),
                            'CG2': dataChannel('ionGauge', 'CG2', 'Chamber Pressure (CG2)', 'pres', self.CG2Plot, self.CG2Enable, self.CG2Value, color='m')
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

        self.timeRangeMode = 'hours'
        self.updateYAxisUnits()

        self.readDBLabels('config')

        self.serialDevices  = {
            'tempArd': serialDevice('tempArd', 'D12A5A1851544B5933202020FF080B15', serial.Serial(None, 9600, timeout=1)),
            'chiller': serialDevice('chiller', 'AL066BK6', serial.Serial(None, 4800, bytesize=serial.SEVENBITS, parity=serial.PARITY_EVEN, stopbits=serial.STOPBITS_ONE, timeout=.15, write_timeout=.1, rtscts=True)),
            'ionGauge': serialDevice('ionGauge', 'B001YA5C', serial.Serial(None, 19200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=.1, write_timeout=.05))
        }

        # reads from each device to initialize COM port
        for device in self.serialDevices.values():
            try:
                device.connectionObject.port = getDevicePath(device.serialNumber)
                device.connectionObject.open()
            except serial.SerialException as e:
                print(f"Device {device.name} not found.")

    # loop called every second when in live logging mode
    def liveUpdateLoop(self):
        loopStartTime = time.time()

        self.updateEnableStatus()
        self.getNewData()
        self.updatePlots()
        
        self.totalTime.setText(str(round((time.time() - loopStartTime), 3)))

    def getNewData(self):
        self.currentTimestamp = time.time()

        if self.serialDevices['tempArd'].enabled:
            # gets temp data
            tempData = self.requestSerialData(self.serialDevices['tempArd'], 'D', 29)
            
            # if temp data exists
            if tempData:
                # converts data string into list of floats
                tempValuesStr = tempData.split(';')
                tempValuesStr.pop()
                
                for i, channel in zip(range(len(tempValuesStr)), self.dataChannels.values()):
                    if channel.enabled:
                        # saves temp data
                        channel.currentValue = validateTemp(safeFloat(tempValuesStr[i]))
                    else:
                        # does not record disabled channel
                        channel.currentValue = None
            else:
                for channel in list(self.dataChannels.values())[:7]:
                    channel.currentValue = None

        self.tempTime.setText(str(round((time.time() - self.currentTimestamp), 3)))
        clock = time.time()
        
        if self.serialDevices['chiller'].enabled:
            # get bath temp
            self.dataChannels['bath_temp'].currentValue = safeFloat(self.requestSerialData(self.serialDevices['chiller'], 'in_pv_00\r', 4))
            
            # only gets setpoint if bath temp was valid
            if self.dataChannels['bath_temp'].currentValue != None:
                # get temperature setpoint
                self.dataChannels['temp_setpoint'].currentValue = safeFloat(self.requestSerialData(self.serialDevices['chiller'], 'in_sp_00\r', 4))
            else:
                self.dataChannels['temp_setpoint'].currentValue = None

        self.chillerTime.setText(str(round((time.time() - clock), 3)))
        clock = time.time()
        
        if self.serialDevices['ionGauge'].enabled:
            # gets pressures from ion gauges
            if self.dataChannels['ion_pressure'].enabled:
                self.dataChannels['ion_pressure'].currentValue = self.validateIonPressure(self.requestSerialData(self.serialDevices['ionGauge'], '#01RD\r', 13))
            else:
                self.dataChannels['ion_pressure'].currentValue = None

            # only gets CG data if there is a response from the ion gauge request
            if self.dataChannels['ion_pressure'].currentValue:
                if self.dataChannels['CG1'].enabled:
                    self.dataChannels['CG1'].currentValue = self.validateIonPressure(self.requestSerialData(self.serialDevices['ionGauge'], '#01RDCG1\r', 13))
                else:
                    self.dataChannels['CG1'].currentValue = None
                
                if self.dataChannels['CG2'].enabled:
                    self.dataChannels['CG2'].currentValue = self.validateIonPressure(self.requestSerialData(self.serialDevices['ionGauge'], '#01RDCG2\r', 13))
                else:
                    self.dataChannels['CG2'].currentValue = None
            

        self.ionTime.setText(str(round((time.time() - clock), 3)))

        clock = time.time()
        self.db.execute("""INSERT INTO data_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG, bath_temp, temp_setpoint, ion_pressure, CG1, CG2)
                      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        self.currentValueTuple())

        self.db.commit()

        self.dbTime.setText(str(round((time.time() - clock), 3)))

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
        
        if self.db:
            cur = self.db.cursor()
            #plots data
            for channel in self.dataChannels.values():
                if channel.enabled:
                    # updates value display
                    if self.currentMode == 'replay':
                        self.setLabelTextColor(channel.currentValueDisplay, 'Replay')
                    elif channel.currentValue == 'Off':
                        self.setLabelTextColor(channel.currentValueDisplay, 'Gauge Off', 'orange')
                    else:
                        value = self.convertUnit(channel.currentValue, channel.dataCategory)
                        if validNumber(value):
                            self.setLabelTextColor(channel.currentValueDisplay, f'{value} {self.currentUnits[channel.dataCategory]}')
                        else:
                            self.setLabelTextColor(channel.currentValueDisplay, 'No Data', 'red')


                    cur.execute(f"""SELECT timestamp, {channel.dbName} FROM data_log 
                                    WHERE timestamp BETWEEN ? AND ?""",
                                    (self.beginGraphTimestamp, self.endGraphTimestamp)) # TODO replace fstring
                    data = cur.fetchall()

                    # print(f'Reading from {channel.dbName} - Data: {data}')

                    xAxis = []
                    yAxis = []

                    lastInputTimestamp = data[0][0]

                    for d in data:
                        # checks for gap in data and adds NaN point to split plots
                        if d[0] - lastInputTimestamp > 3:
                            xAxis.append(lastInputTimestamp + 1)
                            yAxis.append(np.nan)
                        lastInputTimestamp = d[0]
                        xAxis.append(lastInputTimestamp)
                        if validNumber(d[1]):
                            yAxis.append(self.convertUnit(d[1], channel.dataCategory))
                        else:
                            #print('Invalid data for graphing: ', d[1])
                            yAxis.append(np.nan)

                    if channel.singlePlot:
                        channel.plot.clear()
                        channel.plot.setXRange(self.beginGraphTimestamp, self.endGraphTimestamp, update=False)

                    if channel.device != 'chiller' and yAxis:
                        #print(f'Channel: {channel.dbName}  Data: {yAxis}')
                        yMin = min(yAxis)
                        yMax = max(yAxis)

                        yRangeMin = min(yMin * 0.95, yMin - self.minYBorder)
                        yRangeMax = max(yMax * 1.05, yMax + self.minYBorder)

                        if not (np.isnan(yRangeMin) or np.isnan(yRangeMax)):
                            #print(f'Updating Y range - Channel: {channel.dbName} Min: {yRangeMin}, Max: {yRangeMax}')
                            channel.plot.setYRange(yRangeMin, yRangeMax, update=False)

                    channel.plot.plot(xAxis, yAxis, pen=channel.color, connect='finite')
                else:
                    self.setLabelTextColor(channel.currentValueDisplay, 'Disabled', 'gray')

        self.plottingTime.setText(str(round((time.time() - clock), 3)))
            
            
    # sets the time begin and end boxes based on the first and last entry in the database
    def readDateRange(self):
        cur = self.db.cursor()
        cur.execute("SELECT MIN(timestamp), MAX(timestamp) FROM data_log")
        data = cur.fetchall()
        self.dateTimeEditBegin.setDateTime(QDateTimeFromTimestamp(data[0][0]))
        self.dateTimeEditEnd.setDateTime(QDateTimeFromTimestamp(data[0][1]))

    # starts logging and graphing data
    def startLogging(self):
        
        if not self.db:
            self.openDB(f'logs/log{datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")}.db') # creates new database file
        
        self.db.execute("CREATE TABLE IF NOT EXISTS data_log(timestamp, tempA, tempB, tempC, tempD, tempE, tempF, tempG, bath_temp, temp_setpoint, ion_pressure, CG1, CG2)")
        # sets beginning of time range if no range already specified
        if not self.startTime:
            self.startTime = time.time()
            self.dateTimeEditBegin.setDateTime(QDateTime.currentDateTime())
        
        # starts threads to gather data and timer to refresh UI
        self.liveUpdateLoopTimer.start()
        self.setMode('logging')

    # stops logging data
    def stopLogging(self):
        self.liveUpdateLoopTimer.stop()
        self.setMode('stopped')
        
    # imports stored data from a database file
    def openDatabaseFile(self): 
        self.setMode('replay')
        
        openFilePath = QFileDialog.getOpenFileName(self, "Open Database file", '', '*.db')
        self.openDB(openFilePath[0])
        
        # reads labels and date range from database
        self.readDBLabels()
        self.readDateRange()

        # displays full range
        self.displayTimeBox.setCurrentIndex(1)
        
        # updates UI with new data. Also calls updatePlots
        self.updateTimeRangeMode()

    def closeDatabaseFile(self): 
        self.setMode('startup')

        self.liveUpdateLoopTimer.stop()

        self.db.close()
        self.db = None

        # resets plots
        for channel in self.dataChannels.values():
            self.setLabelTextColor(channel.currentValueDisplay, '---------')
            channel.plot.clear()

    
    def saveLabels(self):
        
        if not self.db:
            self.openDB(f'logs/log{datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")}.db')
            
        self.db.execute("CREATE TABLE IF NOT EXISTS labels(channel PRIMARY KEY, label)")
        
        for channel in self.dataChannels.values():
            if channel.renameLabel:
                if channel.renameLabel.text():
                    channel.label = channel.renameLabel.text()
                self.db.execute("REPLACE INTO labels(channel, label) VALUES (?, ?)", (channel.dbName, channel.label))
                self.db.commit()

                self.configDB.execute("REPLACE INTO labels(channel, label) VALUES (?, ?)", (channel.dbName, channel.label))
                self.configDB.commit()
                
                channel.enableDisplay.setText(channel.label)
                channel.renameLabel.clear()
                channel.renameLabel.setPlaceholderText(channel.label)
        
    def readDBLabels(self, readLocation='default'):
        activeDB = None
        table = 'labels'

        if readLocation == 'default':
            activeDB = self.configDB
            table = 'default_labels'
        elif readLocation == 'config':
            activeDB = self.configDB
        elif readLocation == 'log' and self.db:
            activeDB = self.db

        cur = activeDB.cursor()

        cur.execute(f"SELECT label FROM {table}")
        labels = cur.fetchall()

        if readLocation == 'default':
            cur.execute('DELETE FROM labels')
            cur.execute('REPLACE INTO labels SELECT * FROM default_labels')
            activeDB.commit()
            
        labels = [i[0] for i in labels] # removes single tuples
        
        if labels:
            for label, channel in zip(labels, list(self.dataChannels.values())[:7]):
                channel.label = label

                channel.enableDisplay.setText(channel.label)
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
        df = pd.read_sql_query("SELECT * FROM data_log", self.db)
        
        # sets column headers to the label text
        for channel, column in zip(self.dataChannels.values(), df.columns[1:]):
            # print(f"Renaming channel {channel.dbName} column {column}")
            df.rename(columns={column: channel.label}, inplace=True)
                
        df.to_csv(savePath, index=False)
 
    def importData(self):
        self.setMode('replay')

        openPath = QFileDialog.getOpenFileName(self, "Open CSV file", '', '*.csv')[0]

        df = pd.read_csv(openPath)

        self.openDB(f'logs/csvImport{datetime.datetime.now().strftime("%Y-%m-%d--%H-%M-%S")}.db')

        for channel, column in zip(self.dataChannels.values(), df.columns[1:]):
            # Applies custom label to temp sensors
            if channel.device == 'tempArd':
                channel.label = column
                channel.enableDisplay.setText(channel.label)
                channel.renameLabel.clear()
                channel.renameLabel.setPlaceholderText(channel.label)
            
            # sets column name back to the DB name
            df.rename(columns={column: channel.dbName}, inplace=True)

        df.to_sql('data_log', self.db, index=False)
        self.db.commit()

        # sets the date range based on the imported data
        self.readDateRange()

        # displays full range
        self.displayTimeBox.setCurrentIndex(1)
        self.updateTimeRangeMode() # also calls updatePlots


    # adjusts button enabled/disabled based on new mode
    def setMode(self, newMode: str):
        self.currentMode = newMode
        if newMode == 'startup':
            self.startButton.setEnabled(True)
            self.stopButton.setEnabled(False)
            self.renameButton.setEnabled(True)
            self.exportCSVbutton.setEnabled(False)
            self.importCSVbutton.setEnabled(True)
            self.openDBbutton.setEnabled(True)
            self.closeDBbutton.setEnabled(False)
        if newMode == 'logging':
            self.startButton.setEnabled(False)
            self.stopButton.setEnabled(True)
            self.renameButton.setEnabled(True)
            self.exportCSVbutton.setEnabled(True)
            self.importCSVbutton.setEnabled(False)
            self.openDBbutton.setEnabled(False)
            self.closeDBbutton.setEnabled(False)
        if newMode == 'stopped':
            self.startButton.setEnabled(True)
            self.stopButton.setEnabled(False)
            self.renameButton.setEnabled(True)
            self.exportCSVbutton.setEnabled(True)
            self.importCSVbutton.setEnabled(True)
            self.openDBbutton.setEnabled(True)
            self.closeDBbutton.setEnabled(True)
        if newMode == 'replay':
            self.startButton.setEnabled(False)
            self.stopButton.setEnabled(False)
            self.renameButton.setEnabled(False)
            self.exportCSVbutton.setEnabled(True)
            self.importCSVbutton.setEnabled(True)
            self.openDBbutton.setEnabled(True)
            self.closeDBbutton.setEnabled(True)


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

        self.updatePlots()

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
                if self.currentUnits['pres'] == 'Pa':
                    return int(value * 133.322)
                if self.currentUnits['pres'] == 'inHg':
                    return round(value / 25.4, 2)
                if self.currentUnits['pres'] == 'Atm':
                    return round(value / 760.0, 2)
        return None
    
    def setChillerSetpoint(self):
        newValue = self.chillerSetInput.value()
        writeMessage = f'out_sp_00 {newValue}\r'
        print(f'Setting chiller setpoint to {newValue}. Output: ', self.writeSerialData(self.serialDevices['chiller'], writeMessage))

    def startChiller(self):
        if self.writeSerialData(self.serialDevices['chiller'], 'out_mode_05 1\r'):
            print('Chiller commanded on')
            time.sleep(.05)
            chillerStatus = self.requestSerialData(self.serialDevices['chiller'], 'status\r', 1)
            print('Chiller Status: ', chillerStatus)
            if chillerStatus == '03 REMOTE START': # response if chiller on
                self.startChillerButton.setEnabled(False)
                self.stopChillerButton.setEnabled(True)
        

    def stopChiller(self):
        if self.writeSerialData(self.serialDevices['chiller'], 'out_mode_05 0\r'):
            print('Chiller commanded off')
            time.sleep(.05)
            chillerStatus = self.requestSerialData(self.serialDevices['chiller'], 'status\r', 1)
            print('Chiller Status: ', chillerStatus)
            if chillerStatus == '02 REMOTE STOP': # response if chiller off
                self.startChillerButton.setEnabled(True)
                # self.stopChillerButton.setEnabled(False)

    def ionOn(self):
        response = self.requestSerialData(self.serialDevices['ionGauge'], '#01IG1\r', 1)
        print(f"Commanded on. Ion Gauge Response: {response}")
        # if response == '*01 PROGM OK':
        #     self.ionOnButton.setEnabled(False)
        #     self.ionOffButton.setEnabled(True)

    def ionOff(self):
        response = self.requestSerialData(self.serialDevices['ionGauge'], '#01IG0\r', 1)
        print(f"Commanded off. Ion Gauge Response: {response}")
        # if response == '*01 PROGM OK':
        #     self.ionOnButton.setEnabled(True)
        #     self.ionOffButton.setEnabled(False)

    def getStatus(self):
        print('Ion On/Off: ', self.requestSerialData(self.serialDevices['ionGauge'], '#01IGS\r', 1))
        print('Ion Status: ', self.requestSerialData(self.serialDevices['ionGauge'], '#01RS\r', 1))
        print('Chiller On/Off: ', self.requestSerialData(self.serialDevices['chiller'], 'in_mode_05\r', 1))
        print('Chiller Status: ', self.requestSerialData(self.serialDevices['chiller'], 'status\r', 1))

    def updateEnableStatus(self):
        # disables all devices to start
        for device in self.serialDevices.values():
            device.enabled = False
        
        for channel in self.dataChannels.values():
            if channel.enableDisplay.isChecked():
                channel.enabled = True
                self.serialDevices[channel.device].enabled = True # re-enables device
            else:
                channel.enabled = False
            # print(f"Label Status for {channel.dbName}: {channel.currentValueDisplay.isEnabled()}")


    # sets the text of a label with a given color, black as default
    def setLabelTextColor(self, labelObject, text, color='black'):
        labelObject.setText(text)
        labelObject.setStyleSheet(f'color: {color}; font-size: 16px')

    def openDB(self, filepath):
        # closes database if one currently is open
        if self.db:
            self.db.close()
            
        self.db = sqlite3.connect(filepath)

    def validateIonPressure(self, input):
        if input and input[:3] == '*01': # ensures valid return header
            if input[4:] == '9.99E+09': # checks for default return when gauge off
                return 'Off'
            else:
                return safeFloat(input[4:]) # splits data from return header
        else: 
            return None
        
    def serialLog(self, device, error, message):
        if self.db:
            self.db.execute("CREATE TABLE IF NOT EXISTS serial_log(timestamp, device, error, message)")
            self.db.execute("INSERT INTO serial_log(timestamp, device, error, message) VALUES(?, ?, ?, ?)", (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), device, error, message))
            self.db.commit()
        else:
            print(f"No DB exists to log serial error. Device: {device}   Error: {error}   Message: {message}")


    # returns True if successful, False otherwise
    def writeSerialData(self, serialDevice, dataString):
        try:
            serialDevice.connectionObject.write(bytes(dataString, 'ascii'))
            return True
        except serial.serialutil.PortNotOpenError as e:
            self.serialLog(serialDevice.name, type(e).__name__, str(e))
            try:
                resetConnection(serialDevice)
                print('Second data write: ', dataString)
                serialDevice.connectionObject.write(bytes(dataString, 'ascii'))
                return True
            except (serial.serialutil.SerialException, serial.serialutil.SerialTimeoutException, termios.error) as e:
                self.serialLog(serialDevice.name, type(e).__name__, str(e))
                #print('Failed to reopen connection and write data')
                return False
        except (serial.serialutil.SerialException, serial.serialutil.SerialTimeoutException, termios.error) as e:
            self.serialLog(serialDevice.name, type(e).__name__, str(e))
            return False

    def requestSerialData(self, serialDevice, requestString, minByteLength):
        data = None
        try:
            serialDevice.connectionObject.reset_input_buffer()
            serialDevice.connectionObject.write(bytes(requestString, 'ascii'))
            data = serialDevice.connectionObject.read_until(b'\r')
            dataLen = len(data)
            # print(f'Data: {data} - Data len: {dataLen}')
            if dataLen < minByteLength:
                # log if some data is read
                # print(f'{datetime.datetime.now()}  Return too short   Device: {serialDevice.name}   Data: {data}  Min Length: {minByteLength}   Actual Length: {dataLen}')
                self.serialLog(serialDevice.name, 'Return too short', f'Data: {data}  Min Length: {minByteLength}   Actual Length: {dataLen}')
                return None
            data = data.decode('ascii').strip()
        except serial.serialutil.SerialTimeoutException as e:
            #print(f'{datetime.datetime.now()}  Timeout device {serialDevice.name}: {type(e)} {e}')
            self.serialLog(serialDevice.name, type(e).__name__, str(e))
            return None
        except (serial.serialutil.PortNotOpenError, serial.serialutil.SerialException, termios.error) as e:
            # print(f'{datetime.datetime.now()}  Resetting device {serialDevice.name}: {type(e)} {e}')
            self.serialLog(serialDevice.name, type(e).__name__, str(e))
            try:
                resetConnection(serialDevice)
                return None
            except serial.SerialException:
                return None
        if data:
            return data
        else:
            #print(f'{datetime.datetime.now()}  Data not True   Device: {serialDevice.name}   Data: {data}')
            self.serialLog(serialDevice.name, 'Data not True', f'Data: {data}')
            return None

    # cleanly closes the application
    def closeEvent(self, event):
        print('Closing app')

        # stops updating app
        self.liveUpdateLoopTimer.stop()

        # closes db
        if self.db:
            self.db.commit()
            self.db.close()

        # continues closing GUI
        event.accept()
        
        # closes all serial devices
        for device in self.serialDevices.values():
            # print(f'Canceling write {device.name}')
            device.connectionObject.cancel_write()
            # print(f'Canceling read {device.name}')
            device.connectionObject.cancel_read()
            # print(f'Resetting buffers {device.name}')
            device.connectionObject.reset_input_buffer()
            device.connectionObject.reset_output_buffer()
            print(f'Closing {device.name}')
            device.connectionObject.close()
            #print(f'Closed {device.name}')
        
                
@dataclass       
class dataChannel:
    device: str
    dbName: str
    label: str
    dataCategory: str
    plot: any
    enableDisplay: any
    currentValueDisplay: any
    renameLabel: any = None 
    singlePlot: bool = True
    color: str = 'r'
    currentValue: float = None
    enabled: bool = True
    
@dataclass
class serialDevice:
    name: str
    serialNumber: str
    connectionObject: serial.Serial
    enabled: bool = False

    
def getDevicePath(serialNumber):
    for port in serial.tools.list_ports.comports():
        if port.serial_number == serialNumber:
            return port.device
        
def resetConnection(serialDevice):
    serialDevice.connectionObject.close()
    serialDevice.connectionObject.port = getDevicePath(serialDevice.serialNumber)
    serialDevice.connectionObject.open()

                
# Converts a epoch timestamp (float) to a QDateTime object
def QDateTimeFromTimestamp(timestamp):
    dt = QDateTime(0,0,0,0,0) # placeholder
    dt.setSecsSinceEpoch(round(timestamp))
    return dt

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
    app = QApplication([])
    
    mainApp = mainApp()
    mainApp.show()
    
    sys.exit(app.exec())