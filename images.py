"""이미지에 그려진 영어 글자를 한글로 다시 그린다."""
import io
from PIL import Image, ImageDraw, ImageFilter, ImageFont

INK = (0, 0, 0, 255)


def _render(text, font_path, box_w, box_h, min_squeeze=0.75):
    """text(여러 줄 가능)를 box 안에 맞춘 RGBA 이미지로 만든다.
    높이를 먼저 맞추고, 폭이 넘치면 가로로 min_squeeze까지 눌렀다가 그래도 넘치면 크기를 줄인다."""
    lines = text.split('\n')
    big = 120
    f = ImageFont.truetype(font_path, big)
    asc, desc = f.getmetrics()
    lh = int((asc + desc) * 1.05)
    widths = [f.getlength(l) for l in lines]
    w, h = int(max(widths)) + 8, lh * len(lines)
    im = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(im)
    for i, l in enumerate(lines):
        d.text((4, i * lh), l, font=f, fill=255)
    im = im.crop(im.getbbox())
    s = box_h / im.height
    sx = s
    if im.width * s > box_w:
        sx = max(box_w / im.width, s * min_squeeze)
        if im.width * sx > box_w:
            sx = box_w / im.width
            s = sx / min_squeeze
    tw, th = max(1, round(im.width * sx)), max(1, round(im.height * s))
    return im.resize((tw, th), Image.LANCZOS)


def _stamp(img, mask, x, y, color=INK):
    layer = Image.new('RGBA', mask.size, color)
    layer.putalpha(mask)
    img.alpha_composite(layer, (x, y))


