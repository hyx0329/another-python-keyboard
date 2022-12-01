# -*- encoding: utf-8 -*-
# vim: ts=4 noexpandtab

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
		else:
			self.get()
			self.put(value)

	def get(self):
		if self.length > 0:
			value = self.storage[self.head]
			self.head = ( self.head + 1 ) % self.capacity
			self.length -= 1
			return value
		return None

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

