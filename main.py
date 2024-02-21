import pygame
import moderngl as mgl
from array import array
import random
import sys
from bitmap import *


WIN_SIZE = (200, 150)
DOUBLE_WIN_SIZE = tuple(map(lambda x: x * 4, WIN_SIZE))


class MazeGame:
	def __init__(self, x=35, y=35):
		# for each cell, a 2-bit int
		# first bit : bottom wall
		# second bit : right bit
		#
		# +   |
		#     | 1
		# ----+
		#  0
		#              | here all walls are set
		#              v
		self.map = [[0b11 for _ in range(y)] for _ in range(x)]
		self.x, self.y = x, y
		self.image_cache = self.gen_layout()

	def gen_layout(self):
		img = pygame.Surface((self.x * 10, self.y * 10))
		pygame.draw.lines(img, (255, 255, 255), False, [(0, img.get_height()), (0, 0), (img.get_width(), 0)])
		for x in range(self.x):
			for y in range(self.y):
				# bottom
				if self.map[x][y] & 0b01:
					pygame.draw.line(img, (255, 255, 255), (x * 10 + 10, y * 10 + 10), (x * 10, y * 10 + 10))
				# side
				if self.map[x][y] & 0b10:
					pygame.draw.line(img, (255, 255, 255), (x * 10 + 10, y * 10 + 10), (x * 10 + 10, y * 10))

	def depth_first_gen(self):
		arr_sum = lambda x, y: [x[0] + y[0], x[1] + y[1]]
		stack = [[random.randint(0, self.x - 1), random.randint(0, self.y - 1)]]
		visited = []
		while stack:
			moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]
			# exclude out of bounds
			if stack[-1][0] == 0:
				moves.remove((0, -1))
			elif stack[-1][0] == self.x - 1:
				moves.remove((0, 1))
			if stack[-1][1] == 0:
				moves.remove((-1, 0))
			elif stack[-1][1] == self.y - 1:
				moves.remove((1, 0))
			# exclude already visited cells
			i = 0
			while i < len(moves):
				if arr_sum(stack[-1], moves[i]) in stack + visited:
					moves.pop(i)
				else:
					i += 1
			# 'archive' cell if no moves possibles
			if not moves:
				visited.append(stack.pop(-1))
			# apply move
			else:
				move = random.choice(moves)
				new_place = arr_sum(stack[-1], move)
				# remove wall
				if move[0] == 1:
					self.map[stack[-1][0]][stack[-1][1]] &= 0b01
				elif move[1] == 1:
					self.map[stack[-1][0]][stack[-1][1]] &= 0b10
				elif move[0] == -1:
					self.map[new_place[0]][new_place[1]] &= 0b01
				elif move[1] == -1:
					self.map[new_place[0]][new_place[1]] &= 0b10
				# add to stack
				stack.append(new_place)


