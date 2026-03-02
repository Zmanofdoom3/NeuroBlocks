]

class Piece:
    def __init__(self):
        i = random.randint(0, len(SHAPES)-1)
        self.shape = SHAPES[i]
    def __init__(self, idx=None):
        # allow explicit index for next-piece preview
        i = idx if idx is not None else random.randint(0, len(SHAPES)-1)
        self.index = i
        self.shape = [row[:] for row in SHAPES[i]]
self.color = COLORS[i]
self.x = GRID_WIDTH//2 - len(self.shape[0])//2
self.y = 0
@@ -72,25 +74,90 @@ def clear_rows(grid):
new.insert(0,[0]*GRID_WIDTH)
return new, cleared

def draw_ui(score, status):
def draw_ui(score, status, next_piece):
panel_x = GRID_WIDTH * BLOCK_SIZE + 10
pygame.draw.rect(screen, (20,20,30), (GRID_WIDTH * BLOCK_SIZE, 0, 220, SCREEN_HEIGHT))

screen.blit(big_font.render("NeuroBlocks", True, (0,255,255)), (panel_x, 20))
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
    # simple vertical gradient
    for i in range(SCREEN_HEIGHT):
        t = i / SCREEN_HEIGHT
        r = int(8 + t*20)
        g = int(10 + t*25)
        b = int(15 + t*30)
        pygame.draw.line(screen, (r,g,b), (0,i), (GRID_WIDTH*BLOCK_SIZE, i))

def main():
grid = [[0]*GRID_WIDTH for _ in range(GRID_HEIGHT)]
    piece = Piece()
    # next piece system
    next_idx = random.randint(0, len(SHAPES)-1)
    piece = spawn_piece(next_idx)
    next_idx = random.randint(0, len(SHAPES)-1)
    next_piece = Piece(idx=next_idx)

drop_timer = time.time()
drop_speed = BASE_DROP_SPEED
score = 0

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
        screen.fill((10,10,15))

        # background
        draw_background()

for e in pygame.event.get():
if e.type==pygame.QUIT:
@@ -100,8 +167,14 @@ def main():
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
@@ -111,9 +184,32 @@ def main():
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

        # handle held keys (only use for continuous fast-drop)
        # DAS / ARR handling for smooth left/right hold
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

            # handle held keys (only use for continuous fast-drop)
keys = pygame.key.get_pressed()
if keys[pygame.K_DOWN]:
drop_speed = 0.05
@@ -133,32 +229,96 @@ def main():
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
                            grid[piece.y+y][piece.x+x]=piece.color
                            if 0 <= piece.y+y < GRID_HEIGHT and 0 <= piece.x+x < GRID_WIDTH:
                                grid[piece.y+y][piece.x+x]=piece.color
grid, cleared = clear_rows(grid)
                if cleared:
                    # create particles from cleared rows for visual flair
                    for ry in range(GRID_HEIGHT):
                        # detect cleared rows by checking if any cell in row became 0 recently (approx)
                        pass
                    # create particles across the cleared lines area
                    for _ in range(cleared * 12):
                        px = random.uniform(0, GRID_WIDTH*BLOCK_SIZE)
                        py = random.uniform(0, SCREEN_HEIGHT)
                        vx = random.uniform(-60, 60)
                        vy = random.uniform(-150, -50)
                        life = random.uniform(0.6, 1.2)
                        color = random.choice(COLORS)
                        particles.append({"x":px, "y":py, "vx":vx, "vy":vy, "life":life, "t":0, "color":color})

score += cleared * 100
                piece=Piece()
                # spawn next piece
                piece = spawn_piece(next_piece.index)
                # immediately prepare subsequent next
                next_idx = random.randint(0, len(SHAPES)-1)
                next_piece = Piece(idx=next_idx)
                # if new piece invalid at spawn -> game over
                if not valid(piece, grid, 0, 0):
                    # simple game over screen
                    screen.fill((0,0,0))
                    screen.blit(big_font.render("GAME OVER", True, (255,50,50)), (SCREEN_WIDTH//2 - 120, SCREEN_HEIGHT//2 - 20))
                    screen.blit(font.render(f"Final Score: {score}", True, (255,255,255)), (SCREEN_WIDTH//2 - 80, SCREEN_HEIGHT//2 + 20))
                    pygame.display.flip()
                    pygame.time.wait(2000)
                    running = False
drop_timer=time.time()

        # update particles
        new_particles = []
        for p in particles:
            dt = 1.0 / FPS
            p["t"] += dt
            p["x"] += p["vx"] * dt
            p["y"] += p["vy"] * dt
            p["vy"] += 300 * dt  # gravity
            if p["t"] < p["life"]:
                alpha = int(255 * (1 - p["t"]/p["life"]))
                col = p["color"]
                # draw with fading
                surf = pygame.Surface((6,6), pygame.SRCALPHA)
                surf.fill((col[0], col[1], col[2], alpha))
                screen.blit(surf, (p["x"], p["y"]))
                new_particles.append(p)
        particles = new_particles

        # draw grid and ghost
for y in range(GRID_HEIGHT):
for x in range(GRID_WIDTH):
if grid[y][x]:
pygame.draw.rect(screen,grid[y][x],(x*BLOCK_SIZE,y*BLOCK_SIZE,BLOCK_SIZE,BLOCK_SIZE))
pygame.draw.rect(screen,(40,40,60),(x*BLOCK_SIZE,y*BLOCK_SIZE,BLOCK_SIZE,BLOCK_SIZE),1)

        # draw ghost piece (semi-transparent)
        ghost_color = (80,80,100)
        for y,row in enumerate(piece.shape):
            for x,cell in enumerate(row):
                if cell:
                    gx = (piece.x + x) * BLOCK_SIZE
                    gy = (ghost_y + y) * BLOCK_SIZE
                    ghost_surf = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
                    ghost_surf.fill((*ghost_color, 110))
                    screen.blit(ghost_surf, (gx, gy))

        # draw current piece
for y,row in enumerate(piece.shape):
for x,cell in enumerate(row):
if cell:
pygame.draw.rect(screen,piece.color,( (piece.x+x)*BLOCK_SIZE,(piece.y+y)*BLOCK_SIZE,BLOCK_SIZE,BLOCK_SIZE))

status = "Keyboard" if use_keyboard else ("Calibrating..." if not bci.calibrated else "EEG Active")
        draw_ui(score, status)
        draw_ui(score, status, next_piece)

pygame.display.flip()
