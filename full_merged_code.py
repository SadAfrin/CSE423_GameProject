# CSE423_Project
# IDs: 21301603-21301475-21301059
# Section - 01

from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, random
import time


# window/camera
win_w, win_h = 1200, 800
fovY = 100


# ground size (bigger board, same tile feel)
GRID_LEN = 1200
TILES    = 26
TILE_SIZE = (2 * GRID_LEN) / float(TILES)
HALF_TILE = TILE_SIZE * 0.5


# camera
cam_ang = 120.0
cam_rad = 680.0 * (GRID_LEN / 600.)
cam_h   = 420.0 * (GRID_LEN / 600.)
follow  = 0


# player state
player_x = 0.0
player_y = 0.0
player_yaw = 0.0


MOVE_SPEED = 30.0
TURN_SPEED = 10.0


# hit sizes
PLAYER_RADIUS    = 14.0
TREE_TRUNK_R     = 8.0
TREE_COLLIDE_R   = TREE_TRUNK_R + 6.0
PLAYER_PLUS_TREE = (PLAYER_RADIUS + TREE_COLLIDE_R)


# hud/timer
frames     = 0
fps_guess  = 60
sec_left   = 999
score      = 0
lives      = 100
level      = 1
MAX_LEVEL = 2
hud_msg    = ""


# game over
GAME_OVER = False
final_score = 0


PLATE_AWARDED = []
_gate_open_awarded = False
_level_gate_reach_awarded = False


# feature 1: obstacles
WALLS = []   
GATES = []   
HOLES = []   


# level constants
WALL_X     = GRID_LEN * 0.70
WALL_HALF  = 240.0
WALL_THICK = 16.0


GATE_X     = GRID_LEN * 0.92
GATE_HALF  = 300.0
GATE_THICK = 18.0


# feature 2: crates
CRATES = []
CRATE_HALF = HALF_TILE * 0.44
CRATE_ANCHOR   = []
CRATE_PROGRESS = []
CRATE_AXIS     = []


# feature 3: plates
PLATES = []
PLATE_R = CRATE_HALF * 0.90
PLATE_H = 6.0


# feature 4: linked gates
WALL_ENABLED = True


# feature 5: portal radius
PORTAL_R = 70.0


# feature 8: sweepers
SWEEPERS = []


# feature 9: roamers
ROAMERS = []


# feature 10: fragile ground
FRAG_INTACT  = 0
FRAG_CRACKED = 1
FRAG_BROKEN  = 2
FRAG_PATCHES = []
FRAG_R = 70.0
STAND_BREAK_SEC   = 1.0
RESTEP_BREAK_SEC  = 3.0
AUTOHEAL_SEC      = 5.0


# feature 16: level-clear flags
LEVEL_CLEAR = False
NEXT_LEVEL_WIP = False
GATE_GRACE_SEC = 2.5
_last_all_plates_time = 0.0


# utils-helper
def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def forward_vec(yaw_deg):
    r = math.radians(yaw_deg)
    return -math.sin(r), math.cos(r)


def clamp_player_within_bounds():
    global player_x, player_y
    m = GRID_LEN - max(PLAYER_RADIUS, 4.0)
    player_x = clamp(player_x, -m, m)
    player_y = clamp(player_y, -m, m)


def tile_center(i, j):
    x = -GRID_LEN + (i + 0.5) * TILE_SIZE
    y = -GRID_LEN + (j + 0.5) * TILE_SIZE
    return x, y


# input
def keyboard(k, _x, _y):
    global player_yaw, hud_msg, GAME_OVER, LEVEL_CLEAR, level

    if GAME_OVER:
        if k == b'r':
            LEVEL_CLEAR = False
            _start_level(level)
            return
        if b'1' <= k <= b'9':
            try:
                n = int(k.decode('ascii'))
                if 1 <= n <= MAX_LEVEL:
                    LEVEL_CLEAR = False
                    _start_level(n)
                    return
            except:
                pass
        return
   
    if k == b'a':
        player_yaw = (player_yaw + TURN_SPEED) % 360.0
    if k == b'd':
        player_yaw = (player_yaw - TURN_SPEED) % 360.0
    if k == b'w':
        fx, fy = forward_vec(player_yaw)
        try_move(fx * MOVE_SPEED, fy * MOVE_SPEED)
    if k == b's':
        fx, fy = forward_vec(player_yaw)
        try_move(-fx * MOVE_SPEED, -fy * MOVE_SPEED)


def special(key, _x, _y):
    global cam_ang, cam_h
    if follow: return
    if key == GLUT_KEY_LEFT:  cam_ang = (cam_ang + 2) % 360
    if key == GLUT_KEY_RIGHT: cam_ang = (cam_ang - 2) % 360
    if key == GLUT_KEY_UP:    cam_h += 10
    if key == GLUT_KEY_DOWN:  cam_h = max(60, cam_h - 10)


def mouse(btn, st, _x, _y):
    global follow
    if btn == GLUT_RIGHT_BUTTON and st == GLUT_DOWN:
        follow = 1 - follow


# camera
def setup_camera():
    glMatrixMode(GL_PROJECTION); glLoadIdentity()
    gluPerspective(fovY, max(1.0, win_w) / float(max(1.0, win_h)), 0.1, 4000.0)
    glMatrixMode(GL_MODELVIEW); glLoadIdentity()

    if follow:
        fx, fy = forward_vec(player_yaw)
        rx, ry =  fy, -fx
        back, up, right = 650.0, 500.0, 0.0
        ex = player_x - fx*back + rx*right
        ey = player_y - fy*back + ry*right
        ez = up
        look = 220.0
        pitd = 8.0
        dz = math.tan(math.radians(pitd)) * look
        cx = player_x + fx*look
        cy = player_y + fy*look
        cz = ez - dz
        gluLookAt(ex, ey, ez, cx, cy, cz, 0, 0, 1)
    else:
        ang = math.radians(cam_ang)
        ex = math.cos(ang) * cam_rad
        ey = math.sin(ang) * (cam_rad * 0.85)
        ez = cam_h
        gluLookAt(ex, ey, ez, 0, 0, 0, 0, 0, 1)


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18, color=(1.0, 1.0, 1.0), center=False):
    avg_w = 10
    if center:
        x = x - (len(text) * avg_w) * 0.5
    glMatrixMode(GL_PROJECTION)
    glPushMatrix()
    glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix()
    glLoadIdentity()
    glColor3f(*color)
    glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION)
    glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


# sky bg
def draw_sky():
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, win_w, 0, win_h)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glBegin(GL_QUADS)
    glColor3f(0.30, 0.55, 0.90)
    glVertex2f(0,       win_h)  
    glVertex2f(win_w,   win_h)
    glColor3f(0.72, 0.86, 0.98)
    glVertex2f(win_w,   win_h * 0.52)
    glVertex2f(0,       win_h * 0.52)
    glEnd()
    glBegin(GL_QUADS)
    glColor3f(0.72, 0.86, 0.98)
    glVertex2f(0,       win_h * 0.52)
    glVertex2f(win_w,   win_h * 0.52)
    glColor3f(0.64, 0.72, 0.64)
    glVertex2f(win_w,   0)
    glVertex2f(0,       0)
    glEnd()
    glPopMatrix()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


# ground (finite draw)
CELL_SIZE = 240.0


def _hash32(x):
    x = (x ^ (x >> 16)) & 0xffffffff
    x = (x * 0x7feb352d) & 0xffffffff
    x = (x ^ (x >> 15)) & 0xffffffff
    x = (x * 0x846ca68b) & 0xffffffff
    x = (x ^ (x >> 16)) & 0xffffffff
    return x


def _rand3_from_cell(ix, iy):
    h1 = _hash32(ix * 374761393 + iy * 668265263 + 0x9e3779b1)
    h2 = _hash32(ix * 1442695041 + iy * 116410423 + 0x85ebca6b)
    h3 = _hash32(ix * 196613 + iy * 2654435761 + 0xc2b2ae35)
    r1 = (h1 & 0xffff) / 65535.0
    r2 = (h2 & 0xffff) / 65535.0
    r3 = (h3 & 0xffff) / 65535.0
    return r1, r2, r3


