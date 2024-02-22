import pygame
import moderngl as mgl
from array import array
import random
import sys
from bitmap import *
import math
from cryptography.fernet import Fernet
import base64


WIN_SIZE = (200, 150)
DOUBLE_WIN_SIZE = tuple(map(lambda x: x * 4, WIN_SIZE))


class MazeGame:
	cell_size = 15

	def __init__(self, x=35, y=35):
		# for each cell, a 2-bit int
		# first bit : bottom wall
		# second bit : right bit
		#
		# +   |
		#     | bit 1
		# ----+
		# bit 0
		#              | here all walls are set
		#              v
		self.map = [[0b11 for _ in range(y)] for _ in range(x)]
		self.x, self.y = x, y
		self.depth_first_gen()
		self.image_cache = self.gen_layout()
		# player
		self.pos = [0, 0]

	def gen_layout(self):
		img = pygame.Surface((self.x * self.cell_size + 1, self.y * self.cell_size + 1))
		pygame.draw.lines(img, (255, 255, 255), False, [(0, img.get_height()), (0, 0), (img.get_width(), 0)], 2)
		for x in range(self.x):
			for y in range(self.y):
				# bottom
				if self.map[x][y] & 0b01:
					pygame.draw.line(img, (255, 255, 255), (x * self.cell_size + self.cell_size, y * self.cell_size + self.cell_size), (x * self.cell_size, y * self.cell_size + self.cell_size), 2)
				# side
				if self.map[x][y] & 0b10:
					pygame.draw.line(img, (255, 255, 255), (x * self.cell_size + self.cell_size, y * self.cell_size + self.cell_size), (x * self.cell_size + self.cell_size, y * self.cell_size), 2)
		# draw end
		pygame.draw.rect(img, (255, 255, 255), pygame.Rect((self.x - 1) * self.cell_size + 2, (self.y - 1) * self.cell_size + 2, self.cell_size - 4, self.cell_size - 4))
		return img

	def depth_first_gen(self):
		arr_sum = lambda x, y: [x[0] + y[0], x[1] + y[1]]
		stack = [[random.randint(0, self.x - 1), random.randint(0, self.y - 1)]]
		visited = []
		while stack:
			moves = [(0, 1), (0, -1), (1, 0), (-1, 0)]
			# exclude out of bounds
			if stack[-1][0] == 0:
				moves.remove((-1, 0))
			elif stack[-1][0] == self.x - 1:
				moves.remove((1, 0))
			if stack[-1][1] == 0:
				moves.remove((0, -1))
			elif stack[-1][1] == self.y - 1:
				moves.remove((0, 1))
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

	def move(self, move):
		moved = False
		if move[0] == 1 and self.map[self.pos[0]][self.pos[1]] & 0b10 == 0:
			self.pos[0] += 1
			moved = True
		elif move[1] == 1 and self.map[self.pos[0]][self.pos[1]] & 0b01 == 0:
			self.pos[1] += 1
			moved = True
		elif move[0] == -1 and self.map[self.pos[0] - 1][self.pos[1]] & 0b10 == 0 and self.pos[0] > 0:
			self.pos[0] -= 1
			moved = True
		elif move[1] == -1 and self.map[self.pos[0]][self.pos[1] - 1] & 0b01 == 0 and self.pos[1] > 0:
			self.pos[1] -= 1
			moved = True
		if not moved:
			return None
		if self.pos == [self.x - 1, self.y - 1]:
			return True
		return False


