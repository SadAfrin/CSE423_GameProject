# Shadman Section
from common import *
import random, math, time
import block2_core as core


#shared helpers
def _now(): return time.time()
def _point_in_disc(px, py, cx, cy, r): dx, dy = px - cx, py - cy; return (dx*dx + dy*dy) <= (r*r)


def _safe_point_for_player(x, y):
    if any([
        core._collides_walls(x, y),
        core._collides_gates(x, y),
        core._collides_holes(x, y)
    ]): return False
    thr2 = (PLAYER_PLUS_TREE) ** 2
    for (tx, ty, _h, _r, _hue) in trees:
        dx, dy = x - tx, y - ty
        if dx*dx + dy*dy < thr2: return False
    for (cx, cy) in CRATES:
        if core._circle_vs_aabb(x, y, PLAYER_RADIUS, cx, cy, CRATE_HALF): return False
    return True


def _snap_to_nearest_tile_center(x, y):
    i = int(round((x + GRID_LEN - HALF_TILE) / TILE_SIZE))
    j = int(round((y + GRID_LEN - HALF_TILE) / TILE_SIZE))
    i = max(0, min(TILES - 1, i)); j = max(0, min(TILES - 1, j))
    return tile_center(i, j)


def _hole_rim_point(hole, offset=64.0, angle_deg=0.0):
    hx, hy, hr = hole; a = math.radians(angle_deg)
    return (hx + math.cos(a) * (hr + offset), hy + math.sin(a) * (hr + offset))


#(10) Fragile ground
def init_fragile_patches(seed):
    global FRAG_PATCHES
    rng = random.Random(seed + 913)
    FRAG_PATCHES = []; want = 6; tries = 200; border = GRID_LEN * 0.9
    def _clear_enough(x, y):
        if math.hypot(x, y) < 140.0: return False
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
        x = rng.uniform(-border, border); y = rng.uniform(-border, border)
        if _clear_enough(x, y): FRAG_PATCHES.append([x, y, FRAG_R, FRAG_INTACT, None, None, None, False])
        tries -= 1


def fragile_update(now):
    px, py = player_x, player_y
    for p in FRAG_PATCHES:
        cx, cy, r, st, t_cracked, t_enter, t_last, was_in = p
        inside = _point_in_disc(px, py, cx, cy, r)
        if st == FRAG_INTACT:
            if inside:
                st = FRAG_CRACKED; t_cracked = now; t_enter = now; t_last = now
        elif st == FRAG_CRACKED:
            if inside:
                if t_enter is None: t_enter = now
                if (now - t_enter) >= STAND_BREAK_SEC: st = FRAG_BROKEN
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
        if st == FRAG_BROKEN and _point_in_disc(px, py, cx, cy, r - 2.0):
            lose_life_and_respawn(); return


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
            core._draw_hole(cx, cy, r); continue
        glColor3f(0.18, 0.45, 0.22) if st == FRAG_INTACT else glColor3f(0.85, 0.70, 0.10)
        glPushMatrix(); glTranslatef(cx, cy, 0.10); draw_disk(r, 36); glPopMatrix()
        if st == FRAG_CRACKED:
            glColor3f(0.15, 0.05, 0.02); _draw_cracks(cx, cy, r * 0.92)


#(11) Gems
GEMS = []; GEM_R = 13.0; GEMS_TARGET = 8; GEMS_COLLECTED = 0
def _spawn_gems(seed):
    global GEMS, GEMS_COLLECTED
    rng = random.Random(seed + 404); GEMS, GEMS_COLLECTED = [], 0
    tries = 400
    while len(GEMS) < GEMS_TARGET and tries > 0:
        tries -= 1
        x = rng.uniform(-GRID_LEN * 0.7, GATE_X - 5*TILE_SIZE)
        y = rng.uniform(-GRID_LEN * 0.8, GRID_LEN * 0.8)
        if math.hypot(x, y) < 120.0: continue
        if not _safe_point_for_player(x, y): continue
        GEMS.append([x, y, True])


