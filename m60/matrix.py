# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

import asyncio
import digitalio
import board

class Matrix:
	# only one instance anyway
	ROWS = ()
	COLS = ()
	ROW2COL = False  # direction of diode

	def __init__(self):
		self.key_count = len(self.ROWS) * len(self.COLS)
		self.queue = bytearray(self.key_count)
		
		self.rows = list()
		self.cols = list()

		for pin in self.ROWS:
			io = digitalio.DigitalInOut(pin)
			io.direction = digitalio.Direction.OUTPUT
			io.drive_mode = digitalio.DriveMode.PUSH_PULL
			io.value = 0
			self.rows.append(io)

		for pin in self.COLS:
			io = digitalio.DigitalInOut(pin)
			io.direction = digitalio.Direction.INPUT
			io.pull = digitalio.Pull.DOWN if self.ROW2COL else digitalio.Pull.UP
			self.cols.append(io)
		
		self.pressed = bool(self.ROW2COL)
		self.mask = 0
		self.key_val = [0] * self.key_count # for noise filtering

	async def scan_routine(self):
		pressed = self.pressed
		rows = self.rows
		cols = self.cols
		key_val = self.key_val

		# scan every key
		key_index = -1
		while True:
			for row in rows:
				row.value = pressed
				for col in cols:
					key_index += 1
					# TODO: make parameter variable
					if col.value == pressed:
						key_val[key_index] = min(key_val[key_index] + 1, 16)
					else:
						key_val[key_index] = max(key_val[key_index] - 1, 0)
				row.value = not pressed
			key_index = -1
			# switch task
			await asyncio.sleep(0)

	async def get_raw_keys(self):
		# get current key status
		# key up/down events are not generated here
		key_val = self.key_val
		mask = self.mask
		enable_thresh = 8
		disable_thresh = 3
		
		# check changes
		for key_index in range(self.key_count):
			key_mask = 1 << key_index
			if key_val[key_index] > enable_thresh:
				mask |= key_mask
			elif key_val[key_index] < enable_thresh:
				mask &= ~key_mask

		# update result
		self.mask = mask
		print("{:0>64b}".format(mask))
		return mask

