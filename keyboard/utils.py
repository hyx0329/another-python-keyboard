# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

import supervisor


def is_usb_connected():
	if hasattr(supervisor.runtime, 'usb_connected'):
		return supervisor.runtime.usb_connected

	@micropython.asm_thumb
	def mem(r0):
		"""Read memory from the address"""
		ldr(r0, [r0, 0])
	return mem(0x40000438) == 0x3


def do_nothing(*args, **kargs):
	pass


class LightQueue:
	def __init__(self, size):
		self.capacity = size
		self.storage = [0] * size
		self.length = 0
		self.head = 0
		self.tail = 0

	def put(self, value):
		if self.length < self.capacity:
			self.storage[self.tail] = value
			self.tail = ( self.tail + 1 ) % self.capacity
			self.length += 1

	def get(self):
		if self.length > 0:
			value = self.storage[self.head]
			self.head = ( self.head + 1 ) % self.capacity
			self.length -= 1
			return value

	def clear(self):
		self.length = 0
		self.head = 0
		self.tail = 0

	def wipe(self):
		self.clear()
		for i in range(self.capacity):
			self.storage[i] = 0

	def __iter__(self):
		return self

	def __next__(self):
		if self.length == 0:
			raise StopIteration
		else:
			return self.get()

	def __len__(self):
		return self.length

	def __getitem__(self, key):
		if 0 <= key < self.length:
			index = (self.head + key) % self.capacity
			return self.storage[index]
		elif key < 0 and abs(key) <= self.length:
			index = (self.tail + key) % self.capacity
			return self.storage[index]
		else:
			raise IndexError

