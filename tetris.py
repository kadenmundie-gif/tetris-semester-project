

import pygame
import random
import sys

CELL_SIZE = 30
BOARD_WIDTH = 10
BOARD_HEIGHT = 20
SIDEBAR_WIDTH = 200
SCREEN_WIDTH = CELL_SIZE * BOARD_WIDTH + SIDEBAR_WIDTH
SCREEN_HEIGHT = CELL_SIZE * BOARD_HEIGHT

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (40, 40, 40)

COLORS = {
    'I': (0, 255, 255),
    'O': (255, 255, 0),
    'T': (128, 0, 128),
    'S': (0, 255, 0),
    'Z': (255, 0, 0),
    'J': (0, 0, 255),
    'L': (255, 165, 0),
}

# Each piece stored as ONE 4x4 orientation. Other rotations are generated
# at runtime via matrix rotation instead of being hand-written.
SHAPE_TEMPLATES = {
    'I': [[0, 0, 0, 0],
          [1, 1, 1, 1],
          [0, 0, 0, 0],
          [0, 0, 0, 0]],
    'O': [[0, 1, 1, 0],
          [0, 1, 1, 0],
          [0, 0, 0, 0],
          [0, 0, 0, 0]],
    'T': [[0, 1, 0, 0],
          [1, 1, 1, 0],
          [0, 0, 0, 0],
          [0, 0, 0, 0]],
    'S': [[0, 1, 1, 0],
          [1, 1, 0, 0],
          [0, 0, 0, 0],
          [0, 0, 0, 0]],
    'Z': [[1, 1, 0, 0],
          [0, 1, 1, 0],
          [0, 0, 0, 0],
          [0, 0, 0, 0]],
    'J': [[1, 0, 0, 0],
          [1, 1, 1, 0],
          [0, 0, 0, 0],
          [0, 0, 0, 0]],
    'L': [[0, 0, 1, 0],
          [1, 1, 1, 0],
          [0, 0, 0, 0],
          [0, 0, 0, 0]],
}

LINE_SCORES = [0, 40, 100, 300, 1200]  # points for 0/1/2/3/4 lines cleared


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------
class GameObject:

    def __init__(self, x, y):
        self.x = x
        self.y = y

    def draw(self, surface):
        raise NotImplementedError


class Tetromino(GameObject):

    def __init__(self, shape_key):
        super().__init__(x=BOARD_WIDTH // 2 - 2, y=0)
        self.shape_key = shape_key
        self.color = COLORS[shape_key]
        self.matrix = [row[:] for row in SHAPE_TEMPLATES[shape_key]]

    def cells(self):
        return [
            (self.x + c, self.y + r)
            for r, row in enumerate(self.matrix)
            for c, val in enumerate(row)
            if val
        ]

    def rotated(self):
        """Return a NEW matrix rotated 90 degrees clockwise (no mutation)."""
        return [list(row) for row in zip(*self.matrix[::-1])]

    def draw(self, surface):
        for col, row in self.cells():
            if row >= 0:
                rect = pygame.Rect(col * CELL_SIZE, row * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                pygame.draw.rect(surface, self.color, rect)
                pygame.draw.rect(surface, BLACK, rect, 1)


class Board:

    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = [[None] * width for _ in range(height)]

    def is_valid_position(self, cells):
        for col, row in cells:
            if col < 0 or col >= self.width or row >= self.height:
                return False
            if row >= 0 and self.grid[row][col] is not None:
                return False
        return True

    def lock_piece(self, piece):
        for col, row in piece.cells():
            if row >= 0:
                self.grid[row][col] = piece.color

    def clear_lines(self):
        full_rows = [r for r in range(self.height)
                     if all(cell is not None for cell in self.grid[r])]
        for r in full_rows:
            for c in range(self.width):
                self.grid[r][c] = None
        if full_rows:
            self._apply_column_gravity()
        return len(full_rows)

    def _apply_column_gravity(self):
        """Each column's blocks fall independently to fill any gaps below them."""
        for c in range(self.width):
            column = [self.grid[r][c] for r in range(self.height) if self.grid[r][c] is not None]
            padding = [None] * (self.height - len(column))
            new_column = padding + column
            for r in range(self.height):
                self.grid[r][c] = new_column[r]

    def draw(self, surface):
        for r in range(self.height):
            for c in range(self.width):
                rect = pygame.Rect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                if self.grid[r][c]:
                    pygame.draw.rect(surface, self.grid[r][c], rect)
                pygame.draw.rect(surface, GRAY, rect, 1)


class Game:

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tetris")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont(None, 28)

        self.board = Board(BOARD_WIDTH, BOARD_HEIGHT)
        self.score = 0
        self.level = 1
        self.fall_time = 0
        self.fall_speed = 500  # milliseconds per automatic drop

        self.current_piece = self._new_piece()
        self.next_piece = self._new_piece()
        self.game_over = False

    def _new_piece(self):
        return Tetromino(random.choice(list(SHAPE_TEMPLATES.keys())))

    def _fits(self, matrix, dx, dy):
        cells = [
            (self.current_piece.x + c + dx, self.current_piece.y + r + dy)
            for r, row in enumerate(matrix)
            for c, val in enumerate(row)
            if val
        ]
        return self.board.is_valid_position(cells)

    def move(self, dx, dy):
        if self._fits(self.current_piece.matrix, dx, dy):
            self.current_piece.x += dx
            self.current_piece.y += dy
            return True
        return False

    def rotate_piece(self):
        rotated = self.current_piece.rotated()
        if self._fits(rotated, 0, 0):
            self.current_piece.matrix = rotated

    def lock_current_piece(self):
        self.board.lock_piece(self.current_piece)
        cleared = self.board.clear_lines()
        if cleared:
            self.score += LINE_SCORES[cleared] * self.level

        self.current_piece = self.next_piece
        self.next_piece = self._new_piece()
        if not self.board.is_valid_position(self.current_piece.cells()):
            self.game_over = True

    def handle_input(self, event):
        if event.type != pygame.KEYDOWN:
            return
        if event.key == pygame.K_LEFT:
            self.move(-1, 0)
        elif event.key == pygame.K_RIGHT:
            self.move(1, 0)
        elif event.key == pygame.K_DOWN:
            self.move(0, 1)
        elif event.key == pygame.K_UP:
            self.rotate_piece()
        elif event.key == pygame.K_SPACE:
            while self.move(0, 1):
                pass
            self.lock_current_piece()

    def update(self, dt):
        self.fall_time += dt
        if self.fall_time >= self.fall_speed:
            self.fall_time = 0
            if not self.move(0, 1):
                self.lock_current_piece()

    def draw(self):
        self.screen.fill(BLACK)
        self.board.draw(self.screen)
        self.current_piece.draw(self.screen)

        score_surf = self.font.render(f"Score: {self.score}", True, WHITE)
        self.screen.blit(score_surf, (BOARD_WIDTH * CELL_SIZE + 20, 20))

        next_label = self.font.render("Next:", True, WHITE)
        self.screen.blit(next_label, (BOARD_WIDTH * CELL_SIZE + 20, 60))

        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if not self.game_over:
                    self.handle_input(event)
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

            if not self.game_over:
                self.update(dt)

            self.draw()

            if self.game_over:
                over_surf = self.font.render("GAME OVER - ESC to quit", True, WHITE)
                self.screen.blit(over_surf, (10, SCREEN_HEIGHT // 2))
                pygame.display.flip()


if __name__ == "__main__":
    Game().run()