def _draw_gems():
    t = _now()
    for (x, y, active) in GEMS:
        if not active: continue
        s = 1.0 + 0.12 * math.sin(t * 6.0 + (x + y) * 0.01)
        glPushMatrix(); glTranslatef(x, y, 2.0); glScalef(s, s, 1.0)
        glColor3f(1.0, 0.85, 0.15); draw_disk(GEM_R, 24)
        glColor3f(1.0, 1.0, 1.0); seg = 16; rr = GEM_R * 0.6; draw_circle_outline(rr, seg, 0.1)
        glPopMatrix()


def _gems_tick():
    global score, GEMS_COLLECTED, lives, hud_msg
    for g in GEMS:
        if not g[2]: continue
        if _point_in_disc(player_x, player_y, g[0], g[1], GEM_R + PLAYER_RADIUS):
            g[2] = False; score += 25; GEMS_COLLECTED += 1
            hud_msg = f"+25 Gem ({GEMS_COLLECTED}/{GEMS_TARGET})"
            if GEMS_COLLECTED == GEMS_TARGET:
                lives += 1; hud_msg = f"All gems! +1 life (Lives: {lives})"


#(12) Speed pads
SPEED_PADS = []; SPEED_PAD_R = 44.0
BOOST_MULT = 1.8; BOOST_SECS = 5.0
_boost_until = 0.0


def _spawn_speed_pads(seed):
    global SPEED_PADS
    rng = random.Random(seed + 717); SPEED_PADS = []
    GATE_CLEAR  = 4.8 * TILE_SIZE; WALL_CLEAR  = 3.8 * TILE_SIZE; MIN_SPREAD  = 4.5 * TILE_SIZE
    baseA = (-TILE_SIZE * 1.5, 0.0); baseB = (0.0, GRID_LEN * 0.55); baseC = (-GRID_LEN * 0.45, -GRID_LEN * 0.20)
    gate_x_max = GATE_X - GATE_CLEAR; wall_x_max = WALL_X - WALL_CLEAR; x_upper = min(gate_x_max, wall_x_max) - HALF_TILE
    candidates_offsets = [(0,0),(0,2*TILE_SIZE),(0,-2*TILE_SIZE),(2*TILE_SIZE,0),(-2*TILE_SIZE,0),(3*TILE_SIZE,0),(-3*TILE_SIZE,0),
                          (0,3*TILE_SIZE),(0,-3*TILE_SIZE),(2*TILE_SIZE,2*TILE_SIZE),(2,-2),( -2,2),( -2,-2),
                          (4*TILE_SIZE,0),(-4*TILE_SIZE,0),(0,4*TILE_SIZE),(0,-4*TILE_SIZE)]
    def _clear_of_plates(x,y):
        need2 = (SPEED_PAD_R + PLATE_R + 30.0)**2
        for (pxx, pyy) in PLATES:
            if _dist2(x, y, pxx, pyy) < need2: return False
        return True
    def _clear_of_holes_trees(x,y):
        for (hx, hy, hr) in HOLES:
            if _dist2(x, y, hx, hy) < (hr + SPEED_PAD_R + 24.0)**2: return False
        for (tx, ty, _h, _r, _hue) in trees:
            if _dist2(x, y, tx, ty) < (TREE_COLLIDE_R + SPEED_PAD_R + 24.0)**2: return False
        return True
    def _clear_of_gate_wall(x,y):
        for (ax, ay, bx, by, rad) in WALLS:
            if core._point_in_oriented_box(x, y, ax, ay, bx, by, half_thickness=rad, inflate=WALL_CLEAR): return False
        for (ax, ay, bx, by, rad, _open) in GATES:
            if core._point_in_oriented_box(x, y, ax, ay, bx, by, half_thickness=rad, inflate=GATE_CLEAR): return False
        if x > (GATE_X - GATE_CLEAR): return False
        return True
    def _far(x,y, chosen):
        for (ox, oy) in chosen:
            if _dist2(x, y, ox, oy) < (MIN_SPREAD * MIN_SPREAD): return False
        return True
    def _pick(base, chosen):
        bx, by = base; bx = min(bx, x_upper)
        for (ox, oy) in candidates_offsets:
            x, y = min(bx + ox, x_upper), by + oy
            sx, sy = _snap_to_nearest_tile_center(x, y)
            if not _inside_ground(sx, sy, margin=80.0): continue
            if not _clear_of_plates(sx, sy): continue
            if not _clear_of_holes_trees(sx, sy): continue
            if not _clear_of_gate_wall(sx, sy): continue
            if not _safe_point_for_player(sx, sy): continue
            if not _far(sx, sy, chosen): continue
            return (sx, sy)
        return _snap_to_nearest_tile_center(min(bx, x_upper), by)
    chosen = []
    for base in (baseA, baseB, baseC):
        chosen.append(_pick(base, chosen))
    SPEED_PADS = chosen


