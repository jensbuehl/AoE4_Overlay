from PyQt5 import QtCore, QtGui, QtWidgets


class CustomKeySequenceEdit(QtWidgets.QKeySequenceEdit):
    key_changed = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(CustomKeySequenceEdit, self).__init__(parent)

    def keyPressEvent(self, QKeyEvent):
        super(CustomKeySequenceEdit, self).keyPressEvent(QKeyEvent)
        value = self.keySequence()
        self.setKeySequence(QtGui.QKeySequence(value))
        self.key_changed.emit(value.toString())


class OverlayWidget(QtWidgets.QWidget):
    """Custom overlay widget"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fixed: bool = True
        self.set_state(translucent=True)

    def __post_init__(self):
        self.old_pos: QtCore.QPoint = self.pos()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        """ Override used for window dragging"""
        self.old_pos = event.globalPos()

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        """ Override used for window dragging"""
        delta = QtCore.QPoint(event.globalPos() - self.old_pos)
        self.move(self.x() + delta.x(), self.y() + delta.y())
        self.old_pos = event.globalPos()

    def show_hide(self):
        self.hide() if self.isVisible() else self.show()

    def save_geometry(self):
        ...

    def set_state(self, translucent: bool):
        if translucent:
            self.setWindowFlags(QtCore.Qt.FramelessWindowHint
                                | QtCore.Qt.WindowTransparentForInput
                                | QtCore.Qt.WindowStaysOnTopHint
                                | QtCore.Qt.CoverWindow
                                | QtCore.Qt.NoDropShadowWindowHint
                                | QtCore.Qt.WindowDoesNotAcceptFocus)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        else:
            self.setWindowFlags(QtCore.Qt.Window
                                | QtCore.Qt.CustomizeWindowHint
                                | QtCore.Qt.WindowTitleHint)
            self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)

    def change_state(self):
        """ Changes the widget to be movable or not"""
        self.show()
        pos = self.pos()
        if self.fixed:
            self.fixed = False
            self.set_state(translucent=False)
            self.move(pos.x() - 8, pos.y() - 31)
        else:
            self.fixed = True
            self.set_state(translucent=True)
            self.move(pos.x() + 8, pos.y() + 31)
            self.save_geometry()
        self.show()
