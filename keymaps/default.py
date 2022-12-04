from keyboard.action_code import *

NAK = NO  # no action
___  = TRANSPARENT
BOOT = BOOTLOADER
PWDN = SHUTDOWN
FNL1 = LAYER_MODS(1) # use LAYER_MODS to trigger immediately
L2D = LAYER_TAP(2, D)
L3B = LAYER_TAP(3, B)
L5S = LAYER_TAP(5, S)
L5ON = LAYER_ON(5, ON_RELEASE)
L5OFF = LAYER_OFF(5, ON_RELEASE)

LSFT4 = LAYER_MODS(4, MODS(LSHIFT))
RSFT4 = LAYER_MODS(4, MODS(RSHIFT))

# TAP key
SCC = MODS_TAP(MODS(RCTRL), ';')  # Semicolon & Ctrl

# Combined
SINS = MODS_KEY(MODS(SHIFT), INSERT)

# layer 0
kb_layer0_base = (
	ESC,   1,   2,   3,   4,   5,   6,   7,   8,   9,   0, '-', '=', BACKSPACE,
	TAB,   Q,   W,   E,   R,   T,   Y,   U,   I,   O,   P, '[', ']', '|',
	CAPS,  A, L5S, L2D,   F,   G,   H,   J,   K,   L, SCC, '"',    ENTER,
	LSFT4, Z,   X,   C,   V, L3B,   N,   M, ',', '.', '/',         RSFT4,
	LCTRL, LGUI, LALT,          SPACE,            RALT, RGUI, FNL1, RCTRL
)

# layer 1
kb_layer1_function = (
	'`',  F1,  F2,  F3,  F4,  F5,  F6,  F7,  F8,  F9, F10, F11, F12, DEL,
	___, ___,  UP, ___, ___, ___, ___, ___, ___, ___,SUSPEND,___,___,___,
	___,LEFT,DOWN,RIGHT,___, ___, ___, ___, ___, ___, ___, ___, MACRO(0),
	___, MACRO(1), MACRO(2), MACRO(3), MACRO(4), BOOT, ___, ___, ___, ___, ___, ___,
	___, ___, ___,                ___,               ___, ___, ___,  ___
)

# layer 2
kb_layer2_media = (
	'`',  F1,  F2,  F3,  F4,  F5,  F6,  F7,  F8,  F9, F10, F11, F12, DEL,
	___, ___, ___, ___, ___, L5ON,HOME,PGUP, INSERT, ___,SINS,AUDIO_VOL_DOWN,AUDIO_VOL_UP,AUDIO_MUTE,
	___, ___, ___, ___, ___, ___,LEFT,DOWN, UP,RIGHT, ___, ___,      ___,
	___, ___, ___, ___, ___, ___,PGDN,END, ___, ___, ___,           ___,
	___, ___, ___,                ___,               ___, ___, ___,  ___
)

# layer 3
kb_layer3_kbcontrol = (
	BT_TOGGLE,BT1,BT2, BT3,BT4,BT5,BT6,BT7, BT8, BT9, BT0, ___, ___, ___,
	RGB_MOD, ___, ___, ___, ___, ___,___,USB_TOGGLE,___,___,___,___,___, ___,
	RGB_TOGGLE,HUE_RGB,RGB_HUE,SAT_RGB,RGB_SAT,___,___,___,___,___,___,___,___,
	___, ___, ___, ___, ___, ___, ___, ___,VAL_RGB,RGB_VAL, ___,           ___,
	___, ___, ___,                ___,               ___, ___, ___,  ___
)

# layer 4
kb_layer4_restore = (
	'`', ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___,
	___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___, ___,
	___, ___,   S,   D, ___, ___, ___, ___, ___, ___, ';', ___,      ___,
	___, ___, ___, ___, ___,   B, ___, ___, ___, ___, ___,           ___,
	___, ___, ___,                ___,               ___, ___, ___,  ___
)

# layer 5 for mouse control
kb_layer5_mouse = (
	L5OFF, NAK, NAK, NAK, NAK, NAK, NAK, NAK, NAK, NAK, NAK, NAK, NAK, NAK,
	NAK, NAK, NAK, NAK, NAK, NAK,MS_W_UP,MS_UL,MS_UP,MS_UR, NAK, NAK, NAK, NAK,
	NAK, NAK, NAK, NAK, NAK, NAK,MS_BTN1,MS_LT,MS_DN,MS_RT,MS_BTN2, NAK, MS_BTN2,
	NAK, NAK, NAK, NAK, NAK, NAK,MS_W_DN,MS_DL,MS_DN,MS_DR, NAK,           NAK,
	NAK, NAK, NAK,                MS_BTN1,               NAK, NAK, NAK,  NAK
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
