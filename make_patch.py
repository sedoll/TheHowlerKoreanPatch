"""Howler 한글 패치 빌더.

Howler.swf.orig(원본)를 읽어
  1) ABC 문자열 풀의 영어 문장을 ko.json 번역으로 교체하고
  2) Phaeton 비트맵 폰트 4종에 한글 글리프를 추가한 뒤
  3) ../Howler.swf 로 저장한다.
"""
import hashlib, io, json, os, re, struct, sys, zlib
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from swf import read_swf, parse_header, iter_tags, write_tag, write_swf
from abcfile import u30, enc_u30
import images, helpoverlay

SRC = os.path.join(HERE, 'Howler.swf.orig')
DST = os.path.join(HERE, '..', 'Howler.swf')
INTRO_JPG = os.path.join(HERE, '..', 'media', 'bg', 'intro.jpg')
LOADING_BITMAP_ID = 1   # 로고+소개문+Loading... 이 그려진 로딩 화면
ORIG_SHA256 = 'dfac8e9fd1a8180c181529795ea4c679f3c61ed0b29209a5077f9285d8b64ac3'   # Steam판 원본 Howler.swf


def backup(path):
    """게임 폴더 파일의 원본을 orig/에 한 번만 보관하고, 항상 그 원본 경로를 돌려준다."""
    rel = os.path.relpath(os.path.abspath(path), os.path.abspath(os.path.join(HERE, '..', 'media')))
    orig = os.path.join(HERE, 'orig', rel)
    if not os.path.exists(orig):
        os.makedirs(os.path.dirname(orig), exist_ok=True)
        with open(path, 'rb') as f, open(orig, 'wb') as g: g.write(f.read())
    return orig
KO_FONT = os.path.join(HERE, 'fonts', 'GraceSerif-Bold.ttf')   # 우아한세리프, SIL OFL 1.1
KO_SCALE = 0.8    # 원본 폰트 크기 대비 한글 픽셀 크기
TEX_W = 2048


def symbol_names(body, pos):
    syms = {}
    for code, s, p, ln in iter_tags(body, pos):
        if code == 76:
            d = body[p:p+ln]; n = struct.unpack('<H', d[:2])[0]; q = 2
            for _ in range(n):
                cid = struct.unpack('<H', d[q:q+2])[0]; q += 2
                e = d.index(b'\0', q); syms[cid] = d[q:e].decode(); q = e + 1
    return syms


def patch_abc(abc, tr):
    """문자열 풀만 다시 쓴다. 번역 대상이 아닌 문자열은 원본 바이트 그대로 둔다."""
    p = 4
    for skip in (1, 1, 8):          # int, uint, double 풀
        n, p = u30(abc, p)
        for _ in range(max(n-1, 0)):
            if skip == 8: p += 8
            else: _, p = u30(abc, p)
    sp_start = p
    n, p = u30(abc, p)
    out = bytearray(enc_u30(n)); hit = set()
    for _ in range(n-1):
        l, p = u30(abc, p); raw = abc[p:p+l]; p += l
        s = raw.decode('utf-8', 'surrogatepass') if raw else ''
        if s in tr:
            raw = tr[s].encode('utf-8'); hit.add(s)
        out += enc_u30(len(raw)) + raw
    missing = set(tr) - hit
    if missing:
        print('경고: 원본에서 찾지 못한 문장', len(missing), list(missing)[:3])
    return abc[:sp_start] + bytes(out) + abc[p:]


def parse_fnt(xml):
    chars = []
    for line in xml.splitlines():
        if '<char ' in line:
            chars.append({k: int(v) for k, v in re.findall(r'(\w+)="(-?\d+)"', line)})
    common = dict(re.findall(r'(\w+)="(-?\d+)"', re.search(r'<common[^>]*>', xml).group(0)))
    return chars, int(common['lineHeight']), int(common['base'])


def build_font(xml, png, extra_chars):
    chars, line_h, base = parse_fnt(xml)
    size = int(re.search(r'size="(\d+)"', xml).group(1))
    tex = Image.open(io.BytesIO(png)).convert('RGBA')
    font = ImageFont.truetype(KO_FONT, round(size * KO_SCALE))

    glyphs = []   # (char dict, image)
    have = {c['id'] for c in chars}
    for c in chars:
        glyphs.append((c, tex.crop((c['x'], c['y'], c['x']+c['width'], c['y']+c['height']))))
    for ch in sorted(extra_chars):
        if ord(ch) in have: continue
        l, t, r, b = font.getbbox(ch, anchor='ls')
        w, h = max(r - l, 1) + 2, max(b - t, 1) + 2
        im = Image.new('L', (w, h), 0)
        ImageDraw.Draw(im).text((1 - l, 1 - t), ch, font=font, fill=255, anchor='ls')
        g = Image.new('RGBA', (w, h), (255, 255, 255, 0)); g.putalpha(im)
        glyphs.append(({'id': ord(ch), 'width': w, 'height': h, 'xoffset': l - 1,
                        'yoffset': base + t - 1, 'xadvance': round(font.getlength(ch)) + 1}, g))

    # 단순 선반(shelf) 패킹
    x = y = row_h = 0; placed = []
    for c, g in sorted(glyphs, key=lambda cg: -cg[1].height):
        if x + c['width'] + 1 > TEX_W:
            x = 0; y += row_h + 1; row_h = 0
        placed.append((c, g, x, y)); x += c['width'] + 1; row_h = max(row_h, c['height'])
    tex_h = 1
    while tex_h < y + row_h + 1: tex_h *= 2
    if tex_h > 2048: raise SystemExit('폰트 텍스처가 2048을 넘음: 글자 수를 줄여야 함')
    out = Image.new('RGBA', (TEX_W, tex_h), (255, 255, 255, 0))
    lines = []
    for c, g, gx, gy in sorted(placed, key=lambda t: t[0]['id']):
        out.paste(g, (gx, gy))
        lines.append(f'    <char id="{c["id"]}" x="{gx}" y="{gy}" width="{c["width"]}" height="{c["height"]}" '
                     f'xoffset="{c["xoffset"]}" yoffset="{c["yoffset"]}" xadvance="{c["xadvance"]}" page="0" chnl="15" />')

    head = xml[:xml.index('<chars')]
    head = re.sub(r'scaleW="\d+"', f'scaleW="{TEX_W}"', head)
    head = re.sub(r'scaleH="\d+"', f'scaleH="{tex_h}"', head)
    tail = xml[xml.index('</chars>'):]
    new_xml = head + f'<chars count="{len(lines)}">\n' + '\n'.join(lines) + '\n  ' + tail
    buf = io.BytesIO(); out.save(buf, 'PNG', optimize=True)
    return new_xml.encode('utf-8'), buf.getvalue()


