import os
import json
import pathlib

import keyboard
from PyQt5 import QtCore, QtGui, QtWidgets

from overlay.custom_widgets import CustomKeySequenceEdit, OverlayWidget
from overlay.logging_func import catch_exceptions, get_logger
from overlay.settings import settings

from overlay.build_order_tools import check_valid_aoe4_build_order_from_string, MultiQLabelDisplay

logger = get_logger(__name__)


class BuildOrderOverlay(QtWidgets.QMainWindow):
    """Overlay widget showing the selected build order"""

    def __init__(self, parent=None):
        """Constructor

        Parameters
        ----------
        parent    parent of the widget
        """
        super().__init__(parent)
        self.show()

        file_path = str(pathlib.Path(__file__).parent.resolve())
        self.directory_game_pictures = os.path.join(file_path, '..', 'img', 'build_order')  # game pictures

        # color and opacity
        self.setStyleSheet(
            f'background-color: rgb({settings.bo_color_background[0]}, {settings.bo_color_background[1]},'
            f'{settings.bo_color_background[2]})')
        self.setWindowOpacity(settings.bo_opacity)

        # window is transparent and stays on top
        self.setWindowFlags(QtCore.Qt.FramelessWindowHint
                            | QtCore.Qt.WindowTransparentForInput
                            | QtCore.Qt.WindowStaysOnTopHint
                            | QtCore.Qt.CoverWindow
                            | QtCore.Qt.NoDropShadowWindowHint
                            | QtCore.Qt.WindowDoesNotAcceptFocus)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)

        # build order display
        self.build_order_notes = MultiQLabelDisplay(
            font_police='Arial', font_size=settings.bo_font_size, image_height=30, border_size=15, vertical_spacing=10,
            color_default=[255, 255, 255], game_pictures_folder=self.directory_game_pictures)

        self.show()

    def update_build_order_display(self, data: dict):
        self.build_order_notes.clear()
        if 'notes' in data:
            notes = data['notes']
            for note in notes:
                self.build_order_notes.add_row_from_picture_line(parent=self, line=note)

        self.build_order_notes.update_size_position()

        self.resize(self.build_order_notes.row_max_width + 30, self.build_order_notes.row_total_height + 30)

        self.build_order_notes.show()

    def show_hide(self):
        self.hide() if self.isVisible() else self.show()


