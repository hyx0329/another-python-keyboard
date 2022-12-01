# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

import asyncio
import time

from matrix2 import Matrix2
from .bsm import (
	MATRIX_COLS,
	MATRIX_ROWS,
	MATRIX_ROW2COL,
	COORDS,
	battery_level,
	Backlight,
)
from .light_queue import LightQueue


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


def ms():
	return (time.monotonic_ns() // 1000000) & 0x7FFFFFFF


class KeyEventIterator:
	def __init__(self, matrix, queue):
		self._matrix_iter = iter(matrix)
		self._queue = queue
	
	def __next__(self):
		# convert the event's key ID to location on the keymap
		# inner iterator will raise the StopIteration
		# also triggers hardware's key handler
		event = next(self._matrix_iter)
		self._queue.put(event)
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
						 max_bit_count=6,
						 active_bit_count=5,
						 inactive_bit_count=3)
		self.backlight = Backlight()
		self.light_queue = LightQueue(self._matrix.key_count)
		self.key_name = key_name
		self._hid_info = None
	
	def get(self):
		self._matrix.get()

	def __len__(self):
		return len(self._matrix)

	def __getitem__(self, key):
		return self._matrix[key]

	def __iter__(self):
		return KeyEventIterator(self._matrix, self.light_queue)

	def get_all_tasks(self):
		# return a list of tasks
		tasks = list()
		tasks.append(asyncio.create_task(self._scan_routine()))
		if self._hid_info is not None:
			tasks.append(asyncio.create_task(self._backlight_routine()))
		return tasks

	def register_hid_info(self, hid_info):
		self._hid_info = hid_info

	async def _scan_routine(self):
		while True:
			self._matrix.scan()
			await asyncio.sleep(0)

	async def _backlight_routine(self):
		hid_info = self._hid_info
		backlight = self.backlight
		battery_update_time = time.time()
		led_check_counter = 1
		led_check_thresh = 1 << 8

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

			# for a special backlight mode
			for event in self.light_queue:
				key = event & 0x7F
				pressed = event & 0x80 == 0
				backlight.handle_key(key, pressed)

			if led_check_counter > led_check_thresh:
				backlight.check() # high CPU usage
				led_check_counter = 1
			else:
				led_check_counter <<= 1

			backlight.update()

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
		# with battery: 0b10
		return 0b11

	@property
	def key_count(self):
		return self._matrix.key_count

	async def suspend(self):
		# enter low power mode
		# generally, return 0 means no error, but not necessarily suspended
		# since a successful suspend action will reset the supervisor
		return self._matrix.suspend()

	async def get_battery_level(self):
		return battery_level()

