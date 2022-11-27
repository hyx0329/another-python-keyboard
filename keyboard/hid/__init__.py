# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

# This module wraps high-level HID API provided by usb_hid and BLERadio
# So if any alternative connection method is provided, it must implement
# the related HID API

import struct
import time
import microcontroller
import adafruit_logging as logging
logger = logging.getLogger("HID Manager")

# USB interface
import usb_hid
from .devices import (
	KEYBOARD,
	MOUSE,
	CONSUMER_CONTROL,
)

try:
# Bluetooth LE interface
	import _bleio
	from adafruit_ble import BLERadio
	#from adafruit_ble.advertising import Advertisement
	from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
	from adafruit_ble.services.standard import BatteryService
	from adafruit_ble.services.standard.hid import HIDService
	BLE_AVAILABLE = True
except:
	BLE_AVAILABLE = False

#
from keyboard.utils import do_nothing, is_usb_connected


class DummyControl:
	# The dummy one only implements a send_report and to avoid failure only
	def send_report(self, *args, **kwargs):
		pass


def find_device(devices, usage_page, usage):
	for device in devices:
		# find a valid device with requested usage_page and usage
		if (
			device.usage_page == usage_page
			and device.usage == usage
			and hasattr(device, "send_report")
		):
			return device
	return DummyControl()


class HIDInterfaceWrapper:
	# read:
	# https://docs.circuitpython.org/en/latest/shared-bindings/usb_hid/#usb_hid.Device
	# https://learn.adafruit.com/customizing-usb-devices-in-circuitpython/hid-devices
	# https://docs.circuitpython.org/projects/ble/en/latest/standard_services.html#adafruit_ble.services.standard.hid.HIDService

	def __init__(self, devices):
		self.keyboard = find_device(devices, usage_page=0x1, usage=0x06)
		self.mouse = find_device(devices, usage_page=0x1, usage=0x02)
		self.consumer_control = find_device(devices, usage_page=0x0C, usage=0x01)
		self.gamepad = find_device(devices, usage_page=0x1, usage=0x05)
		self.setup_keyboard_led()
		#self.setup_gamepad_led()
	
	def setup_keyboard_led(self):
		if hasattr(self.keyboard, "last_received_report"):
			self.get_keyboard_led_status = self._get_kbd_led_status_usb
		elif hasattr(self.keyboard, "report"):
			self.get_keyboard_led_status = self._get_kbd_led_status_ble

	def _get_kbd_led_status_ble(self):
		return self.keyboard.report[0]

	def _get_kbd_led_status_usb(self):
		return self.keyboard.last_received_report[0]

	def get_keyboard_led_status(self):
		return 0
	
	@property
	def keyboard_led_status(self):
		return self.get_keyboard_led_status()


