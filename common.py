from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math, random, time


win_w, win_h = 1200, 800
fovY = 100
cam_ang = 120.0
GRID_LEN = 1200
TILES    = 26
TILE_SIZE = (2 * GRID_LEN) / float(TILES)
HALF_TILE = TILE_SIZE * 0.5
cam_rad = 680.0 * (GRID_LEN / 600.)
cam_h   = 420.0 * (GRID_LEN / 600.)
follow  = 0


player_x = 0.0
player_y = 0.0
player_yaw = 0.0
MOVE_SPEED = 30.0
TURN_SPEED = 10.0
BASE_MOVE_SPEED = MOVE_SPEED  


# collision sizes 
PLAYER_RADIUS    = 14.0
TREE_TRUNK_R     = 8.0
TREE_COLLIDE_R   = TREE_TRUNK_R + 6.0
PLAYER_PLUS_TREE = (PLAYER_RADIUS + TREE_COLLIDE_R)


frames     = 0
fps_guess  = 60
sec_left   = 999
score      = 0
lives      = 100
level      = 1
MAX_LEVEL  = 2
hud_msg    = ""
GAME_OVER  = False
final_score = 0
LEVEL_CLEAR = False
NEXT_LEVEL_WIP = False
GATE_GRACE_SEC = 2.5
_last_all_plates_time = 0.0


PLATE_AWARDED = []
_gate_open_awarded = False
_level_gate_reach_awarded = False


WALLS = []   # (ax, ay, bx, by, r)
GATES = []   # (ax, ay, bx, by, r, open)
HOLES = []   # (cx, cy, r)


# level constants
WALL_X     = GRID_LEN * 0.70
WALL_HALF  = 240.0
WALL_THICK = 16.0
GATE_X     = GRID_LEN * 0.92
GATE_HALF  = 300.0
GATE_THICK = 18.0


# crates
CRATES = []
CRATE_HALF = HALF_TILE * 0.44
CRATE_ANCHOR   = []
CRATE_PROGRESS = []
CRATE_AXIS     = []


# plates
PLATES = []
PLATE_R = CRATE_HALF * 0.90
PLATE_H = 6.0


# gate link
WALL_ENABLED = True


# portal
PORTAL_R = 70.0


# sweepers & roamers
SWEEPERS = []
ROAMERS  = []


# fragile tiles 
FRAG_INTACT  = 0
FRAG_CRACKED = 1
FRAG_BROKEN  = 2
FRAG_PATCHES = []
FRAG_R = 70.0
STAND_BREAK_SEC   = 1.0
RESTEP_BREAK_SEC  = 3.0
AUTOHEAL_SEC      = 5.0


# helpers
def clamp(v, lo, hi): return max(lo, min(hi, v))
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


def _dist2(ax, ay, bx, by):
    return (ax - bx)*(ax - bx) + (ay - by)*(ay - by)


def _inside_ground(x, y, margin=80.0):
    return (-GRID_LEN + margin <= x <= GRID_LEN - margin) and (-GRID_LEN + margin <= y <= GRID_LEN - margin)


def draw_text(x, y, text, font=GLUT_BITMAP_HELVETICA_18, color=(1.0, 1.0, 1.0), center=False):
    avg_w = 10
    if center:
        x = x - (len(text) * avg_w) * 0.5
    glMatrixMode(GL_PROJECTION)
    glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, 1000, 0, 800)
    glMatrixMode(GL_MODELVIEW)
    glPushMatrix(); glLoadIdentity()
    glColor3f(*color); glRasterPos2f(x, y)
    for ch in text:
        glutBitmapCharacter(font, ord(ch))
    glPopMatrix()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


def draw_sky():
    glMatrixMode(GL_PROJECTION); glPushMatrix(); glLoadIdentity()
    gluOrtho2D(0, win_w, 0, win_h)
    glMatrixMode(GL_MODELVIEW); glPushMatrix(); glLoadIdentity()
    glBegin(GL_QUADS)
    glColor3f(0.30, 0.55, 0.90); glVertex2f(0, win_h); glVertex2f(win_w, win_h)
    glColor3f(0.72, 0.86, 0.98); glVertex2f(win_w, win_h * 0.52); glVertex2f(0, win_h * 0.52)
    glEnd()
    glBegin(GL_QUADS)
    glColor3f(0.72, 0.86, 0.98); glVertex2f(0, win_h*0.52); glVertex2f(win_w, win_h*0.52)
    glColor3f(0.64, 0.72, 0.64); glVertex2f(win_w, 0); glVertex2f(0, 0)
    glEnd()
    glPopMatrix()
    glMatrixMode(GL_PROJECTION); glPopMatrix()
    glMatrixMode(GL_MODELVIEW)


# ground 
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
    return (h1 & 0xffff) / 65535.0, (h2 & 0xffff) / 65535.0, (h3 & 0xffff) / 65535.0
