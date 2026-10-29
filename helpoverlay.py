"""레벨 도움말 오버레이(128x128 타일로 잘린 이미지)의 영어 문구를 한글로 바꾼다.

타일 이름 help-N은 가로 COLS[level]칸 격자의 N번째 칸이다. 타일을 원래 배치로 합쳐
글자 덩어리를 찾아 지운 뒤 한글을 그리고, 다시 타일로 잘라 아틀라스 아래쪽에 붙인다.
"""
import io, re
from collections import deque
import numpy as np
from PIL import Image

# 타일 경계 연속성으로 찾은 레벨별 격자 칸 수
COLS = {'level1': 11, 'level2': 11, 'level3': 13, 'level4': 14, 'level5': 15, 'level6': 12,
        'level7': 18, 'level8': 11, 'level9': 12, 'level10': 11, 'level11': 11, 'level12': 11,
        'level14': 11, 'level15': 13, 'level16': 11}
TILE = 128


def subtextures(xml):
    for m in re.finditer(r'<SubTexture ([^>]*?)/>', xml):
        yield m, dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))


def rebuild(xml, atlas, cols):
    tiles = [a for _, a in subtextures(xml) if a['name'].startswith('help')]
    idx = [int(a['name'].split('-')[1]) for a in tiles]
    rows = max(idx) // cols + 1
    canvas = Image.new('RGBA', (cols * TILE, rows * TILE), (0, 0, 0, 0))
    for a, n in zip(tiles, idx):
        x, y, w, h = (int(a[k]) for k in ('x', 'y', 'width', 'height'))
        if w <= 0 or h <= 0: continue
        fx, fy = -int(a.get('frameX', 0)), -int(a.get('frameY', 0))
        canvas.alpha_composite(atlas.crop((x, y, x + w, y + h)), ((n % cols) * TILE + fx, (n // cols) * TILE + fy))
    return canvas, set(idx)


def _components(mask):
    h, w = mask.shape
    seen = np.zeros_like(mask, bool)
    ys, xs = np.nonzero(mask)
    comps = []
    for y0, x0 in zip(ys, xs):
        if seen[y0, x0]: continue
        q = deque([(y0, x0)]); seen[y0, x0] = True
        minx = maxx = x0; miny = maxy = y0; n = 0
        while q:
            y, x = q.popleft(); n += 1
            minx, maxx, miny, maxy = min(minx, x), max(maxx, x), min(miny, y), max(maxy, y)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    yy, xx = y + dy, x + dx
                    if 0 <= yy < h and 0 <= xx < w and mask[yy, xx] and not seen[yy, xx]:
                        seen[yy, xx] = True; q.append((yy, xx))
        comps.append((int(minx), int(miny), int(maxx) + 1, int(maxy) + 1, n))
    return comps


def _monotone_triangle(profile):
    p = profile[profile > 0]
    if len(p) < 8: return False
    d = np.diff(p)
    return (p.min() <= p.max() * 0.35) and ((d >= -1).all() or (d <= 1).all())


def _is_triangle(mask):
    """꽉 찬 삼각형 화살표: 구멍이 없고, 한 축 방향으로 폭이 꾸준히 늘거나 준다."""
    rows, cols = mask.sum(axis=1), mask.sum(axis=0)
    spans_r = np.array([np.ptp(np.nonzero(r)[0]) + 1 if r.any() else 0 for r in mask])
    if (spans_r - rows).max() > 1: return False
    return _monotone_triangle(rows) or _monotone_triangle(cols)


def _is_glyph(c, a):
    x0, y0, x1, y1, n = c
    w, h = x1 - x0, y1 - y0
    if w <= 6 and h <= 6: return False                      # 점선의 점 (i, j, 마침표 점은 따로 붙음)
    if h > 40 or w > 60: return False                       # 긴 선
    if w >= 9 and h >= 9 and _is_triangle(a[y0:y1, x0:x1]): return False
    return True


def _dilate(m, dx, dy):
    out = m.copy()
    for s in range(1, dx + 1):
        out[:, s:] |= m[:, :-s]; out[:, :-s] |= m[:, s:]
    m2 = out.copy()
    for s in range(1, dy + 1):
        out[s:, :] |= m2[:-s, :]; out[:-s, :] |= m2[s:, :]
    return out


def find_blocks(canvas):
    """글자 덩어리(여러 줄 문단) 상자 목록을 위→아래, 왼→오 순서로 돌려준다.
    각 상자에는 줄 수(lines)와 줄 높이(line_h)를 함께 담는다."""
    a = np.array(canvas)[:, :, 3] > 60
    comps = _components(a)
    gmask = np.zeros_like(a)
    for c in comps:
        if _is_glyph(c, a):
            gmask[c[1]:c[3], c[0]:c[2]] = True
    blobs = _components(_dilate(gmask, 9, 7))
    blocks = []
    for x0, y0, x1, y1, _ in blobs:
        x0, y0, x1, y1 = x0 + 9, y0 + 7, x1 - 9, y1 - 7
        if x1 - x0 < 12: continue
        # 상자 안의 점(i 점, 마침표)까지 포함하도록 실제 픽셀로 다시 조인다
        sub = a[max(0, y0 - 6):y1 + 4, max(0, x0 - 2):x1 + 6]
        ys, xs = np.nonzero(sub)
        box = [max(0, x0 - 2) + int(xs.min()), max(0, y0 - 6) + int(ys.min()),
               max(0, x0 - 2) + int(xs.max()) + 1, max(0, y0 - 6) + int(ys.max()) + 1]
        rows = gmask[box[1]:box[3], box[0]:box[2]].any(axis=1)
        runs = np.diff(np.concatenate([[0], rows.astype(int), [0]]))
        n_lines = max(1, int((runs == 1).sum()))
        blocks.append({'box': box, 'lines': n_lines, 'line_h': (box[3] - box[1]) / n_lines})
    blocks.sort(key=lambda B: (B['box'][1], B['box'][0]))
    return blocks


def erase_text(canvas, box):
    """상자 안의 글자 픽셀만 지운다. 상자 밖으로 이어지는 점선·화살표는 남긴다."""
    arr = np.array(canvas)
    a = arr[:, :, 3] > 0
    x0, y0, x1, y1 = box
    px0, py0 = max(0, x0 - 4), max(0, y0 - 8)
    sub = a[py0:y1 + 4, px0:x1 + 4]
    kill = np.zeros_like(a)
    comps = [(c[0] + px0, c[1] + py0, c[2] + px0, c[3] + py0) for c in _components(sub)]
    comps = [c for c in comps if c[0] >= x0 - 2 and c[2] <= x1 + 2 and c[1] >= y0 - 7 and c[3] <= y1 + 1]
    glyphs = [c for c in comps if _is_glyph((*c, 0), a)
              and not ((c[2] - c[0]) >= 9 and (c[3] - c[1]) >= 9 and _is_triangle(a[c[1]:c[3], c[0]:c[2]]))]
    for c in comps:
        gx0, gy0, gx1, gy1 = c
        if c not in glyphs:
            if (gx1 - gx0) > 6 or (gy1 - gy0) > 6: continue          # 화살표
            # 작은 점: 바로 아래/왼쪽에 글자가 붙어 있을 때만(i·j 점, 마침표·쉼표) 지운다
            cx, cy = (gx0 + gx1) / 2, (gy0 + gy1) / 2
            if not any(g[0] - 2 <= cx <= g[2] + 6 and g[1] - 9 <= cy <= g[3] + 2 for g in glyphs):
                continue
        kill[gy0:gy1, gx0:gx1] |= a[gy0:gy1, gx0:gx1]
    arr[kill] = 0
    return Image.fromarray(arr)


def draw_lines(canvas, box, n_src_lines, text, font_path, ink=(0, 0, 0, 255), glyph_h=None, align='left'):
    from PIL import ImageDraw, ImageFont
    x0, y0, x1, y1 = box
    lines = text.split('\n')
    pitch = (y1 - y0) / n_src_lines                    # 원문 줄 간격
    pitch = max(pitch, 26) if len(lines) > n_src_lines else pitch
    target = glyph_h or pitch * 0.66                   # 한글 글자 높이
    probe = ImageFont.truetype(font_path, 100)
    gh = probe.getbbox('가')[3] - probe.getbbox('가')[1]
    f = ImageFont.truetype(font_path, max(8, round(100 * target / gh)))
    width = x1 - x0
    total_h = pitch * len(lines)
    top = y0 + ((y1 - y0) - total_h) / 2 if len(lines) <= n_src_lines else y0
    for i, line in enumerate(lines):
        l, t, r, b = f.getbbox(line)
        im = Image.new('L', (r - l + 4, b - t + 4), 0)
        ImageDraw.Draw(im).text((2 - l, 2 - t), line, font=f, fill=255)
        im = im.crop(im.getbbox())
        if im.width > width:                          # 넘치면 가로로만 누른다 (최대 25%), 그래도 넘치면 축소
            sx = max(width / im.width, 0.75)
            im = im.resize((round(im.width * sx), im.height), Image.LANCZOS)
            if im.width > width:
                s = width / im.width
                im = im.resize((width, max(1, round(im.height * s))), Image.LANCZOS)
        layer = Image.new('RGBA', im.size, ink); layer.putalpha(im)
        cy = top + pitch * i + (pitch - im.height) / 2
        x = x1 - im.width if align == 'right' else x0
        canvas.alpha_composite(layer, (x, int(round(cy))))
    return canvas


def patch_level(xml, atlas, level, entries, font_path):
    cols = COLS[level]
    canvas, used = rebuild(xml, atlas, cols)
    blocks = find_blocks(canvas)
    for e in entries:
        B = blocks[e['block']]
        canvas = erase_text(canvas, B['box'])
        draw_lines(canvas, B['box'], B['lines'], e['ko'], font_path)
    return reslice(canvas, used, cols, xml, atlas)


def reslice(canvas, used, cols, old_xml, atlas):
    """수정한 오버레이를 원래 있던 칸만 다시 잘라 아틀라스 아래에 붙이고 XML을 고친다."""
    arr = np.array(canvas)
    pieces = {}
    for n in used:
        cx, cy = (n % cols) * TILE, (n // cols) * TILE
        t = canvas.crop((cx, cy, cx + TILE, cy + TILE))
        bb = t.getbbox()
        pieces[n] = (t.crop(bb), bb) if bb else (None, None)
    lost = arr[:, :, 3].copy()
    for n in used:
        cx, cy = (n % cols) * TILE, (n // cols) * TILE
        lost[cy:cy + TILE, cx:cx + TILE] = 0
    if lost.max() > 60:
        ys, xs = np.nonzero(lost > 60)
        raise ValueError(f'원래 없던 칸에 그림이 걸침: x={xs.min()}..{xs.max()} y={ys.min()}..{ys.max()}')
    # 아래쪽에 선반 배치
    W = atlas.width; x = 0; y = atlas.height + 2; row_h = 0; place = {}
    for n in sorted(pieces):
        img, bb = pieces[n]
        if img is None: continue
        if x + img.width > W: x = 0; y += row_h + 2; row_h = 0
        place[n] = (x, y); x += img.width + 2; row_h = max(row_h, img.height)
    new_h = y + row_h + 2
    if new_h > 2048: raise ValueError(f'아틀라스 높이 초과 {new_h}')
    out = Image.new('RGBA', (W, new_h), (0, 0, 0, 0)); out.paste(atlas, (0, 0))
    for n, (px, py) in place.items():
        out.paste(pieces[n][0], (px, py))

    def fix(m):
        a = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        if not a['name'].startswith('help'): return m.group(0)
        n = int(a['name'].split('-')[1]); img, bb = pieces[n]
        if img is None:
            return f'<SubTexture name="{a["name"]}" x="0" y="0" width="-1" height="-1" frameX="0" frameY="0" frameWidth="{TILE}" frameHeight="{TILE}"/>'
        px, py = place[n]
        return (f'<SubTexture name="{a["name"]}" x="{px}" y="{py}" width="{img.width}" height="{img.height}" '
                f'frameX="{-bb[0]}" frameY="{-bb[1]}" frameWidth="{TILE}" frameHeight="{TILE}"/>')
    new_xml = re.sub(r'<SubTexture ([^>]*?)/>', fix, old_xml)
    return out, new_xml
