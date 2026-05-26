#!/usr/bin/env python3
"""
build2udmf.py — Convert Build engine .MAP files to GZDoom UDMF format
Part of PROJECT BACON-GIB
"""

import struct
import sys
import os

BUILD_Z_SCALE = 16.0
BUILD_ANGLE_SCALE = 360.0 / 2048.0

SPRITE_MAP = {
    1680: 3004, 2000: 9, 1920: 3001, 1960: 3002,
    2120: 3005, 2370: 3003, 2630: 16,
    21: 2011, 22: 2012, 51: 2014, 26: 2018,
    40: 2007, 49: 2048, 41: 2010, 42: 2046,
    60: 13, 61: 38, 62: 39,
    170: 2001, 181: 2002,
}

def read_build_map(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    pos = 0
    version = struct.unpack_from('<I', data, pos)[0]; pos += 4
    start_x = struct.unpack_from('<i', data, pos)[0]; pos += 4
    start_y = struct.unpack_from('<i', data, pos)[0]; pos += 4
    start_z = struct.unpack_from('<i', data, pos)[0]; pos += 4
    start_ang = struct.unpack_from('<H', data, pos)[0]; pos += 2
    start_sector = struct.unpack_from('<H', data, pos)[0]; pos += 2
    print(f"  Version: {version}, Start: ({start_x},{start_y},{start_z}), Angle: {start_ang}")

    num_sectors = struct.unpack_from('<H', data, pos)[0]; pos += 2
    print(f"  Sectors: {num_sectors}")
    sectors = []
    for i in range(num_sectors):
        s = {}
        s['wallptr'],s['wallnum'] = struct.unpack_from('<hh', data, pos); pos += 4
        s['ceilingz'],s['floorz'] = struct.unpack_from('<ii', data, pos); pos += 8
        s['ceilingstat'],s['floorstat'] = struct.unpack_from('<HH', data, pos); pos += 4
        s['ceilingpicnum'],s['ceilingheinum'] = struct.unpack_from('<hh', data, pos); pos += 4
        s['ceilingshade'] = struct.unpack_from('<b', data, pos)[0]; pos += 1
        s['ceilingpal'],s['ceilingxpanning'],s['ceilingypanning'] = struct.unpack_from('<BBB', data, pos); pos += 3
        s['floorpicnum'],s['floorheinum'] = struct.unpack_from('<hh', data, pos); pos += 4
        s['floorshade'] = struct.unpack_from('<b', data, pos)[0]; pos += 1
        s['floorpal'],s['floorxpanning'],s['floorypanning'] = struct.unpack_from('<BBB', data, pos); pos += 3
        s['visibility'] = struct.unpack_from('<B', data, pos)[0]; pos += 1
        pos += 1  # filler
        s['lotag'],s['hitag'] = struct.unpack_from('<HH', data, pos); pos += 4
        s['extra'] = struct.unpack_from('<h', data, pos)[0]; pos += 2
        sectors.append(s)

    num_walls = struct.unpack_from('<H', data, pos)[0]; pos += 2
    print(f"  Walls: {num_walls}")
    walls = []
    for i in range(num_walls):
        w = {}
        w['x'],w['y'] = struct.unpack_from('<ii', data, pos); pos += 8
        w['point2'],w['nextwall'],w['nextsector'] = struct.unpack_from('<hhh', data, pos); pos += 6
        w['cstat'] = struct.unpack_from('<H', data, pos)[0]; pos += 2
        w['picnum'],w['overpicnum'] = struct.unpack_from('<hh', data, pos); pos += 4
        w['shade'] = struct.unpack_from('<b', data, pos)[0]; pos += 1
        w['pal'],w['xrepeat'],w['yrepeat'],w['xpanning'],w['ypanning'] = struct.unpack_from('<BBBBB', data, pos); pos += 5
        w['lotag'],w['hitag'] = struct.unpack_from('<HH', data, pos); pos += 4
        w['extra'] = struct.unpack_from('<h', data, pos)[0]; pos += 2
        walls.append(w)

    num_sprites = struct.unpack_from('<H', data, pos)[0]; pos += 2
    print(f"  Sprites: {num_sprites}")
    sprites = []
    for i in range(num_sprites):
        sp = {}
        sp['x'],sp['y'],sp['z'] = struct.unpack_from('<iii', data, pos); pos += 12
        sp['cstat'] = struct.unpack_from('<H', data, pos)[0]; pos += 2
        sp['picnum'] = struct.unpack_from('<h', data, pos)[0]; pos += 2
        sp['shade'] = struct.unpack_from('<b', data, pos)[0]; pos += 1
        sp['pal'],sp['clipdist'] = struct.unpack_from('<BB', data, pos); pos += 2
        pos += 1  # filler
        sp['xrepeat'],sp['yrepeat'] = struct.unpack_from('<BB', data, pos); pos += 2
        sp['xoffset'],sp['yoffset'] = struct.unpack_from('<bb', data, pos); pos += 2
        sp['sectnum'],sp['statnum'],sp['ang'] = struct.unpack_from('<hhh', data, pos); pos += 6
        sp['owner'],sp['xvel'],sp['yvel'],sp['zvel'] = struct.unpack_from('<hhhh', data, pos); pos += 8
        sp['lotag'],sp['hitag'] = struct.unpack_from('<HH', data, pos); pos += 4
        sp['extra'] = struct.unpack_from('<h', data, pos)[0]; pos += 2
        sprites.append(sp)

    return {
        'start': {'x': start_x, 'y': start_y, 'z': start_z, 'ang': start_ang},
        'sectors': sectors, 'walls': walls, 'sprites': sprites
    }

def build_to_udmf(mapdata):
    lines = ['namespace = "zdoom";', '']
    walls = mapdata['walls']
    sectors = mapdata['sectors']

    # Vertices from wall positions
    seen = {}
    vertices = []
    wall_to_vertex = {}
    for i, w in enumerate(walls):
        key = (w['x'], -w['y'])
        if key not in seen:
            seen[key] = len(vertices)
            vertices.append(key)
        wall_to_vertex[i] = seen[key]

    for i, (vx, vy) in enumerate(vertices):
        vx = vx // 4
        vy = vy // 4
        lines += [f'vertex // {i}', '{', f'  x = {vx // 4}.0;', f'  y = {vy // 4}.0;', '}', '']

    # Linedefs + sidedefs
    sidedefs = []
    linedefs_out = []
    
    for sec_idx, sector in enumerate(sectors):
        ws = sector['wallptr']
        wn = sector['wallnum']
        for wi in range(ws, ws + wn):
            w = walls[wi]
            v1 = wall_to_vertex[wi]
            v2 = wall_to_vertex[w['point2']]
            
            front_idx = len(sidedefs)
            sidedefs.append({'sector': sec_idx, 'mid': f'WALL{w["picnum"]:04d}'})
            
            back_idx = -1
            if w['nextsector'] >= 0:
                back_idx = len(sidedefs)
                sidedefs.append({'sector': w['nextsector'], 'mid': '-'})
            
            linedefs_out.append({'v1': v1, 'v2': v2, 'front': front_idx, 'back': back_idx,
                                 'two': w['nextsector'] >= 0, 'block': w['nextsector'] < 0})

    for i, ld in enumerate(linedefs_out):
        lines += [f'linedef // {i}', '{', f'  v1 = {ld["v1"]};', f'  v2 = {ld["v2"]};', f'  sidefront = {ld["front"]};']
        if ld['back'] >= 0: lines.append(f'  sideback = {ld["back"]};')
        if ld['two']: lines.append('  twosided = true;')
        if ld['block']: lines.append('  blocking = true;')
        lines += ['}', '']

    for i, sd in enumerate(sidedefs):
        lines += [f'sidedef // {i}', '{', f'  sector = {sd["sector"]};']
        if sd['mid'] != '-': lines.append(f'  texturemiddle = "{sd["mid"]}";')
        lines += ['}', '']

    for i, s in enumerate(sectors):
        fh = int(-s['floorz'] / BUILD_Z_SCALE)
        ch = int(-s['ceilingz'] / BUILD_Z_SCALE)
        light = max(0, min(255, 255 + s['floorshade'] * 2))
        lines += [f'sector // {i}', '{', f'  heightfloor = {fh};', f'  heightceiling = {ch};',
                  f'  texturefloor = "FLOOR{s["floorpicnum"]:04d}";',
                  f'  textureceiling = "CEIL{s["ceilingpicnum"]:04d}";',
                  f'  lightlevel = {light};', '}', '']

    # Player start
    st = mapdata['start']
    ang = int(st['ang'] * BUILD_ANGLE_SCALE)
    lines += [f'thing // 0 - Player Start', '{', f'  x = {st["x"] // 4}.0;', f'  y = {-st["y"] // 4}.0;',
              f'  angle = {ang};', '  type = 1;', '  skill1 = true;', '  skill2 = true;',
              '  skill3 = true;', '  skill4 = true;', '  skill5 = true;', '}', '']

    # Sprites → things
    tidx = 1
    unmapped = set()
    for sp in mapdata['sprites']:
        if sp['statnum'] >= 3: continue
        dt = SPRITE_MAP.get(sp['picnum'])
        if not dt: unmapped.add(sp['picnum']); continue
        sa = int(sp['ang'] * BUILD_ANGLE_SCALE)
        lines += [f'thing // {tidx}', '{', f'  x = {sp["x"] // 4}.0;', f'  y = {-sp["y"] // 4}.0;',
                  f'  angle = {sa};', f'  type = {dt};', '  skill1 = true;', '  skill2 = true;',
                  '  skill3 = true;', '  skill4 = true;', '  skill5 = true;', '}', '']
        tidx += 1

    if unmapped: print(f"  Unmapped picnums: {sorted(unmapped)}")
    print(f"  Output: {len(vertices)} verts, {len(linedefs_out)} lines, {len(sectors)} sectors, {tidx} things")
    return '\n'.join(lines)

def create_wad(textmap, name="MAP01"):
    lumps = [(name, b''), ('TEXTMAP', textmap.encode('utf-8')), ('ENDMAP', b'')]
    wad = bytearray(b'PWAD')
    wad += struct.pack('<I', len(lumps))
    data_start = 12
    total = sum(len(d) for _,d in lumps)
    wad += struct.pack('<I', data_start + total)
    offsets = []
    o = data_start
    for _,d in lumps:
        offsets.append(o); wad += d; o += len(d)
    for i,(n,d) in enumerate(lumps):
        wad += struct.pack('<I', offsets[i])
        wad += struct.pack('<I', len(d))
        wad += n.encode('ascii').ljust(8, b'\x00')
    return bytes(wad)

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python3 build2udmf.py <input.MAP> [output.wad]")
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else inp.replace('.MAP','.wad').replace('.map','.wad')
    md = read_build_map(inp)
    tm = build_to_udmf(md)
    wd = create_wad(tm)
    with open(out, 'wb') as f: f.write(wd)
    print(f"Wrote: {out} ({len(wd)} bytes)")
