# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab
import storage
try:
	from keyboard_config import NKRO, USB_STORAGE_MODE
except:
	NKRO = False
	USB_STORAGE_MODE = 0

# NKRO config
if NKRO:
	# enable hid using NKRO config
	from nkro_utils import enable_nkro
	enable_nkro()

# storage config
if USB_STORAGE_MODE == 0:
	# do not change anything
	pass
elif USB_STORAGE_MODE == 1:
	# read only for host
	storage.remount('/', 0)
elif USB_STORAGE_MODE == 2:
	# disable usb drive, CPY 7.x only
	storage.disable_usb_drive()

