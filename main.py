import pygame
import random
import time
import math
import numpy as np
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

# --- NEW: visual flair state (starfield, floating texts) ---
stars = [
    {"x": random.uniform(0, SCREEN_WIDTH), "y": random.uniform(0, SCREEN_HEIGHT),
     "r": random.uniform(0.6, 2.6), "phase": random.uniform(0, math.pi*2)}
    for _ in range(72)
]
floating_texts = []  # small transient score / combo pops
_color_cycle_t = 0.0

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
    def __init__(self, idx=None):
        # allow explicit index for next-piece preview
        i = idx if idx is not None else random.randint(0, len(SHAPES)-1)
        self.index = i
        self.shape = [row[:] for row in SHAPES[i]]
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

def draw_ui(score, status, next_piece):
    panel_x = GRID_WIDTH * BLOCK_SIZE + 10
    pygame.draw.rect(screen, (20,20,30), (GRID_WIDTH * BLOCK_SIZE, 0, 220, SCREEN_HEIGHT))

    # --- NEW: pulsing rainbow title ---
    global _color_cycle_t
    t = _color_cycle_t
    hue = int((math.sin(t*1.8) * 0.5 + 0.5) * 255)
    title_col = (hue, 255 - hue, 200)
    pulse = 1.0 + 0.06 * math.sin(t * 6.0)
    title_surf = big_font.render("NeuroBlocks", True, title_col)
    ts_w, ts_h = title_surf.get_size()
    title_surf = pygame.transform.smoothscale(title_surf, (int(ts_w*pulse), int(ts_h*pulse)))
    screen.blit(title_surf, (panel_x, 20 - int((pulse-1.0)*10)))

    screen.blit(font.render(f"Score: {score}", True, (255,255,255)), (panel_x, 80))
    screen.blit(font.render(f"Mode: {status}", True, (180,180,255)), (panel_x, 120))

    # Next piece preview
    screen.blit(font.render("Next:", True, (200,200,255)), (panel_x, 160))
    # preview area
    preview_x = panel_x + 10
    preview_y = 190
    preview_block = 18
    # draw a small 4x4 preview
    for ry in range(4):
        for rx in range(4):
            pygame.draw.rect(screen, (30,30,40), (preview_x+rx*preview_block, preview_y+ry*preview_block, preview_block, preview_block))
            pygame.draw.rect(screen, (40,40,60), (preview_x+rx*preview_block, preview_y+ry*preview_block, preview_block, preview_block), 1)

    # draw next piece centered in preview
    shape = SHAPES[next_piece.index]
    px = preview_x + (4 - len(shape[0]))//2 * preview_block
    py = preview_y + (4 - len(shape))//2 * preview_block
    for y,row in enumerate(shape):
        for x,cell in enumerate(row):
            if cell:
                pygame.draw.rect(screen, next_piece.color, (px + x*preview_block, py + y*preview_block, preview_block, preview_block))

# helper: return ghost y position for current piece
def get_ghost_y(piece, grid):
    g = Piece(idx=piece.index)
    g.shape = [row[:] for row in piece.shape]
    g.x = piece.x
    g.y = piece.y
    while valid(g, grid, 0, 1):
        g.y += 1
    return g.y

def spawn_piece(next_idx):
    return Piece(idx=next_idx)

def clamp(v, a, b):
    return max(a, min(b, v))

def draw_background():
    # simple vertical gradient enhanced with animated stars
    global _color_cycle_t
    # base gradient
    for i in range(SCREEN_HEIGHT):
        t = i / SCREEN_HEIGHT
        r = int(8 + t*20)
        g = int(10 + t*25)
        b = int(15 + t*30)
        pygame.draw.line(screen, (r,g,b), (0,i), (GRID_WIDTH*BLOCK_SIZE, i))

    # animated stars (twinkle)
    for s in stars:
        s["phase"] += 0.02
        tw = 0.5 + 0.5 * math.sin(s["phase"]*2.0 + _color_cycle_t*3.0)
        col = int(200 + 55*tw)
        x = int(s["x"])
        y = int(s["y"])
        r = max(1, int(s["r"]*tw))
        pygame.draw.circle(screen, (col,col,255), (x, y), r)

