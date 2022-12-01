# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

import time
import array
import struct
import microcontroller
import asyncio
import adafruit_logging as logging
logger = logging.getLogger("Keyboard Core")
logger.setLevel(logging.DEBUG)

from .utils import do_nothing
# TODO: explict import
from .action_code import *
from .hid import HIDDeviceManager
import keyboard.hardware_spec_ids as hwspecs

class Keyboard:
	# TODO: add pair key
	# TODO: add macro
	
	def __init__(self, *args, nkro_usb = False, **kwargs):
		self.hardware = None
		self._hardware_module = None
		self.hardware_spec = 0
		self.hid_manager = None
		self.nkro_usb = nkro_usb
		self._keymap = None
		self._heatmap = None # TODO: load heatmap?
		self._profiles = {}  # profile auto switching is not supported yet
		self._pairs = ()
		self._actionmap = None
		self._actionmaps = None
		self._default_actionmap = None
		self._layer_mask = 1
		self._macro_handler = do_nothing
		self._tap_thresh = 170 # micro second
		self.keys_last_action_code = None
		self.keys_down_time = None
		self.keys_up_time = None

	def initialize(self):
		# check then setup basics
		logger.debug("Initializing the hardware and hid_manager")
		self._check_hardware_api(self.hardware)
		params = self._generate_hid_manager_parameters_from_hardware_spec(self.hardware.hardware_spec)
		self.hid_manager = HIDDeviceManager(nkro_usb = self.nkro_usb, *params)
		# initialize shared memory
		logger.debug("Key count: %d" % self.hardware.key_count)
		logger.debug("NKRO(USB): %s" % str(self.nkro_usb))
		self._heatmap = [0] * self.hardware.key_count
		self.keys_last_action_code = [0] * self.hardware.key_count
		self.keys_down_time = [0] * self.hardware.key_count
		self.keys_up_time = [0] * self.hardware.key_count
	
	def _check_hardware_api(self, hardware):
		assert hasattr(self.hardware, "get_all_tasks")
		assert hasattr(self.hardware, "get_keys")
		assert hasattr(self.hardware, "hardware_spec")
		assert hasattr(self.hardware, "key_name")
		assert hasattr(self.hardware, "key_count")
		assert hasattr(self.hardware, "suspend")
		iter(self.hardware)  # hardware should be iterable ( to get key events )
	
	def _generate_hid_manager_parameters_from_hardware_spec(self, hardware_spec):
		params = dict()
		params["enable_ble"] = hardware_spec & hwspecs.HAS_BLE != 0
		params["ble_battery"] = hardware_spec & hwspecs.HAS_BATTERY != 0
		return params

	def run(self):
		self.initialize()
		asyncio.run(self._run())

	async def _run(self):
		own_tasks = self.get_all_tasks()
		hid_tasks = self.hid_manager.get_all_tasks()
		hardware_tasks = self.hardware.get_all_tasks()
		tasks = own_tasks + hid_tasks + hardware_tasks
		logger.debug("Start running %d tasks" % len(tasks))
		await asyncio.gather(*tasks)

	def get_all_tasks(self):
		# return a list of own tasks
		# do not include submodule tasks
		tasks = list()
		tasks.append(asyncio.create_task(self._main_routine()))
		return tasks

	def register_hardware(self, hardware_module):
		self._hardware_module = hardware_module
		self.hardware = hardware_module.KeyboardHardware()

	def register_keymap(self, keymap):
		self._keymap = keymap
		self._compile_keymap()

	def _compile_keymap(self):
		convert = lambda a: array.array("H", (get_action_code(k) for k in a))
		self._default_actionmap = tuple(convert(layer) for layer in self._keymap)
		self._actionmap = self._default_actionmap
		self._actionmaps = {}
		#for key in self._profiles:
		#	self.actionmaps[key] = tuple(
		#		convert(layer) for layer in self.profiles[key]
		#	)

	def register_macro_handler(self, func):
		# TODO: better checking
		if callable(func):
			self._macro_handler = func

	def _get_action_code(self, position):
		# the actual action code varies because of layer support
		layer_mask = self._layer_mask
		for layer in range(len(self._actionmap) - 1, -1, -1):
			if (layer_mask >> layer) & 1:
				code = self._actionmap[layer][position]
				if code == 1:  # TRANSPARENT
					continue
				return code
		return 0

	async def _handle_action_command(self, action_code):
		if action_code == BOOTLOADER:
			microcontroller.on_next_reset(microcontroller.RunMode.BOOTLOADER)
			microcontroller.reset() # normally the first line will be enough
		elif action_code == SUSPEND:
			await self.hardware.suspend()
		elif action_code == SHUTDOWN:
			microcontroller.reset()
		elif action_code == HEATMAP:
			# TODO: write to a external binary file
			print(self._heatmap)
		elif action_code == USB_TOGGLE:
			await self.hid_manager.switch_to_usb()
		elif action_code == BT_TOGGLE:
			await self.hid_manager.switch_to_ble()
		elif BT(0) <= action_code and action_code <= BT(9):
			i = action_code - BT(0)
			logger.info("Manager: Switch to BT {}".format(i))
			await self.hid_manager.ble_switch_to(i)

	async def _handle_action_macro(self, action_code):
		pass

	async def _handle_action_layer_press(self, action_code):
		# op<<10|on<<8|part<<5|(bits&0x1f)
		on = (action_code >> 8) & 0x3
		if on == ON_PRESS or on == ON_BOTH:
			op = (action_code >> 10) & 0x3
			part = (action_code >> 5) & 0x7
			xbit = (action_code >> 4) & 0x1
			bits_shift = part * 4
			bits = (action_code & 0xF) << bits_shift
			mask = bits | ~(0xF << bits_shift) if xbit else bits
			if op == OP_BIT_AND:
				self._layer_mask &= mask
			elif op == OP_BIT_OR:
				self._layer_mask |= mask
			elif op == OP_BIT_XOR:
				self._layer_mask ^= mask

	async def _handle_action_layer_release(self, action_code):
		# op<<10|on<<8|part<<5|(bits&0x1f)
		on = (action_code >> 8) & 0x3
		if on == ON_RELEASE:
			op = (action_code >> 10) & 0x3
			part = (action_code >> 5) & 0x7
			xbit = (action_code >> 4) & 0x1
			bits_shift = part * 4
			bits = (action_code & 0xF) << bits_shift
			mask = bits | ~(0xF << bits_shift) if xbit else bits
			if op == OP_BIT_AND:
				self._layer_mask &= mask
			elif op == OP_BIT_OR:
				self._layer_mask |= mask
			elif op == OP_BIT_XOR:
				self._layer_mask ^= mask
	
	async def _trigger_tapkey_action_hold(self, key_id, key_variant):
		action_code = self.keys_last_action_code[key_id]
		param = (action_code >> 8) & 0x1F
		if key_variant < ACT_USAGE: # MODS_TAP
			keycodes = mods_to_keycodes(param)
			await self.hid_manager.keyboard_press(*keycodes)
		elif key_variant == ACT_LAYER_TAP or key_variant == ACT_LAYER_TAP_EXT:
			self._layer_mask |= 1 << param

	async def _main_routine(self):
		# there's some circuitpython limit that prevents too many long function calls
		# so I have to write everything in one loop
		keys_last_action_code = self.keys_last_action_code
		keys_down_time = self.keys_down_time
		keys_up_time = self.keys_up_time
		hid_manager = self.hid_manager
		input_hardware = self.hardware
		event_count = 0

		# to identify tap keys, need to process separately
		# Store tap keys before triggering them
		# Trigger them before new key's arrival
		# Since every tap key is triggered before any new key's down event processed,
		# there will be only one tap key to process
		tap_thresh = self._tap_thresh
		tap_key_last_id = 0
		tap_key_variant = 0 # also a marker whether tapkey is processed

		# report loop
		while True:
			# switch task, give some time to the scanner
			await asyncio.sleep(0)

			event_count = await input_hardware.get_keys()
			trigger_time = time.monotonic_ns() // 1000000 & 0x7FFFFFFF

			# TODO: here add pair key detection
			
			# check tapkey before any action
			# hold: 12~8: 5bits, modifiers or layer
			# tap: 7~0: 8bit, anykey
			if tap_key_variant > 0:
				duration = trigger_time - keys_down_time[tap_key_last_id]
				if duration > tap_thresh: # hold time long enough
					logger.debug("TAP/L/hold/timeout")
					await self._trigger_tapkey_action_hold(tap_key_last_id, tap_key_variant)
					tap_key_variant = 0


			# process events
			# Note: iter the input_hardware will also consume the events
			for event in input_hardware:
				# the key_id is the relative ID in the keymap
				key_id = event & 0x7F
				press = (event & 0x80) == 0
				logger.debug("Event: %d | %d" % (key_id, press))

				if press:
					keys_down_time[key_id] = trigger_time
					self._heatmap[key_id] += 1

					# trigger tapkey `hold` action when key down events detected
					# This will alter self._layer_mask thus affect action_code
					if tap_key_variant > 0:
						logger.debug("TAP/L/hold/newpress")
						await self._trigger_tapkey_action_hold(tap_key_last_id, tap_key_variant)
						tap_key_variant = 0

					# get action
					action_code = self._get_action_code(key_id)
					keys_last_action_code[key_id] = action_code
					key_variant = action_code >> 12

					# log info
					logger.info(
							"Key {} {:10} \\ {:0>4b} {}".format(
							key_id, self.hardware.key_name(key_id), key_variant, hex(action_code)
						))

					# start parsing key info
					if action_code < 0xFF:
						# plain key
						await hid_manager.keyboard_press(action_code)
					elif key_variant < ACT_MODS_TAP:
						# MODS_KEY, one key for multiple modifiers and one other key
						mods = (action_code >> 8) & 0x1F
						keycodes = mods_to_keycodes(mods)
						keycodes.append(action_code & 0xFF)
						await hid_manager.keyboard_press(*keycodes)
					elif key_variant < ACT_USAGE:
						# MODS_TAP, hold for modifiers, tap for other key
						if event_count != 1:
							# trigger tap directly
							logger.debug("TAP/tap/multiple")
							keycode = action_code & 0xFF
							keys_last_action_code[key_id] = keycode
							await hid_manager.keyboard_press(keycode)
						else:
							# handle it the other way, with a state
							logger.debug("TAP/wait/%d" % key_id)
							tap_key_last_id = key_id
							tap_key_variant = key_variant
					elif key_variant == ACT_USAGE:
						# Consumer control, media keys
						if action_code & 0x400 > 0:
							await hid_manager.consumer_control_press(action_code & 0x3FF)
					elif key_variant == ACT_MOUSEKEY:
						pass
					elif key_variant == ACT_LAYER:
						await self._handle_action_layer_press(action_code)
					elif key_variant == ACT_LAYER_TAP or key_variant == ACT_LAYER_TAP_EXT:
						if action_code & 0xE0 == 0xC0: # press modifiers and switch layer
							logger.debug("LAYER_MODS")
							keycodes = mods_to_keycodes(action_code & 0x1F)
							await hid_manager.keyboard_press(*keycodes)
							layer_mask = 1 << ((action_code >> 8) & 0x1F)
							self._layer_mask |= layer_mask
						elif event_count != 1: # TAP key, change layer(hold) or other(tap)
							logger.debug("TAP-L/hold/multiple")
							keycode = action_code & 0xFF
							keys_last_action_code[key_id] = keycode
							await hid_manager.keyboard_press(keycode)
						else:
							logger.debug("TAP-L/wait/%d" % key_id)
							tap_key_last_id = key_id
							tap_key_variant = key_variant
					elif key_variant == ACT_MACRO:
						await self._handle_action_macro(action_code)
					elif key_variant == ACT_BACKLIGHT:
						pass
					elif key_variant == ACT_COMMAND:
						await self._handle_action_command(action_code)
					
				else: # release
					keys_up_time[key_id] = trigger_time
					action_code = keys_last_action_code[key_id]
					key_variant = action_code >> 12

					logger.info(
							"Key {} {:10} / {:0>4b} {}, {}ms".format(
							key_id, self.hardware.key_name(key_id), key_variant, hex(action_code),
							keys_up_time[key_id] - keys_down_time[key_id],
						))

					if action_code < 0xFF:
						await hid_manager.keyboard_release(action_code)
					elif key_variant < ACT_MODS_TAP:
						# MODS_KEY, one key for multiple modifiers and one other key
						mods = ( action_code >> 8 ) & 0x1F
						keycodes = mods_to_keycodes(mods)
						keycodes.append(action_code & 0xFF)
						await hid_manager.keyboard_release(*keycodes)
					elif key_variant < ACT_USAGE:
						# MODS_TAP
						if key_variant == tap_key_variant and key_id == tap_key_last_id: # not triggered, same id
							# press it then release it
							logger.debug("TAP/tap/tap")
							single_key = action_code & 0xFF
							await hid_manager.keyboard_press(single_key)
							await hid_manager.keyboard_release(single_key)
							tap_key_variant = 0
						else: # release it, already in hold state
							keycodes = mods_to_keycodes(( action_code >> 8 ) & 0x1F)
							await hid_manager.keyboard_release(*keycodes)
					elif key_variant == ACT_USAGE:
						if action_code & 0x400 > 0:
							await hid_manager.consumer_control_release(0)
					elif key_variant == ACT_MOUSEKEY:
						pass
					elif key_variant == ACT_LAYER:
						await self._handle_action_layer_release(action_code)
					elif key_variant == ACT_LAYER_TAP or key_variant == ACT_LAYER_TAP_EXT:
						keycode = action_code & 0xFF
						param = (action_code >> 8) & 0x1F
						layer_mask = 1 << param
						if  key_id == tap_key_last_id and key_variant == tap_key_variant:
							# not triggered, is	tapping key
							logger.debug("TAP-L/tap/tap")
							if keycode == OP_TAP_TOGGLE:
								logger.info("Toggle layer %d" % param)
								self._layer_mask = (self._layer_mask & ~layer_mask) | (layer_mask & ~self._layer_mask)
							else:
								await hid_manager.keyboard_press(keycode)
								await hid_manager.keyboard_release(keycode)
							tap_key_variant = 0
						else: # is `hold`
							if keycode & 0xE0 == 0xC0:
								logger.debug("LAYER_MODS")
								keycodes = mods_to_keycodes(keycode & 0x1F)
								await hid_manager.keyboard_release(*keycodes)
							self._layer_mask &= ~layer_mask
							logger.debug("layer_mask %x" % layer_mask)
					elif key_variant == ACT_MACRO:
						pass
					

