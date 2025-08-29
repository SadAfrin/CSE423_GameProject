#oriented-box & collisions
def _clampf(v, lo, hi): return max(lo, min(hi, v))
def _circle_vs_aabb(px, py, r, bx, by, half):
    qx = _clampf(px, bx - half, bx + half)
    qy = _clampf(py, by - half, by + half)
    dx, dy = px - qx, py - qy
    return (dx*dx + dy*dy) <= (r*r)


def _aabb_overlap(ax, ay, ahalf, bx, by, bhalf):
    return (abs(ax - bx) < (ahalf + bhalf)) and (abs(ay - by) < (ahalf + bhalf))


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
    if not WALL_ENABLED: return False
    pr = PLAYER_RADIUS
    for (ax, ay, bx, by, rad) in WALLS:
        if _point_in_oriented_box(px, py, ax, ay, bx, by, half_thickness=rad, inflate=pr):
            return True
    return False


def _collides_gates(px, py):
    pr = PLAYER_RADIUS
    for (ax, ay, bx, by, rad, is_open) in GATES:
        if is_open: continue
        if _point_in_oriented_box(px, py, ax, ay, bx, by, half_thickness=rad, inflate=pr):
            return True
    return False


def _collides_holes(px, py):
    for (cx, cy, r) in HOLES:
        dx, dy = px - cx, py - cy
        if dx*dx + dy*dy < (r - 1.0)**2:
            return True
    return False


# level geometry
def set_level_geometry():
    global WALLS, GATES, HOLES
    WALLS = [(WALL_X, -WALL_HALF, WALL_X, WALL_HALF, WALL_THICK)]
    GATES = [(GATE_X, -GATE_HALF, GATE_X, GATE_HALF, GATE_THICK, False)]
    HOLES = [(-140, -200, 55), (210, -40, 70)]


def _draw_hole(cx, cy, r):
    glPushMatrix()
    glTranslatef(cx, cy, 0.05)
    glColor3f(0.04, 0.04, 0.06); draw_disk(r, 40)
    glTranslatef(0, 0, 0.01)
    glColor3f(1.00, 0.85, 0.10); draw_circle_outline(r, 40, 0.0)
    glPopMatrix()


def _draw_gate_as_cave(ax, ay, bx, by, rad, is_open):
    cx, cy = (ax + bx) * 0.5, (ay + by) * 0.5
    ang = math.degrees(math.atan2(by - ay, bx - ax))
    q = gluNewQuadric()
    rim_col   = (0.10, 0.70, 0.10) if is_open else (0.70, 0.15, 0.10)
    mound_col = (0.30, 0.25, 0.18) if is_open else (0.40, 0.22, 0.20)
    glPushMatrix(); glTranslatef(cx, cy, 35.0); glRotatef(ang, 0, 0, 1); glScalef(180.0, 160.0, 110.0)
    glColor3f(*mound_col); gluSphere(q, 1.0, 26, 26)
    glPopMatrix()
    mouth_r = max(50.0, rad * 3.2)
    glPushMatrix(); glTranslatef(cx, cy, 50.0); glRotatef(ang, 0, 0, 1); glTranslatef(65.0, 0.0, 0.0); glRotatef(90.0, 0, 1, 0)
    glColor3f(0.02, 0.02, 0.03); draw_disk(mouth_r, 36); glTranslatef(0, 0, 2.0); glColor3f(*rim_col)
    beads = 28; bead_r = max(4.0, min(8.0, rad * 0.9))
    for i in range(beads):
        a = (2.0 * math.pi * i) / beads; x = math.cos(a) * mouth_r; y = math.sin(a) * mouth_r
        glPushMatrix(); glTranslatef(x, y, 0.0); gluSphere(q, bead_r, 12, 12); glPopMatrix()
    glPopMatrix()


def _draw_wall_box(ax, ay, bx, by, half, z=0.10, height=40.0, rgb=(0.35,0.25,0.18)):
    vx, vy = (bx - ax), (by - ay)
    L = math.hypot(vx, vy)
    if L <= 1e-6: return
    ang = math.degrees(math.atan2(vy, vx)); mx, my = (ax + bx) * 0.5, (ay + by) * 0.5
    glPushMatrix()
    glTranslatef(mx, my, z + height * 0.5); glRotatef(ang, 0, 0, 1); glScalef(L + 2*half, 2*half, height)
    glColor3f(*rgb); glutSolidCube(1.0)
    glPopMatrix()


