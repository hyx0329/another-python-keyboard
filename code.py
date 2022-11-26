# from keyboard import *
from keyboard import Keyboard
from keymaps import keymaps
import m60

keyboard = Keyboard()

default_keymap = keymaps['qwerty_mod']
keymap_qwerty_plain = keymaps['qwerty_plain']
keymap_dvorak = keymaps['dvorak']
keymap_norman = keymaps['norman']



### initialize keyboard

keyboard.register_hardware(m60)
keyboard.register_keymap(keymap_qwerty_plain)

# ESC(0)    1(1)   2(2)   3(3)   4(4)   5(5)   6(6)   7(7)   8(8)   9(9)   0(10)  -(11)  =(12)  BACKSPACE(13)
# TAB(27)   Q(26)  W(25)  E(24)  R(23)  T(22)  Y(21)  U(20)  I(19)  O(18)  P(17)  [(16)  ](15)   \(14)
# CAPS(28)  A(29)  S(30)  D(31)  F(32)  G(33)  H(34)  J(35)  K(36)  L(37)  ;(38)  "(39)      ENTER(40)
#LSHIFT(52) Z(51)  X(50)  C(49)  V(48)  B(47)  N(46)  M(45)  ,(44)  .(43)  /(42)            RSHIFT(41)
# LCTRL(53)  LGUI(54)  LALT(55)               SPACE(56)          RALT(57)  MENU(58)  Fn(59)  RCTRL(60)

# Uncomment line below to disable serial debug output
# keyboard.verbose = False

keyboard.run()
