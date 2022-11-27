# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

import time
import array
import struct
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
	
	def __init__(self):
		self.hardware = None
		self._hardware_module = None
		self.hardware_spec = 0
		self.hid_manager = None
		self._keymap = None
		self._profiles = {}  # profile auto switching is not supported yet
		self._pairs = ()
		self._actionmap = None
		self._actionmaps = None
		self._default_actionmap = None
		self._layer_mask = 1
		self._macro_handler = do_nothing
		self._pair_handler = do_nothing
		self._tap_thresh = 170 # micro second
		self._tap_key_not_triggered = False
		self._tap_key_last_one = 0
		self.keys_last_action_code = None
		self.keys_down_time = None
		self.keys_up_time = None

	def initialize(self):
		# check then setup basics
		logger.debug("Initializing the hardware and hid_manager")
		self._check_hardware_api(self.hardware)
		params = self._generate_hid_manager_parameters(self.hardware.hardware_spec)
		self.hid_manager = HIDDeviceManager(*params)
		# initialize shared memory
		self.keys_last_action_code = [0] * self.hardware._key_count
		self.keys_down_time = [0] * self.hardware._key_count
		self.keys_up_time = [0] * self.hardware._key_count
	
	def _check_hardware_api(self, hardware):
		assert hasattr(self.hardware, "get_all_tasks")
		assert hasattr(self.hardware, "get_keys")
		assert hasattr(self.hardware, "hardware_spec")
		assert hasattr(self.hardware, "key_name")
		iter(self.hardware)  # hardware should be iterable ( to get key events )
	
	def _generate_hid_manager_parameters(self, hardware_spec):
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

	def _handle_action_command(self, action_code):
		pass

	def _handle_action_macro(self, action_code):
		pass

	def _handle_action_layer_press(self, action_code):
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

	def _handle_action_layer_release(self, action_code):
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
	
	#def _handle_action_layertap_press(self, action_code, is_tapping_key = True):
	#	pass

	#def _handle_action_layertap_release(self, action_code, is_tapping_key = True):
	#	pass

	#def _check_action_tapkey_timelimit(self, trigger_time):
	#	pass

	#def _trigger_action_tapkey_hold(self):
	#	# blindly trigger the tapkey's `hold` action
	#	pass

	#def _handle_action_modstap_press(self, action_code, key_id, trigger_time):
	#	# not triggered here
	#	pass

	def _handle_action_modstap_release(self, action_code, key_id, trigger_time):
		pass

	async def _main_routine(self):
		keys_last_action_code = self.keys_last_action_code
		keys_down_time = self.keys_down_time
		keys_up_time = self.keys_up_time
		hid_manager = self.hid_manager
		input_hardware = self.hardware
		event_count = 0

		# to identify tap keys, need to process separately
		# Store tap keys before triggering them
		# Trigger them before new key's arrival
		# Since every tap key is triggered before any new key's processed,
		# there will be only one tap key to process
		tap_thresh = self._tap_thresh

		while True:
			# switch task, give some time to the scanner
			await asyncio.sleep(0)

			# event_count is used to assist tap key handling
			event_count = await input_hardware.get_keys()

			# TODO: here add pair key detection

			trigger_time = time.monotonic_ns() // 1000000 & 0x7FFFFFFF
			

			# check tapkey before any action
			# hold: 12~8: 5bits, modifiers only
			# tap: 7~0: 8bit, anykey
			# this function access the input_hardware and hid_interface directly
			# WARN: about tap key, actually there's a minor bug
			if self._tap_key_not_triggered:
				#self._check_action_tapkey_timelimit(trigger_time)
				logger.debug("Checking tapkey's time limit")
				key_id = self._tap_key_last_one
				down_time = self.keys_down_time[key_id]
				duration = trigger_time - down_time
				logger.debug("TAP duration: %d" % duration)
				if duration > self._tap_thresh: # hold time long enough
					# trigger the hold action(modifiers)
					logger.debug("TAP key triggered as HOLD due to timeout")
					modifiers = (self.keys_last_action_code[key_id] >> 8) & 0x1F
					keycodes = mods_to_keycodes(modifiers)
					await self.hid_manager.keyboard_press(*keycodes)
					self._tap_key_not_triggered = False
		

			# process events
			# Note: iter the input_hardware will also consume the events
			for event in input_hardware:
				# the key_id is the relative ID in the keymap
				key_id = event & 0x7F
				press = (event & 0x80) == 0
				logger.debug("Processing key event: %d | %d" % (key_id, press))

				if press:
					keys_down_time[key_id] = trigger_time
					action_code = self._get_action_code(key_id)
					keys_last_action_code[key_id] = action_code
					key_variant = action_code >> 12
					
					# trigger tapkey `hold` action when key down events detected
					if self._tap_key_not_triggered:
						logger.debug("TAP key triggered as HOLD due to another press event")
						key_id = self._tap_key_last_one
						action_code = (self.keys_last_action_code[key_id] >> 8) & 0x1f
						keycodes = mods_to_keycodes(action_code)
						self.keys_last_action_code[keys_id] = action_code
						await self.hid_manager.keyboard_press(action_code)
						self._tap_key_not_triggered = False

					if action_code < 0xFF:
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
							logger.debug("TAP directly for multiple events")
							keycode = action_code & 0xFF
							keys_last_action_code[key_id] = keycode
							await hid_manager.keyboard_press(keycode)
						else:
							# handle it the other way, with a state
							logger.debug("TAP key %s wait to be triggered" % key_id)
							self._tap_key_last_one = key_id
							self._tap_key_not_triggered = True
					elif key_variant == ACT_USAGE:
						# Consumer control, media keys
						if action_code & 0x400 > 0:
							await hid_manager.consumer_control_press(action_code & 0x3FF)
					elif key_variant == ACT_MOUSEKEY:
						pass
					elif key_variant == ACT_LAYER:
						self._handle_action_layer_press(action_code)
					elif key_variant == ACT_LAYER_TAP or key_variant == ACT_LAYER_TAP_EXT:
						self._handle_action_layertap_press(action_code)
					elif key_variant == ACT_MACRO:
						self._handle_action_macro(action_code)
					elif key_variant == ACT_BACKLIGHT:
						pass
					elif key_variant == ACT_COMMAND:
						self._handle_action_command(action_code)
					logger.info(
							"Got {} {:10} \\ {:0>4b} {}".format(
							key_id, self.hardware.key_name(key_id), key_variant, hex(action_code)
						))

				else: # release
					keys_up_time[key_id] = trigger_time
					action_code = keys_last_action_code[key_id]
					key_variant = action_code >> 12

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
						#self._handle_action_modstap_release(action_code, key_id, trigger_time)
						modifiers = ( action_code >> 8 ) & 0x1F
						keycodes = mods_to_keycodes(modifiers)
						single_key = action_code & 0xFF
						if self._tap_key_not_triggered:
							# press it then release it
							await self.hid_manager.keyboard_press(single_key)
							await self.hid_manager.keyboard_release(single_key)
							self._tap_key_not_triggered = False
						else:
							# release it
							await self.hid_manager.keyboard_release(*keycodes)
					elif key_variant == ACT_USAGE:
						if action_code & 0x400 > 0:
							await hid_manager.consumer_control_release(0)
					elif key_variant == ACT_MOUSEKEY:
						pass
					elif key_variant == ACT_LAYER:
						self._handle_action_layer_release(action_code)
					elif key_variant == ACT_LAYER_TAP or key_variant == ACT_LAYER_TAP_EXT:
						pass
					elif key_variant == ACT_MACRO:
						pass

					# if required, log here
					logger.info(
							"Got {} {:10} / {:0>4b} {}, {}ms".format(
							key_id, self.hardware.key_name(key_id), key_variant, hex(action_code),
							keys_up_time[key_id] - keys_down_time[key_id],
						))

