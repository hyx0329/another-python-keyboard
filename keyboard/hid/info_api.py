# -*- encoding: utf-8 -*-
# vim: set ts=4 noexpandtab
from ..utils import is_usb_connected

class HIDInfo:
    # wrap HIDDeviceManager, provide a consistent interface for hardware module
    def __init__(self, manager):
        self._manager = manager

    @property
    def usb_connected(self):
        # if USB is connected
        return is_usb_connected()

    @property
    def ble_connected(self):
        # if BLE is connected
        if self._manager._ble_radio is not None:
            return self._manager._ble_radio.connected
        else:
            return False

    @property
    def ble_advertising(self):
        # if is advertising
        if self._manager._ble_radio is not None:
            return self._manager._ble_advertisement_started or self._manager._ble_radio.advertising
        else:
            return False

    @property
    def ble_id(self):
        # current BLE ID, 0 to 9
        return self._manager._ble_id

    @property
    def keyboard_led(self):
        # keyboard led raw data
        return self._manager.keyboard_led_status

    def set_battery_level(self, value: int):
        if self._manager._ble_battery is not None:
            self._manager._ble_battery.value = max(0, min(100, value))