class Game:
	speed = 0.1

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
		# saving things
		# random encrypt key -----------------,
		# saving is not really secured        |
		# it just discourage                  v
		self.cipher = Fernet(b'cUvENNHqvNIvZrg-Tdb6b0B83N9KvKFRbLhF8HtgFiw=')
		self.best_score = self.load_best_score()
		# game things
		self.font = pygame.font.Font('fonts/roboto/Roboto-Light.ttf', 120)
		self.font_small = pygame.font.Font('fonts/roboto/Roboto-Light.ttf', 50)
		self.bitmap = Bitmap(*WIN_SIZE)
		self.draw_init_msg()
		self.set_colors = (
			(255, 255, 255),
			(255, 0, 0),
			(0, 97, 255),
			(0, 126, 93),
			(255, 223, 185),
		)
		self.unset_colors = (
			(0, 0, 0),
			(0, 0, 0),
			(96, 239, 255),
			(248, 200, 40),
			(164, 25, 61),
		)
		self.current_color = 0
		# the current game state
		self._game_state = 0
		# 0 for shuffling
		self.n = 0
		self.target = 500  # 500 here (decrease for faster debug)
		# 1 for text displaying
		# 2 for star wars text
		self.text = ''
		self.txt_pos = pygame.Rect(0, 0, 0, 0)
		self.txt_surf = pygame.Surface((0, 0))
		# 3 for in game
		self.game = None
		self.key_buffer = []
		self.pos = [0, 0]
		self.moves_count = 0

	def load_best_score(self):
		score = -1
		try:
			with open('score.data', 'r') as f:
				data = f.read()
			score = int.from_bytes(self.cipher.decrypt(base64.b64decode(data)), 'big')
		except Exception as e:
			print('can\'t load data : %s' % e)
		return score

	def save_best_score(self):
		if self.best_score > 0:
			try:
				data = self.cipher.encrypt(self.best_score.to_bytes((self.best_score.bit_length() + 7) // 8, 'big'))
				with open('score.data', 'w') as f:
					f.write(base64.b64encode(data).decode('utf-8'))
			except Exception as e:
				print('error saving best score (%i) : %s' % (self.best_score, e))

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
			self.key_buffer = []
			self.pos = [20, 20]
			self.moves_count = 0
			self.game = MazeGame(20, 20)

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

	def move_towards(self, x, target):
		return x + math.copysign(min(abs(x - target), self.speed), target - x)

	def draw_random_line(self):
		img = pygame.Surface(WIN_SIZE)
		pygame.draw.line(
			img,
			(255, 255, 255),
			(random.randint(0, WIN_SIZE[0] - 1), random.randint(0, WIN_SIZE[1] - 1)),
			(random.randint(0, WIN_SIZE[0] - 1), random.randint(0, WIN_SIZE[1] - 1))
		)
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

	def update_maze(self):
		if self.pos == self.game.pos:
			if self.key_buffer:
				action = self.game.move(self.key_buffer.pop(0))
				if action is not None:
					self.moves_count += 1
				if action:
					if self.best_score == -1:
						self.best_score = self.moves_count
					else:
						self.best_score = min(self.best_score, self.moves_count)
					self.text = 'Well Done !  solved in %i moves' % self.moves_count
					if self.best_score > 0:
						self.text += ', best score : %i' % self.best_score
					self.game_state = 1
		else:
			# move towards
			self.pos = [self.move_towards(self.pos[0], self.game.pos[0]), self.move_towards(self.pos[1], self.game.pos[1])]
			# draw
			a = pygame.Surface((200, 150))
			a.blit(self.game.image_cache, (
				-self.pos[0] * MazeGame.cell_size + WIN_SIZE[0] / 2 - MazeGame.cell_size / 2,
				-self.pos[1] * MazeGame.cell_size + WIN_SIZE[1] / 2 - MazeGame.cell_size / 2
			))
			pygame.draw.rect(a, (255, 255, 255), pygame.Rect(WIN_SIZE[0] / 2 - 3, WIN_SIZE[1] / 2 - 3, 7, 7))
			self.bitmap.invert_mask(Bitmap.image_to_bitmap(a))

	def update(self):
		# the update wrapper
		[self.draw_random_line, self.draw_text, self.star_wars_text, self.update_maze][self.game_state]()

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
					self.save_best_score()
					pygame.quit()
					sys.exit()
				if event.type == pygame.KEYDOWN:
					if event.key == pygame.K_c:
						# cycles through colors
						self.current_color = (self.current_color + 1) % len(self.set_colors)
					elif self.game_state in {1, 2}:
						if event.key == pygame.K_ESCAPE:
							self.text = 'HARDER MAZE  press enter to play -- press h to get help'
							self.game_state = 1
						elif event.key == pygame.K_h:
							self.text = 'play with arrows <> escape tu return to menu <> enter = play <> h = help <> c = change colors <> s = shuffle screen <> e = explanations of the graphics <> x = best score'
							self.game_state = 1
						elif event.key == pygame.K_s:
							self.target = 500
							self.game_state = 0
						elif event.key == pygame.K_x:
							if self.best_score > 0:
								self.text = 'Best score : %i' % self.best_score
							else:
								self.text = 'No best score yet'
							self.game_state = 1
						elif event.key == pygame.K_e:
							self.text = '''
each time something is drawn on screen,
the colors are inverted where there are colors.
thisisaverylongword
the movment gives the illusion of shapes
'''
							self.game_state = 2
						elif event.key == pygame.K_RETURN:
							self.game_state = 3
					elif self.game_state == 3:
						if event.key == pygame.K_ESCAPE:
							self.text = 'HARDER MAZE  press enter to play -- press h to get help'
							self.game_state = 1
						elif event.key == pygame.K_UP:
							self.key_buffer.append([0, -1])
						elif event.key == pygame.K_DOWN:
							self.key_buffer.append([0, 1])
						elif event.key == pygame.K_LEFT:
							self.key_buffer.append([-1, 0])
						elif event.key == pygame.K_RIGHT:
							self.key_buffer.append([1, 0])
			self.update()
			self.draw()
			pygame.display.flip()
			self.clock.tick(30)


if __name__ == "__main__":
	pygame.init()
	pygame.display.set_caption('Harder Maze')
	Game().run()