def draw_text(img, box, text, font_path, align='left', color=INK):
    """box=(x0,y0,x1,y1) 안에 세로 가운데 정렬로 글자를 찍는다."""
    x0, y0, x1, y1 = box
    m = _render(text, font_path, x1 - x0, y1 - y0)
    if align == 'center':
        x = x0 + (x1 - x0 - m.width) // 2
    else:
        x = x0
    _stamp(img, m, x, y0 + (y1 - y0 - m.height) // 2, color)
    return x + m.width


def clear(img, box, fill=(0, 0, 0, 0)):
    x0, y0, x1, y1 = box
    img.paste(Image.new('RGBA', (x1 - x0, y1 - y0), fill), (x0, y0))


def patch_paper(img, box, src_dy, hard_bottom=False):
    """종이 배경 위 글자: 위/아래로 src_dy 떨어진 깨끗한 종이를 복사해 덮고 경계를 흐린다.
    hard_bottom이면 아래 경계(스프라이트 끝)는 흐리지 않고 끝까지 덮는다."""
    x0, y0, x1, y1 = box
    patch = img.crop((x0, y0 + src_dy, x1, y1 + src_dy))
    m = Image.new('L', patch.size, 0)
    ImageDraw.Draw(m).rectangle((2, 2, patch.width - 3, patch.height - 3), fill=255)
    m = m.filter(ImageFilter.GaussianBlur(2))
    if hard_bottom:
        ImageDraw.Draw(m).rectangle((6, patch.height // 2, patch.width - 7, patch.height), fill=255)
    img.paste(patch, (x0, y0), m)


# 아틀라스 좌표(intro.png)의 스프라이트별 작업: (지울 영역, 그릴 영역, 문구)
ATLAS = [
    # 음성 모드 켜짐/꺼짐: 체크박스 오른쪽 글자
    ((621 + 178, 95 + 36, 621 + 304, 95 + 74), (621 + 180, 95 + 41, 621 + 300, 95 + 70), '음성 모드'),
    ((503 + 166, 312 + 31, 503 + 290, 312 + 62), (503 + 169, 312 + 35, 503 + 287, 312 + 59), '음성 모드'),
    # 마이크 안내문 (스프라이트 전체가 글자)
    ((795, 432, 795 + 231, 432 + 50), (795 + 2, 432 + 3, 795 + 229, 432 + 48), '참고: 일부 기기에는\n마이크가 없을 수 있습니다'),
    # Click for help (위쪽 화살표는 유지)
    ((846, 484 + 62, 846 + 160, 484 + 98), (846 + 10, 484 + 66, 846 + 158, 484 + 94), '눌러서 도움말'),
    # 타이틀 부제
    ((2, 982, 2 + 334, 982 + 27), (2 + 2, 982 + 1, 2 + 332, 982 + 26), '터치와 외침의 게임'),
]
# 상점 항목: 오른쪽 '$'는 남기고 글자+점선만 교체 (배경은 거의 투명한 흰색)
SHOP = [
    ((2 + 98, 527 + 26, 2 + 393, 527 + 72), '광고 제거'),
    ((2 + 98, 280 + 48, 2 + 393, 280 + 94), '모든 레벨 잠금 해제'),
    ((2 + 98, 424 + 26, 2 + 393, 424 + 72), '폭탄 무제한'),
]
THE_END = (795 + 80, 312 + 76, 795 + 220, 312 + 118)


def patch_atlas(png_bytes, font_path):
    img = Image.open(io.BytesIO(png_bytes)).convert('RGBA')
    for clr, box, text in ATLAS:
        clear(img, clr)
        draw_text(img, box, text, font_path, align='center' if '\n' in text else 'left')
    shop_bg = img.getpixel((2 + 5, 527 + 5))
    for (x0, y0, x1, y1), text in SHOP:
        clear(img, (x0, y0, x1, y1), shop_bg)
        end = draw_text(img, (x0 + 3, y0 + 8, x1 - 10, y1 - 6), text, font_path)
        dot = (y1 - 9)
        for dx in range(end + 6, x1 - 4, 9):
            ImageDraw.Draw(img).ellipse((dx, dot, dx + 3, dot + 3), fill=INK)
    patch_paper(img, THE_END, -42, hard_bottom=True)
    draw_text(img, (795 + 87, 312 + 78, 795 + 210, 312 + 114), '끝', font_path,
              align='center', color=(60, 60, 60, 255))
    buf = io.BytesIO()
    img.save(buf, 'PNG', optimize=True)
    return buf.getvalue()


LOADING_TEXT = [
    # (지울 영역, 그릴 영역, 원문 줄 수, 글자 높이, 정렬, 문구)
    ((0, 290, 1566, 645), (14, 302, 1554, 621), 4, 40, 'left',
     '1905년, 빌뉴스. 비행선과 열기구, 증기 자동차가 누비는\n'
     '자유 도시. 연금술사와 기계공들은 놀라운 기계와\n'
     '오토마톤을 움직인다. 강대한 이웃 나라들은\n'
     '이 자유 도시의 혁신을 두려워한다.'),
    ((0, 755, 560, 850), (16, 772, 400, 828), 1, 38, 'left', '불러오는 중...'),
    ((1040, 755, 1436, 850), (900, 779, 1429, 825), 1, 38, 'right', '눌러서 일시정지'),
]


def patch_loading(argb, size, font_path):
    """로딩 화면 비트맵(DefineBitsLossless2, ARGB)의 소개문을 바꾼다."""
    import helpoverlay
    img = Image.frombytes('RGBA', size, argb, 'raw', 'ARGB')
    for clr, box, n, gh, align, text in LOADING_TEXT:
        clear(img, clr)
        helpoverlay.draw_lines(img, box, n, text, font_path, glyph_h=gh, align=align)
    r, g, b, a = img.split()
    return Image.merge('RGBA', (a, r, g, b)).tobytes()   # PIL에는 ARGB 패커가 없어 채널 순서를 직접 바꾼다


CASE_NO = (80, 72, 228, 118)


def patch_intro_jpg(src, dst, font_path):
    img = Image.open(src).convert('RGBA')
    patch_paper(img, CASE_NO, 46)
    draw_text(img, (88, 82, 208, 110), '사건 번호:', font_path,
              color=(38, 34, 32, 255))
    img.convert('RGB').save(dst, 'JPEG', quality=92)
