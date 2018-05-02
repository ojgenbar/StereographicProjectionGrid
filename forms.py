import os

from PyQt4 import QtGui, uic


MAIN_FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'main.ui'))
GRID_FORM_CLASS, _ = uic.loadUiType(os.path.join(os.path.dirname(__file__), 'grid.ui'))


class MainForm(QtGui.QDialog, MAIN_FORM_CLASS):
    def __init__(self, parent=None):
        super(MainForm, self).__init__(parent)
        self.setupUi(self)


class GridForm(QtGui.QDialog, GRID_FORM_CLASS):
    def __init__(self, parent=None):
        super(GridForm, self).__init__(parent)
        self.setupUi(self)