def _terrain_color_infinite(x, y):
    ix = int(math.floor(x / CELL_SIZE))
    iy = int(math.floor(y / CELL_SIZE))
    best_d2 = 1e30
    best_kind = 0.0
    for dj in (-1, 0, 1):
        for di in (-1, 0, 1):
            cx = ix + di; cy = iy + dj
            r1, r2, r3 = _rand3_from_cell(cx, cy)
            fx = (cx + r1) * CELL_SIZE
            fy = (cy + r2) * CELL_SIZE
            dx = x - fx; dy = y - fy
            d2 = dx*dx + dy*dy
            if d2 < best_d2:
                best_d2 = d2
                best_kind = r3
    dist = math.sqrt(best_d2)
    t = max(0.0, min(1.0, dist / (0.55 * CELL_SIZE)))
    band = 0.5 + 0.5 * math.sin(x*0.006 + y*0.004)
    tilt = 0.15 * (y / 2000.0)
    if best_kind < 0.6:
        center = (0.20, 0.50, 0.26)
        edge   = (0.28+0.05*band, 0.60+0.06*band, 0.32+0.05*band)
    else:
        center = (0.42, 0.32, 0.20)
        edge   = (0.36+0.04*band, 0.28+0.04*band, 0.18+0.04*band)
    r = center[0] + (edge[0]-center[0])*t
    g = center[1] + (edge[1]-center[1])*t
    b = center[2] + (edge[2]-center[2])*t
    if best_kind < 0.6:
        r *= (1.0 - 0.05*tilt); g *= (1.0 + 0.10*tilt)
    else:
        r *= (1.0 + 0.10*tilt); g *= (1.0 - 0.05*tilt)
    return (r, g, b)


def draw_ground_infinite():
    span = GRID_LEN
    step = TILE_SIZE
    x0 = -span; x1 = +span
    y0 = -span; y1 = +span
    xi = x0
    while xi < x1:
        xj = y0
        xip = min(xi + step, x1)
        while xj < y1:
            yjp = min(xj + step, y1)
            cx = (xi + xip) * 0.5
            cy = (xj + yjp) * 0.5
            r, g, b = _terrain_color_infinite(cx, cy)
            glColor3f(r, g, b)
            glBegin(GL_QUADS)
            glVertex3f(xi,  xj,  0.0)
            glVertex3f(xip, xj,  0.0)
            glVertex3f(xip, yjp, 0.0)
            glVertex3f(xi,  yjp, 0.0)
            glEnd()
            xj = yjp
        xi = xip


# simple shapes
def draw_disk(radius, segments=40):
    glBegin(GL_TRIANGLES)
    for i in range(segments):
        a0 = (2.0 * math.pi * i) / segments
        a1 = (2.0 * math.pi * (i + 1)) / segments
        # center
        glVertex3f(0.0, 0.0, 0.0)
        # rim point i
        glVertex3f(math.cos(a0) * radius, math.sin(a0) * radius, 0.0)
        # rim point i+1
        glVertex3f(math.cos(a1) * radius, math.sin(a1) * radius, 0.0)
    glEnd()

def draw_circle_outline(radius, segments=40, z=0.0):
    glBegin(GL_LINES)
    for i in range(segments):
        a0 = 2.0 * math.pi *  i      / segments
        a1 = 2.0 * math.pi * (i + 1) / segments
        glVertex3f(math.cos(a0) * radius, math.sin(a0) * radius, z)
        glVertex3f(math.cos(a1) * radius, math.sin(a1) * radius, z)
    glEnd()


def _draw_hole(cx, cy, r):
    glPushMatrix()
    glTranslatef(cx, cy, 0.05)
    glColor3f(0.04, 0.04, 0.06)
    draw_disk(r, 40)
    glTranslatef(0, 0, 0.01)
    glColor3f(1.00, 0.85, 0.10)
    draw_circle_outline(r, 40, 0.0)
    glPopMatrix()


def _draw_gate_as_cave(ax, ay, bx, by, rad, is_open):
    cx, cy = (ax + bx) * 0.5, (ay + by) * 0.5
    ang = math.degrees(math.atan2(by - ay, bx - ax))
    q = gluNewQuadric()
    rim_col   = (0.10, 0.70, 0.10) if is_open else (0.70, 0.15, 0.10)
    mound_col = (0.30, 0.25, 0.18) if is_open else (0.40, 0.22, 0.20)
    glPushMatrix()
    glTranslatef(cx, cy, 35.0)
    glRotatef(ang, 0, 0, 1)
    glScalef(180.0, 160.0, 110.0)
    glColor3f(*mound_col)
    gluSphere(q, 1.0, 26, 26)
    glPopMatrix()
    mouth_r = max(50.0, rad * 3.2)
    glPushMatrix()
    glTranslatef(cx, cy, 50.0)
    glRotatef(ang, 0, 0, 1)
    glTranslatef(65.0, 0.0, 0.0)
    glRotatef(90.0, 0, 1, 0)
    glColor3f(0.02, 0.02, 0.03)
    draw_disk(mouth_r, 36)
    glTranslatef(0, 0, 2.0)
    glColor3f(*rim_col)
    beads   = 28
    bead_r  = max(4.0, min(8.0, rad * 0.9))
    for i in range(beads):
        a = (2.0 * math.pi * i) / beads
        x = math.cos(a) * mouth_r
        y = math.sin(a) * mouth_r
        glPushMatrix()
        glTranslatef(x, y, 0.0)
        gluSphere(q, bead_r, 12, 12)
        glPopMatrix()
    glPopMatrix()


def _clampf(v, lo, hi):
    return max(lo, min(hi, v))


def _circle_vs_aabb(px, py, r, bx, by, half):
    qx = _clampf(px, bx - half, bx + half)
    qy = _clampf(py, by - half, by + half)
    dx, dy = px - qx, py - qy
    return (dx*dx + dy*dy) <= (r*r)


def find_colliding_crate(px, py):
    for i, (cx, cy) in enumerate(CRATES):
        if _circle_vs_aabb(px, py, PLAYER_RADIUS, cx, cy, CRATE_HALF):
            return i
    return None


def _aabb_overlap(ax, ay, ahalf, bx, by, bhalf):
    return (abs(ax - bx) < (ahalf + bhalf)) and (abs(ay - by) < (ahalf + bhalf))


def _crate_blocked_at(cx, cy, half, ignore_index=None):
    thresh2 = (half + TREE_COLLIDE_R) ** 2
    for (tx, ty, _h, _r, _hue) in trees:
        dx, dy = (cx - tx), (cy - ty)
        if dx*dx + dy*dy < thresh2:
            return True
    for (ax, ay, bx, by, rad) in WALLS:
        if _point_in_oriented_box(cx, cy, ax, ay, bx, by, half_thickness=rad, inflate=half):
            return True
    for (ax, ay, bx, by, rad, is_open) in GATES:
        if not is_open and _point_in_oriented_box(cx, cy, ax, ay, bx, by, half_thickness=rad, inflate=half):
            return True
    for (hx, hy, hr) in HOLES:
        dx, dy = (cx - hx), (cy - hy)
        if (dx*dx + dy*dy) < (hr*hr):
            return True
    for j, (ox, oy) in enumerate(CRATES):
        if j == ignore_index:
            continue
        if _aabb_overlap(cx, cy, half, ox, oy, CRATE_HALF):
            return True
    return False


def _cardinal_from_vec(dx, dy):
    if abs(dx) >= abs(dy):
        return (1.0 if dx >= 0 else -1.0, 0.0)
    else:
        return (0.0, 1.0 if dy >= 0 else -1.0)


def push_crate_continuous(i, mov_dx, mov_dy):
    cx, cy = CRATES[i]
    dirx, diry = _cardinal_from_vec(mov_dx, mov_dy)
    vpx, vpy = (cx - player_x), (cy - player_y)
    if (vpx * dirx + vpy * diry) <= 0.0:
        return 0.0
    ax, ay = CRATE_AXIS[i]
    if (ax, ay) != (dirx, diry):
        CRATE_AXIS[i]   = (dirx, diry)
        CRATE_ANCHOR[i] = (cx, cy)
        CRATE_PROGRESS[i] = 0.0
    step_len = abs(mov_dx * dirx + mov_dy * diry)
    if step_len <= 0.0:
        return 0.0
    remaining = TILE_SIZE - CRATE_PROGRESS[i]
    delta = min(step_len, remaining)
    nx = CRATE_ANCHOR[i][0] + (CRATE_PROGRESS[i] + delta) * dirx
    ny = CRATE_ANCHOR[i][1] + (CRATE_PROGRESS[i] + delta) * diry
    if _crate_blocked_at(nx, ny, CRATE_HALF, ignore_index=i):
        return 0.0
    CRATES[i] = (nx, ny)
    CRATE_PROGRESS[i] += delta
    if CRATE_PROGRESS[i] >= TILE_SIZE - 1e-5:
        CRATE_ANCHOR[i]   = (nx, ny)
        CRATE_PROGRESS[i] = 0.0
    return delta


