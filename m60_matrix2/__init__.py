# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

import asyncio

from matrix2 import Matrix2
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


class KeyEventIterator:
	def __init__(self, matrix):
		self._matrix_iter = iter(matrix)
	
	def __next__(self):
		# convert the event's key ID to location on the keymap
		# inner iterator will raise the StopIteration
		event = next(self._matrix_iter)
		event = COORDS[event & 0x7F] | (event & 0x80)
		return event

class KeyboardHardware:
	# minimum APIs:
	#  get_all_tasks()
	#  get_keys()
	#  iterator
	#  hardware_spec
	#  key_name(can be dummy)

	def __init__(self):
		self._matrix = Matrix2(MATRIX_ROWS, MATRIX_COLS,
						 columns_to_anodes=True,
						 max_bit_count=3,
						 active_bit_count=2,
						 inactive_bit_count=1)
		self._battery_update_callback = lambda x: None
		self.key_name = key_name
	
	def get(self):
		self._matrix.get()

	def __len__(self):
		return len(self._matrix)

	def __getitem__(self, key):
		return self._matrix[key]

	def __iter__(self):
		return KeyEventIterator(self._matrix)

	def get_all_tasks(self):
		# return a list of tasks
		tasks = list()
		tasks.append(asyncio.create_task(self._scan_routine()))
		return tasks

	async def _scan_routine(self):
		while True:
			self._matrix.scan()
			await asyncio.sleep(0)

	async def _led_routine(self):
		raise NotImplemented

	async def get_keys(self):
		# generate key events and return events count
		# BTW for masks: 0 means inactive(released up), 1 means active(pressed down)
		# for events, set 0x80 if key becomes inactive 
		# here we convert the raw ID to the position in the Keymap
		# note the key ID should not exceed 0x7F(127), which should be sufficient
		self._matrix.generate_events()
		return self.__len__()

	@property
	def hardware_spec(self):
		# ble only: 0b01
		# with battery: 0b11
		return 0b11

	@property
	def key_count(self):
		return self._matrix.key_count

	async def get_battery_level(self):
		return battery_level()

	async def set_keyboard_led(self):
		pass
	
	async def set_gamepad_led(self):
		pass

