# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

# This module wraps high-level HID API provided by usb_hid and BLERadio

import struct
import time
import microcontroller
import asyncio
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
	from adafruit_ble.advertising import Advertisement
	from adafruit_ble.advertising.standard import ProvideServicesAdvertisement
	from adafruit_ble.services.standard import BatteryService
	from adafruit_ble.services.standard.hid import HIDService
	BLE_AVAILABLE = True
except:
	BLE_AVAILABLE = False

# tools
from ..utils import do_nothing, is_usb_connected, async_no_fail


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
				battery = True,
				verbose = False,
				**kwargs):
		self._interfaces = dict()
		self._nkro_usb = nkro_usb
		self._nkro_ble = False
		self._hid_ble_handle = None
		self._ble_radio = None
		self._ble_mac_pool = None
		self._ble_id = 1
		self._ble_battery = None
		self._ble_advertisement = None
		self._ble_advertisement_scan_response = None
		self._ble_advertisement_started = False
		self._ble_name_prefix = "PYKB"
		self._ble_advertise_stop_time = time.time()
		self._ble_last_connected_time = time.time()
		self._current_interface_name = "unknown"
		self._previous_interface_name = "unknown"
		self._usb_was_connected = False
		# initialize interfaces and activate a proper one
		self.__initialize_usb_interface()
		if enable_ble and BLE_AVAILABLE:
			self.__initialize_ble_interface(battery = battery)
		self.current_interface = self._auto_select_device()
		if not verbose:
			logger.setLevel(logging.ERROR)
		else:
			logger.setLevel(logging.DEBUG)
	
	def get_all_tasks(self):
		# get tasks to run
		# TODO: coroutine to check USB and BLE connections, switch accordingly
		tasks = list()
		tasks.append(asyncio.create_task(self.connection_check()))
		return tasks

	def __initialize_usb_interface(self):
		logger.debug("Initializing USB HID interface")
		self._interfaces["usb"] = wrap_hid_interface(usb_hid.devices, self._nkro_usb)

	def __initialize_ble_interface(self, battery = False):
		# The bluetooth hid interface uses predefined descriptor consists of
		# keyboard, mouse, and consumer control (read HIDDevice's doc)
		# to add a gamepad, need to write a suitable descriptor
		logger.debug("Initializing BLE HID interface")
		self._hid_ble_handle = HIDService()
		ble_services = list()
		ble_services.append(self._hid_ble_handle)
		if battery:
			logger.debug("BLE has battery service")
			self._ble_battery = BatteryService()
			self._ble_battery.level = 100
			ble_services.append(self._ble_battery)
		self._ble_advertisement = ProvideServicesAdvertisement(*ble_services)
		self._ble_advertisement.appearance = 961 # keyboard
		self._ble_advertisement_scan_response = Advertisement()
		self._ble_name_prefix = "PYKB" # TODO: better naming?
		self._ble_id = 1
		self._ble_radio = BLERadio()
		if self._ble_radio.connected:
			for c in self._ble_radio.connections:
				c.disconnect()
		self._interfaces["ble"] = wrap_hid_interface(self._hid_ble_handle.devices, self._nkro_ble)

	def _auto_select_device(self):
		# Connected USB > BLE > Disconnected USB
		# only use in __init__
		if self._interfaces.get("usb", None) and is_usb_connected():
			logger.debug("Auto select interface: USB")
			self.set_current_interface_name("usb")
			return self._interfaces.get("usb")
		elif self._interfaces.get("ble", None):
			logger.debug("Auto select interface: BLE")
			self.set_current_interface_name("ble")
			return self._interfaces.get("ble")
		elif self._interfaces.get("usb", None):
			logger.debug("Auto select interface: USB")
			self.set_current_interface_name("usb")
			return self._interfaces.get("usb")
		raise RuntimeError("No valid interface!")

	async def connection_check(self):
		while True:
			await asyncio.sleep(1) # run at most one time a second

			# check USB, switch to USB automatically if just connected
			if is_usb_connected():
				if not self._usb_was_connected:
					await self.switch_to_usb()
				self._usb_was_connected = True
			else:
				self._usb_was_connected = False

			# check BLE, auto stop advertisement
			if "ble" in self._interfaces:
				# check connection and advertisement timeout
				if self._ble_radio.advertising:
					if time.time() > self._ble_advertise_stop_time:
						await self.ble_advertisement_stop()
						await asyncio.sleep(1)
				# check ble connection
				if self._ble_radio.connected:
					self._ble_last_connected_time = time.time()
					# CPY will stop it
					#await self.ble_advertisement_stop()
					self._ble_advertisement_started = False

				# auto restart advertisement
				# not connected doesn't mean it's not trying to connect, so, watchout
				# here I use `self._ble_advertisement_started` to mark if ble advertisement already started by me
				# This value is set to False when self.ble_advertisement_stop is called
				# when making connections, the ble advertisement will be stopped
				if self._current_interface_name == "ble" \
					and not self._ble_radio.advertising \
					and not self._ble_radio.connected \
					and not self._ble_advertisement_started:
						if time.time() - self._ble_last_connected_time < 180: # connected 3min ago
							await self.ble_advertisement_start(60)
				# switch to ble if usb is not available
				if not is_usb_connected():
					await self.switch_to_ble()
	
	def _ble_generate_static_mac(self, n):
		n = abs(n) % 10
		uid = microcontroller.cpu.uid
		mac = bytearray( (i+n*2) & 0xFF for i in uid[:6] )
		mac[-1] |= 0xC0 # only this is necessary for RANDOM_STATIC
		mac[0] |= 0xC0
		address = _bleio.Address(bytes(mac), _bleio.Address.RANDOM_STATIC)
		return address

	## (USB &) BLE interface control

	async def switch_to_previous_interface(self):
		previous_interface_name = self._previous_interface_name
		if previous_interface_name == "usb":
			if is_usb_connected():
				logger.info("Switch to USB interface")
				await self.switch_to_usb()
			pass
		elif previous_interface_name == "ble":
			await self.switch_to_ble()
		else:
			# do nothing
			pass

	async def switch_to_usb(self):
		interface = self._interfaces.get("usb", None)
		if interface and self._current_interface_name != "usb":
			logger.info("Switching to USB")
			await self.release_all()
			self.current_interface = interface
			self.set_current_interface_name("usb")

	async def switch_to_ble(self):
		interface = self._interfaces.get("ble", None)
		if interface and self._current_interface_name != "ble":
			logger.info("Switching to BLE(%d)" % self._ble_id)
			await self.release_all()
			await self.ble_advertisement_update()
			self.current_interface = interface
			self.set_current_interface_name("ble")
			# the check loop will restart the advertisement automatically, don't do it here
			# but set the time
			self._ble_last_connected_time = time.time()

	async def ble_advertisement_update(self):
		bt_id = self._ble_id
		try:
			self._ble_radio._adapter.address = self._ble_generate_static_mac(bt_id)
			_name = "%s %s" % (self._ble_name_prefix, str(bt_id))
			self._ble_radio.name = _name
			self._ble_advertisement.complete_name = _name
			logger.debug("Update BLE info: %s, %s" % (_name, str(self._ble_radio._adapter.address)))
		except Exception as e:
			print(e)

	async def ble_switch_to(self, bt_id = -1):
		if not "ble" in self._interfaces:
			return

		bt_id = abs(bt_id) % 10 # limit it
		if self._ble_id == bt_id:
			# if not connected, advertise, switch to bt
			# reset last connected time so advertisement will auto start
			self._ble_last_connected_time = time.time()
			await self.switch_to_ble()
			return
		else:
			self._ble_id = bt_id

		# stop advertising and disconnect all
		await self.ble_advertisement_stop()
		await self.ble_disconnect_all()
		#await self.ble_advertisement_update()
		await self.ble_advertisement_start()

		await self.switch_to_ble()

	async def ble_advertisement_start(self, timeout = 60):
		#await self.ble_advertisement_stop()
		await self.ble_advertisement_update()
		self._ble_advertise_stop_time = time.time() + max(10, timeout)
		if not self._ble_radio.advertising:
			logger.debug("Starting BLE advertisement")
			self._ble_radio.start_advertising(self._ble_advertisement, self._ble_advertisement_scan_response)

	async def ble_advertisement_stop(self):
		self._ble_advertisement_started = False
		if self._ble_radio.advertising:
			logger.debug("Stopping BLE advertisement")
			try:
				self._ble_radio.stop_advertising()
			except Exception as e:
				print(e)

	def ble_is_connected(self):
		return self._ble_radio.connected

	async def ble_disconnect_all(self):
		logger.debug("Disconnecting all BLE hosts")
		if self.ble_is_connected:
			for c in self._ble_radio.connections:
				c.disconnect()

	async def ble_set_battery_level(self, value: int):
		if self._ble_battery is not None:
			self._ble_battery.value = max(0, min(100, value))

	## HID control API mirrored from interface wrapper

	@async_no_fail
	async def release_all(self):
		await self.current_interface.release_all()

	@async_no_fail
	async def keyboard_press(self, *keycodes):
		await self.current_interface.keyboard_press(*keycodes)

	@async_no_fail
	async def keyboard_release(self, *keycodes):
		await self.current_interface.keyboard_release(*keycodes)

	@async_no_fail
	async def consumer_control_press(self, keycode):
		await self.current_interface.consumer_control_press(keycode)
	
	@async_no_fail
	async def consumer_control_release(self, keycode):
		await self.current_interface.consumer_control_release(keycode)

	@async_no_fail
	async def mouse_press(self, buttons):
		await self.current_interface.mouse_press(buttons)

	@async_no_fail
	async def mouse_release(self, buttons):
		await self.current_interface.mouse_release(buttons)

	@async_no_fail
	async def mouse_move(self, buttons, x=0, y=0, wheel=0):
		await self.current_interface.mouse_move(buttons, x, y, wheel)

	## Misc
	def set_current_interface_name(self, value):
		self._previous_interface_name = self._current_interface_name
		self._current_interface_name = value
	
	def get_current_interface_name(self):
		return self._current_interface_name
		
	@property
	def keyboard_led_status(self):
		# get current led status (Capslock, etc.)
		return self.current_interface.keyboard_led_status