def init_crates():
    global CRATES, CRATE_ANCHOR, CRATE_PROGRESS, CRATE_AXIS
    CRATES = []
    x, y = 600.0, 0.0
    for _ in range(8):
        if not _crate_blocked_at(x, y, CRATE_HALF): break
        x -= TILE_SIZE
    CRATES.append((x, y))
    c_i, c_j = TILES // 2, TILES // 2
    candidates_ij = [(c_i - 2, c_j + 2), (c_i - 3, c_j - 1), (c_i - 1, c_j - 3), (c_i + 2, c_j - 2)]
    placed2 = None
    for (i, j) in candidates_ij:
        px, py = tile_center(i, j)
        if not _crate_blocked_at(px, py, CRATE_HALF):
            placed2 = (px, py); break
    if placed2 is None:
        px, py = -TILE_SIZE * 2, 0.0
        for _ in range(10):
            if not _crate_blocked_at(px, py, CRATE_HALF):
                placed2 = (px, py); break
            px -= TILE_SIZE
    CRATES.append(placed2)
    if level >= 2:
        placed3 = None
        base_i, base_j = TILES//2 + 3, TILES//2
        more_candidates = [
            (base_i, base_j),
            (base_i, base_j+2), (base_i, base_j-2),
            (base_i-2, base_j), (base_i+2, base_j),
            (base_i-3, base_j+1), (base_i-3, base_j-1),
        ]
        for (i, j) in more_candidates:
            px, py = tile_center(max(0,min(TILES-1,i)), max(0,min(TILES-1,j)))
            if not _crate_blocked_at(px, py, CRATE_HALF):
                placed3 = (px, py); break
        if placed3 is None:
            px, py = -TILE_SIZE * 4, TILE_SIZE * 2
            for _ in range(12):
                if not _crate_blocked_at(px, py, CRATE_HALF):
                    placed3 = (px, py); break
                px -= TILE_SIZE
        CRATES.append(placed3)
    CRATE_ANCHOR   = list(CRATES)
    CRATE_PROGRESS = [0.0 for _ in CRATES]
    CRATE_AXIS     = [(0.0, 0.0) for _ in CRATES]


def init_plates():
    global PLATES, PLATE_AWARDED
    off = TILE_SIZE * 1.6
    px1 = WALL_X - 1.5 * TILE_SIZE
    px2 = WALL_X - 3.0 * TILE_SIZE
    PLATES = [(px1, +off), (px2, -off)]
    if level >= 2:
        px3 = WALL_X - 2.2 * TILE_SIZE
        PLATES.append((px3, 0.0))
    PLATE_AWARDED = [False] * len(PLATES)


def init_sweepers():
    global SWEEPERS
    SWEEPERS = [
        [WALL_X - 2.5 * TILE_SIZE,    0.0,   30.0,  280.0,   0.0,   +3.0,  12.0],
        [WALL_X + 0.8 * TILE_SIZE,  220.0,   30.0,  240.0,  45.0,   -4.0,  12.0],
    ]


def init_roamers():
    global ROAMERS
    ROAMERS = [
        [-320.0, 180.0, 30.0, 240.0, 1.30,  5.0,   90.0,   -0.8,  45, 45, 12.0],
        [ 100.0,-260.0, 30.0, 200.0, 0.00,  6.0,    0.0,   +1.2,  30, 30, 10.0],
    ]


def init_trees(seed=999, count=12, min_dist=240.0, border_margin=None):
    global trees
    rng = random.Random(seed)
    trees = []
    if border_margin is None:
        border_margin = max(100.0, TREE_COLLIDE_R + 40.0)
    border = max(50.0, GRID_LEN - border_margin)
    keep_clear = 160.0
    attempts   = count * 300
    def _inside_board(x, y):
        return (-border <= x <= border) and (-border <= y <= border)
    while len(trees) < count and attempts > 0:
        attempts -= 1
        x = rng.uniform(-border, border)
        y = rng.uniform(-border, border)
        if not _inside_board(x, y): continue
        if math.hypot(x, y) < keep_clear: continue
        ok = True
        for (tx, ty, *_rest) in trees:
            if (x - tx) ** 2 + (y - ty) ** 2 < (min_dist ** 2):
                ok = False; break
        if not ok: continue
        h  = rng.uniform(80.0, 150.0)
        r  = h * rng.uniform(0.28, 0.40)
        hue = rng.uniform(-0.06, 0.08)
        trees.append((x, y, h, r, hue))


def draw_tree(x, y, trunk_h, crown_r, hue):
    q = gluNewQuadric()
    glColor3f(0.32, 0.22, 0.12)
    glPushMatrix()
    glTranslatef(x, y, 0.0)
    gluCylinder(q, TREE_TRUNK_R, TREE_TRUNK_R * 0.85, trunk_h, 12, 1)
    glPopMatrix()
    g_base = (0.10, 0.45, 0.20)
    g_top  = (0.08, 0.60, 0.22)
    g0 = (g_base[0] + hue*0.4, g_base[1] + hue*0.2, g_base[2])
    g1 = (g_top [0] + hue*0.2, g_top [1] + hue*0.3, g_top [2])
    glPushMatrix()
    glTranslatef(x, y, trunk_h)
    glColor3f(*g0); gluSphere(q, crown_r, 18, 18)
    glColor3f(*g1); glTranslatef(-crown_r*0.35, crown_r*0.2, crown_r*0.15); gluSphere(q, crown_r*0.75, 16, 16)
    glTranslatef(crown_r*0.7, -crown_r*0.05, -crown_r*0.10); gluSphere(q, crown_r*0.65, 16, 16)
    glPopMatrix()


def draw_jungle_props():
    for (x, y, h, r, hue) in trees:
        draw_tree(x, y, h, r, hue)


def collides_noncrate(nx, ny):
    thresh2 = (PLAYER_PLUS_TREE) ** 2
    for (tx, ty, _h, _r, _hue) in trees:
        dx, dy = nx - tx, ny - ty
        if dx*dx + dy*dy < thresh2:
            return True
    if _collides_walls(nx, ny):  return True
    if _collides_gates(nx, ny):  return True
    if _collides_holes(nx, ny):  return True
    return False


def try_move(dx, dy):
    global player_x, player_y, hud_msg
    nx = player_x + dx
    ny = player_y + dy
    if not collides_noncrate(nx, ny):
        hit = find_colliding_crate(nx, ny)
        if hit is None:
            player_x, player_y = nx, ny
            clamp_player_within_bounds()
            return
        else:
            moved = push_crate_continuous(hit, dx, dy)
            if moved > 0.0:
                dirx, diry = _cardinal_from_vec(dx, dy)
                cxx, cyy = CRATES[hit]
                gap = CRATE_HALF + PLAYER_RADIUS + 1.0
                player_x = cxx - dirx * gap
                player_y = cyy - diry * gap
                hud_msg = ""
                clamp_player_within_bounds()
                update_gates_linked()
                check_exit_portal()
                return
    nx_only = player_x + dx
    if not collides_noncrate(nx_only, player_y) and find_colliding_crate(nx_only, player_y) is None:
        player_x = nx_only
        clamp_player_within_bounds()
        return
    ny_only = player_y + dy
    if not collides_noncrate(player_x, ny_only) and find_colliding_crate(player_x, ny_only) is None:
        player_y = ny_only
        clamp_player_within_bounds()
        return
    update_gates_linked()


def set_level_geometry():
    global WALLS, GATES, HOLES
    WALLS = [(WALL_X, -WALL_HALF, WALL_X, WALL_HALF, WALL_THICK)]
    GATES = [(GATE_X, -GATE_HALF, GATE_X, GATE_HALF, GATE_THICK, False)]
    HOLES = [(-140, -200, 55), (210, -40, 70)]


# player draw + arrow
def draw_forward_arrow():
    glPushMatrix()
    glTranslatef(0.0, 22.0, 2.0)
    glColor3f(1.0, 0.9, 0.2)
    glBegin(GL_TRIANGLES) 
    glVertex3f(0.0, 28.0, 0.0)
    glVertex3f(-12.0, -10.0, 0.0)
    glVertex3f( 12.0, -10.0, 0.0)
    glEnd()
    glBegin(GL_QUADS)
    glVertex3f(-8.0, -10.0, 0.0)
    glVertex3f( 8.0, -10.0, 0.0)
    glVertex3f( 8.0, -18.0, 0.0)
    glVertex3f(-8.0, -18.0, 0.0)
    glEnd()
    glPopMatrix()


def draw_player():
    glPushMatrix()
    glTranslatef(player_x, player_y, 0)
    glRotatef(player_yaw, 0, 0, 1)
    draw_forward_arrow()
    glPushMatrix()
    s = 0.85
    glScalef(s, s, s)
    glColor3f(0.0, 0.0, 1.0)
    glPushMatrix()
    glTranslatef(0, 0, 50)
    glScalef(3, 2, 5)
    glutSolidCube(10)
    glPopMatrix()
    glColor3f(0.15, 0.15, 0.20)
    glPushMatrix(); glTranslatef( 15, 0, 0); gluCylinder(gluNewQuadric(), 5, 7.5, 35, 24, 1); glPopMatrix()
    glPushMatrix(); glTranslatef(-15, 0, 0); gluCylinder(gluNewQuadric(), 5, 7.5, 35, 24, 1); glPopMatrix()
    q = gluNewQuadric()
    glPushMatrix()
    glTranslatef(15, 0, 80); glRotatef(-90, 1, 0, 0)
    glColor3f(0.0, 0.95, 0.95); gluCylinder(q, 6, 6, 28, 24, 1)
    glTranslatef(0, 0, 28); glColor3f(1.0, 0.87, 0.74); gluSphere(q, 4.8, 18, 18)
    glPopMatrix()
    glPushMatrix()
    glTranslatef(-15, 0, 80); glRotatef(-90, 1, 0, 0)
    glColor3f(0.0, 0.95, 0.95); gluCylinder(q, 6, 6, 28, 24, 1)
    glTranslatef(0, 0, 28); glColor3f(1.0, 0.87, 0.74); gluSphere(q, 4.8, 18, 18)
    glPopMatrix()
    glColor3f(0.0, 0.0, 0.0)
    glPushMatrix(); glTranslatef(0, 0, 90); gluSphere(gluNewQuadric(), 13, 30, 30); glPopMatrix()
    glPopMatrix()
    glPopMatrix()


