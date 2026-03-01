import pygame
import random
import time
from settings import *
from bci_engine import BCIEngine

print("Select Control Mode:")
print("1 - Headset (EEG via LSL)")
print("2 - Keyboard")
mode = input("Enter 1 or 2: ").strip()

use_keyboard = mode == "2"

# new debug toggle from terminal
debug_input = input("Enable BCI debug output? (y/N): ").strip().lower()
debug = debug_input == "y"

pygame.init()
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("NeuroBlocks Hybrid")
clock = pygame.time.Clock()

font = pygame.font.SysFont("consolas", 20)
big_font = pygame.font.SysFont("consolas", 28)

if not use_keyboard:
    bci = BCIEngine(debug=debug)

SHAPES = [
    [[1,1,1,1]],
    [[1,1],[1,1]],
    [[0,1,0],[1,1,1]],
    [[1,0,0],[1,1,1]],
    [[0,0,1],[1,1,1]],
]

COLORS = [
    (0,255,255),
    (255,255,0),
    (200,0,200),
    (255,100,0),
    (0,200,100)
]

class Piece:
    def __init__(self):
        i = random.randint(0, len(SHAPES)-1)
        self.shape = SHAPES[i]
        self.color = COLORS[i]
        self.x = GRID_WIDTH//2 - len(self.shape[0])//2
        self.y = 0

    def rotate(self):
        self.shape = [list(row) for row in zip(*self.shape[::-1])]

def valid(piece, grid, dx=0, dy=0):
    for y,row in enumerate(piece.shape):
        for x,cell in enumerate(row):
            if cell:
                nx = piece.x+x+dx
                ny = piece.y+y+dy
                if nx<0 or nx>=GRID_WIDTH or ny>=GRID_HEIGHT:
                    return False
                if ny>=0 and grid[ny][nx]:
                    return False
    return True

def clear_rows(grid):
    new = [row for row in grid if any(cell==0 for cell in row)]
    cleared = GRID_HEIGHT - len(new)
    while len(new)<GRID_HEIGHT:
        new.insert(0,[0]*GRID_WIDTH)
    return new, cleared

def draw_ui(score, status):
    panel_x = GRID_WIDTH * BLOCK_SIZE + 10
    pygame.draw.rect(screen, (20,20,30), (GRID_WIDTH * BLOCK_SIZE, 0, 220, SCREEN_HEIGHT))

    screen.blit(big_font.render("NeuroBlocks", True, (0,255,255)), (panel_x, 20))
    screen.blit(font.render(f"Score: {score}", True, (255,255,255)), (panel_x, 80))
    screen.blit(font.render(f"Mode: {status}", True, (180,180,255)), (panel_x, 120))

def main():
    grid = [[0]*GRID_WIDTH for _ in range(GRID_HEIGHT)]
    piece = Piece()
    drop_timer = time.time()
    drop_speed = BASE_DROP_SPEED
    score = 0

    running=True
    while running:
        clock.tick(FPS)
        screen.fill((10,10,15))

        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                running=False
            elif e.type==pygame.KEYDOWN:
                # handle single-action keys on keydown to avoid repeated rotations/moves
                if use_keyboard:
                    if e.key==pygame.K_LEFT and valid(piece,grid,-1,0):
                        piece.x-=1
                    elif e.key==pygame.K_RIGHT and valid(piece,grid,1,0):
                        piece.x+=1
                    elif e.key==pygame.K_UP:
                        old=piece.shape
                        piece.rotate()
                        if not valid(piece,grid):
                            piece.shape=old
                    # allow immediate fast-drop on press; holding is handled below
                    elif e.key==pygame.K_DOWN:
                        drop_speed = 0.05
                # keep EEG mode keydown handling empty (testing could be added)

        # handle held keys (only use for continuous fast-drop)
        if use_keyboard:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_DOWN]:
                drop_speed = 0.05
            else:
                drop_speed = BASE_DROP_SPEED
        else:
            commands = bci.update()
            if commands:
                if commands["left"] and valid(piece,grid,-1,0):
                    piece.x-=1
                if commands["right"] and valid(piece,grid,1,0):
                    piece.x+=1
                if commands["rotate"]:
                    old=piece.shape
                    piece.rotate()
                    if not valid(piece,grid):
                        piece.shape=old
                drop_speed = BASE_DROP_SPEED/commands["drop_multiplier"]

        if time.time()-drop_timer>drop_speed:
            if valid(piece,grid,0,1):
                piece.y+=1
            else:
                for y,row in enumerate(piece.shape):
                    for x,cell in enumerate(row):
                        if cell:
                            grid[piece.y+y][piece.x+x]=piece.color
                grid, cleared = clear_rows(grid)
                score += cleared * 100
                piece=Piece()
            drop_timer=time.time()

        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if grid[y][x]:
                    pygame.draw.rect(screen,grid[y][x],(x*BLOCK_SIZE,y*BLOCK_SIZE,BLOCK_SIZE,BLOCK_SIZE))
                pygame.draw.rect(screen,(40,40,60),(x*BLOCK_SIZE,y*BLOCK_SIZE,BLOCK_SIZE,BLOCK_SIZE),1)

        for y,row in enumerate(piece.shape):
            for x,cell in enumerate(row):
                if cell:
                    pygame.draw.rect(screen,piece.color,( (piece.x+x)*BLOCK_SIZE,(piece.y+y)*BLOCK_SIZE,BLOCK_SIZE,BLOCK_SIZE))

        status = "Keyboard" if use_keyboard else ("Calibrating..." if not bci.calibrated else "EEG Active")
        draw_ui(score, status)

        pygame.display.flip()

    pygame.quit()

if __name__=="__main__":
    main()
