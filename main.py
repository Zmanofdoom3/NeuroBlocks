import pygame
import random
import time
import math
from settings import *
from bci_engine import BCIEngine

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("NeuroBlocks: Cascade Edition")
clock = pygame.time.Clock()

font = pygame.font.SysFont("consolas", 20)
big_font = pygame.font.SysFont("consolas", 32)

# -------------------------
# SHAPES
# -------------------------
SHAPES = [
    [[1,1,1,1]],
    [[1,0,0],[1,1,1]],
    [[0,0,1],[1,1,1]],
    [[1,1],[1,1]],
    [[0,1,1],[1,1,0]],
    [[0,1,0],[1,1,1]],
    [[1,1,0],[0,1,1]]
]

COLORS = [
    (0,255,255),
    (0,0,255),
    (255,165,0),
    (255,255,0),
    (0,255,0),
    (160,32,240),
    (255,0,0)
]

# -------------------------
# PIECE
# -------------------------
class Piece:
    def __init__(self, idx=None):
        i = idx if idx is not None else random.randint(0, len(SHAPES)-1)
        self.index = i
        self.shape = [row[:] for row in SHAPES[i]]
        self.color = COLORS[i]
        self.x = GRID_WIDTH // 2 - len(self.shape[0]) // 2
        self.y = 0

    def rotate(self):
        self.shape = [list(row) for row in zip(*self.shape[::-1])]

# -------------------------
# HELPERS
# -------------------------
def valid(piece, grid, dx, dy):
    for y,row in enumerate(piece.shape):
        for x,cell in enumerate(row):
            if cell:
                nx = piece.x + x + dx
                ny = piece.y + y + dy
                if nx < 0 or nx >= GRID_WIDTH or ny >= GRID_HEIGHT:
                    return False
                if ny >= 0 and grid[ny][nx]:
                    return False
    return True

def clear_rows(grid):
    new = [row for row in grid if any(cell == 0 for cell in row)]
    cleared = GRID_HEIGHT - len(new)
    for _ in range(cleared):
        new.insert(0, [0]*GRID_WIDTH)
    return new, cleared

def apply_cascade_gravity(grid):
    moved = True
    while moved:
        moved = False
        for y in range(GRID_HEIGHT-2, -1, -1):
            for x in range(GRID_WIDTH):
                if grid[y][x] and grid[y+1][x] == 0:
                    grid[y+1][x] = grid[y][x]
                    grid[y][x] = 0
                    moved = True
    return grid

def get_ghost_y(piece, grid):
    g = Piece(idx=piece.index)
    g.shape = [row[:] for row in piece.shape]
    g.x = piece.x
    g.y = piece.y
    while valid(g, grid, 0, 1):
        g.y += 1
    return g.y

# -------------------------
# DRAWING
# -------------------------
def draw_background(t):
    for y in range(GRID_HEIGHT):
        for x in range(GRID_WIDTH):
            pulse = int(30 + 20 * math.sin(t*2 + x*0.4 + y*0.3))
            pygame.draw.rect(
                screen,
                (pulse, pulse, pulse+10),
                (x*BLOCK_SIZE, y*BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),
                1
            )

def draw_block(x, y, color, offset):
    ox, oy = offset
    rect = pygame.Rect(
        x*BLOCK_SIZE + ox,
        y*BLOCK_SIZE + oy,
        BLOCK_SIZE,
        BLOCK_SIZE
    )

    glow = pygame.Surface((BLOCK_SIZE+8, BLOCK_SIZE+8), pygame.SRCALPHA)
    pygame.draw.rect(glow, (*color, 80), (4,4,BLOCK_SIZE,BLOCK_SIZE), border_radius=6)
    screen.blit(glow, (rect.x-4, rect.y-4))

    pygame.draw.rect(screen, color, rect, border_radius=6)

    highlight = tuple(min(255, c+60) for c in color)
    pygame.draw.rect(screen, highlight, rect, 2, border_radius=6)

def draw_next_piece(next_piece):
    panel_x = GRID_WIDTH*BLOCK_SIZE + 20
    preview_y = 260
    preview_block = 20

    screen.blit(font.render("Next:", True, (200,200,255)),
                (panel_x, preview_y-30))

    shape = next_piece.shape
    offset_x = panel_x + (80 - len(shape[0])*preview_block)//2
    offset_y = preview_y

    for y,row in enumerate(shape):
        for x,cell in enumerate(row):
            if cell:
                pygame.draw.rect(screen, next_piece.color,
                    (offset_x + x*preview_block,
                     offset_y + y*preview_block,
                     preview_block, preview_block), border_radius=4)

