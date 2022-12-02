# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

import asyncio
import keypad
import time

from .bsm import (
	MATRIX_COLS,
	MATRIX_ROWS,
	MATRIX_ROW2COL,
	COORDS,
	battery_level,
	Backlight,
)


KEY_NAME =  (
	'ESC', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'BACKSPACE',
	'TAB', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', '|',
	'CAPS', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', '"', 'ENTER',
	'LSHIFT', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/', 'RSHIFT',
	'LCTRL', 'LGUI', 'LALT', 'SPACE', 'RALT', 'MENU', 'FN', 'RCTRL'
)


def key_name(key):
	# `key` is the relative id on the keymap
	# not the actual physical id
	return KEY_NAME[key]


class KeyboardHardware:
	# minimum APIs:
	#  get_all_tasks()
	#  get_keys()
	#  iterator
	#  hardware_spec
	#  key_name(can be dummy)

	def __init__(self):
		self._keypad = keypad.KeyMatrix(MATRIX_ROWS, MATRIX_COLS,
								  columns_to_anodes = not MATRIX_ROW2COL)
		self.key_name = key_name
		self.backlight = Backlight()
		self._key_count = self._keypad.key_count
		self._key_events_length = 0
		self._key_events = [0] * self._key_count
		self._key_events_head = 0
		self._key_events_tail = 0
		self._hid_info = None

	def _put(self, value):
		if self._key_events_length < self._key_count:
			self._key_events[self._key_events_tail] = value
			self._key_events_tail = ( self._key_events_tail + 1 ) % self._key_count
			self._key_events_length += 1
		else:
			# discard the oldest one
			self._get()
			self._put(value)

	def _get(self):
		if self._key_events_length > 0:
			value = self._key_events[self._key_events_head]
			self._key_events_head = ( self._key_events_head + 1 ) % self._key_count
			self._key_events_length -= 1
			return value

	def __next__(self):
		if self._key_events_length == 0:
			raise StopIteration
		else:
			return self._get()

	def __len__(self):
		return self._key_events_length

	def __getitem__(self, key):
		if 0 <= key < self._key_events_length:
			index = (self._key_events_head + key) % self._key_count
			return self._key_events[index]
		elif key < 0 and abs(key) <= self._key_events_length:
			index = (self._key_events_tail + key) % self._key_count
			return self._key_events[index]
		else:
			raise IndexError

	def __iter__(self):
		return self

	def get_all_tasks(self):
		# return a list of tasks
		tasks = list()
		tasks.append(asyncio.create_task(self._scan_routine()))
		tasks.append(asyncio.create_task(self._backlight_routine()))
		return tasks

	def register_hid_info(self, hid_info):
		self._hid_info = hid_info

	async def _scan_routine(self):
		while True:
			event = self._keypad.events.get() # is there a non-blocking API?
			if event is not None:
				key_number = event.key_number
				pressed = 0x00 if event.pressed else 0x80
				encoded_event = COORDS[key_number] | pressed
				self._put(encoded_event)
				await asyncio.sleep(0)

	async def _backlight_routine(self):
		# because the scan will block every coroutine, I decided to not enable the fancy
		# backlight in this implementation(not calling backlight.check()).
		hid_info = self._hid_info
		backlight = self.backlight
		battery_update_time = time.time()

		if hid_info is None:
			return

		while True:
			await asyncio.sleep(0)
			# ble led
			if hid_info.ble_advertising:
				backlight.set_bt_led(self._hid_info.ble_id)
			else:
				backlight.set_bt_led(None)

			# hid led
			backlight.set_hid_leds(hid_info.keyboard_led)

			# battery level, in a backlight coroutine hahaha(not that good)
			if time.time() > battery_update_time:
				hid_info.set_battery_level(battery_level())
				battery_update_time = time.time() + 300  # update every 5 min

			backlight.check()

	async def get_keys(self):
		# get key events count
		# BTW for masks: 0 means inactive(released up), 1 means active(pressed down)
		# for events, set 0x80 if key becomes inactive 
		# here we convert the raw ID to the position in the Keymap
		# note the key ID should not exceed 0x7F(127), which should be sufficient
		return self.__len__()

	@property
	def hardware_spec(self):
		# ble only: 0b01
		# with battery: 0b11
		return 0b11

	@property
	def key_count(self):
		return self._key_count

	async def suspend(self):
		return 0

