# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

import array
import struct
import asyncio

from .utils import do_nothing
# TODO: explict import
from .action_code import *
from .hid import HIDDeviceManager

HAS_BLE = 0b01
HAS_BATTERY = 0b10

class Keyboard:
	# TODO: add pair key
	# TODO: add macro
	
	def __init__(self):
		self.hardware = None
		self._hardware_module = None
		self.hardware_spec = 0
		self.hid_manager = None
		self._keymap = None
		self._profiles = {}
		self._pairs = ()
		self._actionmap = None
		self._actionmaps = None
		self._default_actionmap = None
		self._layer_mask = 1
		self._macro_handler = do_nothing
		self._pair_handler = do_nothing
		self._coroutine_scan = None
		self._coroutine_secondary = None

	def initialize(self):
		# check then setup basics
		assert hasattr(self.hardware, "scan_routine")
		assert hasattr(self.hardware, "get_keys")
		self.hardware_spec = self.hardware.hardware_spec
		enable_ble = self.hardware_spec & HAS_BLE != 0
		ble_battery = self.hardware_spec & HAS_BATTERY != 0
		self.hid_manager = HIDDeviceManager(enable_ble=enable_ble, ble_battery=ble_battery)
		self._coroutine_scan = self.hardware.scan_routine
		if self.hardware.has_secondary_routine:
			self._coroutine_secondary = self.hardware.secondary_routine
		else:
			self._coroutine_secondary = None

	def run(self):
		self.initialize()
		asyncio.run(self._run())

	async def _run(self):
		task_main = asyncio.create_task(self.routine())
		task_scan = asyncio.create_task(self._coroutine_scan())
		await asyncio.gather(task_main, task_scan)

	def get_all_entry_points(self):
		entries = list()
		entries.append(self.routine)
		entries.append(self._coroutine_scan)
		if callable(self._coroutine_secondary):
			entries.append(self.hardware.secondary_routine)
		return entries

	def get_all_coroutines(self):
		tasks = list()
		for entry in self.get_all_coroutines():
			tasks.append(asyncio.create_task(entry()))
		return tasks

	def register_hardware(self, hardware_module):
		self._hardware_module = hardware_module
		self.hardware = hardware_module.KeyboardHardware()
		self.key_name = hardware_module.key_name
		self.COORDS = hardware_module.COORDS

	def register_keymap(self, keymap):
		self._keymap = keymap
		self._compile_keymap()

	def _compile_keymap(self):
		convert = lambda a: array.array("H", (get_action_code(k) for k in a))
		self._default_actionmap = tuple(convert(layer) for layer in self._keymap)
		self._actionmap = self._default_actionmap
		self._actionmaps = {}
		#for key in self.profiles:
		#	self.actionmaps[key] = tuple(
		#		convert(layer) for layer in self.profiles[key]
		#	)

	def register_macro_handler(self, func):
		# TODO: better checking
		if callable(func):
			self._macro_handler = func

	def _get_action_code(self, position):
		# the actual action code varies because of layer support
		position = self.COORDS[position]
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
		# don't understand QAQ
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
	
	def _handle_action_layertap_press(self, action_code, is_tapping_key = True):
		pass

	def _handle_action_layertap_release(self, action_code, is_tapping_key = True):
		pass

	async def routine(self):
		keys_last_action_code = [0] * self.hardware._key_count
		keys_down_time = [0] * self.hardware._key_count
		keys_up_time = [0] * self.hardware._key_count
		event_count = 0
		hid_manager = self.hid_manager
		input_hardware = self.hardware

		mouse_action = 0

		while True:
			await asyncio.sleep(0)
			event_count = await input_hardware.get_keys()
			# TODO: here add pair key detection and tap key detection

			if event_count > 0:
				print(event_count)
			else:
				continue

			for event in input_hardware:
				key_id = event & 0x7F
				press = key_id & 0x80 == 0
				if press:
					action_code = self._get_action_code(key_id)
					keys_last_action_code[key_id] = action_code
					key_variant = action_code >> 12
					if action_code < 0xFF:
						await hid_manager.keyboard_press(action_code)
					elif key_variant < ACT_MODS_TAP:
						# MODS
						mods = (action_code >> 8) & 0x1F
						keycodes = mods_to_keycodes(mods)
						keycodes.append(action_code & 0xFF)
						await hid_manager.keyboard_press(*keycodes)
					elif key_variant < ACT_USAGE:
						# MODS_TAP
						pass
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
					# if required, log here

				else: # release
					action_code = keys_last_action_code[key_id]
					key_variant = action_code >> 12
					if action_code < 0xFF:
						await hid_manager.keyboard_release(action_code)
					elif key_variant < ACT_MODS_TAP:
						# MODS
						pass
					elif key_variant < ACT_USAGE:
						# MODS_TAP
						pass
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

		if mouse_action != 0:
			pass