# -------------------------
# MAIN
# -------------------------
def main():

    mode = input("Use keyboard or headset? (k/h): ").lower()
    use_keyboard = mode != "h"
    bci = BCIEngine(debug=False) if not use_keyboard else None

    grid = [[0]*GRID_WIDTH for _ in range(GRID_HEIGHT)]

    next_piece = Piece()
    piece = Piece(idx=next_piece.index)
    next_piece = Piece()

    drop_timer = time.time()
    drop_speed = BASE_DROP_SPEED
    score = 0
    combo = 0
    level = 1

    shake_time = 0
    flash_time = 0
    camera_offset = [0,0]
    particles = []

    running = True

    while running:
        now = time.time()
        clock.tick(FPS)
        screen.fill((10,10,15))

        if shake_time > 0:
            shake_time -= 1/FPS
            camera_offset = [random.randint(-6,6), random.randint(-6,6)]
        else:
            camera_offset = [0,0]

        draw_background(now)

        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False

            if use_keyboard and e.type == pygame.KEYDOWN:
                if e.key == pygame.K_LEFT and valid(piece, grid, -1, 0):
                    piece.x -= 1
                if e.key == pygame.K_RIGHT and valid(piece, grid, 1, 0):
                    piece.x += 1
                if e.key == pygame.K_UP:
                    old = piece.shape
                    piece.rotate()
                    if not valid(piece, grid, 0, 0):
                        piece.shape = old
                if e.key == pygame.K_DOWN:
                    drop_speed = 0.05

            if use_keyboard and e.type == pygame.KEYUP:
                if e.key == pygame.K_DOWN:
                    drop_speed = BASE_DROP_SPEED

        if now - drop_timer > drop_speed:
            if valid(piece, grid, 0, 1):
                piece.y += 1
            else:
                for y,row in enumerate(piece.shape):
                    for x,cell in enumerate(row):
                        if cell:
                            grid[piece.y+y][piece.x+x] = piece.color

                grid, cleared = clear_rows(grid)

                if cleared:
                    grid = apply_cascade_gravity(grid)
                    combo += 1
                    score += cleared * 100 * combo
                    shake_time = 0.25
                    flash_time = 0.15
                else:
                    combo = 0

                level = 1 + score // 1000
                drop_speed = max(0.08, BASE_DROP_SPEED - level*0.03)

                piece = Piece(idx=next_piece.index)
                next_piece = Piece()

                if not valid(piece, grid, 0, 0):
                    running = False

            drop_timer = now

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if grid[y][x]:
                    draw_block(x, y, grid[y][x], camera_offset)

        ghost_y = get_ghost_y(piece, grid)
        for y,row in enumerate(piece.shape):
            for x,cell in enumerate(row):
                if cell:
                    surf = pygame.Surface((BLOCK_SIZE,BLOCK_SIZE), pygame.SRCALPHA)
                    surf.fill((120,120,140,100))
                    screen.blit(surf,
                        ((piece.x+x)*BLOCK_SIZE + camera_offset[0],
                         (ghost_y+y)*BLOCK_SIZE + camera_offset[1]))

        for y,row in enumerate(piece.shape):
            for x,cell in enumerate(row):
                if cell:
                    draw_block(piece.x+x, piece.y+y, piece.color, camera_offset)

        if flash_time > 0:
            flash_time -= 1/FPS
            overlay = pygame.Surface((GRID_WIDTH*BLOCK_SIZE, SCREEN_HEIGHT))
            overlay.set_alpha(120)
            overlay.fill((255,255,255))
            screen.blit(overlay, (0,0))

        panel_x = GRID_WIDTH*BLOCK_SIZE + 10
        pygame.draw.rect(screen, (20,20,30),
                         (GRID_WIDTH*BLOCK_SIZE,0,220,SCREEN_HEIGHT))

        screen.blit(big_font.render("NeuroBlocks", True, (0,255,255)),
                    (panel_x, 20))
        screen.blit(font.render(f"Score: {score}", True, (255,255,255)),
                    (panel_x, 80))
        screen.blit(font.render(f"Combo: x{combo}", True, (255,180,0)),
                    (panel_x, 110))
        screen.blit(font.render(f"Level: {level}", True, (180,255,180)),
                    (panel_x, 140))

        draw_next_piece(next_piece)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