def draw_crates():
    glColor3f(0.80, 0.35, 0.10)
    for (cx, cy) in CRATES:
        glPushMatrix()
        glTranslatef(cx, cy, CRATE_HALF)
        glScalef(2*CRATE_HALF, 2*CRATE_HALF, 2*CRATE_HALF)
        glutSolidCube(1.0)
        glPopMatrix()


def _crate_on_plate(px, py):
    for (cx, cy) in CRATES:
        if _circle_vs_aabb(px, py, PLATE_R * 0.95, cx, cy, CRATE_HALF * 0.98):
            return True
    return False


def draw_pressure_plates():
    q = gluNewQuadric()
    for (px, py) in PLATES:
        active = _crate_on_plate(px, py)
        if active:
            glColor3f(0.2, 1.0, 0.2)
        else:
            glColor3f(0.7, 0.6, 0.1)
        glPushMatrix()
        glTranslatef(px, py, 1.0)
        gluCylinder(q, PLATE_R, PLATE_R, PLATE_H, 28, 1)
        glTranslatef(0, 0, PLATE_H)
        draw_disk(PLATE_R, 28)
        glPopMatrix()


def all_plates_active():
    return all(_crate_on_plate(px, py) for (px, py) in PLATES)


def update_gates_linked():
    global WALL_ENABLED, _last_all_plates_time
    global score, hud_msg, _gate_open_awarded, PLATE_AWARDED
    for i, (px, py) in enumerate(PLATES):
        if i < len(PLATE_AWARDED) and not PLATE_AWARDED[i] and _crate_on_plate(px, py):
            PLATE_AWARDED[i] = True
            score += 30
            hud_msg = "+30: Plate activated"
    now = time.time()
    all_now = all_plates_active()
    if all_now:
        _last_all_plates_time = now
    open_now = all_now or ((now - _last_all_plates_time) <= GATE_GRACE_SEC)
    if open_now and not _gate_open_awarded:
        _gate_open_awarded = True
        score += 100
        hud_msg = "+100: Gate opened"
    for i, (ax, ay, bx, by, rad, is_open) in enumerate(GATES):
        if is_open != open_now:
            GATES[i] = (ax, ay, bx, by, rad, open_now)
    WALL_ENABLED = (not open_now)


def plates_status():
    k = sum(1 for (px, py) in PLATES if _crate_on_plate(px, py))
    return k, len(PLATES)


def gates_status_text():
    if not GATES:
        return "-"
    return "OPEN" if all(g[5] for g in GATES) else "CLOSED"


# collision (boxes/discs)
def _point_in_oriented_box(px, py, ax, ay, bx, by, half_thickness, inflate=0.0):
    mx, my = (ax + bx) * 0.5, (ay + by) * 0.5
    vx, vy = (bx - ax), (by - ay)
    L = math.hypot(vx, vy)
    if L <= 1e-6:
        dx, dy = px - mx, py - my
        return (abs(dx) <= half_thickness + inflate) and (abs(dy) <= half_thickness + inflate)
    ux, uy = vx / L, vy / L
    vxp, vyp = -uy, ux
    dx, dy = px - mx, py - my
    local_x = dx * ux + dy * uy
    local_y = dx * vxp + dy * vyp
    half_len = L * 0.5
    return (abs(local_x) <= half_len + inflate) and (abs(local_y) <= half_thickness + inflate)


def _collides_walls(px, py):
    if not WALL_ENABLED:
        return False
    pr = PLAYER_RADIUS
    for (ax, ay, bx, by, rad) in WALLS:
        if _point_in_oriented_box(px, py, ax, ay, bx, by, half_thickness=rad, inflate=pr):
            return True
    return False


def _collides_gates(px, py):
    pr = PLAYER_RADIUS
    for (ax, ay, bx, by, rad, is_open) in GATES:
        if is_open:
            continue
        if _point_in_oriented_box(px, py, ax, ay, bx, by, half_thickness=rad, inflate=pr):
            return True
    return False


def _collides_holes(px, py):
    for (cx, cy, r) in HOLES:
        dx, dy = px - cx, py - cy
        if dx*dx + dy*dy < (r - 1.0)**2:
            return True
    return False


def _draw_wall_box(ax, ay, bx, by, half, z=0.10, height=40.0, rgb=(0.35,0.25,0.18)):
    vx, vy = (bx - ax), (by - ay)
    L = math.hypot(vx, vy)
    if L <= 1e-6:
        return
    ang = math.degrees(math.atan2(vy, vx))
    mx, my = (ax + bx) * 0.5, (ay + by) * 0.5
    glPushMatrix()
    glTranslatef(mx, my, z + height * 0.5)
    glRotatef(ang, 0, 0, 1)
    glScalef(L + 2*half, 2*half, height)
    glColor3f(*rgb)
    glutSolidCube(1.0)
    glPopMatrix()


def draw_level_geometry():
    for (ax, ay, bx, by, rad, is_open) in GATES:
        _draw_gate_as_cave(ax, ay, bx, by, rad, is_open)
    if WALL_ENABLED:
        for (ax, ay, bx, by, rad) in WALLS:
            _draw_wall_box(ax, ay, bx, by, rad, z=0.10, rgb=(0.18, 0.22, 0.80))
    for (cx, cy, r) in HOLES:
        _draw_hole(cx, cy, r)


def _gate_center(g):
    ax, ay, bx, by = g[0], g[1], g[2], g[3]
    return ((ax + bx) * 0.5, (ay + by) * 0.5)


def check_exit_portal():
    global hud_msg, LEVEL_CLEAR, score, _level_gate_reach_awarded
    if not GATES or LEVEL_CLEAR:
        return
    cx, cy = _gate_center(GATES[0])
    dx, dy = (player_x - cx), (player_y - cy)
    if dx*dx + dy*dy <= PORTAL_R * PORTAL_R:
        gate_is_open = all(g[5] for g in GATES)
        if gate_is_open:
            if not _level_gate_reach_awarded:
                score += 200
                _level_gate_reach_awarded = True
                hud_msg = "+200: Reached the gate"
            LEVEL_CLEAR = True
        else:
            hud_msg = "Teleport blocked"


