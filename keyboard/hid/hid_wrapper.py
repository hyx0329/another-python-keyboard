# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab
import struct

class DummyControl:
	# The dummy one only implements a send_report and to avoid failure only
	def send_report(self, *args, **kwargs):
		pass


def find_device(devices, usage_page, usage):
	for device in devices:
		# find a valid device with requested usage_page and usage
		if (
			device.usage_page == usage_page
			and device.usage == usage
			and hasattr(device, "send_report")
		):
			return device
	return DummyControl()


class HIDInterfaceWrapper:
	# read:
	# https://docs.circuitpython.org/en/latest/shared-bindings/usb_hid/#usb_hid.Device
	# https://learn.adafruit.com/customizing-usb-devices-in-circuitpython/hid-devices
	# https://docs.circuitpython.org/projects/ble/en/latest/standard_services.html#adafruit_ble.services.standard.hid.HIDService
    # suitable for 6KRO

	def __init__(self, devices):
		self.keyboard = find_device(devices, usage_page=0x1, usage=0x06)
		self.mouse = find_device(devices, usage_page=0x1, usage=0x02)
		self.consumer_control = find_device(devices, usage_page=0x0C, usage=0x01)
		self.gamepad = find_device(devices, usage_page=0x1, usage=0x05)
		self.setup_keyboard_led()
		#self.setup_gamepad_led()

		# the reports to send, pre allocate the memory
		# these are negotiated through `descriptors`
		# report_keyboard[0] modifiers
		# report_keyboard[1] unused
		# report_keyboard[2:] regular keys
		self.report_keyboard = bytearray(8)
		self.report_keys = memoryview(self.report_keyboard)[2:]
		self.report_consumer_control = bytearray(2)
		self.report_mouse = bytearray(4)
		#self.report_gamepad = None
	
	def setup_keyboard_led(self):
		if hasattr(self.keyboard, "last_received_report"):
			self.get_keyboard_led_status = self._get_kbd_led_status_usb
		elif hasattr(self.keyboard, "report"):
			self.get_keyboard_led_status = self._get_kbd_led_status_ble

	def get_keyboard_led_status(self):
		return 0
	
	def _get_kbd_led_status_ble(self):
		return self.keyboard.report[0]

	def _get_kbd_led_status_usb(self):
		return self.keyboard.last_received_report[0]

	@property
	def keyboard_led_status(self):
		return self.get_keyboard_led_status()

	## HID APIs ##

	async def _send_keyboard(self):
		self.keyboard.send_report(self.report_keyboard)

	async def _send_consumer_control(self):
		self.consumer_control.send_report(self.report_consumer_control)

	async def _send_mouse(self):
		self.mouse.send_report(self.report_mouse)

	async def _send_gamepad(self):
		raise NotImplemented

	async def release_all(self):
		for i in range(len(self.report_keyboard)):
			self.report_keyboard[i] = 0
		for i in range(len(self.report_mouse)):
			self.report_mouse[i] = 0
		for i in range(len(self.report_consumer_control)):
			self.report_consumer_control[i] = 0
		await self._send_keyboard()
		await self._send_mouse()
		await self._send_consumer_control()

	async def keyboard_press(self, *keycodes):
		for keycode in keycodes:
			if 0xE0 <= keycode < 0xE8: # modifiers
				self.report_keyboard[0] |= 1 << (keycode & 0x7)
				continue
			for c in self.report_keys:
				if c == keycode:
					break
			else:
				for i in range(6):
					if self.report_keys[i] == 0:
						self.report_keys[i] = keycode
						break
		await self._send_keyboard()

	async def keyboard_release(self, *keycodes):
		for keycode in keycodes:
			if 0xE0 <= keycode < 0xE8: # modifiers
				self.report_keyboard[0] &= ~(1 << (keycode & 0x7))
				continue
			for i in range(6):
				if self.report_keys[i] == keycode:
					self.report_keys[i] = 0
		await self._send_keyboard()

	async def consumer_control_press(self, keycode):
		struct.pack_into("<H", self.report_consumer_control, 0, keycode)
		await self._send_consumer_control()
	
	async def consumer_control_release(self, keycode = None):
		await self.consumer_control_press(0)

	async def mouse_press(self, buttons):
		# buttons is a number
		self.report_mouse[0] |= buttons
		await self._send_mouse()

	async def mouse_release(self, buttons):
		# buttons is a number
		self.report_mouse[0] &= ~buttons
		await self._send_mouse()

	async def mouse_move(self, buttons, x=0, y=0, wheel=0):
		self.report_mouse[1] = x & 0xFF
		self.report_mouse[2] = y & 0xFF
		self.report_mouse[3] = wheel & 0xFF
		await self._send_mouse()


class HIDInterfaceWrapperNKRO(HIDInterfaceWrapper):
	# reference: https://learn.adafruit.com/custom-hid-devices-in-circuitpython/n-key-rollover-nkro-hid-device
	# currently only keyboard is different so I inherit other from original implementation

	def __init__(self, devices):
		self.keyboard = find_device(devices, usage_page=0x1, usage=0x06)
		self.mouse = find_device(devices, usage_page=0x1, usage=0x02)
		self.consumer_control = find_device(devices, usage_page=0x0C, usage=0x01)
		self.gamepad = find_device(devices, usage_page=0x1, usage=0x05)
		self.setup_keyboard_led()

		# a little different for keyboard
		self.report_keyboard = bytearray(16)
		self.report_keys = memoryview(self.report_keyboard)[1:]
		self.report_consumer_control = bytearray(2)
		self.report_mouse = bytearray(4)

	async def keyboard_press(self, *keycodes):
		for keycode in keycodes:
			if 0xE0 <= keycode < 0xE8: # modifiers
				self.report_keyboard[0] |= 1 << (keycode & 0x7)
				continue
			else:
				self.report_keys[keycode >> 3] |= 1 << (keycode & 0x7)
		await self._send_keyboard()

	async def keyboard_release(self, *keycodes):
		for keycode in keycodes:
			if 0xE0 <= keycode < 0xE8: # modifiers
				self.report_keyboard[0] &= ~(1 << (keycode & 0x7))
				continue
			else:
				self.report_keys[keycode >> 3] &= ~(1 << (keycode & 0x7))
		await self._send_keyboard()

# a utility function
def wrap_hid_interface(devices, nkro=False):
	if not nkro:
		return HIDInterfaceWrapper(devices)
	else:
		return HIDInterfaceWrapperNKRO(devices)

