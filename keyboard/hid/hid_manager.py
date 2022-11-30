# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

# This module wraps high-level HID API provided by usb_hid and BLERadio

import struct
import time
import microcontroller
import adafruit_logging as logging
logger = logging.getLogger("HID Manager")
logger.setLevel(logging.DEBUG)

from .hid_wrapper import wrap_hid_interface

# USB interface
import usb_hid

# Bluetooth LE interface
try:
	import _bleio
	from adafruit_ble import BLERadio
	#from adafruit_ble.advertising import Advertisement
	from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
	from adafruit_ble.services.standard import BatteryService
	from adafruit_ble.services.standard.hid import HIDService
	BLE_AVAILABLE = True
except:
	BLE_AVAILABLE = False

# tools
from ..utils import do_nothing, is_usb_connected


class HIDDeviceManager:
	# This is a composed HID device manager
	# should be transparent to upper level
	# Provides control over keyboard and mouse
	# gamepad should be possible as long as the descriptor is correctly configured
	# The actual hid action is performed by hid wrapper

	## initialization

	def __init__(self, *args,
				nkro_usb = False,
				enable_ble = True,
				ble_battery_report = False,
				**kwargs):
		self._interfaces = dict()
		self._nkro_usb = nkro_usb
		self._nkro_ble = False
		# initialize interfaces and activate a proper one
		self.__initialize_usb_interface()
		if enable_ble and BLE_AVAILABLE:
			self.__initialize_ble_interface(battery = ble_battery_report)
		self.current_interface = self._auto_select_device()
	
	def get_all_tasks(self):
		# get tasks to run
		# TODO: coroutine to check USB and BLE connections, switch accordingly
		tasks = list()
		return tasks

	def __initialize_usb_interface(self):
		logger.debug("Initializing USB HID interface")
		self._interfaces["usb"] = wrap_hid_interface(usb_hid.devices, self._nkro_usb)

	def __initialize_ble_interface(self, battery = False):
		# The bluetooth hid interface uses predefined descriptor consists of
		# keyboard, mouse, and consumer control (read HIDDevice's doc)
		# to add a gamepad, need to write a suitable descriptor
		logger.debug("Initializing BLE HID interface")
		self._ble_radio = BLERadio()
		ble_services = list()
		self._hid_ble_handle = HIDService()
		self._interfaces["ble"] = wrap_hid_interface(self._hid_ble_handle.devices, self._nkro_ble)
		ble_services.append(self._hid_ble_handle)
		if battery:
			self._ble_battery = BatteryService()
			self._ble_battery.level = 100
			ble_services.append(self._ble_battery)
		self._ble_advertisement = ProvideServicesAdvertisement(*ble_services)
		self._ble_advertisement.appearance = 961 # keyboard
		self._ble_name_prefix = "PYKB" # TODO: better naming?
		self._ble_id = 1
		self._ble_advertise_stop_time = -1

	def _auto_select_device(self):
		# Connected USB > BLE > Disconnect USB
		if self._interfaces.get("usb", None) and is_usb_connected():
			logger.debug("Auto select interface: USB")
			return self._interfaces.get("usb")
		elif self._interfaces.get("ble", None):
			logger.debug("Auto select interface: BLE")
			return self._interfaces.get("ble")
		elif self._interfaces.get("usb", None):
			logger.debug("Auto select interface: USB")
			return self._interfaces.get("usb")
		raise RuntimeError("No valid interface!")
	
	def _ble_generate_static_mac(self, n):
		n = abs(n) & 10
		if not hasattr(self, "_ble_mac_pool"):
			uid = microcontroller.cpu.uid
			for i in range(3):
				uid[i], uid[-(i+1)] = uid[-(i+1)], uid[i]
			uid = microcontroller.cpu.uid + uid
			self._ble_mac_pool = uid
		mac = self._ble_mac_pool[n:n+6]
		mac[-1] &= 0xC0
		address = _bleio.Address(mac, _bleio.Address.RANDOM_STATIC)
		return address

	## (USB &) BLE interface control

	async def switch_to_usb(self):
		interface = self._interfaces.get("usb", None)
		if interface:
			logger.info("Switching to USB")
			await self.release_all()
			self.current_interface = interface

	async def switch_to_ble(self):
		interface = self._interfaces.get("ble", None)
		if interface:
			logger.info("Switching to BLE(%d)" % self._ble_id)
			await self._release_all()
			if not self.ble_is_connected:
				self.ble_advertisement_start(timeout = 60)

	async def ble_switch_to(self, bt_id = -1):
		if not hasattr(self, "_hid_ble"):
			return

		bt_id = abs(bt_id) % 10 # limit it
		if self._ble_id == bt_id:
			# if not connected, advertise, switch to bt
			await self.switch_to_ble()
			return

		# stop advertising and disconnect all
		await self.ble_advertisement_stop()
		await self.ble_disconnect_all()

		# change name and MAC
		try:
			self._ble_radio._adapter.address = self._ble_generate_static_mac(bt_id)
			_name = "%s %s" % self._ble_name_prefix, bt_id
			self._ble_radio.name = _name
			self._ble_advertisement.complete_name = _name
			self._ble_id = bt_id
		except Exception as e:
			print(e)
		# restart advertising will be done by check
		await self.switch_to_ble()

	async def ble_advertisement_start(self, timeout = 60):
		self._ble_radio.start_advertising(self._ble_advertisement)
		if timeout > 0:
			self._ble_advertise_stop_time = time.time() + timeout

	async def ble_advertisement_stop(self):
		try:
			self._ble_radio.stop_advertising()
			self._ble_advertise_stop_time = -1
		except Exception as e:
			print(e)

	async def ble_is_connected(self):
		return self._ble_radio.connected

	async def ble_disconnect_all(self):
		if self._ble_radio.connected:
			for c in self._ble_radio.connections:
				c.disconnect()

	async def ble_set_battery_level(self, value: int):
		if hasattr(self._ble_battery):
			self._ble_battery.value = max(0, min(100, value))

	## HID control API mirrored from interface wrapper

	async def release_all(self):
		self.current_interface.release_all()

	async def keyboard_press(self, *keycodes):
		await self.current_interface.keyboard_press(*keycodes)

	async def keyboard_release(self, *keycodes):
		await self.current_interface.keyboard_release(*keycodes)

	async def consumer_control_press(self, keycode):
		await self.current_interface.consumer_control_press(keycode)
	
	async def consumer_control_release(self, keycode):
		await self.current_interface.consumer_control_release(keycode)

	async def mouse_press(self, buttons):
		await self.current_interface.mouse_press(buttons)

	async def mouse_release(self, buttons):
		await self.current_interface.mouse_release(buttons)

	async def mouse_move(self, buttons, x=0, y=0, wheel=0):
		await self.current_interface.mouse_move(buttons, x, y, wheel)

	## Misc

	@property
	def keyboard_led_status(self):
		# get current led status (Capslock, etc.)
		return self.current_interface.keyboard_led_status