class Game:
	def __init__(self):
		self.screen = pygame.display.set_mode(DOUBLE_WIN_SIZE, pygame.OPENGL | pygame.DOUBLEBUF)
		# openGL things
		self.ctx = mgl.create_context()
		self.quad_buffer = self.ctx.buffer(
			data=array('f', [
				-1.0, 1.0, 0.0, 0.0,
				1.0, 1.0, 1.0, 0.0,
				-1.0, -1.0, 0.0, 1.0,
				1.0, -1.0, 1.0, 1.0
			])
		)
		self.program = self.ctx.program(
			vertex_shader=self.load_vertex(),
			fragment_shader=self.load_fragment(),
		)
		self.vao = self.ctx.vertex_array(self.program, [(self.quad_buffer, '2f 2f', 'vert', 'texcoord')])
		# pygame things
		self.clock = pygame.time.Clock()
		self.events = pygame.event.get()
		# game things
		self.font = pygame.font.Font('fonts/roboto/Roboto-Light.ttf', 120)
		self.font_small = pygame.font.Font('fonts/roboto/Roboto-Light.ttf', 50)
		self.bitmap = Bitmap(*WIN_SIZE)
		self.draw_init_msg()
		self.set_colors = (
			(1.0, 1.0, 1.0),
			(1.0, 0.0, 1.0)
		)
		self.unset_colors = (
			(0.0, 0.0, 0.0),
			(0.0, 1.0, 0.0)
		)
		self.current_color = 0
		# the current game state
		self._game_state = 0
		# 0 for shuffling
		self.n = 0
		self.target = 600
		# 1 for text displaying
		# 2 for star wars text
		self.text = ''
		self.txt_pos = pygame.Rect(0, 0, 0, 0)
		self.txt_surf = pygame.Surface((0, 0))
		# 3 for in game
		self.game = MazeGame()

	def draw_init_msg(self):
		img = pygame.Surface(WIN_SIZE)
		surf = pygame.font.Font('fonts/roboto/Roboto-Light.ttf', 80).render('WAIT!', False, (255, 255, 255))
		rect = surf.get_rect(center=img.get_rect().center)
		img.blit(surf, rect)
		self.bitmap.invert_mask(Bitmap.image_to_bitmap(img))

	@property
	def game_state(self):
		return self._game_state

	@game_state.setter
	def game_state(self, value):
		self._game_state = value
		if value == 0:
			self.n = 0
		elif value == 1:
			self.text = ' '.join(self.text.split('\n'))
			self.txt_surf = self.font.render(self.text, False, (255, 255, 255))
			self.txt_pos = self.txt_surf.get_rect(topleft=(WIN_SIZE[0], 150 / 2 - self.txt_surf.get_height() / 2))
		elif value == 2:
			self.text = self.wrapped_text()
			self.txt_surf = self.multiline_render()
			self.txt_pos = self.txt_surf.get_rect(topleft=(0, WIN_SIZE[1]))
		elif value == 3:
			raise NotImplementedError('Maze is not yet implemented')

	def wrapped_text(self):
		max_chars = 8
		allow_multiples_words = False
		text = ['']
		for elem in self.text.split(' '):
			if len(text[-1] + elem) < max_chars and allow_multiples_words:
				text[-1] = text[-1] + ' ' + elem
			else:
				i = 0
				while len(elem[i*max_chars::]) > max_chars:
					text.append(elem[i*max_chars:i*max_chars+max_chars:] + '-')
					i += 1
				text.append(elem[i*max_chars:i*max_chars+max_chars:])
		return '\n'.join(text)

	def multiline_render(self):
		img = pygame.Surface((0, 0))
		for txt in self.text.split('\n'):
			surf = self.font_small.render(txt, False, (255, 255, 255))
			new_img = pygame.Surface((max(img.get_width(), surf.get_width()), img.get_height() + surf.get_height()))
			new_img.blit(img, (0, 0))
			new_img.blit(surf, (0, img.get_height()))
			img = new_img
		return img

	@staticmethod
	def load_vertex():
		with open('shaders/vert.glsl', 'r') as f:
			data = f.read()
		return data

	@staticmethod
	def load_fragment():
		with open('shaders/frag.glsl', 'r') as f:
			data = f.read()
		return data

	def draw_random_line(self):
		img = pygame.Surface(WIN_SIZE)
		pygame.draw.line(
			img,
			(255, 255, 255),
			(random.randint(0, WIN_SIZE[0] - 1), random.randint(0, WIN_SIZE[1] - 1)),
			(random.randint(0, WIN_SIZE[0] - 1), random.randint(0, WIN_SIZE[1] - 1))
		)
		self.bitmap.invert_mask(Bitmap.image_to_bitmap(img))
		self.n += 1
		if self.n >= self.target:
			self.text = 'HARDER MAZE   press enter to play -- press h to get help'
			self.game_state = 1

	def draw_text(self):
		img = pygame.Surface(WIN_SIZE)
		img.blit(self.txt_surf, self.txt_pos)
		self.bitmap.invert_mask(Bitmap.image_to_bitmap(img))
		self.txt_pos.x -= 6
		if self.txt_pos.right < 0:
			self.txt_pos.left = WIN_SIZE[0]

	def star_wars_text(self):
		img = pygame.Surface(WIN_SIZE)
		img.blit(self.txt_surf, self.txt_pos)
		self.bitmap.invert_mask(Bitmap.image_to_bitmap(img))
		self.txt_pos.y -= 6
		if self.txt_pos.bottom < 0:
			self.txt_pos.top = WIN_SIZE[1]

	def update(self):
		# the update wrapper
		[self.draw_random_line, self.draw_text, self.star_wars_text][self.game_state]()

	def draw(self):
		self.program['bitmap'] = array(
			'I',
			# [random.randint(0, 2 ** 32 - 1) for _ in range(938)]
			self.bitmap.bufferize()
		)
		self.program['set_color'] = self.set_colors[self.current_color]
		self.program['unset_color'] = self.unset_colors[self.current_color]
		self.vao.render(mode=mgl.TRIANGLE_STRIP)

	def run(self):
		while True:
			self.events = pygame.event.get()
			for event in self.events:
				if event.type == pygame.QUIT:
					pygame.quit()
					sys.exit()
				if event.type == pygame.KEYDOWN and event.key == pygame.K_c:
					# cycles through colors
					self.current_color = (self.current_color + 1) % len(self.set_colors)
				if event.type == pygame.KEYDOWN and self.game_state in {1, 2}:
					if event.key == pygame.K_ESCAPE:
						self.text = 'HARDER MAZE  press enter to play -- press h to get help'
						self.game_state = 1
					elif event.key == pygame.K_h:
						self.text = 'play with arrows <> enter = play <> h = help <> c = change colors <> s = shuffle screen <> e = explanations of the graphics'
						self.game_state = 1
					elif event.key == pygame.K_s:
						self.target = 500
						self.game_state = 0
					elif event.key == pygame.K_e:
						self.text = '''
each time something is drawn on screen,
the colors are inverted where there are colors.
thisisaverylongword
the movment gives the illusion of shapes
'''
						self.game_state = 2
			self.update()
			self.draw()
			pygame.display.flip()
			self.clock.tick(30)


if __name__ == "__main__":
	pygame.init()
	pygame.display.set_caption('Harder Maze')
	Game().run()
