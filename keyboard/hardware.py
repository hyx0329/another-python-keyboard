# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

class KeyboardHardware:
	# minimum APIs

	async def scan_routine(self):
		# scan keys
		pass

	async def secondary_routine(self):
		# other stuff
		pass

	async def get_keys(self):
		# get key changes
		pass

	@property
	def has_secondary_routine(self):
		return False

	@property
	def has_ble(self):
		return False

	async def set_keyboard_led(self):
		pass
	
	async def set_gamepad_led(self):
		pass

