from audio_plot_ui import Ui_MainWindow

from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import uic
from PyQt5.QtCore import pyqtSlot
from PyQt5.QtMultimedia import QAudioDeviceInfo, QAudio, QCameraInfo

import sys, matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as ticker
import queue
import numpy
import sounddevice as sd

inputAudioDevices = QAudioDeviceInfo.availableDevices(QAudio.AudioInput)

class mplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = fig.add_subplot(111)
        super(mplCanvas, self).__init__(fig)
        fig.tight_layout()

class MainWindow(qtw.QMainWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        
        self.threadpool = qtc.QThreadPool()
        self.deviceNames = []
        for device in inputAudioDevices:
            self.deviceNames.append(device.deviceName())
            
        self.ui.audioDeviceBox.addItems(self.deviceNames)
        self.ui.audioDeviceBox.currentIndexChanged['QString'].connect(self.update)
        self.ui.audioDeviceBox.setCurrentIndex(0)
        
        self.canvas = mplCanvas(self, width=5, height=4, dpi=100)
        self.ui.gridLayout.addWidget(self.canvas, 2, 1, 1, 1)
        self.reference_plot = None
        self.q = queue.Queue(maxsize=20)

        self.device = self.devices_list[0]
        self.window_length = 1000
        self.downsample = 1
        self.channels = [1]
        self.interval = 30 
        
        device_info = sd.query_devices(self.devices, 'input')
        self.samplerate = device_info['default_samplerate']
        
if __name__ == '__main__':
    app = qtw.QApplication([])
    
    window = MainWindow()
    window.show()
    
    app.exec_()