def draw_level_geometry():
    for (ax, ay, bx, by, rad, is_open) in GATES:
        _draw_gate_as_cave(ax, ay, bx, by, rad, is_open)
    if WALL_ENABLED:
        for (ax, ay, bx, by, rad) in WALLS:
            _draw_wall_box(ax, ay, bx, by, rad, z=0.10, rgb=(0.18, 0.22, 0.80))
    for (cx, cy, r) in HOLES:
        _draw_hole(cx, cy, r)


# crates & pushing 
def find_colliding_crate(px, py):
    for i, (cx, cy) in enumerate(CRATES):
        if _circle_vs_aabb(px, py, PLAYER_RADIUS, cx, cy, CRATE_HALF):
            return i
    return None


def _crate_blocked_at(cx, cy, half, ignore_index=None):
    thresh2 = (half + TREE_COLLIDE_R) ** 2
    for (tx, ty, _h, _r, _hue) in trees:
        dx, dy = (cx - tx), (cy - ty)
        if dx*dx + dy*dy < thresh2: return True
    for (ax, ay, bx, by, rad) in WALLS:
        if _point_in_oriented_box(cx, cy, ax, ay, bx, by, half_thickness=rad, inflate=half): return True
    for (ax, ay, bx, by, rad, is_open) in GATES:
        if not is_open and _point_in_oriented_box(cx, cy, ax, ay, bx, by, half_thickness=rad, inflate=half): return True
    for (hx, hy, hr) in HOLES:
        dx, dy = (cx - hx), (cy - hy)
        if (dx*dx + dy*dy) < (hr*hr): return True
    for j, (ox, oy) in enumerate(CRATES):
        if j == ignore_index: continue
        if _aabb_overlap(cx, cy, half, ox, oy, CRATE_HALF): return True
    return False


def _cardinal_from_vec(dx, dy):
    if abs(dx) >= abs(dy): return (1.0 if dx >= 0 else -1.0, 0.0)
    else:                  return (0.0, 1.0 if dy >= 0 else -1.0)


def push_crate_continuous(i, mov_dx, mov_dy):
    cx, cy = CRATES[i]
    dirx, diry = _cardinal_from_vec(mov_dx, mov_dy)
    vpx, vpy = (cx - player_x), (cy - player_y)
    if (vpx * dirx + vpy * diry) <= 0.0: return 0.0
    ax, ay = CRATE_AXIS[i]
    if (ax, ay) != (dirx, diry):
        CRATE_AXIS[i]   = (dirx, diry)
        CRATE_ANCHOR[i] = (cx, cy)
        CRATE_PROGRESS[i] = 0.0
    step_len = abs(mov_dx * dirx + mov_dy * diry)
    if step_len <= 0.0: return 0.0
    remaining = TILE_SIZE - CRATE_PROGRESS[i]
    delta = min(step_len, remaining)
    nx = CRATE_ANCHOR[i][0] + (CRATE_PROGRESS[i] + delta) * dirx
    ny = CRATE_ANCHOR[i][1] + (CRATE_PROGRESS[i] + delta) * diry
    if _crate_blocked_at(nx, ny, CRATE_HALF, ignore_index=i): return 0.0
    CRATES[i] = (nx, ny); CRATE_PROGRESS[i] += delta
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
        if not _crate_blocked_at(px, py, CRATE_HALF): placed2 = (px, py); break
    if placed2 is None:
        px, py = -TILE_SIZE * 2, 0.0
        for _ in range(10):
            if not _crate_blocked_at(px, py, CRATE_HALF): placed2 = (px, py); break
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
            if not _crate_blocked_at(px, py, CRATE_HALF): placed3 = (px, py); break
        if placed3 is None:
            px, py = -TILE_SIZE * 4, TILE_SIZE * 2
            for _ in range(12):
                if not _crate_blocked_at(px, py, CRATE_HALF): placed3 = (px, py); break
                px -= TILE_SIZE
        CRATES.append(placed3)
    CRATE_ANCHOR   = list(CRATES)
    CRATE_PROGRESS = [0.0 for _ in CRATES]
    CRATE_AXIS     = [(0.0, 0.0) for _ in CRATES]


def draw_crates():
    glColor3f(0.80, 0.35, 0.10)
    for (cx, cy) in CRATES:
        glPushMatrix(); glTranslatef(cx, cy, CRATE_HALF)
        glScalef(2*CRATE_HALF, 2*CRATE_HALF, 2*CRATE_HALF)
        glutSolidCube(1.0)
        glPopMatrix()


