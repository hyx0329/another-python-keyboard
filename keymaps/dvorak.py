from keyboard.action_code import *
from .default import kb_layer3_kbcontrol, kb_layer5_mouse


___ = TRANSPARENT
BOOT = BOOTLOADER
PWDN = SHUTDOWN
FNL1 = LAYER_TAP(1)
LSFT4 = LAYER_MODS(4, MODS(LSHIFT))
RSFT4 = LAYER_MODS(4, MODS(RSHIFT))

L2E = LAYER_TAP(2, E)
L3X = LAYER_TAP(3, X)
L5O = LAYER_TAP(5, O)

# dvorak base
kb_layer0_base = (
	ESC, '[',   7,   5,   3,   1,   9,   0,   2,   4,   6,   8, ']', BACKSPACE,
	TAB, '/', ',', '.',   P,   Y,   F,   G,   C,   R,   L, '"', '=', '|',
	CAPS,  A, L5O, L2E,   U,   I,   D,   H,   T,   N,   S, '-',    ENTER,
	LSFT4, ';',   Q,   J,   K, L3X,   B,   M,   W,   V,   Z,       RSFT4,
	LCTRL, LALT, LGUI,          SPACE,            RGUI, RALT,  FNL1, RCTRL
)

# dvorak style layer 1
kb_layer1_function = (
	'`', F11,  F7,  F5,  F3,  F1,  F9, F10,  F2,  F4,  F6,  F8, F12, DEL,
	___, ___,  UP, ___, ___, ___, ___, ___, ___, ___,SUSPEND,___,___,___,
	___,LEFT,DOWN,RIGHT,___, ___, ___, ___, ___, ___, ___, ___, MACRO(0),
	___, MACRO(1), MACRO(2), MACRO(3), MACRO(4), BOOT, ___, ___, ___, ___, ___, ___,
	___, ___, ___,                ___,               ___, ___, ___,  ___
)

# dvorak style layer 2
kb_layer2_media = (
	'`', F11,  F7,  F5,  F3,  F1,  F9, F10,  F2,  F4,  F6,  F8, F12, DEL,
	___, ___, ___, ___, ___, ___,HOME,PGUP, ___, ___,___,AUDIO_VOL_DOWN,AUDIO_VOL_UP,AUDIO_MUTE,
	___, ___, ___, ___, ___, ___,LEFT,DOWN, UP,RIGHT, ___, ___,      ___,
	___, ___, ___, ___, ___, ___,PGDN,END, ___, ___, ___,           ___,
	___, ___, ___,                ___,               ___, ___, ___,  ___
)

# restore tap keys
kb_layer4_restore = (
	'`', ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___,
	___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___,
	___, ___,   O,   E, ___, ___, ___, ___, ___, ___, ___, ___,      ___,
	___, ___, ___, ___, ___,   B, ___, ___, ___, ___, ___,           ___,
	___, ___, ___,                ___,               ___, ___, ___,  ___
)


# compose up
keymap = (
	kb_layer0_base,
	kb_layer1_function,
	kb_layer2_media,
	kb_layer3_kbcontrol,
	kb_layer4_restore,
	kb_layer5_mouse
)
