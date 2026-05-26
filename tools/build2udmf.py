import struct, sys

BUILD_Z_SCALE = 26.0
BUILD_ANGLE_SCALE = 360.0 / 2048.0
SCALE = 2

SPRITE_MAP = {
    1680: 3004, 1744: 3004, 2000: 9, 1920: 3001, 1960: 3002,
    2120: 3005, 2370: 3003, 2630: 16,
    21: 2011, 22: 2012, 51: 2014, 26: 2018,
    40: 2007, 49: 2048, 41: 2010, 42: 2046,
    60: 13, 61: 38, 62: 39, 170: 2001, 181: 2002,
}

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
        cpn = struct.unpack_from('<h', data, p+16)[0]
        cs = struct.unpack_from('<b', data, p+20)[0]
        fpn = struct.unpack_from('<h', data, p+24)[0]
        fs = struct.unpack_from('<b', data, p+28)[0]
        p += 40
        secs.append({'wallptr':wp,'wallnum':wn,'ceilingz':cz,'floorz':fz,'ceilingpicnum':cpn,'ceilingshade':cs,'floorpicnum':fpn,'floorshade':fs})
    nw = struct.unpack_from('<H', data, p)[0]; p += 2
    walls = []
    for i in range(nw):
        wx = struct.unpack_from('<i', data, p)[0]
        wy = struct.unpack_from('<i', data, p+4)[0]
        pt2 = struct.unpack_from('<h', data, p+8)[0]
        nwl = struct.unpack_from('<h', data, p+10)[0]
        nsc = struct.unpack_from('<h', data, p+12)[0]
        pn = struct.unpack_from('<h', data, p+16)[0]
        p += 32
        walls.append({'x':wx,'y':wy,'point2':pt2,'nextwall':nwl,'nextsector':nsc,'picnum':pn})
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
        sdefs.append(front_sec)
        back_idx = -1
        twosided = False
        if w['nextsector'] >= 0:
            back_idx = len(sdefs)
            sdefs.append(w['nextsector'])
            twosided = True
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
    for i, sec in enumerate(sdefs):
        lines += [f'sidedef // {i}','{',f'  sector = {sec};',f'  texturemiddle = "GRAY1";','}','']
    for i, s in enumerate(sectors):
        fh = -s["floorz"] // 256
        ch = -s["ceilingz"] // 256
        light = max(0, min(255, 255 + s['floorshade'] * 2))
        lines += [f'sector // {i}','{',f'  heightfloor = {fh};',f'  heightceiling = {ch};',f'  texturefloor = "CEIL3_5";',f'  textureceiling = "CEIL3_5";',f'  lightlevel = {light};','}','']
    st = md['start']
    ang = int(st['ang'] * BUILD_ANGLE_SCALE)
    lines += ['thing // 0','{',f'  x = {st["x"]//SCALE}.0;',f'  y = {-(st["y"]//SCALE)}.0;',f'  angle = {ang};','  type = 1;','  skill1 = true;','  skill2 = true;','  skill3 = true;','  skill4 = true;','  skill5 = true;','}','']
    tidx = 1
    for sp in md['sprites']:
        if sp['statnum'] >= 3:
            continue
        dt = SPRITE_MAP.get(sp['picnum'])
        if not dt:
            continue
        lines += [f'thing // {tidx}','{',f'  x = {sp["x"]//SCALE}.0;',f'  y = {-(sp["y"]//SCALE)}.0;',f'  angle = {int(sp["ang"] * BUILD_ANGLE_SCALE)};',f'  type = {dt};','  skill1 = true;','  skill2 = true;','  skill3 = true;','  skill4 = true;','  skill5 = true;','}','']
        tidx += 1
    print(f"  Output: {len(verts)} verts, {len(ldefs)} lines, {len(sdefs)} sides, {len(sectors)} sectors, {tidx} things")
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