# helper: simple procedural tone for clears (no external assets)
def play_clear_tone(cleared):
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=1)
    except Exception:
        return
    # base freq rises with cleared count
    freq = 440 + cleared*110
    sr = 44100
    length = 0.28
    t = np.linspace(0, length, int(sr*length), False)
    wave = 0.5 * np.sin(2 * np.pi * freq * t) * np.exp(-3*t)  # pluck-like
    # add second harmonic
    wave += 0.25 * np.sin(2 * np.pi * (freq*2) * t) * np.exp(-6*t)
    # convert to 16-bit
    audio = np.int16(wave * 32767)
    try:
        sound = pygame.sndarray.make_sound(audio)
        sound.play()
    except Exception:
        pass

# helper: build scanline surface once
def make_scanlines(width, height, spacing=3):
    surf = pygame.Surface((width, height), pygame.SRCALPHA)
    for y in range(0, height, spacing):
        pygame.draw.line(surf, (0,0,0,40), (0,y), (width,y))
    return surf

# helper: additive bloom pass (cheap)
def bloom_blit(target, src, strength=0.18):
    w,h = src.get_size()
    # upscale-smudge technique
    up = pygame.transform.smoothscale(src, (w*2, h*2))
    blur = pygame.transform.smoothscale(up, (w, h))
    tmp = blur.copy()
    tmp.set_alpha(int(255*strength))
    target.blit(tmp, (0,0), special_flags=pygame.BLEND_ADD)

