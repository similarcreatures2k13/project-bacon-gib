import struct, sys

BUILD_ANGLE_SCALE = 360.0 / 2048.0
SCALE = 2

SPRITE_MAP = {
    1680: 3004, 1744: 3004, 2000: 9, 1920: 3001, 1960: 3002,
    2120: 3005, 2370: 3003, 2630: 7,
    21: 2001, 22: 2002, 23: 2006, 24: 2004, 25: 2003, 26: 2006,
    28: 2003, 29: 2005,
    40: 2012, 41: 2019, 42: 2013, 51: 2014, 52: 2011, 53: 2045,
    49: 2048, 60: 13, 61: 2008, 62: 2048,
    170: 2001, 181: 2002,
    2560: 16, 2710: 16, 4610: 3004,
    5294: 0,
}

SKIP_PICNUMS = {0, 1, 5, 6, 7, 10}

def read_map(fp):
    with open(fp, 'rb') as f:
        data = f.read()
    p = 4
    sx = struct.unpack_from('<i', data, p)[0]; p += 4
    sy = struct.unpack_from('<i', data, p)[0]; p += 4
    sz = struct.unpack_from('<i', data, p)[0]; p += 4
    sa = struct.unpack_from('<H', data, p)[0]; p += 2
    p += 2
    ns = struct.unpack_from('<H', data, p)[0]; p += 2
    secs = []
    for i in range(ns):
        wp = struct.unpack_from('<h', data, p)[0]
        wn = struct.unpack_from('<h', data, p+2)[0]
        cz = struct.unpack_from('<i', data, p+4)[0]
        fz = struct.unpack_from('<i', data, p+8)[0]
        cstat = struct.unpack_from("<H", data, p+12)[0]
        cpn = struct.unpack_from("<h", data, p+14)[0]
        cs = struct.unpack_from('<b', data, p+18)[0]
        fpn = struct.unpack_from('<h', data, p+24)[0]
        fs = struct.unpack_from('<b', data, p+28)[0]
        p += 40
        secs.append({'wallptr':wp,'wallnum':wn,'ceilingz':cz,'floorz':fz,'ceilingpicnum':cpn,'ceilingshade':cs,'floorpicnum':fpn,'floorshade':fs,'cstat':cstat})
    nw = struct.unpack_from('<H', data, p)[0]; p += 2
    walls = []
    for i in range(nw):
        wx = struct.unpack_from('<i', data, p)[0]
        wy = struct.unpack_from('<i', data, p+4)[0]
        pt2 = struct.unpack_from('<h', data, p+8)[0]
        nwl = struct.unpack_from('<h', data, p+10)[0]
        nsc = struct.unpack_from('<h', data, p+12)[0]
        pn = struct.unpack_from('<h', data, p+16)[0]
        xr = struct.unpack_from('<B', data, p+21)[0]
        yr = struct.unpack_from('<B', data, p+22)[0]
        xp = struct.unpack_from('<B', data, p+23)[0]
        yp = struct.unpack_from('<B', data, p+24)[0]
        p += 32
        walls.append({'x':wx,'y':wy,'point2':pt2,'nextwall':nwl,'nextsector':nsc,'picnum':pn,'xr':xr,'yr':yr,'xp':xp,'yp':yp})
    nsp = struct.unpack_from('<H', data, p)[0]; p += 2
    sprites = []
    for i in range(nsp):
        spx = struct.unpack_from('<i', data, p)[0]
        spy = struct.unpack_from('<i', data, p+4)[0]
        spz = struct.unpack_from('<i', data, p+8)[0]
        spn = struct.unpack_from('<h', data, p+14)[0]
        stn = struct.unpack_from('<h', data, p+24)[0]
        ang = struct.unpack_from('<h', data, p+26)[0]
        p += 44
        sprites.append({'x':spx,'y':spy,'z':spz,'picnum':spn,'statnum':stn,'ang':ang})
    print(f"  Parsed: {ns} sectors, {nw} walls, {nsp} sprites")
    return {'start':{'x':sx,'y':sy,'ang':sa},'sectors':secs,'walls':walls,'sprites':sprites}