def _draw_speed_pads():
    for (x, y) in SPEED_PADS:
        glPushMatrix(); glTranslatef(x, y, 0.12)
        glColor3f(0.15, 0.85, 1.0); draw_disk(SPEED_PAD_R, 36)
        glColor3f(1, 1, 1); seg = 28; rr = SPEED_PAD_R * 0.6; draw_circle_outline(rr, seg, 0.1)
        glPopMatrix()


def _boost_tick(now):
    global MOVE_SPEED, _boost_until, hud_msg
    MOVE_SPEED = BASE_MOVE_SPEED if now >= _boost_until else BASE_MOVE_SPEED * BOOST_MULT
    for (x, y) in SPEED_PADS:
        if _point_in_disc(player_x, player_y, x, y, SPEED_PAD_R):
            _boost_until = now + BOOST_SECS
            MOVE_SPEED = BASE_MOVE_SPEED * BOOST_MULT
            hud_msg = "Speed boost!"


# (13) Checkpoint & life loss
_checkpoint_pos = (0.0, 0.0)
CHECKPAD_R = 48.0
_checkpoint_active = False


def _place_checkpoint_near_exit():
    global _checkpoint_pos
    base = (WALL_X - TILE_SIZE * 2.0, 0.0)
    candidates = [base, (base[0], base[1] + TILE_SIZE), (base[0], base[1] - TILE_SIZE),
                  (base[0] - TILE_SIZE, base[1]), (base[0] - TILE_SIZE, base[1] + TILE_SIZE), (base[0] - TILE_SIZE, base[1] - TILE_SIZE)]
    for (x, y) in candidates:
        sx, sy = _snap_to_nearest_tile_center(x, y)
        if _safe_point_for_player(sx, sy): _checkpoint_pos = (sx, sy); return
    _checkpoint_pos = base


def _draw_checkpoint():
    x, y = _checkpoint_pos
    glPushMatrix(); glTranslatef(x, y, 0.12)
    glColor3f(0.2, 1.0, 0.2) if _checkpoint_active else glColor3f(0.9, 0.75, 0.15)
    draw_disk(CHECKPAD_R, 40)
    glColor3f(1, 1, 1); seg = 36; rr = CHECKPAD_R * 0.58; draw_circle_outline(rr, seg, 0.02)
    glPopMatrix()


