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
keyboard.register_hardware(m60)
keyboard.register_keymap(default_keymap)

## start
keyboard.run()