def to_udmf(md):
    lines = ['namespace = "zdoom";','']
    walls = md['walls']
    sectors = md['sectors']
    seen = {}
    verts = []
    w2v = {}
    for i, w in enumerate(walls):
        key = (w['x'] // SCALE, -(w['y'] // SCALE))
        if key not in seen:
            seen[key] = len(verts)
            verts.append(key)
        w2v[i] = seen[key]
    for i, (x, y) in enumerate(verts):
        lines += [f'vertex // {i}','{',f'  x = {x}.0;',f'  y = {y}.0;','}','']
    wall_sector = {}
    for si, s in enumerate(sectors):
        for wi in range(s['wallptr'], s['wallptr'] + s['wallnum']):
            wall_sector[wi] = si
    sdefs = []
    ldefs = []
    for wi, w in enumerate(walls):
        v1 = w2v[wi]
        v2 = w2v[w['point2']]
        if v1 == v2:
            continue
        front_sec = wall_sector.get(wi, 0)
        front_idx = len(sdefs)
        wall_tex = f"DTL{w['picnum']:04d}"
        twosided = w['nextsector'] >= 0
        if twosided:
            sdefs.append({'sector':front_sec,'upper':wall_tex,'lower':wall_tex,'mid':'-','xofs':w.get('xp',0),'yofs':w.get('yp',0)})
            back_idx = len(sdefs)
            back_tex = wall_tex
            if w['nextwall'] >= 0 and w['nextwall'] < len(walls):
                back_tex = f"DTL{walls[w['nextwall']]['picnum']:04d}"
            sdefs.append({'sector':w['nextsector'],'upper':back_tex,'lower':back_tex,'mid':'-','xofs':0,'yofs':0})
        else:
            sdefs.append({'sector':front_sec,'upper':'-','lower':'-','mid':wall_tex,'xofs':w.get('xp',0),'yofs':w.get('yp',0)})
            back_idx = -1
        ldefs.append({'v1':v1,'v2':v2,'front':front_idx,'back':back_idx,'two':twosided})
    for i, ld in enumerate(ldefs):
        lines += [f'linedef // {i}','{',f'  v1 = {ld["v1"]};',f'  v2 = {ld["v2"]};',f'  sidefront = {ld["front"]};']
        if ld['back'] >= 0:
            lines.append(f'  sideback = {ld["back"]};')
        if ld['two']:
            lines.append('  twosided = true;')
        else:
            lines.append('  blocking = true;')
        lines += ['}','']
    for i, sd in enumerate(sdefs):
        if isinstance(sd, dict):
            lines += [f'sidedef // {i}','{',f'  sector = {sd["sector"]};']
            if sd['mid'] != '-':
                lines.append(f'  texturemiddle = "{sd["mid"]}";')
            if sd['upper'] != '-':
                lines.append(f'  texturetop = "{sd["upper"]}";')
            if sd['lower'] != '-':
                lines.append(f'  texturebottom = "{sd["lower"]}";')
            if sd.get('xofs', 0) != 0:
                lines.append(f'  offsetx = {sd["xofs"]};')
            if sd.get('yofs', 0) != 0:
                lines.append(f'  offsety = {sd["yofs"]};')
            lines += ['}','']
        else:
            lines += [f'sidedef // {i}','{',f'  sector = {sd};',f'  texturemiddle = "GRAY1";','}','']
    for i, s in enumerate(sectors):
        fh = (-s["floorz"] // 256) * 2
        ch = (-s["ceilingz"] // 256) * 2
        vis = s.get('vis', 0)
        shade = s['floorshade']
        if shade > 50:
            light = max(80, 160 - shade)
        elif vis > 200:
            light = max(96, 160 - (vis - 200))
        else:
            light = max(128, min(255, 224 - shade * 2))
        ftex = f"DTL{s['floorpicnum']:04d}"
        if s.get('cstat', 0) & 1:
            ctex = "F_SKY1"
        else:
            ctex = f"DTL{s['ceilingpicnum']:04d}"
        if ch <= fh:
            ch = fh + 8
        lines += [f'sector // {i}','{',f'  heightfloor = {fh};',f'  heightceiling = {ch};',f'  texturefloor = "{ftex}";',f'  textureceiling = "{ctex}";',f'  lightlevel = {light};','}','']
    st = md['start']
    ang = int(st['ang'] * BUILD_ANGLE_SCALE)
    # Use original Build start position
    px = st['x'] // SCALE
    py = -(st['y'] // SCALE)
    # Find centroid of first 5 enemies to place player nearby
    enemy_things = [sp for sp in md['sprites'] if sp['picnum'] in (1680,1744,2000,1920,1960,2120)]
    if enemy_things:
        ax = sum(s['x'] for s in enemy_things[:5]) // (len(enemy_things[:5]) * SCALE)
        ay = sum(-(s['y']) for s in enemy_things[:5]) // (len(enemy_things[:5]) * SCALE)
        px, py = ax - 200, ay - 200
    lines += ['thing // 0','{',f'  x = {px}.0;',f'  y = {py}.0;',f'  angle = {ang};','  type = 1;','  skill1 = true;','  skill2 = true;','  skill3 = true;','  skill4 = true;','  skill5 = true;','}','']
    tidx = 1
    unmapped = {}
    for sp in md['sprites']:
        if sp['picnum'] in SKIP_PICNUMS:
            continue
        dt = SPRITE_MAP.get(sp['picnum'])
        if not dt:
            unmapped[sp['picnum']] = unmapped.get(sp['picnum'], 0) + 1
            continue
        if dt == 0:
            continue
        lines += [f'thing // {tidx}','{',f'  x = {sp["x"]//SCALE}.0;',f'  y = {-(sp["y"]//SCALE)}.0;',f'  angle = {int(sp["ang"] * BUILD_ANGLE_SCALE)};',f'  type = {dt};','  skill1 = true;','  skill2 = true;','  skill3 = true;','  skill4 = true;','  skill5 = true;','}','']
        tidx += 1
    print(f"  Output: {len(verts)} verts, {len(ldefs)} lines, {len(sdefs)} sides, {len(sectors)} sectors, {tidx} things")
    if unmapped:
        print(f"  Unmapped sprite picnums:")
        for pn, c in sorted(unmapped.items(), key=lambda x:-x[1])[:15]:
            print(f"    {pn}: {c}x")
    return '\n'.join(lines)

def make_wad(textmap, name="MAP01"):
    lumps = [(name, b''), ('TEXTMAP', textmap.encode('utf-8')), ('ENDMAP', b'')]
    wad = bytearray(b'PWAD')
    wad += struct.pack('<I', len(lumps))
    ds = 12
    total = sum(len(d) for _, d in lumps)
    wad += struct.pack('<I', ds + total)
    offs = []
    o = ds
    for _, d in lumps:
        offs.append(o)
        wad += d
        o += len(d)
    for i, (n, d) in enumerate(lumps):
        wad += struct.pack('<I', offs[i])
        wad += struct.pack('<I', len(d))
        wad += n.encode('ascii').ljust(8, b'\x00')
    return bytes(wad)

inp = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else inp.replace('.MAP','.wad').replace('.map','.wad')
print(f"Converting: {inp}")
md = read_map(inp)
tm = to_udmf(md)
wd = make_wad(tm)
with open(out, 'wb') as f:
    f.write(wd)
print(f"Wrote: {out} ({len(wd)} bytes)")