def main():
    global floating_texts, _color_cycle_t
    grid = [[0]*GRID_WIDTH for _ in range(GRID_HEIGHT)]
    # next piece system
    next_idx = random.randint(0, len(SHAPES)-1)
    piece = spawn_piece(next_idx)
    next_idx = random.randint(0, len(SHAPES)-1)
    next_piece = Piece(idx=next_idx)

    # render-to-surface for bloom & shake
    scene_w = GRID_WIDTH * BLOCK_SIZE
    scene_h = SCREEN_HEIGHT
    scene_surf = pygame.Surface((scene_w, scene_h)).convert_alpha()
    scan_surf = make_scanlines(scene_w, scene_h, spacing=3)

    drop_timer = time.time()
    drop_speed = BASE_DROP_SPEED
    score = 0

    # combo + shake
    combo = 0
    last_clear_time = 0.0
    screen_shake = 0.0

    # input DAS/ARR state
    left_held = False
    right_held = False
    hold_start = None
    last_arr = 0.0
    DAS = 0.15   # seconds before auto-shift starts
    ARR = 0.06   # repeat interval once DAS passed

    # particles for row clears
    particles = []

    running=True
    while running:
        now = time.time()
        clock.tick(FPS)

        # update global visuals timer
        dt_frame = clock.get_time() / 1000.0
        _color_cycle_t += dt_frame

        # clear scene surface (draw background into scene)
        scene_surf.fill((0,0,0,0))
        # draw background gradient onto scene_surf (reuse previous draw_background logic)
        for i in range(scene_h):
            t = i / scene_h
            r = int(8 + t*20)
            g = int(10 + t*25)
            b = int(15 + t*30)
            pygame.draw.line(scene_surf, (r,g,b), (0,i), (scene_w, i))
        # stars (slightly parallax)
        for s in stars:
            tw = 0.5 + 0.5 * math.sin(s["phase"]*2.0 + _color_cycle_t*3.0)
            col = int(200 + 55*tw)
            r = max(1, int(s["r"]*tw))
            pygame.draw.circle(scene_surf, (col,col,255), (int(s["x"]*0.85), int(s["y"]*0.9)), r)
            s["phase"] += 0.02

        for e in pygame.event.get():
            if e.type==pygame.QUIT:
                running=False
            elif e.type==pygame.KEYDOWN:
                # handle single-action keys on keydown to avoid repeated rotations/moves
                if use_keyboard:
                    if e.key==pygame.K_LEFT and valid(piece,grid,-1,0):
                        piece.x-=1
                        left_held = True
                        hold_start = now
                        last_arr = now
                    elif e.key==pygame.K_RIGHT and valid(piece,grid,1,0):
                        piece.x+=1
                        right_held = True
                        hold_start = now
                        last_arr = now
                    elif e.key==pygame.K_UP:
                        old=piece.shape
                        piece.rotate()
                        if not valid(piece,grid):
                            piece.shape=old
                    # allow immediate fast-drop on press; holding is handled below
                    elif e.key==pygame.K_DOWN:
                        drop_speed = 0.05
                # keep EEG mode keydown handling empty (testing could be added)
            elif e.type==pygame.KEYUP:
                if use_keyboard:
                    if e.key==pygame.K_LEFT:
                        left_held = False
                        hold_start = None
                    elif e.key==pygame.K_RIGHT:
                        right_held = False
                        hold_start = None
                    elif e.key==pygame.K_DOWN:
                        drop_speed = BASE_DROP_SPEED

        # DAS / ARR handling
        if use_keyboard:
            if left_held or right_held:
                if hold_start is None:
                    hold_start = now
                held_time = now - hold_start
                if held_time >= DAS:
                    if now - last_arr >= ARR:
                        if left_held and valid(piece, grid, -1, 0):
                            piece.x -= 1
                        if right_held and valid(piece, grid, 1, 0):
                            piece.x += 1
                        last_arr = now

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

        # ghost calculation
        ghost_y = get_ghost_y(piece, grid)

        if time.time()-drop_timer>drop_speed:
            if valid(piece,grid,0,1):
                piece.y+=1
            else:
                # lock piece into grid
                for y,row in enumerate(piece.shape):
                    for x,cell in enumerate(row):
                        if cell:
                            if 0 <= piece.y+y < GRID_HEIGHT and 0 <= piece.x+x < GRID_WIDTH:
                                grid[piece.y+y][piece.x+x]=piece.color
                grid, cleared = clear_rows(grid)
                if cleared:
                    # audio + combo
                    play_clear_tone(cleared)
                    if now - last_clear_time < 1.2:
                        combo += 1
                    else:
                        combo = 1
                    last_clear_time = now

                    # screen shake proportional to clear and combo
                    screen_shake = min(24.0, cleared*6 + combo*2)

                    # particles + colorful confetti burst
                    for _ in range(cleared * 20 + combo*6):
                        px = random.uniform(0, GRID_WIDTH*BLOCK_SIZE)
                        py = random.uniform(0, SCREEN_HEIGHT/2)
                        vx = random.uniform(-240, 240)
                        vy = random.uniform(-260, -80)
                        life = random.uniform(0.9, 1.8)
                        size = random.choice([3,4,6,8])
                        color = (random.randint(120,255), random.randint(80,255), random.randint(80,255))
                        particles.append({"x":px, "y":py, "vx":vx, "vy":vy, "life":life, "t":0, "color":color, "size":size})

                    # floating score pop with combo text
                    pop_text = f"+{cleared*100}"
                    if combo>1:
                        pop_text += f"  x{combo}"
                    floating_texts.append({"x": SCREEN_WIDTH//2, "y": SCREEN_HEIGHT//2 - 20, "text": pop_text, "t": 0.0, "life": 1.4})

                score += cleared * 100 * max(1, combo)
                # spawn next piece
                piece = spawn_piece(next_piece.index)
                # immediately prepare subsequent next
                next_idx = random.randint(0, len(SHAPES)-1)
                next_piece = Piece(idx=next_idx)
                # if new piece invalid at spawn -> game over
                if not valid(piece, grid, 0, 0):
                    # simple game over screen (with shake freeze)
                    screen.fill((0,0,0))
                    screen.blit(big_font.render("GAME OVER", True, (255,50,50)), (SCREEN_WIDTH//2 - 120, SCREEN_HEIGHT//2 - 20))
                    screen.blit(font.render(f"Final Score: {score}", True, (255,255,255)), (SCREEN_WIDTH//2 - 80, SCREEN_HEIGHT//2 + 20))
                    pygame.display.flip()
                    pygame.time.wait(2000)
                    running = False
            drop_timer=time.time()

        # update particles (draw into scene_surf)
        new_particles = []
        for p in particles:
            p["t"] += dt_frame
            p["x"] += p["vx"] * dt_frame
            p["y"] += p["vy"] * dt_frame
            p["vy"] += 420 * dt_frame  # gravity
            if p["t"] < p["life"]:
                alpha = int(255 * (1 - p["t"]/p["life"]))
                col = p["color"]
                size = p.get("size", 6)
                surf = pygame.Surface((size, size), pygame.SRCALPHA)
                surf.fill((col[0], col[1], col[2], alpha))
                scene_surf.blit(surf, (p["x"], p["y"]))
                new_particles.append(p)
        particles = new_particles

        # floating text update & draw (draw on scene)
        new_floats = []
        for ft in floating_texts:
            ft["t"] += dt_frame
            yoff = -60 * (ft["t"]/ft["life"])
            alpha = max(0, int(255 * (1 - ft["t"]/ft["life"])))
            txt = big_font.render(ft["text"], True, (255, 220, 100))
            txt.set_alpha(alpha)
            scene_surf.blit(txt, (ft["x"] - txt.get_width()//2, ft["y"] + yoff))
            if ft["t"] < ft["life"]:
                new_floats.append(ft)
        floating_texts = new_floats

        # draw grid and pieces onto scene_surf (with glow)
        for y in range(GRID_HEIGHT):
            for x in range(GRID_WIDTH):
                if grid[y][x]:
                    glow_surf = pygame.Surface((BLOCK_SIZE+6, BLOCK_SIZE+6), pygame.SRCALPHA)
                    col = grid[y][x]
                    glow_surf.fill((*col, 28))
                    scene_surf.blit(glow_surf, (x*BLOCK_SIZE-3, y*BLOCK_SIZE-3))
                    pygame.draw.rect(scene_surf,grid[y][x],(x*BLOCK_SIZE,y*BLOCK_SIZE,BLOCK_SIZE,BLOCK_SIZE))
                pygame.draw.rect(scene_surf,(40,40,60),(x*BLOCK_SIZE,y*BLOCK_SIZE,BLOCK_SIZE,BLOCK_SIZE),1)

        # ghost + piece draw onto scene_surf
        ghost_color = (80,80,100)
        for y,row in enumerate(piece.shape):
            for x,cell in enumerate(row):
                if cell:
                    gx = (piece.x + x) * BLOCK_SIZE
                    gy = (ghost_y + y) * BLOCK_SIZE
                    ghost_surf = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
                    ghost_surf.fill((*ghost_color, 90))
                    scene_surf.blit(ghost_surf, (gx, gy))
        for y,row in enumerate(piece.shape):
            for x,cell in enumerate(row):
                if cell:
                    bx = (piece.x+x)*BLOCK_SIZE
                    by = (piece.y+y)*BLOCK_SIZE
                    glow = pygame.Surface((BLOCK_SIZE+8, BLOCK_SIZE+8), pygame.SRCALPHA)
                    glow.fill((*piece.color, 48))
                    scene_surf.blit(glow, (bx-4, by-4))
                    pygame.draw.rect(scene_surf,piece.color,(bx,by,BLOCK_SIZE,BLOCK_SIZE))
                    pygame.draw.rect(scene_surf,(255,255,255),(bx,by,BLOCK_SIZE,BLOCK_SIZE),1)

        # UI draws onto scene_surf panel area (reuse draw_ui but draw on scene then later blit; simpler: call draw_ui to draw onto screen after bloom)
        # apply bloom onto a temporary surface and blit to screen with possible shake
        screen.fill((0,0,0))
        # create bloom effect by additive blit of blurred scene
        bloom_blit(screen, scene_surf, strength=0.14)
        # main scene
        # compute shake offset and blit
        if screen_shake > 0.05:
            sx = int(random.uniform(-screen_shake, screen_shake))
            sy = int(random.uniform(-screen_shake, screen_shake))
            screen_shake = max(0.0, screen_shake - 40*dt_frame)
        else:
            sx = sy = 0
            screen_shake = 0.0
        screen.blit(scene_surf, (sx, sy))
        # scanlines on grid area
        screen.blit(scan_surf, (sx, sy), special_flags=pygame.BLEND_MULT)

        status = "Keyboard" if use_keyboard else ("Calibrating..." if not bci.calibrated else "EEG Active")
        draw_ui(score, status, next_piece)

        pygame.display.flip()

    pygame.quit()

if __name__=="__main__":
    main()