# plates & linked gates
def _crate_on_plate(px, py):
    for (cx, cy) in CRATES:
        if _circle_vs_aabb(px, py, PLATE_R * 0.95, cx, cy, CRATE_HALF * 0.98):
            return True
    return False


def draw_pressure_plates():
    q = gluNewQuadric()
    for (px, py) in PLATES:
        active = _crate_on_plate(px, py)
        glColor3f(0.2, 1.0, 0.2) if active else glColor3f(0.7, 0.6, 0.1)
        glPushMatrix(); glTranslatef(px, py, 1.0)
        gluCylinder(q, PLATE_R, PLATE_R, PLATE_H, 28, 1)
        glTranslatef(0, 0, PLATE_H); draw_disk(PLATE_R, 28)
        glPopMatrix()


def all_plates_active():
    return all(_crate_on_plate(px, py) for (px, py) in PLATES)


def update_gates_linked():
    global WALL_ENABLED, _last_all_plates_time
    global score, hud_msg, _gate_open_awarded, PLATE_AWARDED
    for i, (px, py) in enumerate(PLATES):
        if i < len(PLATE_AWARDED) and not PLATE_AWARDED[i] and _crate_on_plate(px, py):
            PLATE_AWARDED[i] = True
            score += 30; hud_msg = "+30: Plate activated"
    now = time.time()
    all_now = all_plates_active()
    if all_now: _last_all_plates_time = now
    open_now = all_now or ((now - _last_all_plates_time) <= GATE_GRACE_SEC)
    if open_now and not _gate_open_awarded:
        _gate_open_awarded = True
        score += 100; hud_msg = "+100: Gate opened"
    for i, (ax, ay, bx, by, rad, is_open) in enumerate(GATES):
        if is_open != open_now:
            GATES[i] = (ax, ay, bx, by, rad, open_now)
    WALL_ENABLED = (not open_now)


def plates_status():
    k = sum(1 for (px, py) in PLATES if _crate_on_plate(px, py))
    return k, len(PLATES)


def gates_status_text():
    if not GATES: return "-"
    return "OPEN" if all(g[5] for g in GATES) else "CLOSED"


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


# movement & player 
def collides_noncrate(nx, ny):
    thresh2 = (PLAYER_PLUS_TREE) ** 2
    for (tx, ty, _h, _r, _hue) in trees:
        dx, dy = nx - tx, ny - ty
        if dx*dx + dy*dy < thresh2: return True
    if _collides_walls(nx, ny):  return True
    if _collides_gates(nx, ny):  return True
    if _collides_holes(nx, ny):  return True
    return False


def try_move(dx, dy):
    global player_x, player_y, hud_msg
    nx = player_x + dx; ny = player_y + dy
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
        player_x = nx_only; clamp_player_within_bounds(); return
    ny_only = player_y + dy
    if not collides_noncrate(player_x, ny_only) and find_colliding_crate(player_x, ny_only) is None:
        player_y = ny_only; clamp_player_within_bounds(); return
    update_gates_linked()


def draw_forward_arrow():
    glPushMatrix()
    glTranslatef(0.0, 22.0, 2.0); glColor3f(1.0, 0.9, 0.2)
    glBegin(GL_TRIANGLES)
    glVertex3f(0.0, 28.0, 0.0); glVertex3f(-12.0, -10.0, 0.0); glVertex3f(12.0, -10.0, 0.0)
    glEnd()
    glBegin(GL_QUADS)
    glVertex3f(-8.0, -10.0, 0.0); glVertex3f(8.0, -10.0, 0.0); glVertex3f(8.0, -18.0, 0.0); glVertex3f(-8.0, -18.0, 0.0)
    glEnd()
    glPopMatrix()


