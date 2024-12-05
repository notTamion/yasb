import re
import logging
import time

import homematicip
from core.widgets.base import BaseWidget
from core.validation.widgets.yasb.heater import VALIDATION_SCHEMA
from PyQt6.QtWidgets import QLabel, QHBoxLayout, QWidget
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QWheelEvent
from homematicip.device import HeatingThermostat
from homematicip.group import HeatingGroup
from homematicip.home import Home
# Disable comtypes logging
logging.getLogger('comtypes').setLevel(logging.CRITICAL)
logging.getLogger('homematicip').setLevel(logging.CRITICAL)
 
class HeaterWidget(BaseWidget):
    validation_schema = VALIDATION_SCHEMA
    update_label_signal = pyqtSignal()

    def __init__(
        self,
        label: str,
        label_alt: str,
        heater_icon: str,
        callbacks: dict[str, str]
    ):
        super().__init__(timer_interval=5000, class_name="heater-widget")
        self._show_alt_label = False
        self._label_content = label
        self._label_alt_content = label_alt

        self.heatingGroup = None
        self.lastFetch = time.time()
        self.lastChange = None
        self._display_set = False
        self._heater_icon = heater_icon
        self._widget_container_layout: QHBoxLayout = QHBoxLayout()
        self._widget_container_layout.setSpacing(0)
        self._widget_container_layout.setContentsMargins(0, 0, 0, 0)
        self._widget_container: QWidget = QWidget()
        self._widget_container.setLayout(self._widget_container_layout)
        self._widget_container.setProperty("class", "widget-container")
        self.widget_layout.addWidget(self._widget_container)
        self._create_dynamically_label(self._label_content, self._label_alt_content)
        self.register_callback("toggle_label", self._toggle_label)
        self.register_callback("update_label", self._update_label)
        self.callback_right = callbacks["on_right"]
        self.callback_middle = callbacks["on_middle"]
        self.callback_timer = "update_label"

        self._initialize_homematic_interface()
        self.update_label_signal.connect(self._update_label)
        
        self._update_label()
        self.start_timer()

    def _toggle_label(self):
        self._show_alt_label = not self._show_alt_label
        for widget in self._widgets:
            widget.setVisible(not self._show_alt_label)
        for widget in self._widgets_alt:
            widget.setVisible(self._show_alt_label)
        self._update_label()

    def _create_dynamically_label(self, content: str, content_alt: str):
        def process_content(content, is_alt=False):
            label_parts = re.split('(<span.*?>.*?</span>)', content)
            label_parts = [part for part in label_parts if part]
            widgets = []
            for part in label_parts:
                part = part.strip()
                if not part:
                    continue
                if '<span' in part and '</span>' in part:
                    class_name = re.search(r'class=(["\'])([^"\']+?)\1', part)
                    class_result = class_name.group(2) if class_name else 'icon'
                    icon = re.sub(r'<span.*?>|</span>', '', part).strip()
                    label = QLabel(icon)
                    label.setProperty("class", class_result)
                else:
                    label = QLabel(part)
                    label.setProperty("class", "label")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self._widget_container_layout.addWidget(label)
                widgets.append(label)
                if is_alt:
                    label.hide()
                else:
                    label.show()
            return widgets
        self._widgets = process_content(content)
        self._widgets_alt = process_content(content_alt, is_alt=True)

    def _update_label(self):
        if self.lastChange is not None and self.lastChange + 5 < time.time():
            self.lastChange = None
            self.heatingGroup.set_point_temperature(self.heatingGroup.setPointTemperature)
        active_widgets = self._widgets_alt if self._show_alt_label else self._widgets
        active_label_content = self._label_alt_content if self._show_alt_label else self._label_content
        label_parts = re.split('(<span.*?>.*?</span>)', active_label_content)
        label_parts = [part for part in label_parts if part]
        widget_index = 0
        try:
            icon_volume = self._heater_icon
            if self.lastChange is not None:
                level_volume = f'{self.heatingGroup.setPointTemperature}°C'
            else:
                level_volume = f'{self.heatingGroup.actualTemperature}°C'
            self._display_set = False
        except Exception:
            icon_volume, level_volume = "N/A", "N/A"

        label_options = {
            "{icon}": icon_volume,
            "{level}": level_volume
        }

        for part in label_parts:
            part = part.strip()
            if part:
                formatted_text = part
                for option, value in label_options.items():
                    formatted_text = formatted_text.replace(option, str(value))
                if '<span' in part and '</span>' in part:
                    if widget_index < len(active_widgets) and isinstance(active_widgets[widget_index], QLabel):
                        active_widgets[widget_index].setText(formatted_text)
                else:
                    if widget_index < len(active_widgets) and isinstance(active_widgets[widget_index], QLabel):
                        active_widgets[widget_index].setText(formatted_text)
                widget_index += 1

    def _increase_temperature(self):
        self.heatingGroup.setPointTemperature += 0.5
        self.lastChange = time.time()
        self._update_label()

    def _decrease_temperature(self):
        self.heatingGroup.setPointTemperature -= 0.5
        self.lastChange = time.time()
        self._update_label()

    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self._increase_temperature()
        elif event.angleDelta().y() < 0:
            self._decrease_temperature()

    def _initialize_homematic_interface(self):
        config = homematicip.find_and_load_config_file()
        self.home = Home()
        self.home.set_auth_token(config.auth_token)
        self.home.init(config.access_point)
        self.home.get_current_state()
        self.home.onEvent += self.handle_event
        self.home.enable_events()
        for group in self.home.groups:
            if isinstance(group, HeatingGroup):
                for device in group.devices:
                    if isinstance(device, HeatingThermostat):
                        if str(device.label).startswith("Simon"):
                            self.heatingGroup = group

    def handle_event(self, event_list):
        for event in event_list:
            if event["eventType"] == "GROUP_CHANGED":
                data = event["data"]
                if isinstance(data, HeatingGroup):
                    if str(data.label).startswith("Simon"):
                        if self.lastChange is None:
                            self.heatingGroup.actualTemperature = data.actualTemperature
                            self.heatingGroup.setPointTemperature = data.setPointTemperature