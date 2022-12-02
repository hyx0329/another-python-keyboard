# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

# from keyboard import *
from keyboard import Keyboard
from keymaps import keymaps
import m60_matrix2 as m60

try:
	from keyboard_config import NKRO
except:
	NKRO = False

default_keymap = keymaps['qwerty_mod']
keymap_qwerty_plain = keymaps['qwerty_plain']
keymap_dvorak = keymaps['dvorak']
keymap_norman = keymaps['norman']


## initialize keyboard
keyboard = Keyboard(nkro_usb = NKRO)
keyboard.register_hardware(m60.KeyboardHardware)
keyboard.register_keymap(default_keymap)

# macro handler example
async def macro_handler(dev, i, press):
	if press:
		if i == 0:
			print("Switching to QWERTY_MOD")
			dev.keyboard_core.register_keymap(default_keymap)
		elif i == 1:
			print("Switching to QWERTY_PLAIN")
			dev.keyboard_core.register_keymap(keymap_plain)
		elif i == 2:
			await dev.send_text("Hello Python Keyboard!")
		else:
			print("Macro %d pressed" % i)
	else:
		print("Macro %d released" % i)

# register macro handler
keyboard.register_macro_handler(macro_handler)

## start
keyboard.run()

