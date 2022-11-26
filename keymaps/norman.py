from keyboard.action_code import *
from .default import kb_layer1_function, kb_layer2_media, kb_layer3_kbcontrol, kb_layer5_mouse


___ = TRANSPARENT
L2E = LAYER_TAP(2, E)
L5S = LAYER_TAP(5, S)
L3B = LAYER_TAP(3, B)
FNL1 = LAYER_TAP(1)
LSFT4 = LAYER_MODS(4, MODS(LSHIFT))
RSFT4 = LAYER_MODS(4, MODS(RSHIFT))


kb_layer0_base = (
	ESC,   1,   2,   3,   4,   5,   6,   7,   8,   9,   0, '-', '=', BACKSPACE,
	TAB,   Q,   W,   D,   F,   K,   J,   U,   R,   L, ';', '[', ']', '|',
	CAPS,  A, L5S, L2E,   T,   G,   Y,   N,   I,   O,   H, '"',    ENTER,
	LSFT4, Z,   X,   C,   V, L3B,   P,   M, ',', '.', '/',         RSFT4,
	LCTRL, LALT, LGUI,          SPACE,            RGUI, RALT, FNL1, RCTRL
)

kb_layer4_restore = (
	'`', ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___,
	___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___,
	___, ___,   S,   E, ___, ___, ___, ___, ___, ___, ___, ___,      ___,
	___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___,           ___,
	___, ___, ___,                ___,               ___, ___, ___,  ___
)


keymap = (
	kb_layer0_base,
	kb_layer1_function,
	kb_layer2_media,
	kb_layer3_kbcontrol,
	kb_layer4_restore,
	kb_layer5_mouse
)
