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

from .utils import async_no_fail, ms
from .action_code import *
from .hid import HIDDeviceManager, HIDInfo
from .macro_interface import MacroInterface
import keyboard.hardware_spec_ids as hwspecs


class Keyboard:
	# TODO: add pair key
	# TODO: add macro
	
	def __init__(self, *args,
			  nkro_usb = False,
			  verbose = False,
			  time_tap_thresh = 170,
			  time_tap_delay = 80,
			  **kwargs):
		self.hardware = None
		self.hardware_spec = 0
		self.hid_manager = None
		self.nkro_usb = nkro_usb
		self.verbose = verbose
		self._keymap = None
		self._heatmap = None # TODO: load heatmap?
		self._profiles = {}  # profile auto switching is not supported yet
		self._actionmap = None
		self._actionmaps = None
		self._default_actionmap = None
		self._layer_mask = 1
		self._macro_handler = None
		self._tap_thresh = time_tap_thresh # micro second
		self._tap_delay = time_tap_delay # micro second
		self._mouse_status = 0
		self._mouse_time = 0
		self._mouse_move = [0,0,0]
		self._mouse_speed = 1
		self.keys_last_action_code = None
		self.keys_down_time = None
		self.keys_up_time = None

		if not verbose:
			logger.setLevel(logging.ERROR)
		else:
			logger.setLevel(logging.DEBUG)

	def initialize(self):
		# check then setup basics
		logger.debug("Initializing the hardware and hid_manager")
		self._check_hardware_api(self.hardware)
		params = self._generate_hid_manager_parameters_from_hardware_spec(self.hardware.hardware_spec)
		self.hid_manager = HIDDeviceManager(nkro_usb = self.nkro_usb, verbose = self.verbose, *params)
		hid_info = HIDInfo(self.hid_manager)
		self.hardware.register_hid_info(hid_info)
		# initialize shared memory
		logger.debug("Key count: %d" % self.hardware.key_count)
		logger.debug("NKRO(USB): %s" % str(self.nkro_usb))
		self._heatmap = [0] * self.hardware.key_count
		self.keys_last_action_code = [0] * self.hardware.key_count
		self.keys_down_time = [0] * self.hardware.key_count
		self.keys_up_time = [0] * self.hardware.key_count
	
	def _check_hardware_api(self, hardware):
		assert hasattr(hardware, "get_all_tasks")
		assert hasattr(hardware, "get_keys")
		assert hasattr(hardware, "hardware_spec")
		assert hasattr(hardware, "key_count")
		assert hasattr(hardware, "suspend")
		assert hasattr(hardware, "register_hid_info")
		iter(hardware)  # hardware should be iterable ( to get key events )
		# optional APIs
		if not hasattr(hardware, "key_name"):
			hardware.key_name = lambda *_: "Unknown"
	
	def _generate_hid_manager_parameters_from_hardware_spec(self, hardware_spec):
		params = dict()
		params["enable_ble"] = hardware_spec & hwspecs.HAS_BLE != 0
		params["battery"] = hardware_spec & hwspecs.HAS_BATTERY != 0
		return params

	def run(self):
		self.initialize()
		asyncio.run(self._run())

	async def _run(self):
		own_tasks = self.get_all_tasks()
		hid_tasks = self.hid_manager.get_all_tasks()
		hardware_tasks = self.hardware.get_all_tasks()
		tasks = own_tasks + hid_tasks + hardware_tasks
		logger.debug("%d tasks collected" % len(tasks))
		await asyncio.gather(*tasks)

	def get_all_tasks(self):
		# return a list of own tasks
		# do not include submodule tasks
		tasks = list()
		tasks.append(asyncio.create_task(self._main_routine()))
		return tasks

	def register_hardware(self, keyboard_hardware):
		hardware = keyboard_hardware()
		self._check_hardware_api(hardware)
		self.hardware = hardware

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
		return 0 # no action

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

	@async_no_fail
	async def _handle_action_macro(self, action_code, press):
		if self._macro_handler is None:
			return
		macro_interface = MacroInterface(
				keyboard_core = self,
				hid_manager = self.hid_manager,
				keyboard_hardware = self.hardware)
		i = action_code & 0xFFF
		await self._macro_handler(macro_interface, i, press)

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

	async def _trigger_tapkey_action_tap(self, key_id, key_variant):
		action_code = self.keys_last_action_code[key_id]
		keycode = action_code & 0xFF
		self.keys_last_action_code[key_id] = keycode
		await self.hid_manager.keyboard_press(keycode)

	@async_no_fail
	async def _handle_action_backlight(self, action_code):
		backlight = self.hardware.backlight
		if action_code == RGB_MOD:
			backlight.next()
		elif action_code == RGB_TOGGLE:
			backlight.toggle()
		elif action_code == RGB_HUE:
			backlight.hue += 8
		elif action_code == HUE_RGB:
			backlight.hue -= 8
		elif action_code == RGB_SAT:
			backlight.sat += 8
		elif action_code == SAT_RGB:
			backlight.sat -= 8
		elif action_code == RGB_VAL:
			backlight.val += 8
		elif action_code == VAL_RGB:
			backlight.val -= 8

	async def _update_mouse_movement(self):
		if self._mouse_status <= 0:
			return
		x, y, wheel = self._mouse_move
		current_time = time.monotonic_ns()
		dt = current_time - self._mouse_time
		distance = max(1, dt * self._mouse_speed // 40000000)
		self._mouse_time = current_time
		await self.hid_manager.mouse_move(x * distance, y * distance, wheel)
		logger.debug('dt %f, distance %d' % (dt, distance))
		# TODO: better acceleration curve
		if self._mouse_speed < 50:
			self._mouse_speed += 1

	async def _handle_action_mouse_press(self, action_code):
		mouse_code = (action_code >> 8) & 0xF
		if mouse_code == 0: # BTN1~5
			await self.hid_manager.mouse_press(action_code & 0xF)
		elif mouse_code >= 11: # MS_ACC
			self._mouse_speed += 1
		else:
			self._mouse_status += 1
			m = MS_MOVEMENT[mouse_code]
			self._mouse_move[0] += m[0]
			self._mouse_move[1] += m[1]
			self._mouse_move[2] += m[2]
			self._mouse_time = time.monotonic_ns()

	async def _handle_action_mouse_release(self, action_code):
		mouse_code = (action_code >> 8) & 0xF
		if mouse_code == 0: # BTN1~5
			await self.hid_manager.mouse_release(action_code & 0xF)
		elif mouse_code >= 11: # MS_ACC
			self._mouse_speed -= 1
		else:
			self._mouse_status -= 1
			m = MS_MOVEMENT[mouse_code]
			self._mouse_move[0] -= m[0]
			self._mouse_move[1] -= m[1]
			self._mouse_move[2] -= m[2]
			if self._mouse_status == 0:
				self._mouse_speed = 1
				await self.hid_manager.mouse_move() # reset mouse movement

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
		# Normal Typing 1 - A is a tap-key
		#   A???      B???      A???      B???
		# --+-------+-------+-------+------> t
		#           |       |
		#           V
		#           Trigger A(HOLD) here
		# Normal Typing 2 - A is a tap-key
		#   A???              A???
		# --+-------+-------+--------------> t
		#      dt1  |       |
		#           V
		#           Trigger A(HOLD) here, dt1 > tap_thresh
		tap_thresh = self._tap_thresh
		tap_key_last_id = 0
		tap_key_variant = 0 # also a marker whether tapkey is processed
		# to improve fast typing, use tap_delay to find out if the key is a tap in a sequence
		# Fast Typing - B is a tap-key
		#   A???      B???      A???      B???
		# --+-------+-------+-------+------> t
		#           |  dt1  |
		#         dt1 < tap_delay
		tap_delay = self._tap_delay
		# to further impove fast typing, add another check
		# Fast Typing - B is a tap-key
		#   B???      C???      B???      C???
		# --+-------+-------+-------+------> t
		#   |  dt1  |  dt2  |
		# dt1 < tap_delay && dt2 < fast_type_thresh
		# comparing dt2 and fast_type_thresh is not implemented
		# then it becomes:
		#  press    delay     thresh
		#  |        ^         ^
		#  v   1    |    2    |    3
		# ----------+---------+---------> t
		# 1: any key action will trigger `tap`
		# 2: any `pressed` action will trigger `hold`, any `release` action will trigger `tap`
		# 3: `hold` is triggered


		# for auto suspend, like a watch dog
		last_active_time = time.monotonic()
		suspend_time_limit = 10 * 60  # 10 min

		# report loop
		while True:
			if time.monotonic() - last_active_time > suspend_time_limit:
				logger.info("Auto suspend the keyboard")
				await input_hardware.suspend()
				# set last_active_time in case suspend is a dummy function
				last_active_time = time.monotonic()

			# switch task, give some time to the scanner
			await asyncio.sleep(0)

			event_count = await input_hardware.get_keys()
			trigger_time = ms()

			
			# check tapkey before any action
			# hold: 12~8: 5bits, modifiers or layer
			# tap: 7~0: 8bit, anykey
			if tap_key_variant > 0:
				duration = trigger_time - keys_down_time[tap_key_last_id]
				if duration > tap_thresh: # hold time long enough
					logger.debug("TAP/L/hold/timeout")
					await self._trigger_tapkey_action_hold(tap_key_last_id, tap_key_variant)
					tap_key_variant = 0

			# update mouse movements
			await self._update_mouse_movement()

			# process events
			# Note: iter the input_hardware will also consume the events
			for event in input_hardware:
				# the key_id is the relative ID in the keymap
				key_id = event & 0x7F
				press = (event & 0x80) == 0
				logger.debug("Event: %d | %d" % (key_id, press))
				last_active_time = time.monotonic()

				if press:
					keys_down_time[key_id] = trigger_time
					self._heatmap[key_id] += 1

					# trigger tapkey `hold` action when key down events detected
					# This will alter self._layer_mask thus affect action_code
					if tap_key_variant > 0:
						if duration < tap_delay: # quick typing
							# TODO: better checking
							logger.debug("TAP/L/tap/sequence")
							await self._trigger_tapkey_action_tap(tap_key_last_id, tap_key_variant)
							tap_key_variant = 0
						else:
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
						await self._handle_action_mouse_press(action_code)
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
						await self._handle_action_macro(action_code, press)
					elif key_variant == ACT_BACKLIGHT:
						await self._handle_action_backlight(action_code)
					elif key_variant == ACT_COMMAND:
						await self._handle_action_command(action_code)
					
				else: # release
					keys_up_time[key_id] = trigger_time

					# detect tap key in a sequence
					if tap_key_variant > 0:
						duration = trigger_time - keys_down_time[tap_key_last_id]
						if duration < tap_thresh: # just a tap in a sequence
							logger.debug("TAP/L/tap/sequence")
							await self._trigger_tapkey_action_tap(tap_key_last_id, tap_key_variant)
							tap_key_variant = 0

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
						await self._handle_action_mouse_release(action_code)
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
						await self._handle_action_macro(action_code, press)

