# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

from .action_code import get_action_code, ASCII_TO_KEYCODE, SHIFT

class MacroInterface:

	def __init__(self, keyboard_core, hid_manager, keyboard_hardware):
		self.keyboard_core = keyboard_core
		self.hid_manager = hid_manager
		self.keyboard_hardware = keyboard_hardware

	async def send_text(self, text: str):
		await self.hid_manager.release_all()
		for character in text:
			keycode = ASCII_TO_KEYCODE[ord(character)]
			if keycode & 0x80: # Upper case / need shift
				keycode = keycode & 0x7F
				await self.hid_manager.keyboard_press(SHIFT)
				await self.hid_manager.keyboard_press(keycode)
				await self.hid_manager.keyboard_release(keycode)
				await self.hid_manager.keyboard_release(SHIFT)
			else:
				await self.hid_manager.keyboard_press(keycode)
				await self.hid_manager.keyboard_release(keycode)