class HIDDeviceManager:
	# This is a composed HID device manager
	# should be transparent to upper level
	# Provides control over keyboard and mouse
	# gamepad should be possible as long as the descriptor is correctly configured

	## initialization

	def __init__(self, *args, enable_ble = True, **kwargs):
		# kwargs is for addtional configuration, subject to change

		# the reports to send, pre allocate the memory
		# these are negotiated through `descriptors`
		# report_keyboard[0] modifiers
		# report_keyboard[1] unused
		# report_keyboard[2:] regular keys
		self.report_keyboard = bytearray(8)
		self.report_keys = memoryview(self.report_keyboard)[2:]
		self.report_consumer_control = bytearray(2)
		self.report_mouse = bytearray(4)
		#self.report_gamepad = None
		self._usb_status = 0

		self._interfaces = dict()

		self.__initialize_usb_interface()
		if enable_ble and BLE_AVAILABLE:
			use_battry_service = kwargs.get("ble_battery", False)
			self.__initialize_ble_interface(battery = use_battry_service)
		self.current_interface = self._auto_select_device()
	
	def get_all_tasks(self):
		# return all just created coroutines/tasks
		tasks = list()
		return tasks

	def __initialize_usb_interface(self):
		logger.debug("Initializing USB HID interface")
		# NOTE: the USB interfaces can only be changed at boot time(boot.py)
		self._interfaces["usb"] = HIDInterfaceWrapper(usb_hid.devices)

	def __initialize_ble_interface(self, battery = False):
		# The bluetooth hid interface uses predefined descriptor consists of
		# keyboard, mouse, and consumer control (read HIDDevice's doc)
		# to add a gamepad, need to write a suitable descriptor
		logger.debug("Initializing BLE HID interface")
		self._ble_radio = BLERadio()
		ble_services = list()
		self._hid_ble_handle = HIDService()
		self._interfaces["ble"] = HIDInterfaceWrapper(self._hid_ble_handle.devices)
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
		if self._interfaces.get("usb", None) and is_usb_connected():
			return self._interfaces.get("usb")
		elif self._interfaces.get("ble", None):
			return self._interfaces.get("ble")
		elif self._interfaces.get("usb", None):
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

	# NOTE: whether to make all of these APIs corotines?

	## async "daemon" and internal control
	## General interface control

	async def check(self):
		# check BLE & USB
		if "ble" in self._interfaces.keys():
			if self._ble_advertise_stop_time > 0:
				if self._ble_advertise_stop_time < time.time():
					await self.ble_advertisement_stop()

	async def _send_keyboard(self):
		self.current_interface.keyboard.send_report(self.report_keyboard)
	
	async def _send_consumer_control(self):
		self.current_interface.consumer_control.send_report(self.report_consumer_control)

	async def _send_mouse(self):
		self.current_interface.mouse.send_report(self.report_mouse)

	async def _send_gamepad(self):
		#self.current_interface.gamepad.send_report(self.report_gamepad)
		pass

	async def _release_all(self):
		for i in range(8):
			self.report_keyboard[i] = 0
		for i in range(4):
			self.report_mouse[i] = 0
		await self.consumer_control_press(0)
		await self._send_keyboard()
		await self._send_mouse()

	async def switch_to_usb(self):
		interface = self._interfaces.get("usb", None)
		if interface:
			await self._release_all()
			self.current_interface = interface

	async def switch_to_ble(self):
		interface = self._interfaces.get("ble", None)
		if interface:
			await self._release_all()
			if not self.ble_is_connected:
				self.ble_advertisement_start(timeout = 60)

	## (USB &) BLE interface control

	async def ble_enable(self):
		# just placeholder
		pass

	async def ble_disable(self):
		# just placeholder
		pass

	async def ble_set_name_prefix(self, prefix: str):
		# TODO: figure out the real limit
		self._ble_name_prefix = prefix[:10]
		# TODO: restart advertisement
	
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

	## HID control

	async def keyboard_press(self, *keycodes):
		for keycode in keycodes:
			if 0xE0 <= keycode < 0xE8:
				self.report_keyboard[0] |= 1 << (keycode & 0x7)
				continue
			for c in self.report_keys:
				if c == keycode:
					break
			else:
				for i in range(6):
					if self.report_keys[i] == 0:
						self.report_keys[i] = keycode
						break
		await self._send_keyboard()

	async def keyboard_release(self, *keycodes):
		for keycode in keycodes:
			if 0xE0 <= keycode < 0xE8:
				self.report_keyboard[0] &= ~(1 << (keycode & 0x7))
				continue
			for i in range(6):
				if self.report_keys[i] == keycode:
					self.report_keys[i] = 0
		await self._send_keyboard()

	async def consumer_control_press(self, keycode):
		# TODO: find a way to integrate it in the keyboard's method
		struct.pack_into("<H", self.report_consumer_control, 0, keycode)
		await self._send_consumer_control()
	
	async def consumer_control_release(self, keycode):
		struct.pack_into("<H", self.report_consumer_control, 0, 0)
		await self._send_consumer_control()

	async def mouse_press(self, buttons):
		# buttons is a number
		self.report_mouse[0] |= buttons
		self.report_mouse[1] = 0
		self.report_mouse[2] = 0
		self.report_mouse[3] = 0
		await self._send_mouse()

	async def mouse_release(self, buttons):
		# buttons is a number
		self.report_mouse[0] &= ~buttons
		self.report_mouse[1] = 0
		self.report_mouse[2] = 0
		self.report_mouse[3] = 0
		await self._send_mouse()

	async def mouse_move(self, buttons, x=0, y=0, wheel=0):
		self.report_mouse[1] = x & 0xFF
		self.report_mouse[2] = y & 0xFF
		self.report_mouse[3] = wheel & 0xFF
		await self._send_mouse()

	## Misc

	@property
	def keyboard_led_status(self):
		# get current led status (Capslock, etc.)
		return self.current_interface.keyboard_led_status