def draw_player():
    glPushMatrix()
    glTranslatef(player_x, player_y, 0); glRotatef(player_yaw, 0, 0, 1)
    draw_forward_arrow()
    glPushMatrix(); s = 0.85; glScalef(s, s, s); glColor3f(0.0, 0.0, 1.0)
    glPushMatrix(); glTranslatef(0, 0, 50); glScalef(3, 2, 5); glutSolidCube(10); glPopMatrix()
    glColor3f(0.15, 0.15, 0.20)
    glPushMatrix(); glTranslatef( 15, 0, 0); gluCylinder(gluNewQuadric(), 5, 7.5, 35, 24, 1); glPopMatrix()
    glPushMatrix(); glTranslatef(-15, 0, 0); gluCylinder(gluNewQuadric(), 5, 7.5, 35, 24, 1); glPopMatrix()
    q = gluNewQuadric()
    glPushMatrix(); glTranslatef(15, 0, 80); glRotatef(-90, 1, 0, 0)
    glColor3f(0.0, 0.95, 0.95); gluCylinder(q, 6, 6, 28, 24, 1)
    glTranslatef(0, 0, 28); glColor3f(1.0, 0.87, 0.74); gluSphere(q, 4.8, 18, 18); glPopMatrix()
    glPushMatrix(); glTranslatef(-15, 0, 80); glRotatef(-90, 1, 0, 0)
    glColor3f(0.0, 0.95, 0.95); gluCylinder(q, 6, 6, 28, 24, 1)
    glTranslatef(0, 0, 28); glColor3f(1.0, 0.87, 0.74); gluSphere(q, 4.8, 18, 18); glPopMatrix()
    glColor3f(0.0, 0.0, 0.0)
    glPushMatrix(); glTranslatef(0, 0, 90); gluSphere(gluNewQuadric(), 13, 30, 30); glPopMatrix()
    glPopMatrix(); glPopMatrix()


# gate portal f5
def _gate_center(g):
    ax, ay, bx, by = g[0], g[1], g[2], g[3]
    return ((ax + bx) * 0.5, (ay + by) * 0.5)


def check_exit_portal():
    global hud_msg, LEVEL_CLEAR, score, _level_gate_reach_awarded
    if not GATES or LEVEL_CLEAR: return
    cx, cy = _gate_center(GATES[0])
    dx, dy = (player_x - cx), (player_y - cy)
    if dx*dx + dy*dy <= PORTAL_R * PORTAL_R:
        gate_is_open = all(g[5] for g in GATES)
        if gate_is_open:
            if not _level_gate_reach_awarded:
                score += 200; _level_gate_reach_awarded = True; hud_msg = "+200: Reached the gate"
            LEVEL_CLEAR = True
        else:
            hud_msg = "Teleport blocked"


# sweepers & roamers 
def _sweeper_endpoints(s):
    cx, cy, _cz, length, ang_deg, _spd, _half = s
    a = math.radians(ang_deg)
    hx = math.cos(a) * (0.5 * length); hy = math.sin(a) * (0.5 * length)
    return (cx + hx, cy + hy), (cx - hx, cy - hy)


def _roamer_endpoints(r):
    cx, cy, _cz, length, _dir, _spd, spin_deg, _spin_speed, _je, _jl, half = r
    a = math.radians(spin_deg)
    hx = math.cos(a) * (0.5 * length); hy = math.sin(a) * (0.5 * length)
    return (cx + hx, cy + hy), (cx - hx, cy - hy)


def init_sweepers():
    global SWEEPERS
    SWEEPERS = [
        [WALL_X - 2.5 * TILE_SIZE,    0.0,   30.0,  280.0,   0.0,   +3.0,  12.0],
        [WALL_X + 0.8 * TILE_SIZE,  220.0,   30.0,  240.0,  45.0,   -4.0,  12.0],
    ]


def update_sweepers():
    for s in SWEEPERS:
        s[4] = (s[4] + s[5]) % 360.0


def draw_sweepers():
    q = gluNewQuadric()
    for s in SWEEPERS:
        cx, cy, cz, length, ang_deg, _spd, half = s
        glPushMatrix(); glTranslatef(cx, cy, cz); glRotatef(ang_deg, 0, 0, 1)
        glColor3f(0.85, 0.15, 0.15)
        glPushMatrix(); glScalef(length, 2.0 * half, 2.0 * half); glutSolidCube(1.0); glPopMatrix()
        glColor3f(0.20, 0.20, 0.22); gluSphere(q, half * 0.95, 18, 18)
        glPopMatrix()


def _dist2_point_to_segment(px, py, ax, ay, bx, by):
    vx, vy = (bx - ax), (by - ay); wx, wy = (px - ax), (py - ay)
    c1 = vx * wx + vy * wy
    if c1 <= 0.0: dx, dy = px - ax, py - ay; return dx*dx + dy*dy
    c2 = vx * vx + vy * vy
    if c2 <= 1e-12: dx, dy = px - ax, py - ay; return dx*dx + dy*dy
    t = c1 / c2
    if t >= 1.0: dx, dy = px - bx, py - by; return dx*dx + dy*dy
    qx = ax + t * vx; qy = ay + t * vy; dx, dy = px - qx, py - qy; return dx*dx + dy*dy


