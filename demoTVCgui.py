from PyQt6 import uic
from PyQt6.QtWidgets import QApplication
import sys

Form, Window = uic.loadUiType("demoTVCgui.ui")

app = QApplication([])
window = Window()

form = Form()
form.setupUi(window)

window.show()
sys.exit(app.exec())