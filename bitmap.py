import pygame
import numpy as np
import moderngl as mgl
from line_profiler_pycharm import profile
import struct


def load_compute():
	with open('shaders/compute.glsl', 'r') as f:
		data = f.read()
	return data


ctx = mgl.create_standalone_context()
compute_shader = ctx.compute_shader(load_compute())
data_buffer = ctx.buffer(np.zeros(shape=(200 * 150, ), dtype=np.uint32))
data_buffer.bind_to_storage_buffer(0)
output_buffer = ctx.buffer(np.zeros(shape=(938, ), dtype=np.uint32), dynamic=True)  # chatgpt told me to add dynamic
# and to remove the following line
#output_buffer.bind_to_storage_buffer(1)


@profile
def compute_image_to_bitmap(img: pygame.Surface):
	data = np.frombuffer(img.get_buffer().raw, dtype=np.uint32)
	data_buffer.write(data)
	output_buffer.write(np.zeros(shape=(938, ), dtype=np.uint32))
	compute_shader.run(200, 150, 1)
	result = output_buffer.read()
	# warning : causes segfault
	# yes, python segfault
	#result = np.empty(shape=(938,), dtype=np.uint32)
	#output_buffer.read_into(result)
	integer_value = int.from_bytes(b''.join(struct.pack('<I', val) for val in result), byteorder='little')
	return Bitmap(*img.get_size(), integer_value)


class Bitmap:
	def __init__(self, x, y, map_data=0):
		self.x = x
		self.y = y
		self.all1 = 2 ** (self.x * self.y) - 1
		self.map = map_data

	@staticmethod
	def mask_from_img(img: pygame.Surface, col):
		# toooooooo slow
		# using compute shaders instead
		size = img.get_size()
		mask = Bitmap(*size)
		for x in range(size[0]):
			for y in range(size[1]):
				if img.get_at((x, y)) == col:
					mask.set_at(x, y, 1)
		return mask

	@staticmethod
	def image_to_bitmap(img: pygame.Surface):
		# faster but not working
		data = np.frombuffer(img.get_buffer().raw, dtype=np.uint32)
		bitmap = 0
		for n, i in enumerate(data):
			# shit
			# problems with signed int 64
			bitmap += int(i & 0b1) << n
		return Bitmap(*img.get_size(), bitmap)

	def invert_mask(self, mask):
		self.map = self.map ^ mask.map

	def intersect_mask(self, mask):
		self.map = self.map & mask.map

	def union_mask(self, mask):
		self.map = self.map | mask.map

	def reverse(self):
		self.map = ~self.map

	def reversed(self):
		return Bitmap(self.x, self.y, ~self.map)

	def _flatten_coords(self, x, y):
		return x + self.x * y

	def get_at(self, x, y):
		return (self.map >> self._flatten_coords(x, y)) & 0b1

	def set_at(self, x, y, d):
		fc = self._flatten_coords(x, y)
		mask = self.all1 - 2 ** fc
		self.map = (self.map & mask) | ((d & 0b1) << fc)

	def bufferize(self):
		buffer = []
		for i in range(938):
			buffer.append((self.map >> (32 * i)) & (2 ** 32 - 1))
		return buffer
