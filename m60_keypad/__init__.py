# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

import asyncio
import keypad

from .matrix import Matrix
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
		self._battery_update_callback = lambda x: None
		self.key_name = key_name
		self._key_count = self._keypad.key_count
		self._key_events_length = 0
		self._key_events = [0] * self._key_count
		self._key_events_head = 0
		self._key_events_tail = 0
		self._battery_update_callback = lambda x: None

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
		return tasks

	async def _scan_routine(self):
		while True:
			event = self._keypad.events.get()
			if event is not None:
				key_number = event.key_number
				pressed = 0x00 if event.pressed else 0x80
				encoded_event = COORDS[key_number] | pressed
				self._put(encoded_event)
				await asyncio.sleep(0)

	async def _led_routine(self):
		raise NotImplemented

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

	async def get_battery_level(self):
		return battery_level()

	async def set_keyboard_led(self):
		pass
	
	async def set_gamepad_led(self):
		pass