def _terrain_color_infinite(x, y):
    ix = int(math.floor(x / CELL_SIZE)); iy = int(math.floor(y / CELL_SIZE))
    best_d2 = 1e30; best_kind = 0.0
    for dj in (-1,0,1):
        for di in (-1,0,1):
            cx, cy = ix+di, iy+dj
            r1, r2, r3 = _rand3_from_cell(cx, cy)
            fx = (cx + r1) * CELL_SIZE; fy = (cy + r2) * CELL_SIZE
            d2 = (x - fx)**2 + (y - fy)**2
            if d2 < best_d2: best_d2, best_kind = d2, r3
    dist = math.sqrt(best_d2)
    t = max(0.0, min(1.0, dist / (0.55 * CELL_SIZE)))
    band = 0.5 + 0.5 * math.sin(x*0.006 + y*0.004)
    tilt = 0.15 * (y / 2000.0)
    if best_kind < 0.6:
        center = (0.20, 0.50, 0.26); edge = (0.28+0.05*band, 0.60+0.06*band, 0.32+0.05*band)
    else:
        center = (0.42, 0.32, 0.20); edge = (0.36+0.04*band, 0.28+0.04*band, 0.18+0.04*band)
    r = center[0] + (edge[0]-center[0])*t
    g = center[1] + (edge[1]-center[1])*t
    b = center[2] + (edge[2]-center[2])*t
    if best_kind < 0.6: r *= (1.0 - 0.05*tilt); g *= (1.0 + 0.10*tilt)
    else:                r *= (1.0 + 0.10*tilt); g *= (1.0 - 0.05*tilt)
    return (r, g, b)
def draw_ground_infinite():
    span = GRID_LEN; step = TILE_SIZE
    x0 = -span; x1 = +span; y0 = -span; y1 = +span
    xi = x0
    while xi < x1:
        xj = y0; xip = min(xi + step, x1)
        while xj < y1:
            yjp = min(xj + step, y1); cx = (xi + xip) * 0.5; cy = (xj + yjp) * 0.5
            r, g, b = _terrain_color_infinite(cx, cy)
            glColor3f(r, g, b)
            glBegin(GL_QUADS)
            glVertex3f(xi, xj, 0.0); glVertex3f(xip, xj, 0.0); glVertex3f(xip, yjp, 0.0); glVertex3f(xi, yjp, 0.0)
            glEnd()
            xj = yjp
        xi = xip


# simple shapes 
def draw_disk(radius, segments=40):
    glBegin(GL_TRIANGLES)
    for i in range(segments):
        a0 = (2.0 * math.pi * i) / segments
        a1 = (2.0 * math.pi * (i+1)) / segments
        glVertex3f(0.0, 0.0, 0.0)
        glVertex3f(math.cos(a0)*radius, math.sin(a0)*radius, 0.0)
        glVertex3f(math.cos(a1)*radius, math.sin(a1)*radius, 0.0)
    glEnd()
def draw_circle_outline(radius, segments=40, z=0.0):
    glBegin(GL_LINES)
    for i in range(segments):
        a0 = 2.0 * math.pi *  i      / segments
        a1 = 2.0 * math.pi * (i + 1) / segments
        glVertex3f(math.cos(a0) * radius, math.sin(a0) * radius, z)
        glVertex3f(math.cos(a1) * radius, math.sin(a1) * radius, z)
    glEnd()


# trees 
trees = []
def init_trees(seed=999, count=12, min_dist=240.0, border_margin=None):
    global trees
    rng = random.Random(seed); trees = []
    if border_margin is None: border_margin = max(100.0, TREE_COLLIDE_R + 40.0)
    border = max(50.0, GRID_LEN - border_margin); keep_clear = 160.0; attempts = count * 300
    def _inside_board(x, y): return (-border <= x <= border) and (-border <= y <= border)
    while len(trees) < count and attempts > 0:
        attempts -= 1
        x = rng.uniform(-border, border); y = rng.uniform(-border, border)
        if not _inside_board(x, y): continue
        if math.hypot(x, y) < keep_clear: continue
        ok = True
        for (tx, ty, *_rest) in trees:
            if (x - tx) ** 2 + (y - ty) ** 2 < (min_dist ** 2): ok = False; break
        if not ok: continue
        h = rng.uniform(80.0, 150.0); r = h * rng.uniform(0.28, 0.40); hue = rng.uniform(-0.06, 0.08)
        trees.append((x, y, h, r, hue))


def draw_tree(x, y, trunk_h, crown_r, hue):
    q = gluNewQuadric()
    glColor3f(0.32, 0.22, 0.12)
    glPushMatrix(); glTranslatef(x, y, 0.0)
    gluCylinder(q, TREE_TRUNK_R, TREE_TRUNK_R * 0.85, trunk_h, 12, 1)
    glPopMatrix()
    g_base = (0.10, 0.45, 0.20); g_top  = (0.08, 0.60, 0.22)
    g0 = (g_base[0] + hue*0.4, g_base[1] + hue*0.2, g_base[2])
    g1 = (g_top [0] + hue*0.2, g_top [1] + hue*0.3, g_top [2])
    glPushMatrix(); glTranslatef(x, y, trunk_h)
    glColor3f(*g0); gluSphere(q, crown_r, 18, 18)
    glColor3f(*g1); glTranslatef(-crown_r*0.35, crown_r*0.2, crown_r*0.15); gluSphere(q, crown_r*0.75, 16, 16)
    glTranslatef(crown_r*0.7, -crown_r*0.05, -crown_r*0.10); gluSphere(q, crown_r*0.65, 16, 16)
    glPopMatrix()


def draw_jungle_props():
    for (x, y, h, r, hue) in trees:
        draw_tree(x, y, h, r, hue)


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
