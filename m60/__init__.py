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
		self._key_events_length = 0
		self._key_events = [0] * self._key_count
		self._key_events_head = 0
		self._key_events_tail = 0
		self._battery_update_callback = lambda x: None
		# override the scan_routine
		self.scan_routine = self._matrix.scan_routine
		self.get_raw_keys = self._matrix.get_raw_keys
	
	def _put(self, value):
		if self._key_events_length < self._key_count:
			self._key_events[self._key_events_tail] = value
			self._key_events_tail = ( self._key_events_tail + 1 ) % self._key_count
			self._key_events_length += 1

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

	def __getitem__(self):
		return self._get()

	def __iter__(self):
		return self

	async def scan_routine(self):
		# scan keys
		# This is a place holder
		while True:
			await asyncio.sleep(0)

	async def secondary_routine(self):
		# other stuff: led, battery, whatever
		while True:
			# led.refresh()
			await asyncio.sleep(0)

	async def get_keys(self):
		# generate key events and return events count
		# BTW for masks: 0 means inactive(released up), 1 means active(pressed down)
		# for events, set 0x80 if key becomes inactive 
		# here we convert the raw ID to the relative position in the Keymap
		# note the key ID should not exceed 0x7F(127), which should be sufficient
		old_mask = self._key_mask
		new_mask = await self.get_raw_keys()
		self._key_mask = new_mask
		for raw_key_id in range(self._key_count):
			imask = 1 << raw_key_id
			old_status = old_mask & imask
			new_status = new_mask & imask
			up = old_status > new_status
			down = old_status < new_status
			if up: # released
				self._put( 0x80 | COORDS[raw_key_id] )
			elif down: # pressed
				self._put( COORDS[raw_key_id] )
			# otherwise no change
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
		return battery_level()

	async def set_keyboard_led(self):
		pass
	
	async def set_gamepad_led(self):
		pass