def _checkpoint_tick():
    global _checkpoint_active, hud_msg
    if not _checkpoint_active and _point_in_disc(player_x, player_y, _checkpoint_pos[0], _checkpoint_pos[1], CHECKPAD_R):
        _checkpoint_active = True; hud_msg = "Checkpoint reached!"


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
        player_x, player_y = _checkpoint_pos; player_yaw = 0.0; hud_msg = "Respawned at checkpoint"
    else:
        cx, cy = tile_center(TILES // 2, TILES // 2)
        player_x, player_y = cx, cy; player_yaw = 0.0; hud_msg = "Respawned at start"


#(14) Teleports
TELE_R = 56.0
TELE_LINKS = []
_tele_cd_until = 0.0
TELE_COOLDOWN_SECS = 0.75


def _telepad_spot_ok(x, y):
    if not _inside_ground(x, y, margin=80.0): return False
    if not _safe_point_for_player(x, y): return False
    need_plates2 = (TELE_R + PLATE_R + 26.0)**2
    for (px, py) in PLATES:
        if _dist2(x, y, px, py) < need_plates2: return False
    need_speed2 = (TELE_R + SPEED_PAD_R + 26.0)**2
    for (sx, sy) in SPEED_PADS:
        if _dist2(x, y, sx, sy) < need_speed2: return False
    for (fx, fy, fr, *_rest) in FRAG_PATCHES:
        if _dist2(x, y, fx, fy) < (fr + TELE_R + 20.0)**2: return False
    for (hx, hy, hr) in HOLES:
        if _dist2(x, y, hx, hy) < (hr + TELE_R + 20.0)**2: return False
    for (ax, ay, bx, by, rad) in WALLS:
        if core._point_in_oriented_box(x, y, ax, ay, bx, by, half_thickness=rad, inflate=TELE_R + 36.0): return False
    for (ax, ay, bx, by, rad, _open) in GATES:
        if core._point_in_oriented_box(x, y, ax, ay, bx, by, half_thickness=rad, inflate=TELE_R + 36.0): return False
    return True


def _build_teleports_from_holes():
    global TELE_LINKS
    TELE_LINKS = []
    n = len(HOLES); rim_pts = []
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
    candidates = [(ox, oy) for oy in offsets_y_pos for ox in (0, -TILE_SIZE, TILE_SIZE)]
    candidates += [(ox, oy) for oy in offsets_y_mix for ox in offsets_x]
    for (ox, oy) in candidates:
        x_try = base[0] + ox; y_try = base[1] + oy; x_try = min(x_try, x_upper)
        sx, sy = _snap_to_nearest_tile_center(x_try, y_try)
        if sx > x_upper: sx = x_upper - HALF_TILE
        if _telepad_spot_ok(sx, sy): gate_pad = (sx, sy); break
    if gate_pad and rim_pts:
        TELE_LINKS.append((gate_pad, rim_pts[0]))
        i = 1
        while i + 1 < len(rim_pts):
            TELE_LINKS.append((rim_pts[i], rim_pts[i+1])); i += 2
        if (len(rim_pts) - 1) % 2 == 1:
            TELE_LINKS.append((rim_pts[-1], rim_pts[1] if len(rim_pts) > 1 else rim_pts[0]))
    elif not gate_pad and len(rim_pts) > 0:
        i = 0
        while i + 1 < len(rim_pts):
            TELE_LINKS.append((rim_pts[i], rim_pts[i+1])); i += 2
        if len(rim_pts) % 2 == 1: TELE_LINKS.append((rim_pts[-1], rim_pts[0]))


def _draw_telepads():
    cols = [ (0.65,0.25,0.95), (0.25,0.95,0.65) ]
    for p_i, ((ax, ay), (bx, by)) in enumerate(TELE_LINKS):
        for j,(x,y) in enumerate(((ax,ay),(bx,by))):
            col = cols[j%2]
            glPushMatrix(); glTranslatef(x, y, 0.12)
            glColor3f(*col); draw_disk(TELE_R, 46)
            glColor3f(1, 1, 1); seg = 40; rr = TELE_R * 0.58; draw_circle_outline(rr, seg, 0.02)
            glPopMatrix()


def _teleport_tick(now):
    global player_x, player_y, _tele_cd_until, hud_msg
    if now < _tele_cd_until: return
    for ((ax, ay), (bx, by)) in TELE_LINKS:
        onA = _point_in_disc(player_x, player_y, ax, ay, TELE_R)
        onB = _point_in_disc(player_x, player_y, bx, by, TELE_R)
        if onA and _safe_point_for_player(bx, by):
            player_x, player_y = bx, by; _tele_cd_until = now + TELE_COOLDOWN_SECS; hud_msg = "Teleported!"; return
        if onB and _safe_point_for_player(ax, ay):
            player_x, player_y = ax, ay; _tele_cd_until = now + TELE_COOLDOWN_SECS; hud_msg = "Teleported!"; return


#(15) Dash
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
        core.try_move(fx * step, fy * step)
    _last_dash_time = now; hud_msg = "Dash!"


#(16) Level system
def _apply_level_lives():
    global lives
    if level == 1: lives = 7
    elif level == 2: lives = 5


def on_level_clear():
    global score, level, sec_left, hud_msg, player_x, player_y, player_yaw
    time_bonus = int(max(0, sec_left)); score += time_bonus; level += 1
    _apply_level_lives()
    hud_msg = f"Level cleared! +{time_bonus} → Level {level}"
    sec_left = 120
    player_x, player_y = tile_center(TILES//2, TILES//2); player_yaw = 0.0
    init_world(seed=1000 + level)
    core.update_gates_linked()


def reset_run():
    global frames, sec_left, score, lives, level, hud_msg, GAME_OVER
    global player_x, player_y, player_yaw
    global LEVEL_CLEAR, _last_all_plates_time
    global _checkpoint_active, _boost_until, _last_dash_time, MOVE_SPEED, BASE_MOVE_SPEED
    frames = 0; sec_left = 120; score = 0; level = 1
    _apply_level_lives()
    hud_msg = ""; GAME_OVER = False; LEVEL_CLEAR = False
    _last_all_plates_time = 0.0
    _checkpoint_active = False; _boost_until = 0.0; _last_dash_time = 0.0
    MOVE_SPEED = BASE_MOVE_SPEED
    cx, cy = tile_center(TILES // 2, TILES // 2)
    player_x, player_y = cx, cy; player_yaw = 0.0
    init_world(seed=1000 + level)


def _start_level(lvl):
    global level, LEVEL_CLEAR, GAME_OVER, frames, sec_left, hud_msg
    global player_x, player_y, player_yaw
    global _checkpoint_active, _boost_until, _last_dash_time, MOVE_SPEED
    level = lvl; LEVEL_CLEAR = False; GAME_OVER = False
    frames = 0; sec_left = 120; hud_msg = ""
    _checkpoint_active = False; _boost_until = 0.0; _last_dash_time = 0.0
    MOVE_SPEED = BASE_MOVE_SPEED
    _apply_level_lives()
    cx, cy = tile_center(TILES // 2, TILES // 2)
    player_x, player_y = cx, cy; player_yaw = 0.0
    init_world(seed=1000 + level); core.update_gates_linked()


#keypress
def keyboard_gameplay(k, x, y):
    if k == b' ':
        _try_dash(_now())
        return
    core.keyboard_core(k, x, y)


# level difficulty
def _apply_level_difficulty(lvl):
    global GATE_GRACE_SEC
    if lvl <= 1: GATE_GRACE_SEC = 2.5
    elif lvl == 2: GATE_GRACE_SEC = 1.4
    else: GATE_GRACE_SEC = max(0.9, 2.5 - 0.5 * (lvl - 1))
    speed_mult = 1.0 + 0.25 * max(0, lvl - 1)
    for s in SWEEPERS:
        s[5] = (abs(s[5]) * speed_mult) * (1 if s[5] >= 0 else -1)
    for r in ROAMERS:
        r[5] *= speed_mult; r[7] *= speed_mult
    if lvl >= 2:
        try:
            hx = -GRID_LEN * 0.45; hy = GRID_LEN * 0.10; hr = 60.0
            if _inside_ground(hx, hy, margin=80.0):
                HOLES.append((hx, hy, hr))
        except:
            pass
        SWEEPERS.append([-TILE_SIZE * 3.0, TILE_SIZE * 1.0, 30.0, 240.0, 0.0, 3.5 * speed_mult, 12.0])
        ROAMERS.append([-GRID_LEN*0.30, -GRID_LEN*0.25, 30.0, 220.0, 0.6, 6.0 * speed_mult, 45.0, 1.0 * speed_mult, 40, 40, 11.0])


# compose
def init_world(seed):
    core.init_world(seed)
    _apply_level_difficulty(level)
    core.resolve_sweepers_vs_crates()
    _place_checkpoint_near_exit()
    _build_teleports_from_holes()
    _spawn_speed_pads(seed)
    _spawn_gems(seed)
    init_fragile_patches(seed)
    global _gate_open_awarded, _level_gate_reach_awarded
    _gate_open_awarded = False; _level_gate_reach_awarded = False