def ensure_original():
    """처음 실행이면 게임 폴더의 원본 Howler.swf를 Howler.swf.orig로 보관한다. 버전이 다르면 중단."""
    path = SRC if os.path.exists(SRC) else DST
    with open(path, 'rb') as f: data = f.read()
    if hashlib.sha256(data).hexdigest() != ORIG_SHA256:
        raise SystemExit(f'{os.path.abspath(path)} 가 패치 대상 원본(Steam판)과 다릅니다.\n'
                         'Steam에서 "게임 파일 무결성 확인"을 한 뒤 orig 폴더를 지우고 다시 실행하세요.')
    if path == DST:
        with open(SRC, 'wb') as f: f.write(data)


def main():
    ensure_original()
    tr = json.load(open(os.path.join(HERE, 'ko.json'), encoding='utf-8'))
    extra = {ch for v in tr.values() for ch in v if ord(ch) > 126}
    ver, body = read_swf(SRC)
    pos = parse_header(body)
    syms = symbol_names(body, pos)

    tags = list(iter_tags(body, pos))
    fnt_xml, fnt_png, level_xml = {}, {}, {}
    for code, s, p, ln in tags:
        cid = struct.unpack('<H', body[p:p+2])[0] if ln >= 2 else None
        name = syms.get(cid, '')
        m = re.match(r'Phaeton_(\d+)_(fnt|png)\$', name)
        if m and code == 87: fnt_xml[m[1]] = (cid, body[p+6:p+ln].decode('utf-8'))
        if m and code == 21: fnt_png[m[1]] = (cid, body[p+2:p+ln])
        if code == 21 and name.startswith('intro_png$'): atlas = (cid, body[p+2:p+ln])
        m = re.match(r'(level\d+)_xml\$', name)
        if m and code == 87: level_xml[m[1]] = (cid, body[p+6:p+ln].decode('utf-8'))
        if code == 36 and cid == LOADING_BITMAP_ID: loading = body[p:p+ln]

    new_fnt, new_png = {}, {}
    new_png[atlas[0]] = images.patch_atlas(atlas[1], KO_FONT)
    images.patch_intro_jpg(backup(INTRO_JPG), INTRO_JPG, KO_FONT)

    # 로딩 화면 비트맵 (DefineBitsLossless2, 32비트 ARGB)
    fmt, w, h = struct.unpack('<BHH', loading[2:7])
    argb = images.patch_loading(zlib.decompress(loading[7:]), (w, h), KO_FONT)
    new_lossless = {LOADING_BITMAP_ID: loading[:7] + zlib.compress(argb, 9)}

    # 레벨 도움말 오버레이: 아틀라스 PNG는 media/levels, 좌표 XML은 SWF 안
    help_tr = json.load(open(os.path.join(HERE, 'ko_help.json'), encoding='utf-8'))
    for lv, entries in help_tr.items():
        if lv.startswith('_'): continue
        png_path = os.path.join(HERE, '..', 'media', 'levels', lv + '.png')
        cid, xml = level_xml[lv]
        img, new_xml = helpoverlay.patch_level(xml, Image.open(backup(png_path)).convert('RGBA'), lv, entries, KO_FONT)
        img.save(png_path, optimize=True)
        new_fnt[cid] = new_xml.encode('utf-8')
    print(f'도움말 오버레이 {len(help_tr) - 1}개 레벨 교체')

    for k in fnt_xml:
        x, g = build_font(fnt_xml[k][1], fnt_png[k][1], extra)
        new_fnt[fnt_xml[k][0]] = x; new_png[fnt_png[k][0]] = g
        print(f'Phaeton{k}: 글리프 {x.count(b"<char ")}개, 텍스처 {len(g)//1024}KB')

    out = bytearray(body[:pos])
    for code, s, p, ln in tags:
        data = body[p:p+ln]
        cid = struct.unpack('<H', data[:2])[0] if ln >= 2 else None
        if code == 82:
            e = data.index(b'\0', 4)
            data = data[:e+1] + patch_abc(data[e+1:], tr)
            out += write_tag(code, data, True)
        elif code == 87 and cid in new_fnt:
            out += write_tag(code, data[:6] + new_fnt[cid], True)
        elif code == 21 and cid in new_png:
            out += write_tag(code, data[:2] + new_png[cid], True)
        elif code == 36 and cid in new_lossless:
            out += write_tag(code, new_lossless[cid], True)
        else:
            out += body[s:p+ln]
    write_swf(DST, ver, bytes(out), 'CWS')
    print('완료:', os.path.abspath(DST), f'{len(tr)}개 문장 번역, 한글 글자 {len(extra)}종')


if __name__ == '__main__':
    main()