def on_level_clear():
    global score, level, sec_left, hud_msg
    global player_x, player_y, player_yaw, lives
    time_bonus = int(max(0, sec_left))
    score += time_bonus
    level += 1
    _apply_level_lives()
    hud_msg = f"Level cleared! +{time_bonus} → Level {level}"
    sec_left = 120
    player_x, player_y = tile_center(TILES//2, TILES//2)
    player_yaw = 0.0
    init_world(seed=1000 + level)
    update_gates_linked()


def _sweeper_endpoints(s):
    cx, cy, _cz, length, ang_deg, _spd, _half = s
    a = math.radians(ang_deg)
    hx = math.cos(a) * (0.5 * length)
    hy = math.sin(a) * (0.5 * length)
    return (cx + hx, cy + hy), (cx - hx, cy - hy)


def _roamer_endpoints(r):
    cx, cy, _cz, length, _dir, _spd, spin_deg, _spin_speed, _je, _jl, half = r
    a = math.radians(spin_deg)
    hx = math.cos(a) * (0.5 * length)
    hy = math.sin(a) * (0.5 * length)
    return (cx + hx, cy + hy), (cx - hx, cy - hy)


def update_sweepers():
    for s in SWEEPERS:
        s[4] = (s[4] + s[5]) % 360.0


def update_roamers():
    border = GRID_LEN - 40.0
    for r in ROAMERS:
        cx, cy, cz, length, dir_rads, speed, spin_deg, spin_speed, jitter_every, jitter_left, half = r
        spin_deg = (spin_deg + spin_speed) % 360.0
        jitter_left -= 1
        if jitter_left <= 0:
            dir_rads += random.uniform(-0.30, +0.30)
            jitter_left = jitter_every
        nx = cx + speed * math.cos(dir_rads)
        ny = cy + speed * math.sin(dir_rads)
        if abs(nx) > border:
            dir_rads = math.pi - dir_rads
        else:
            cx = nx
        if abs(ny) > border:
            dir_rads = -dir_rads
        else:
            cy = ny
        dir_rads = (dir_rads + 2.0*math.pi) % (2.0*math.pi)
        r[0], r[1] = cx, cy
        r[4] = dir_rads
        r[6] = spin_deg
        r[9] = jitter_left


def draw_roamers():
    q = gluNewQuadric()
    for r in ROAMERS:
        cx, cy, cz, length, _dir, _spd, spin_deg, _spin_speed, _je, _jl, half = r
        glPushMatrix()
        glTranslatef(cx, cy, cz)
        glRotatef(spin_deg, 0, 0, 1)
        glColor3f(0.95, 0.35, 0.15)
        glPushMatrix()
        glScalef(length, 2.0 * half, 2.0 * half)
        glutSolidCube(1.0)
        glPopMatrix()
        glColor3f(0.18, 0.18, 0.20)
        gluSphere(q, half * 0.85, 16, 16)
        glPopMatrix()


def roamers_check_collision():
    pr = PLAYER_RADIUS
    px, py = player_x, player_y
    for r in ROAMERS:
        (ax, ay), (bx, by) = _roamer_endpoints(r)
        half = r[10]
        rad = pr + half
        if _dist2_point_to_segment(px, py, ax, ay, bx, by) <= (rad * rad):
            lose_life_and_respawn()
            return


def draw_sweepers():
    q = gluNewQuadric()
    for s in SWEEPERS:
        cx, cy, cz, length, ang_deg, _spd, half = s
        glPushMatrix()
        glTranslatef(cx, cy, cz)
        glRotatef(ang_deg, 0, 0, 1)
        glColor3f(0.85, 0.15, 0.15)
        glPushMatrix()
        glScalef(length, 2.0 * half, 2.0 * half)
        glutSolidCube(1.0)
        glPopMatrix()
        glColor3f(0.20, 0.20, 0.22)
        gluSphere(q, half * 0.95, 18, 18)
        glPopMatrix()


def _dist2_point_to_segment(px, py, ax, ay, bx, by):
    vx, vy = (bx - ax), (by - ay)
    wx, wy = (px - ax), (py - ay)
    c1 = vx * wx + vy * wy
    if c1 <= 0.0:
        dx, dy = px - ax, py - ay
        return dx*dx + dy*dy
    c2 = vx * vx + vy * vy
    if c2 <= 1e-12:
        dx, dy = px - ax, py - ay
        return dx*dx + dy*dy
    t = c1 / c2
    if t >= 1.0:
        dx, dy = px - bx, py - by
        return dx*dx + dy*dy
    qx = ax + t * vx
    qy = ay + t * vy
    dx, dy = px - qx, py - qy
    return dx*dx + dy*dy


def sweepers_check_collision():
    pr = PLAYER_RADIUS
    px, py = player_x, player_y
    for s in SWEEPERS:
        (ax, ay), (bx, by) = _sweeper_endpoints(s)
        half = s[6]
        rad = pr + half
        if _dist2_point_to_segment(px, py, ax, ay, bx, by) <= (rad * rad):
            lose_life_and_respawn()
            return


def _crate_within_sweep_disc(s, cx, cy):
    scx, scy, _cz, length, _ang, _spd, half = s
    need = 0.5 * length + half + CRATE_HALF + 6.0
    dx, dy = scx - cx, scy - cy
    return (dx*dx + dy*dy) <= (need * need)


def resolve_sweepers_vs_crates(max_outer=32):
    for s in SWEEPERS:
        for _ in range(max_outer):
            if all(not _crate_within_sweep_disc(s, cx, cy) for (cx, cy) in CRATES):
                break
            scx, scy, _cz, length, _ang, _spd, half = s
            if s[3] > 120.0:
                s[3] -= TILE_SIZE * 0.25
                continue
            worst = None; worst_pen = -1e9
            for (cx, cy) in CRATES:
                need = 0.5 * s[3] + half + CRATE_HALF + 6.0
                d = math.hypot(scx - cx, scy - cy)
                pen = need - d
                if pen > worst_pen:
                    worst_pen = pen; worst = (cx, cy, d)
            cx, cy, d = worst
            if d < 1e-6:
                s[0] += TILE_SIZE
            else:
                dx, dy = scx - cx, scy - cy
                step = max((0.5 * s[3] + half + CRATE_HALF + 8.0) - d, TILE_SIZE * 0.5)
                s[0] += (dx / d) * step
                s[1] += (dy / d) * step


def _inside_disc(px, py, cx, cy, r):
    dx, dy = px - cx, py - cy
    return (dx*dx + dy*dy) <= (r*r)


def init_fragile_patches(seed):
    global FRAG_PATCHES
    rng = random.Random(seed + 913)
    FRAG_PATCHES = []
    want = 6
    tries = 200
    border = GRID_LEN * 0.9
    def _clear_enough(x, y):
        if math.hypot(x - 0.0, y - 0.0) < 140.0:   return False
        for (tx, ty, *_r) in trees:
            if (x - tx)**2 + (y - ty)**2 < (FRAG_R + TREE_COLLIDE_R + 30.0)**2: return False
        for (hx, hy, hr) in HOLES:
            if (x - hx)**2 + (y - hy)**2 < (FRAG_R + hr + 30.0)**2: return False
        for (px, py) in PLATES:
            if (x - px)**2 + (y - py)**2 < (FRAG_R + PLATE_R + 60.0)**2: return False
        for (cx, cy) in CRATES:
            if (x - cx)**2 + (y - cy)**2 < (FRAG_R + CRATE_HALF + 40.0)**2: return False
        return True
    while len(FRAG_PATCHES) < want and tries > 0:
        x = rng.uniform(-border, border)
        y = rng.uniform(-border, border)
        if _clear_enough(x, y):
            FRAG_PATCHES.append([x, y, FRAG_R, FRAG_INTACT, None, None, None, False])
        tries -= 1


def fragile_update(now):
    px, py = player_x, player_y
    for p in FRAG_PATCHES:
        cx, cy, r, st, t_cracked, t_enter, t_last, was_in = p
        inside = _inside_disc(px, py, cx, cy, r)
        if st == FRAG_INTACT:
            if inside:
                st = FRAG_CRACKED
                t_cracked = now
                t_enter = now
                t_last = now
        elif st == FRAG_CRACKED:
            if inside:
                if t_enter is None: t_enter = now
                if (now - t_enter) >= STAND_BREAK_SEC:
                    st = FRAG_BROKEN
                t_last = now
            else:
                if t_last is not None and (now - t_last) >= AUTOHEAL_SEC:
                    st, t_cracked, t_enter, t_last = FRAG_INTACT, None, None, None
            if (not was_in) and inside and t_cracked is not None and (now - t_cracked) <= RESTEP_BREAK_SEC:
                st = FRAG_BROKEN
        p[3], p[4], p[5], p[6], p[7] = st, t_cracked, t_enter, t_last, inside


def fragile_check_player_fall():
    px, py = player_x, player_y
    for (cx, cy, r, st, *_rest) in FRAG_PATCHES:
        if st == FRAG_BROKEN and _inside_disc(px, py, cx, cy, r - 2.0):
            lose_life_and_respawn()
            return


def _draw_cracks(cx, cy, r):
    glBegin(GL_LINES) 
    spoke = 8
    for i in range(spoke):
        a = (2.0 * math.pi * i) / spoke
        rr = r * (0.45 + 0.35 * ((i * 37) % 10) / 10.0)
        glVertex3f(cx, cy, 0.12)
        glVertex3f(cx + math.cos(a) * rr, cy + math.sin(a) * rr, 0.12)
    glEnd()


def draw_fragile_patches():
    for (cx, cy, r, st, *_rest) in FRAG_PATCHES:
        if st == FRAG_BROKEN:
            _draw_hole(cx, cy, r)
            continue
        if st == FRAG_INTACT:
            glColor3f(0.18, 0.45, 0.22)
        else:
            glColor3f(0.85, 0.70, 0.10)
        glPushMatrix()
        glTranslatef(cx, cy, 0.10)
        draw_disk(r, 36)
        glPopMatrix()
        if st == FRAG_CRACKED:
            glColor3f(0.15, 0.05, 0.02)
            _draw_cracks(cx, cy, r * 0.92)



# world init
def init_world(seed):
    init_trees(seed=seed + 71, count=12, min_dist=240.0)
    set_level_geometry()
    init_crates()
    init_plates()
    init_sweepers()
    resolve_sweepers_vs_crates()
    init_roamers()
    init_fragile_patches(seed)


# reset/idle
def reset_run():
    global frames, sec_left, score, lives, level, hud_msg, GAME_OVER
    global player_x, player_y, player_yaw
    global LEVEL_CLEAR, _last_all_plates_time
    global _checkpoint_active, _boost_until, _last_dash_time, MOVE_SPEED
    frames = 0
    sec_left = 120
    score = 0
    level = 1
    _apply_level_lives()
    hud_msg = ""
    GAME_OVER = False
    LEVEL_CLEAR = False
    _last_all_plates_time = 0.0
    _checkpoint_active = False
    _boost_until = 0.0
    _last_dash_time = 0.0
    MOVE_SPEED = BASE_MOVE_SPEED
    cx, cy = tile_center(TILES // 2, TILES // 2)
    player_x, player_y = cx, cy
    player_yaw = 0.0
    init_world(seed=1000 + level)


def idle():
    global frames, sec_left, GAME_OVER, score, final_score
    if not GAME_OVER and not LEVEL_CLEAR:
        frames += 1
        if frames % fps_guess == 0 and sec_left > 0:
            sec_left -= 1
            if sec_left <= 0:
                GAME_OVER = True
                final_score = score
                score = 0
    glutPostRedisplay()


# shadman feature start

# shared helpers
def _now(): return time.time()


def _point_in_disc(px, py, cx, cy, r):
    dx, dy = px - cx, py - cy
    return (dx*dx + dy*dy) <= (r*r)


def _safe_point_for_player(x, y):
    if _collides_walls(x, y): return False
    if _collides_gates(x, y): return False
    if _collides_holes(x, y): return False
    thr2 = (PLAYER_PLUS_TREE) ** 2
    for (tx, ty, _h, _r, _hue) in trees:
        dx, dy = x - tx, y - ty
        if dx*dx + dy*dy < thr2: return False
    for (cx, cy) in CRATES:
        if _circle_vs_aabb(x, y, PLAYER_RADIUS, cx, cy, CRATE_HALF):
            return False
    return True


def _snap_to_nearest_tile_center(x, y):
    i = int(round((x + GRID_LEN - HALF_TILE) / TILE_SIZE))
    j = int(round((y + GRID_LEN - HALF_TILE) / TILE_SIZE))
    i = max(0, min(TILES - 1, i))
    j = max(0, min(TILES - 1, j))
    return tile_center(i, j)


def _hole_rim_point(hole, offset=64.0, angle_deg=0.0):
    hx, hy, hr = hole
    a = math.radians(angle_deg)
    return (hx + math.cos(a) * (hr + offset),
            hy + math.sin(a) * (hr + offset))


# feature 11: gems
GEMS = []
GEM_R = 13.0
GEMS_TARGET = 8
GEMS_COLLECTED = 0


def _spawn_gems(seed):
    global GEMS, GEMS_COLLECTED
    rng = random.Random(seed + 404)
    GEMS, GEMS_COLLECTED = [], 0
    tries = 400
    while len(GEMS) < GEMS_TARGET and tries > 0:
        tries -= 1
        x = rng.uniform(-GRID_LEN * 0.7, WALL_X - TILE_SIZE * 1.2)
        y = rng.uniform(-GRID_LEN * 0.8, GRID_LEN * 0.8)
        if math.hypot(x, y) < 120.0: continue
        if not _safe_point_for_player(x, y): continue
        GEMS.append([x, y, True])
    if SPEED_PADS:
        cx, cy = max(SPEED_PADS, key=lambda p: p[1])
        ring_r = SPEED_PAD_R + 70.0
        num = 5
        for i in range(num):
            a = 2.0 * math.pi * i / num + rng.uniform(-0.35, 0.35)
            r = ring_r + rng.uniform(-12.0, 18.0)
            gx = cx + math.cos(a) * r
            gy = cy + math.sin(a) * r
            if _inside_ground(gx, gy, margin=60.0) and _safe_point_for_player(gx, gy):
                GEMS.append([gx, gy, True])


def _draw_gems():
    t = _now()
    for (x, y, active) in GEMS:
        if not active: continue
        s = 1.0 + 0.12 * math.sin(t * 6.0 + (x + y) * 0.01)
        glPushMatrix()
        glTranslatef(x, y, 2.0)
        glScalef(s, s, 1.0)
        glColor3f(1.0, 0.85, 0.15)
        draw_disk(GEM_R, 24)
        glColor3f(1.0, 1.0, 1.0)
        seg = 16; rr = GEM_R * 0.6
        draw_circle_outline(rr, seg, 0.1)
        glPopMatrix()


def _gems_tick():
    global score, GEMS_COLLECTED, lives, hud_msg
    for g in GEMS:
        if not g[2]: continue
        if _point_in_disc(player_x, player_y, g[0], g[1], GEM_R + PLAYER_RADIUS):
            g[2] = False
            score += 25
            GEMS_COLLECTED += 1
            hud_msg = f"+25 Gem ({GEMS_COLLECTED}/{GEMS_TARGET})"
            if GEMS_COLLECTED == GEMS_TARGET:
                lives += 1
                hud_msg = f"All gems! +1 life (Lives: {lives})"


# feature 12: speed pads
SPEED_PADS = []
SPEED_PAD_R = 44.0
BOOST_MULT = 1.8
BOOST_SECS = 5.0
BASE_MOVE_SPEED = MOVE_SPEED
_boost_until = 0.0


def _spawn_speed_pads(seed):
    global SPEED_PADS
    rng = random.Random(seed + 717)
    SPEED_PADS = []
    GATE_CLEAR  = 4.8 * TILE_SIZE
    WALL_CLEAR  = 3.8 * TILE_SIZE
    MIN_SPREAD  = 4.5 * TILE_SIZE
    baseA = (-TILE_SIZE * 1.5, 0.0)
    baseB = (0.0, GRID_LEN * 0.55)
    baseC = (-GRID_LEN * 0.45, -GRID_LEN * 0.20)
    gate_x_max = GATE_X - GATE_CLEAR
    wall_x_max = WALL_X - WALL_CLEAR
    x_upper = min(gate_x_max, wall_x_max) - HALF_TILE
    candidates_offsets = [
        (0,0),
        (0,  2*TILE_SIZE), (0, -2*TILE_SIZE),
        (2*TILE_SIZE, 0),  (-2*TILE_SIZE, 0),
        (3*TILE_SIZE, 0),  (-3*TILE_SIZE, 0),
        (0,  3*TILE_SIZE), (0, -3*TILE_SIZE),
        (2*TILE_SIZE,  2*TILE_SIZE), (2*TILE_SIZE, -2*TILE_SIZE),
        (-2*TILE_SIZE, 2*TILE_SIZE), (-2*TILE_SIZE,-2*TILE_SIZE),
        (4*TILE_SIZE,  0), (-4*TILE_SIZE,  0),
        (0,  4*TILE_SIZE), (0, -4*TILE_SIZE),
    ]
    def _clear_of_plates(x, y):
        need2 = (SPEED_PAD_R + PLATE_R + 30.0)**2
        for (pxx, pyy) in PLATES:
            if _dist2(x, y, pxx, pyy) < need2:
                return False
        return True
    def _clear_of_holes_trees(x, y):
        for (hx, hy, hr) in HOLES:
            if _dist2(x, y, hx, hy) < (hr + SPEED_PAD_R + 24.0)**2:
                return False
        for (tx, ty, _h, _r, _hue) in trees:
            if _dist2(x, y, tx, ty) < (TREE_COLLIDE_R + SPEED_PAD_R + 24.0)**2:
                return False
        return True
    def _clear_of_gate_wall(x, y):
        for (ax, ay, bx, by, rad) in WALLS:
            if _point_in_oriented_box(x, y, ax, ay, bx, by, half_thickness=rad, inflate=WALL_CLEAR):
                return False
        for (ax, ay, bx, by, rad, _open) in GATES:
            if _point_in_oriented_box(x, y, ax, ay, bx, by, half_thickness=rad, inflate=GATE_CLEAR):
                return False
        if x > (GATE_X - GATE_CLEAR):
            return False
        return True
    def _far_enough_from_existing(x, y, chosen):
        for (ox, oy) in chosen:
            if _dist2(x, y, ox, oy) < (MIN_SPREAD * MIN_SPREAD):
                return False
        return True
    def _pick_near_spread(base, chosen):
        bx, by = base
        bx = min(bx, x_upper)
        for (ox, oy) in candidates_offsets:
            x, y = bx + ox, by + oy
            x = min(x, x_upper)
            sx, sy = _snap_to_nearest_tile_center(x, y)
            if not _inside_ground(sx, sy, margin=80.0):       continue
            if not _clear_of_plates(sx, sy):                  continue
            if not _clear_of_holes_trees(sx, sy):             continue
            if not _clear_of_gate_wall(sx, sy):               continue
            if not _safe_point_for_player(sx, sy):            continue
            if not _far_enough_from_existing(sx, sy, chosen): continue
            return (sx, sy)
        bx = min(bx, x_upper)
        return _snap_to_nearest_tile_center(bx, by)
    chosen = []
    for base in (baseA, baseB, baseC):
        chosen.append(_pick_near_spread(base, chosen))
    SPEED_PADS = chosen


def _draw_speed_pads():
    for (x, y) in SPEED_PADS:
        glPushMatrix()
        glTranslatef(x, y, 0.12)
        glColor3f(0.15, 0.85, 1.0)
        draw_disk(SPEED_PAD_R, 36)
        glColor3f(1, 1, 1)
        seg = 28; rr = SPEED_PAD_R * 0.6
        draw_circle_outline(rr, seg, 0.1)
        glPopMatrix()


def _boost_tick(now):
    global MOVE_SPEED, _boost_until, hud_msg
    MOVE_SPEED = BASE_MOVE_SPEED if now >= _boost_until else BASE_MOVE_SPEED * BOOST_MULT
    for (x, y) in SPEED_PADS:
        if _point_in_disc(player_x, player_y, x, y, SPEED_PAD_R):
            _boost_until = now + BOOST_SECS
            MOVE_SPEED = BASE_MOVE_SPEED * BOOST_MULT
            hud_msg = "Speed boost!"


# feature 13: checkpoint
_checkpoint_pos = (0.0, 0.0)
CHECKPAD_R = 48.0
_checkpoint_active = False


def _place_checkpoint_near_exit():
    global _checkpoint_pos
    base = (WALL_X - TILE_SIZE * 2.0, 0.0)
    candidates = [
        base,
        (base[0], base[1] + TILE_SIZE),
        (base[0], base[1] - TILE_SIZE),
        (base[0] - TILE_SIZE, base[1]),
        (base[0] - TILE_SIZE, base[1] + TILE_SIZE),
        (base[0] - TILE_SIZE, base[1] - TILE_SIZE),
    ]
    for (x, y) in candidates:
        sx, sy = _snap_to_nearest_tile_center(x, y)
        if _safe_point_for_player(sx, sy):
            _checkpoint_pos = (sx, sy)
            return
    _checkpoint_pos = base


def _draw_checkpoint():
    x, y = _checkpoint_pos
    glPushMatrix()
    glTranslatef(x, y, 0.12)
    glColor3f(0.2, 1.0, 0.2) if _checkpoint_active else glColor3f(0.9, 0.75, 0.15)
    draw_disk(CHECKPAD_R, 40)
    glColor3f(1, 1, 1)
    seg = 36; rr = CHECKPAD_R * 0.58
    draw_circle_outline(rr, seg, 0.02)
    glPopMatrix()


def _checkpoint_tick():
    global _checkpoint_active, hud_msg
    if not _checkpoint_active and _point_in_disc(player_x, player_y, _checkpoint_pos[0], _checkpoint_pos[1], CHECKPAD_R):
        _checkpoint_active = True
        hud_msg = "Checkpoint reached!"


def lose_life_and_respawn():
    global lives, player_x, player_y, player_yaw, hud_msg, GAME_OVER, score, final_score
    lives -= 1
    if lives <= 0:
        GAME_OVER = True
        final_score = score 
        score = 0
        hud_msg = ""
        return
    if _checkpoint_active:
        player_x, player_y = _checkpoint_pos
        player_yaw = 0.0
        hud_msg = "Respawned at checkpoint"
    else:
        cx, cy = tile_center(TILES // 2, TILES // 2)
        player_x, player_y = cx, cy
        player_yaw = 0.0
        hud_msg = "Respawned at start"


# feature 14: teleports
TELE_R = 56.0
TELE_LINKS = []
_tele_cd_until = 0.0
TELE_COOLDOWN_SECS = 0.75


def _build_teleports_from_holes():
    global TELE_LINKS
    TELE_LINKS = []
    n = len(HOLES)
    rim_pts = []
    if n > 0:
        for idx, h in enumerate(HOLES):
            ang = 0.0 if (idx % 2 == 0) else 180.0
            rim_pts.append(_hole_rim_point(h, offset=64.0, angle_deg=ang))
    gate_pad = None
    WALL_KEEPBACK = WALL_THICK + TELE_R + 36.0
    x_upper = WALL_X - WALL_KEEPBACK
    NORTH_BIAS_TILES = 2
    base = (x_upper - HALF_TILE, NORTH_BIAS_TILES * TILE_SIZE)
    offsets_y_pos = [k * TILE_SIZE for k in range(NORTH_BIAS_TILES, NORTH_BIAS_TILES + 7)]
    offsets_y_mix = [0, TILE_SIZE, -TILE_SIZE, 2*TILE_SIZE, -2*TILE_SIZE, 3*TILE_SIZE, -3*TILE_SIZE]
    offsets_x     = [0, -TILE_SIZE, TILE_SIZE, -2*TILE_SIZE, 2*TILE_SIZE]
    candidates = []
    for oy in offsets_y_pos:
        for ox in (0, -TILE_SIZE, TILE_SIZE):
            candidates.append((ox, oy))
    for oy in offsets_y_mix:
        for ox in offsets_x:
            candidates.append((ox, oy))
    for (ox, oy) in candidates:
        x_try = base[0] + ox
        y_try = base[1] + oy
        x_try = min(x_try, x_upper)
        sx, sy = _snap_to_nearest_tile_center(x_try, y_try)
        if sx > x_upper:
            sx = x_upper - HALF_TILE
        if _telepad_spot_ok(sx, sy):
            gate_pad = (sx, sy)
            break
    if gate_pad and rim_pts:
        TELE_LINKS.append((gate_pad, rim_pts[0]))
        i = 1
        while i + 1 < len(rim_pts):
            TELE_LINKS.append((rim_pts[i], rim_pts[i+1]))
            i += 2
        if (len(rim_pts) - 1) % 2 == 1:
            TELE_LINKS.append((rim_pts[-1], rim_pts[1] if len(rim_pts) > 1 else rim_pts[0]))
    elif not gate_pad and len(rim_pts) > 0:
        i = 0
        while i + 1 < len(rim_pts):
            TELE_LINKS.append((rim_pts[i], rim_pts[i+1]))
            i += 2
        if len(rim_pts) % 2 == 1:
            TELE_LINKS.append((rim_pts[-1], rim_pts[0]))


def _draw_telepads():
    cols = [ (0.65,0.25,0.95), (0.25,0.95,0.65) ]
    for p_i, ((ax, ay), (bx, by)) in enumerate(TELE_LINKS):
        for j,(x,y) in enumerate(((ax,ay),(bx,by))):
            col = cols[j%2]
            glPushMatrix()
            glTranslatef(x, y, 0.12)
            glColor3f(*col)
            draw_disk(TELE_R, 46)
            glColor3f(1, 1, 1)
            seg = 40; rr = TELE_R * 0.58
            draw_circle_outline(rr, seg, 0.02)
            glPopMatrix()


def _teleport_tick(now):
    global player_x, player_y, _tele_cd_until, hud_msg
    if now < _tele_cd_until: return
    for ((ax, ay), (bx, by)) in TELE_LINKS:
        onA = _point_in_disc(player_x, player_y, ax, ay, TELE_R)
        onB = _point_in_disc(player_x, player_y, bx, by, TELE_R)
        if onA and _safe_point_for_player(bx, by):
            player_x, player_y = bx, by
            _tele_cd_until = now + TELE_COOLDOWN_SECS
            hud_msg = "Teleported!"
            return
        if onB and _safe_point_for_player(ax, ay):
            player_x, player_y = ax, ay
            _tele_cd_until = now + TELE_COOLDOWN_SECS
            hud_msg = "Teleported!"
            return


# feature 15: dash
DASH_DIST = 180.0
DASH_STEPS = 6
DASH_COOLDOWN_SECS = 1.2
_last_dash_time = 0.0


def _try_dash(now):
    global _last_dash_time, hud_msg
    if (now - _last_dash_time) < DASH_COOLDOWN_SECS: return
    fx, fy = forward_vec(player_yaw)
    step = (DASH_DIST / float(DASH_STEPS))
    for _ in range(DASH_STEPS):
        try_move(fx * step, fy * step)
    _last_dash_time = now
    hud_msg = "Dash!"


# wrap callbacks
__orig_init_world = init_world
__orig_keyboard_lvl = keyboard
def keyboard(k, x, y):
    global LEVEL_CLEAR, NEXT_LEVEL_WIP, level

    if LEVEL_CLEAR:
        if level == 2:
            if NEXT_LEVEL_WIP:
                if k == b'r':
                    NEXT_LEVEL_WIP = False
                    LEVEL_CLEAR = False
                    _start_level(2)
                    return
                if k == b'1':
                    NEXT_LEVEL_WIP = False
                    LEVEL_CLEAR = False
                    _start_level(1)
                    return
                return
            else:
                if k == b'l':
                    NEXT_LEVEL_WIP = True
                    return
                if k == b'1':
                    LEVEL_CLEAR = False
                    _start_level(1)
                    return
                if k == b'r':
                    LEVEL_CLEAR = False
                    _start_level(2)
                    return
                return
        else:
            if k == b'l':
                LEVEL_CLEAR = False
                on_level_clear()
                return
            if k == b'r':
                LEVEL_CLEAR = False
                reset_run()
                return
            return


    if k == b' ':
        _try_dash(_now())  
        return


    __orig_keyboard_lvl(k, x, y)



# F16
def _apply_level_difficulty(lvl): 
    global GATE_GRACE_SEC
    if lvl <= 1:
        GATE_GRACE_SEC = 2.5
    elif lvl == 2:
        GATE_GRACE_SEC = 1.4
    else:
        GATE_GRACE_SEC = max(0.9, 2.5 - 0.5 * (lvl - 1))
    speed_mult = 1.0 + 0.25 * max(0, lvl - 1)
    for s in SWEEPERS:
        s[5] = (abs(s[5]) * speed_mult) * (1 if s[5] >= 0 else -1)
    for r in ROAMERS:
        r[5] *= speed_mult
        r[7] *= speed_mult
    if lvl >= 2:
        try:
            hx = -GRID_LEN * 0.45
            hy =  GRID_LEN * 0.10
            hr = 60.0
            if _inside_ground(hx, hy, margin=80.0):
                HOLES.append((hx, hy, hr))
        except:
            pass
        SWEEPERS.append([
            -TILE_SIZE * 3.0,
             TILE_SIZE * 1.0,
             30.0,
             240.0,
             0.0,
             3.5 * speed_mult,
             12.0
        ])
        ROAMERS.append([
            -GRID_LEN*0.30, -GRID_LEN*0.25, 30.0, 220.0,
            0.6, 6.0 * speed_mult, 45.0, 1.0 * speed_mult,
            40, 40, 11.0
        ])


# shadman feat (11–15): init & screen

def init_world(seed):
    __orig_init_world(seed)
    _apply_level_difficulty(level)   # 16
    resolve_sweepers_vs_crates()
    _place_checkpoint_near_exit()    # 13
    _build_teleports_from_holes()    # 14
    _spawn_speed_pads(seed)          # 12
    _spawn_gems(seed)                # 11
    
    global _gate_open_awarded, _level_gate_reach_awarded
    _gate_open_awarded = False
    _level_gate_reach_awarded = False



def showscreen():
    glClearColor(0.30, 0.55, 0.90, 1.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glViewport(0, 0, win_w, win_h)

    # game over
    if 'GAME_OVER' in globals() and GAME_OVER:
        draw_sky()
        cx = 500
        draw_text(cx, 420, "GAME OVER", color=(1,0,0), center=True)
        draw_text(cx, 380, f"Final Score: {final_score}   Level: {level}", color=(0,0,0), center=True)
        draw_text(cx, 340, f"Press R to restart Level-{level}", color=(0,0,0), center=True)
        y = 300
        for n in range(1, MAX_LEVEL + 1):
            draw_text(cx, y, f"Press '{n}' to go to Level-{n}", color=(0,0,0), center=True)
            y -= 30
        glutSwapBuffers()
        return


    # level clear
    if 'LEVEL_CLEAR' in globals() and LEVEL_CLEAR:
        draw_sky()
        cx = 500
        if level == 2:
            if NEXT_LEVEL_WIP:
                draw_text(cx, 420, "NEXT LEVEL UNDER IMPLEMENTATION", color=(0.7,0,0), center=True)
                draw_text(cx, 390, f"Score: {score}", color=(0,0,0), center=True)
                draw_text(cx, 360, "Press R to restart Level-2", color=(0,0,0), center=True)
                draw_text(cx, 330, "Press '1' to go to Level-1", color=(0,0,0), center=True)
            else:
                draw_text(cx, 420, "LEVEL-2 COMPLETED", color=(0,0.6,0), center=True)
                draw_text(cx, 390, f"Score: {score}", color=(0,0,0), center=True)
                draw_text(cx, 360, "Press 'L' for the Next Level", color=(0,0,0), center=True)
                draw_text(cx, 330, "Press '1' to go to Level-1", color=(0,0,0), center=True)
                draw_text(cx, 300, "Press R to restart Level-2", color=(0,0,0), center=True)
        else:
            draw_text(cx, 420, f"LEVEL-{level} COMPLETED", color=(0,0.6,0), center=True)
            draw_text(cx, 390, f"Score: {score}", color=(0,0,0), center=True)
            draw_text(cx, 360, "Press L for the Next Level", color=(0,0,0), center=True)
            draw_text(cx, 320, "Press R to restart", color=(0,0,0), center=True)
        glutSwapBuffers()
        return


    # runtime updates
    update_gates_linked()
    check_exit_portal()
    update_sweepers()
    update_roamers()


    t = _now()
    fragile_update(t)
    sweepers_check_collision()
    roamers_check_collision()
    fragile_check_player_fall()


    _checkpoint_tick()     # 13
    _teleport_tick(t)      # 14
    _boost_tick(t)         # 12
    _gems_tick()           # 11


    # draw
    draw_sky()
    setup_camera()
    draw_ground_infinite()
    draw_level_geometry()
    draw_jungle_props()
    draw_fragile_patches()
    draw_pressure_plates()
    draw_crates()
    draw_sweepers()
    draw_roamers()
    _draw_telepads()       # 14
    _draw_speed_pads()     # 12
    _draw_gems()           # 11
    _draw_checkpoint()     # 13
    draw_player()


    # hud
    k, n = plates_status()
    draw_text(10, 770, f"Lives: {lives}  Time: {sec_left}s  Score: {score}  Level: {level}")
    draw_text(10, 745, f"Plates: {k}/{n}   Gates: {gates_status_text()}")
    boost_left = max(0.0, _boost_until - t)
    dash_cd    = max(0.0, (_last_dash_time + DASH_COOLDOWN_SECS) - t)
    ck = "ACTIVE" if _checkpoint_active else "-"
    line3 = f"Gems: {GEMS_COLLECTED}/{GEMS_TARGET}   "
    line3 += ("Boost %.1fx (%.1fs)   " % (BOOST_MULT, boost_left)) if boost_left > 0.01 else "Boost ready   "
    line3 += f"Dash CD: {dash_cd:.1f}s   "
    line3 += f"Checkpoint: {ck}"
    draw_text(10, 720, line3)
    if hud_msg:
        draw_text(10, 695, hud_msg)
    glutSwapBuffers()

# shadman feature end-----------------------------

# Extra helpers after shadman

def _dist2(ax, ay, bx, by):
    return (ax - bx)*(ax - bx) + (ay - by)*(ay - by)


def _inside_ground(x, y, margin=80.0):
    return (-GRID_LEN + margin <= x <= GRID_LEN - margin) and (-GRID_LEN + margin <= y <= GRID_LEN - margin)


def _telepad_spot_ok(x, y):
    """Check if a telepad spot is valid and clear of conflicts."""
    if not _inside_ground(x, y, margin=80.0):
        return False
    if not _safe_point_for_player(x, y):
        return False


    # keep distance from plates
    need_plates2 = (TELE_R + PLATE_R + 26.0)**2
    for (px, py) in PLATES:
        if _dist2(x, y, px, py) < need_plates2:
            return False


    # keep distance from speed pads
    need_speed2 = (TELE_R + SPEED_PAD_R + 26.0)**2
    for (sx, sy) in SPEED_PADS:
        if _dist2(x, y, sx, sy) < need_speed2:
            return False


    # avoid fragile patches and holes
    for (fx, fy, fr, *_rest) in FRAG_PATCHES:
        if _dist2(x, y, fx, fy) < (fr + TELE_R + 20.0)**2:
            return False
    for (hx, hy, hr) in HOLES:
        if _dist2(x, y, hx, hy) < (hr + TELE_R + 20.0)**2:
            return False


    # avoid overlap with walls and gates
    for (ax, ay, bx, by, rad) in WALLS:
        if _point_in_oriented_box(x, y, ax, ay, bx, by, half_thickness=rad, inflate=TELE_R + 36.0):
            return False
    for (ax, ay, bx, by, rad, _open) in GATES:
        if _point_in_oriented_box(x, y, ax, ay, bx, by, half_thickness=rad, inflate=TELE_R + 36.0):
            return False

    return True


def _apply_level_lives():
    """Assign lives per level."""
    global lives
    if level == 1:
        lives = 7
    elif level == 2:
        lives = 5


def _start_level(lvl):
    """Start a level with default state and spawns."""
    global level, LEVEL_CLEAR, GAME_OVER, frames, sec_left, hud_msg
    global player_x, player_y, player_yaw
    global _checkpoint_active, _boost_until, _last_dash_time, MOVE_SPEED


    level = lvl
    LEVEL_CLEAR = False
    GAME_OVER = False
    frames = 0
    sec_left = 120
    hud_msg = ""


    # reset state
    _checkpoint_active = False
    _boost_until = 0.0
    _last_dash_time = 0.0
    MOVE_SPEED = BASE_MOVE_SPEED


    # per-level lives
    _apply_level_lives()


    # spawn player in center
    cx, cy = tile_center(TILES // 2, TILES // 2)
    player_x, player_y = cx, cy
    player_yaw = 0.0
    init_world(seed=1000 + level)
    update_gates_linked()



# ---- boot ----
def main():
    glutInit()
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowPosition(0, 0)
    glutInitWindowSize(win_w, win_h)
    wind = glutCreateWindow(b"Lab Final Project-Relic Rush 3D")


    glutDisplayFunc(showscreen)
    glutKeyboardFunc(keyboard)
    glutSpecialFunc(special)
    glutMouseFunc(mouse)
    glutIdleFunc(idle)


    reset_run()
    glutMainLoop()

if __name__ == "__main__":
    main()