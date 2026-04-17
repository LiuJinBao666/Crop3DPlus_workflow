try:
    from PySide6 import QtCore, QtGui, QtWidgets

    QT_API = "PySide6"
except ImportError:
    from PySide2 import QtCore, QtGui, QtWidgets

    QT_API = "PySide2"


Signal = QtCore.Signal
Slot = QtCore.Slot