def sweepers_check_collision():
    pr = PLAYER_RADIUS; px, py = player_x, player_y
    for s in SWEEPERS:
        (ax, ay), (bx, by) = _sweeper_endpoints(s)
        half = s[6]; rad = pr + half
        if _dist2_point_to_segment(px, py, ax, ay, bx, by) <= (rad * rad):
            # lose life implemented from shadman
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
                s[3] -= TILE_SIZE * 0.25; continue
            worst = None; worst_pen = -1e9
            for (cx, cy) in CRATES:
                need = 0.5 * s[3] + half + CRATE_HALF + 6.0
                d = math.hypot(scx - cx, scy - cy); pen = need - d
                if pen > worst_pen: worst_pen = pen; worst = (cx, cy, d)
            cx, cy, d = worst
            if d < 1e-6:
                s[0] += TILE_SIZE
            else:
                dx, dy = scx - cx, scy - cy
                step = max((0.5 * s[3] + half + CRATE_HALF + 8.0) - d, TILE_SIZE * 0.5)
                s[0] += (dx / d) * step; s[1] += (dy / d) * step


# roamers 
def init_roamers():
    global ROAMERS
    ROAMERS = [
        [-320.0, 180.0, 30.0, 240.0, 1.30,  5.0,   90.0,   -0.8,  45, 45, 12.0],
        [ 100.0,-260.0, 30.0, 200.0, 0.00,  6.0,    0.0,   +1.2,  30, 30, 10.0],
    ]


def update_roamers():
    border = GRID_LEN - 40.0
    for r in ROAMERS:
        cx, cy, cz, length, dir_rads, speed, spin_deg, spin_speed, jitter_every, jitter_left, half = r
        spin_deg = (spin_deg + spin_speed) % 360.0
        jitter_left -= 1
        if jitter_left <= 0:
            dir_rads += random.uniform(-0.30, +0.30); jitter_left = jitter_every
        nx = cx + speed * math.cos(dir_rads); ny = cy + speed * math.sin(dir_rads)
        if abs(nx) > border: dir_rads = math.pi - dir_rads
        else:                cx = nx
        if abs(ny) > border: dir_rads = -dir_rads
        else:                cy = ny
        dir_rads = (dir_rads + 2.0*math.pi) % (2.0*math.pi)
        r[0], r[1] = cx, cy; r[4] = dir_rads; r[6] = spin_deg; r[9] = jitter_left


def draw_roamers():
    q = gluNewQuadric()
    for r in ROAMERS:
        cx, cy, cz, length, _dir, _spd, spin_deg, _spin_speed, _je, _jl, half = r
        glPushMatrix(); glTranslatef(cx, cy, cz); glRotatef(spin_deg, 0, 0, 1)
        glColor3f(0.95, 0.35, 0.15)
        glPushMatrix(); glScalef(length, 2.0 * half, 2.0 * half); glutSolidCube(1.0); glPopMatrix()
        glColor3f(0.18, 0.18, 0.20); gluSphere(q, half * 0.85, 16, 16)
        glPopMatrix()


def roamers_check_collision():
    pr = PLAYER_RADIUS; px, py = player_x, player_y
    for r in ROAMERS:
        (ax, ay), (bx, by) = _roamer_endpoints(r)
        half = r[10]; rad = pr + half
        if _dist2_point_to_segment(px, py, ax, ay, bx, by) <= (rad * rad):
            # from shadman
            lose_life_and_respawn()
            return


# core keyboard (WASD & turning only) 
def keyboard_core(k, _x, _y):
    global player_yaw
    if k == b'a': player_yaw = (player_yaw + TURN_SPEED) % 360.0
    if k == b'd': player_yaw = (player_yaw - TURN_SPEED) % 360.0
    if k == b'w':
        fx, fy = forward_vec(player_yaw); try_move(fx * MOVE_SPEED, fy * MOVE_SPEED)
    if k == b's':
        fx, fy = forward_vec(player_yaw); try_move(-fx * MOVE_SPEED, -fy * MOVE_SPEED)


def init_world(seed):
    init_trees(seed=seed + 71, count=12, min_dist=240.0)
    set_level_geometry()
    init_crates()
    init_plates()
    init_sweepers()
    resolve_sweepers_vs_crates()
    init_roamers()