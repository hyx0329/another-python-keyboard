# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

import asyncio

from .matrix import Matrix
from .bsm import (
	MATRIX_COLS,
	MATRIX_ROWS,
	MATRIX_ROW2COL,
	COORDS,
	battery_level,
	Backlight,
)

Matrix.COLS = MATRIX_COLS
Matrix.ROWS = MATRIX_ROWS
Matrix.ROW2COL = MATRIX_ROW2COL


KEY_NAME =  (
	'ESC', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'BACKSPACE',
	'TAB', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '[', ']', '|',
	'CAPS', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ';', '"', 'ENTER',
	'LSHIFT', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', ',', '.', '/', 'RSHIFT',
	'LCTRL', 'LGUI', 'LALT', 'SPACE', 'RALT', 'MENU', 'FN', 'RCTRL'
)


def key_name(key):
	return KEY_NAME[COORDS[key]]


class KeyboardHardware:
	# minimum APIs
	def __init__(self):
		self._matrix = Matrix()
		self._key_mask = 0
		self._key_count = self._matrix.key_count
		self._key_events_size = 0
		self._key_events = [0] * (self._key_count + 1)
		self._key_events_head = 0
		self._key_events_tail = 0
		self._battery_update_callback = lambda x: None
		# override the scan_routine
		self.scan_routine = self._matrix.scan_routine
		self.get_raw_keys = self._matrix.get_raw_keys
	
	def _put(self, value):
		if self._key_events_size >= self._key_count:
			return
		self._key_events[self._key_events_tail] = value
		self._key_events_tail = (self._key_events_tail + 1) % self._key_count
		self._key_events_size += 1

	def _get(self):
		if self._key_events_size <= 0:
			return None
		value = self._key_events[self._key_events_head]
		self._key_events_head = (self._key_events_head + 1) % self._key_count
		self._key_events_size -= 1
		return value

	get = _get

	def __len__(self):
		return self._key_events_size

	def __getitem__(self):
		return self._get()

	def __iter__(self):
		return self

	def __next__(self):
		if self._key_events_size == 0:
			raise StopIteration
		value = self._key_events[self._key_events_head]
		self._key_events_head = (self._key_events_head + 1) % self._key_events_size
		self._key_events_size -= 1
		return value

	async def scan_routine(self):
		# scan keys
		while True:
			await asyncio.sleep(0)

	async def secondary_routine(self):
		# other stuff: led, battery, whatever
		while True:
			# led.refresh()
			await asyncio.sleep(0)

	async def get_keys(self):
		# generate key events and return events count
		# BTW for masks: 0 means inactive, 1 means active
		# for events, set 0x80 if key becomes inactive 
		last_mask = self._key_mask
		mask = await self._matrix.get_raw_keys()
		for i in range(self._key_count):
			imask = 1 << i
			status = imask & mask
			changed = (status ^ last_mask) & imask
			if changed > 0:
				self._put( 0x80 | i if status == 0 else i )
		self._key_mask = mask
		return self.__len__()

	@property
	def has_secondary_routine(self):
		return False

	@property
	def hardware_spec(self):
		# ble only: 0b01
		# with battery: 0b11
		return 0b11

	async def get_battery_level(self):
		return battery_level

	async def set_keyboard_led(self):
		pass
	
	async def set_gamepad_led(self):
		pass

