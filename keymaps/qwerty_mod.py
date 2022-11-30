from keyboard.action_code import *

from .default import kb_layer2_media, kb_layer3_kbcontrol, kb_layer4_restore, kb_layer5_mouse
from .default import ___, FNL1, L2D, L3B, LSFT4, RSFT4, L5S, SCC, BOOT

CESC = MODS_TAP(MODS(LCTRL), ESC)
L2TAB = LAYER_TAP(2, TAB)

# layer 0
kb_layer0_base = (
	ESC,   1,   2,   3,   4,   5,   6,   7,   8,   9,   0, '-', '=', BACKSPACE,
	L2TAB, Q,   W,   E,   R,   T,   Y,   U,   I,   O,   P, '[', ']', '|',
	CESC,  A,   S,   D,   F,   G,   H,   J,   K,   L, SCC, '"',    ENTER,
	LSFT4, Z,   X,   C,   V, L3B,   N,   M, ',', '.', '/',         RSFT4,
	LCTRL, LALT, LGUI,          SPACE,            RGUI, RALT, FNL1, RCTRL
)

# plain version, no tap keys or layer changes except FN
kb_layer0_base_plain = (
	ESC,   1,   2,   3,   4,   5,   6,   7,   8,   9,   0, '-', '=', BACKSPACE,
	TAB,   Q,   W,   E,   R,   T,   Y,   U,   I,   O,   P, '[', ']', '|',
	CAPS,  A,   S,   D,   F,   G,   H,   J,   K,   L, ';', '"',    ENTER,
	LSHIFT,Z,   X,   C,   V,   B,   N,   M, ',', '.', '/',         RSHIFT,
	LCTRL, LALT, LGUI,          SPACE,            RGUI, RALT, FNL1, RCTRL
)

# layer 1
# add/change function keys
# additions:
#   printscreen, heatmap key, mute, vol-up, vol-down
# modifications:
#   SUSPEND -> PAUSE
#	O -> SUSPEND
kb_layer1_function = (
	'`',  F1,  F2,  F3,  F4,  F5,  F6,  F7,  F8,  F9, F10, F11, F12, DEL,
	___, ___,  UP, ___, ___, ___, ___, ___, ___, SUSPEND,PAUSE,AUDIO_VOL_DOWN,AUDIO_VOL_UP,AUDIO_MUTE,
	CAPS,LEFT,DOWN,RIGHT,___, ___, HEATMAP, ___, ___, ___, ___, ___, MACRO(0),
	___, MACRO(1), MACRO(2), MACRO(3), MACRO(4), BOOT, ___, ___, ___, ___, ___, ___,
	___, ___, ___,                ___,               PRTSCN, ___, ___,  ___
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

keymap_plain = (
	kb_layer0_base_plain,
	kb_layer1_function
)