class BoTab(QtWidgets.QWidget):
    show_hide_overlay = QtCore.pyqtSignal()
    cycle_build_order = QtCore.pyqtSignal()
    previous_step_build_order = QtCore.pyqtSignal()
    next_step_build_order = QtCore.pyqtSignal()

    def __init__(self, parent):
        super().__init__(parent)

        self.build_order_step = -1  # step of the build order, negative if not valid
        self.build_order_step_count = -1  # number of steps in the build order, negative if not valid

        self.overlay = BuildOrderOverlay()
        self.initUI()
        self.init_hotkeys()

        # Connect signals
        self.show_hide_overlay.connect(self.overlay.show_hide)
        self.cycle_build_order.connect(self.cycle_overlay)
        self.previous_step_build_order.connect(self.select_previous_build_order_step)
        self.next_step_build_order.connect(self.select_next_build_order_step)

        self.update_overlay()

    def init_hotkeys(self):
        if settings.bo_overlay_hotkey_show:
            try:
                self.key_showhide.setKeySequence(
                    QtGui.QKeySequence.fromString(
                        settings.bo_overlay_hotkey_show))
                keyboard.add_hotkey(settings.bo_overlay_hotkey_show,
                                    self.show_hide_overlay.emit)
            except Exception:
                logger.exception("Failed to set hotkey")
                settings.bo_overlay_hotkey_show = ""
                self.key_showhide.setKeySequence(
                    QtGui.QKeySequence.fromString(""))

        if settings.bo_overlay_hotkey_cycle:
            try:
                self.key_cycle.setKeySequence(
                    QtGui.QKeySequence.fromString(
                        settings.bo_overlay_hotkey_cycle))
                keyboard.add_hotkey(settings.bo_overlay_hotkey_cycle,
                                    self.cycle_build_order.emit)
            except Exception:
                logger.exception("Failed to set hotkey")
                settings.bo_overlay_hotkey_cycle = ""
                self.key_cycle.setKeySequence(
                    QtGui.QKeySequence.fromString(""))

        if settings.bo_overlay_hotkey_previous_step:
            try:
                self.key_previous_step.setKeySequence(
                    QtGui.QKeySequence.fromString(
                        settings.bo_overlay_hotkey_previous_step))
                keyboard.add_hotkey(settings.bo_overlay_hotkey_previous_step,
                                    self.previous_step_build_order.emit)
            except Exception:
                logger.exception("Failed to set hotkey")
                settings.bo_overlay_hotkey_previous_step = ""
                self.key_previous_step.setKeySequence(
                    QtGui.QKeySequence.fromString(""))

        if settings.bo_overlay_hotkey_next_step:
            try:
                self.key_next_step.setKeySequence(
                    QtGui.QKeySequence.fromString(
                        settings.bo_overlay_hotkey_next_step))
                keyboard.add_hotkey(settings.bo_overlay_hotkey_next_step,
                                    self.next_step_build_order.emit)
            except Exception:
                logger.exception("Failed to set hotkey")
                settings.bo_overlay_hotkey_next_step = ""
                self.key_next_step.setKeySequence(
                    QtGui.QKeySequence.fromString(""))

    def initUI(self):
        hlayout = QtWidgets.QHBoxLayout()
        self.setLayout(hlayout)

        # Text edit field
        self.edit = QtWidgets.QTextEdit()
        hlayout.addWidget(self.edit)

        ### Build order controls
        controls = QtWidgets.QFrame()
        controls.setMaximumWidth(350)
        clayout = QtWidgets.QVBoxLayout()
        clayout.setContentsMargins(0, 0, 0, 0)
        controls.setLayout(clayout)
        hlayout.addWidget(controls)

        # Renaming build orders
        self.rename_widget = QtWidgets.QLineEdit()
        self.rename_widget.setToolTip("Rename build order here")
        self.rename_widget.setTextMargins(3, 0, 0, 0)
        clayout.addWidget(self.rename_widget)

        # Build order list
        self.bo_list = QtWidgets.QListWidget()
        clayout.addWidget(self.bo_list)
        for name in settings.build_orders:
            self.bo_list.addItem(name)
        self.bo_list.currentItemChanged.connect(self.bo_selected)
        self.bo_list.setCurrentRow(0)

        # Add build orders
        add_bo_btn = QtWidgets.QPushButton("Add build order")
        add_bo_btn.clicked.connect(self.add_build_order)
        clayout.addWidget(add_bo_btn)

        # Remove build order
        remove_bo_btn = QtWidgets.QPushButton("Remove build order")
        remove_bo_btn.clicked.connect(self.remove_build_order)
        clayout.addWidget(remove_bo_btn)

        clayout.addSpacing(30)
        age4builder = QtWidgets.QLabel(
            'Find & copy build orders from <a href="https://age4builder.com/">age4builder.com</a>'
        )
        age4builder.setOpenExternalLinks(True)
        clayout.addWidget(age4builder)

        clayout.addSpacing(10)

        ### Overlay controls
        overlay_box = QtWidgets.QGroupBox("Overlay")
        overlay_layout = QtWidgets.QGridLayout()
        overlay_box.setLayout(overlay_layout)
        clayout.addWidget(overlay_box)

        # Show/hide hotkey
        key_label = QtWidgets.QLabel("Hotkey for showing and hiding overlay:")
        overlay_layout.addWidget(key_label, 0, 0)

        self.key_showhide = CustomKeySequenceEdit(self)
        self.key_showhide.setMaximumWidth(100)
        self.key_showhide.setToolTip("Hotkey for showing and hiding overlay")
        overlay_layout.addWidget(self.key_showhide, 0, 1)
        self.key_showhide.key_changed.connect(self.show_hotkey_changed)

        # Cycle hotkey
        key_label = QtWidgets.QLabel("Hotkey for cycling build orders:")
        overlay_layout.addWidget(key_label, 1, 0)

        self.key_cycle = CustomKeySequenceEdit(self)
        self.key_cycle.setMaximumWidth(100)
        self.key_cycle.setToolTip("Hotkey for cycling build orders")
        overlay_layout.addWidget(self.key_cycle, 1, 1)
        self.key_cycle.key_changed.connect(self.cycle_hotkey_changed)

        # Previous build order step hotkey
        key_label = QtWidgets.QLabel("Hotkey to go to previous step:")
        overlay_layout.addWidget(key_label, 2, 0)

        self.key_previous_step = CustomKeySequenceEdit(self)
        self.key_previous_step.setMaximumWidth(100)
        self.key_previous_step.setToolTip("Hotkey to go to the previous step of the build order.")
        overlay_layout.addWidget(self.key_previous_step, 2, 1)
        self.key_previous_step.key_changed.connect(self.previous_step_hotkey_changed)

        # Next build order step hotkey
        key_label = QtWidgets.QLabel("Hotkey to go to next step:")
        overlay_layout.addWidget(key_label, 3, 0)

        self.key_next_step = CustomKeySequenceEdit(self)
        self.key_next_step.setMaximumWidth(100)
        self.key_next_step.setToolTip("Hotkey to go to the next step of the build order.")
        overlay_layout.addWidget(self.key_next_step, 3, 1)
        self.key_next_step.key_changed.connect(self.next_step_hotkey_changed)

        # Overlay font
        font_label = QtWidgets.QLabel("Overlay font size:")
        overlay_layout.addWidget(font_label, 4, 0)

        self.font_size_combo = QtWidgets.QComboBox()
        for i in range(1, 50):
            self.font_size_combo.addItem(f"{i} pt")
        self.font_size_combo.setCurrentIndex(settings.bo_font_size - 1)
        self.font_size_combo.currentIndexChanged.connect(
            self.font_size_changed)
        overlay_layout.addWidget(self.font_size_combo, 4, 1)

        # Position change button
        self.btn_change_position = QtWidgets.QPushButton(
            "Change/fix overlay position")
        self.btn_change_position.setToolTip(
            "Click to change overlay position. Click again to fix its position."
        )
        # self.btn_change_position.clicked.connect(self.overlay.change_state)
        overlay_layout.addWidget(self.btn_change_position, 5, 0, 1, 2)

    def save_current_bo(self):
        bo_name = self.bo_list.currentItem().text()
        bo_text = self.edit.toPlainText()
        settings.build_orders[bo_name] = bo_text
        self.update_overlay()

    def bo_selected(self, item: QtWidgets.QListWidgetItem):
        # Try disconnecting signals (throws an error when nothing connected)
        try:
            self.edit.disconnect()
        except TypeError:
            pass
        try:
            self.rename_widget.disconnect()
        except TypeError:
            pass

        # Change values
        self.rename_widget.setText(item.text())
        self.edit.setText(settings.build_orders.get(item.text(), ""))
        self.update_overlay()

        # Reconnect signals
        self.edit.textChanged.connect(self.save_current_bo)
        self.rename_widget.textChanged.connect(self.name_changed)

    def name_changed(self, text: str):
        self.bo_list.currentItem().setText(text)

        # Remove the old build order
        rows = self.bo_list.count()
        bo_names = {self.bo_list.item(i).text() for i in range(rows)}
        for name in settings.build_orders:
            if name not in bo_names:
                del settings.build_orders[name]
                break

        # Add the new build order
        self.save_current_bo()

    def add_build_order(self):
        self.bo_list.addItem(f"Build order {self.bo_list.count() + 1}")
        self.bo_list.setCurrentRow(self.bo_list.count() - 1)
        self.save_current_bo()

    def remove_build_order(self):
        if self.bo_list.count() == 1:
            return
        del settings.build_orders[self.bo_list.currentItem().text()]
        self.bo_list.takeItem(self.bo_list.currentRow())

    def font_size_changed(self, font_index: int):
        settings.bo_font_size = font_index + 1
        self.overlay.update_style(font_index + 1)

    def show_hotkey_changed(self, new_hotkey: str):
        """ Checks whether the hotkey is actually new and valid.
        Updates keyboard threads"""
        old_hotkey = settings.bo_overlay_hotkey_show
        new_hotkey = CustomKeySequenceEdit.convert_hotkey(new_hotkey.lower())

        if new_hotkey == "Del":
            self.key_showhide.setKeySequence(QtGui.QKeySequence.fromString(""))
            settings.bo_overlay_hotkey_show = ""
            return
        elif not new_hotkey or new_hotkey == settings.bo_overlay_hotkey_show:
            return

        try:
            keyboard.add_hotkey(new_hotkey, self.show_hide_overlay.emit)
            if settings.bo_overlay_hotkey_show:
                keyboard.remove_hotkey(settings.bo_overlay_hotkey_show)
            settings.bo_overlay_hotkey_show = new_hotkey
            logger.info(f"Setting new build order show hotkey to: {new_hotkey}")
        except Exception:
            logger.exception(f"Failed to set hotkey: {new_hotkey}")
            self.key_showhide.setKeySequence(
                QtGui.QKeySequence.fromString(old_hotkey))

    def cycle_hotkey_changed(self, new_hotkey: str):
        """ Checks whether the hotkey is actually new and valid.
        Updates keyboard threads"""
        old_hotkey = settings.bo_overlay_hotkey_cycle
        new_hotkey = CustomKeySequenceEdit.convert_hotkey(new_hotkey.lower())

        if new_hotkey == "Del":
            self.key_cycle.setKeySequence(QtGui.QKeySequence.fromString(""))
            settings.bo_overlay_hotkey_cycle = ""
            return
        elif not new_hotkey or new_hotkey == settings.bo_overlay_hotkey_cycle:
            return

        try:
            keyboard.add_hotkey(new_hotkey, self.cycle_build_order.emit)
            if settings.bo_overlay_hotkey_cycle:
                keyboard.remove_hotkey(settings.bo_overlay_hotkey_cycle)
            settings.bo_overlay_hotkey_cycle = new_hotkey
            logger.info(
                f"Setting new build order cycle hotkey to: {new_hotkey}")
        except Exception:
            logger.exception(f"Failed to set hotkey: {new_hotkey}")
            self.key_cycle.setKeySequence(
                QtGui.QKeySequence.fromString(old_hotkey))

    def previous_step_hotkey_changed(self, new_hotkey: str):
        """ Checks whether the hotkey is actually new and valid.
        Updates keyboard threads"""
        old_hotkey = settings.bo_overlay_hotkey_previous_step
        new_hotkey = CustomKeySequenceEdit.convert_hotkey(new_hotkey.lower())

        if new_hotkey == "Del":
            self.key_previous_step.setKeySequence(QtGui.QKeySequence.fromString(""))
            settings.bo_overlay_hotkey_previous_step = ""
            return
        elif not new_hotkey or new_hotkey == settings.bo_overlay_hotkey_previous_step:
            return

        try:
            keyboard.add_hotkey(new_hotkey, self.previous_step_build_order.emit)
            if settings.bo_overlay_hotkey_previous_step:
                keyboard.remove_hotkey(settings.bo_overlay_hotkey_previous_step)
            settings.bo_overlay_hotkey_previous_step = new_hotkey
            logger.info(
                f"Setting new build order cycle hotkey to: {new_hotkey}")
        except Exception:
            logger.exception(f"Failed to set hotkey: {new_hotkey}")
            self.key_previous_step.setKeySequence(
                QtGui.QKeySequence.fromString(old_hotkey))

    def next_step_hotkey_changed(self, new_hotkey: str):
        """ Checks whether the hotkey is actually new and valid.
        Updates keyboard threads"""
        old_hotkey = settings.bo_overlay_hotkey_next_step
        new_hotkey = CustomKeySequenceEdit.convert_hotkey(new_hotkey.lower())

        if new_hotkey == "Del":
            self.key_next_step.setKeySequence(QtGui.QKeySequence.fromString(""))
            settings.bo_overlay_hotkey_next_step = ""
            return
        elif not new_hotkey or new_hotkey == settings.bo_overlay_hotkey_next_step:
            return

        try:
            keyboard.add_hotkey(new_hotkey, self.next_step_build_order.emit)
            if settings.bo_overlay_hotkey_next_step:
                keyboard.remove_hotkey(settings.bo_overlay_hotkey_next_step)
            settings.bo_overlay_hotkey_next_step = new_hotkey
            logger.info(
                f"Setting new build order cycle hotkey to: {new_hotkey}")
        except Exception:
            logger.exception(f"Failed to set hotkey: {new_hotkey}")
            self.key_next_step.setKeySequence(
                QtGui.QKeySequence.fromString(old_hotkey))

    def limit_build_order_step(self):
        if self.build_order_step_count < 1:
            self.build_order_step = -1
            self.build_order_step_count = -1
        elif self.build_order_step < 0:
            self.build_order_step = 0
        elif self.build_order_step >= self.build_order_step_count:
            self.build_order_step = self.build_order_step_count - 1

    def select_previous_build_order_step(self):
        init_build_order_step = self.build_order_step
        self.build_order_step -= 1
        self.limit_build_order_step()
        if (init_build_order_step != self.build_order_step) and (self.build_order_step >= 0):
            self.update_overlay()

    def select_next_build_order_step(self):
        init_build_order_step = self.build_order_step
        self.build_order_step += 1
        self.limit_build_order_step()
        if (init_build_order_step != self.build_order_step) and (self.build_order_step >= 0):
            self.update_overlay()

    def update_overlay(self):
        """Send new data to the overlay"""
        if self.bo_list.count():
            bo_name = self.bo_list.currentItem().text()
            bo_text = self.edit.toPlainText()
            valid_check = check_valid_aoe4_build_order_from_string(bo_text)
            if valid_check:
                data = json.loads(bo_text)
                self.build_order_step_count = len(data['build_order'])
                self.limit_build_order_step()
                self.overlay.update_build_order_display(data['build_order'][self.build_order_step])
            else:
                self.build_order_step = -1
                self.build_order_step_count = -1
                self.overlay.update_build_order_display({'txt': bo_text})

    def cycle_overlay(self):
        """ Cycles through build orders and sends data to the overlay"""
        # Update widget (move to higher row)
        count = self.bo_list.count()
        # This also automatically update overlay
        self.bo_list.setCurrentRow((self.bo_list.currentRow() + 1) % count)
        self.overlay.show()
