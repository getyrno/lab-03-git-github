#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Лабораторная работа №2. Вариант 14. Система учета в видеопрокате.
Генератор даталогических диаграмм: модель 3NF и модель Data Vault.

Диаграммы строятся программно из описания модели, приведенного ниже,
и экспортируются в SVG (векторный исходник) и PNG (растр, 3x суперсэмплинг).

Линии связи прокладываются ортогональным маршрутизатором, который
перебирает свободные каналы и выбирает кратчайший маршрут, не проходящий
сквозь рамки таблиц.

Запуск:  python3 make_diagrams.py
"""

import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

F_REG = "/System/Library/Fonts/Supplemental/Arial.ttf"
F_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
F_ITAL = "/System/Library/Fonts/Supplemental/Arial Italic.ttf"
F_MONO = "/System/Library/Fonts/Supplemental/Courier New.ttf"
F_MONOB = "/System/Library/Fonts/Supplemental/Courier New Bold.ttf"

SS = 3                 # коэффициент суперсэмплинга при отрисовке
# Итоговый растр сохраняется с увеличением OUT_SCALE: при печати диаграммы на
# листе A4 шириной ~258 мм это дает около 340 dpi, поэтому текст и линии
# остаются четкими, а не размытыми.
OUT_SCALE = 2
S_TITLE = 18           # заголовок таблицы
S_SUB = 14             # подзаголовок (HUB / LINK / SATELLITE)
S_ROW = 15             # строка атрибута
S_DESC = 12            # тип данных / пояснение
S_CARD = 13            # кардинальность
S_NOTE = 15            # примечание

ROW_H = 16
HEADER_H = 32
HEADER_H2 = 46
KEY_COL = 38           # ширина колонки метки PK / FK / UQ

INK = (26, 26, 26)
MUTED = (108, 118, 128)
SEP = (203, 211, 219)
TITLE_INK = (20, 40, 70)

PAL_ER = {
    "header": (31, 78, 121), "body": (255, 255, 255), "border": (31, 78, 121),
    "pk": (176, 42, 55), "fk": (11, 105, 88), "uq": (150, 96, 10),
    "line": (72, 86, 100),
}

PAL_DV = {
    "HUB":  {"header": (31, 78, 121), "body": (233, 241, 250), "border": (31, 78, 121)},
    "LINK": {"header": (11, 105, 88), "body": (230, 245, 240), "border": (11, 105, 88)},
    "SAT":  {"header": (150, 96, 10), "body": (254, 247, 231), "border": (150, 96, 10)},
}

_fc = {}


def fnt(path, size):
    k = (path, size)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(path, size * SS)
    return _fc[k]


def tw(s, path, size):
    return fnt(path, size).getlength(s) / SS


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ===========================================================================
# Таблица
# ===========================================================================
def wrap_name(name, limit=20):
    """Разбивает длинное имя таблицы по символу '_' на две строки,
    чтобы таблицы оставались узкими и читаемыми на печати."""
    if tw(name, F_BOLD, S_TITLE) <= limit * S_TITLE * 0.62:
        return [name]
    best = None
    for i in range(4, len(name) - 3):
        if name[i] != "_":
            continue
        a, b = name[:i], name[i + 1:]
        if best is None or abs(len(a) - len(b)) < abs(len(best[0]) - len(best[1])):
            best = (a, b)
    return [best[0], best[1]] if best else [name]


class Table:
    def __init__(self, name, subtitle, rows, kind="ER", min_w=200, show_types=True):
        self.name, self.subtitle, self.rows, self.kind = name, subtitle, rows, kind
        self.show_types = show_types
        self.name_lines = wrap_name(name)
        self.x = self.y = 0
        # метрики, при которых таблица построена: нужны для внешних проверок
        self.row_h = ROW_H
        self.key_col = KEY_COL
        self.s_row = S_ROW
        self.s_desc = S_DESC

        w = max(tw(l, F_BOLD, S_TITLE) for l in self.name_lines) + 30
        if subtitle:
            w = max(w, tw(subtitle, F_ITAL, S_SUB) + 30)
        for k, a, d in rows:
            need = KEY_COL + 14 + tw(a, F_MONO, S_ROW)
            if d and show_types:
                need += 16 + tw(d, F_ITAL, S_DESC)
            w = max(w, need + 16)
        self.w = max(min_w, w)
        self.h = self.header_h() + len(rows) * self.row_h + 10

    def header_h(self):
        base = HEADER_H2 if self.subtitle else HEADER_H
        return base + (len(self.name_lines) - 1) * (S_TITLE + 3)

    def anchor(self, side):
        cx, cy = self.x + self.w / 2, self.y + self.h / 2
        return {"l": (self.x, cy), "r": (self.x + self.w, cy),
                "t": (cx, self.y), "b": (cx, self.y + self.h)}[side]

    def rect(self):
        return (self.x, self.y, self.x + self.w, self.y + self.h)


def layout(rows, margin_x=44, margin_y=44, gap_x=34, gap_y=56, top=0):
    """Раскладка таблиц по строкам сетки (None - пустая ячейка).

    Возвращает (ширина, высота, полосы_строк, полосы_колонок),
    где полосы используются маршрутизатором связей как свободные каналы.
    """
    cols = max(len(r) for r in rows)
    col_w = [0] * cols
    for r in rows:
        for i, t in enumerate(r):
            if t is not None:
                col_w[i] = max(col_w[i], t.w)
    total_w = sum(col_w) + gap_x * (cols - 1)

    y = margin_y + top
    bands = []
    for r in rows:
        row_w = sum(col_w[i] for i in range(len(r)) if r[i] is not None) \
            + gap_x * (len(r) - 1)
        x = margin_x + (total_w - row_w) / 2
        h = 0
        for i, t in enumerate(r):
            if t is not None:
                t.x, t.y = x, y
                h = max(h, t.h)
            x += col_w[i] + gap_x
        bands.append((y, y + h))
        y += h + gap_y

    height = y - gap_y + margin_y
    width = total_w + 2 * margin_x

    col_bands = []
    x = margin_x
    for i in range(cols):
        col_bands.append((x, x + col_w[i]))
        x += col_w[i] + gap_x
    return width, height, bands, col_bands


def channel_lines(bands, cols, W, H, tables=(), extra_y=(), extra_x=()):
    """Свободные вертикальные и горизонтальные каналы для маршрутизации.

    Каналы берутся по серединам промежутков между полосами строк и колонок,
    а также по краям рамок таблиц: этого достаточно, чтобы обойти препятствия
    без пересечения рамок.
    """
    y_chan = [24] + [(bands[i][1] + bands[i + 1][0]) / 2
                     for i in range(len(bands) - 1)] + [H - 20]
    x_chan = [16, W - 16]
    for i in range(len(cols) - 1):
        x_chan.append((cols[i][1] + cols[i + 1][0]) / 2)
    for t in tables:
        x_chan += [t.x - 14, t.x + t.w + 14]
        y_chan += [t.y - 14, t.y + t.h + 14]
    x_chan += list(extra_x)
    y_chan += list(extra_y)
    return sorted(set(round(v, 1) for v in x_chan)), sorted(set(round(v, 1) for v in y_chan))


# ===========================================================================
# Холсты
# ===========================================================================
class Svg:
    def __init__(self, w, h):
        self.w, self.h, self.p = int(round(w)), int(round(h)), []
        self.log = []          # журнал примитивов для автоматической проверки

    @staticmethod
    def c(col):
        return "none" if col is None else "#%02x%02x%02x" % col

    def rect(self, x, y, w, h, fill=None, stroke=None, sw=1.5, rx=0):
        s = (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}"'
             + (f' rx="{rx}"' if rx else "") + f' fill="{self.c(fill)}"')
        if stroke:
            s += f' stroke="{self.c(stroke)}" stroke-width="{sw}"'
        self.p.append(s + "/>")
        self.log.append(("rect", x, y, w, h, fill, stroke))

    def line(self, x1, y1, x2, y2, stroke=INK, sw=1.5):
        self.p.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" '
                      f'y2="{y2:.1f}" stroke="{self.c(stroke)}" stroke-width="{sw}"/>')
        self.log.append(("line", x1, y1, x2, y2, stroke))

    def poly(self, pts, stroke=INK, sw=1.5, dash=None):
        p = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        s = (f'<polyline points="{p}" fill="none" stroke="{self.c(stroke)}" '
             f'stroke-width="{sw}"')
        if dash:
            s += f' stroke-dasharray="{dash}"'
        self.p.append(s + "/>")
        self.log.append(("poly", list(pts), stroke, dash))

    def text(self, x, y, s, size=S_ROW, color=INK, bold=False, italic=False,
             mono=False, anchor="start"):
        fam = "Courier New, monospace" if mono else "Arial, Helvetica, sans-serif"
        a = (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{fam}" '
             f'font-size="{size}" fill="{self.c(color)}"')
        if bold:
            a += ' font-weight="bold"'
        if italic:
            a += ' font-style="italic"'
        if anchor != "start":
            a += f' text-anchor="{anchor}"'
        self.p.append(a + f">{esc(s)}</text>")
        self.log.append(("text", x, y, s, size, color, bold, italic, mono, anchor))

    def save(self, path):
        head = ('<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" '
                f'height="{self.h}" viewBox="0 0 {self.w} {self.h}">\n'
                f'<rect width="{self.w}" height="{self.h}" fill="#ffffff"/>\n')
        open(path, "w", encoding="utf-8").write(head + "\n".join(self.p) + "\n</svg>\n")


class Png:
    def __init__(self, w, h):
        self.w, self.h = int(round(w)), int(round(h))
        self.img = Image.new("RGB", (self.w * SS, self.h * SS), (255, 255, 255))
        self.d = ImageDraw.Draw(self.img)

    def rect(self, x, y, w, h, fill=None, stroke=None, sw=1.5, rx=0):
        self.d.rounded_rectangle([x * SS, y * SS, (x + w) * SS, (y + h) * SS],
                                 radius=rx * SS, fill=fill, outline=stroke,
                                 width=max(1, int(round(sw * SS))))

    def line(self, x1, y1, x2, y2, stroke=INK, sw=1.5):
        self.d.line([x1 * SS, y1 * SS, x2 * SS, y2 * SS], fill=stroke,
                    width=max(1, int(round(sw * SS))))

    def poly(self, pts, stroke=INK, sw=1.5, dash=None):
        self.d.line([v * SS for p in pts for v in p], fill=stroke,
                    width=max(1, int(round(sw * SS))), joint="curve")

    def text(self, x, y, s, size=S_ROW, color=INK, bold=False, italic=False,
             mono=False, anchor="start"):
        path = F_MONO if mono else F_REG
        if mono and bold:
            path = F_MONOB
        elif bold:
            path = F_BOLD
        elif italic:
            path = F_ITAL
        f = fnt(path, size)
        px, py = x * SS, y * SS
        if anchor == "middle":
            self.d.text((px, py), s, font=f, fill=color, anchor="mm")
        elif anchor == "end":
            self.d.text((px, py), s, font=f, fill=color, anchor="rm")
        else:
            self.d.text((px, py), s, font=f, fill=color)

    def save(self, path):
        """Сохраняет PNG с разрешением, достаточным для печати.

        Изображение строится с суперсэмплингом SS и уменьшается до
        OUT_SCALE-кратного размера макета: это понижающая выборка из
        избыточной сетки, поэтому линии и мелкий текст остаются резкими.
        При печати на A4 ширина диаграммы около 258 мм, что дает ~340 dpi.
        """
        target = (self.w * OUT_SCALE, self.h * OUT_SCALE)
        self.img.resize(target, Image.LANCZOS).save(path, "PNG", optimize=True)


# ===========================================================================
# Отрисовка таблиц
# ===========================================================================
KEY_COLOR = {"PK": "pk", "FK": "fk", "UQ": "uq", "PK,FK": "pk", "PK,UQ": "pk"}


def draw_table(c, t):
    pal = PAL_ER if t.kind == "ER" else PAL_DV[t.kind]
    hh = t.header_h()
    c.rect(t.x, t.y, t.w, t.h, fill=pal["body"], stroke=pal["border"], sw=1.8, rx=10)
    c.rect(t.x, t.y, t.w, hh, fill=pal["header"], stroke=pal["border"], sw=1.8, rx=10)
    c.rect(t.x, t.y + hh - 12, t.w, 12, fill=pal["header"], stroke=None, rx=0)

    if t.subtitle:
        c.text(t.x + 15, t.y + 26, t.subtitle, size=S_SUB, color=(220, 231, 243),
               italic=True)
        ny = t.y + 48
    else:
        ny = t.y + 28
    for line in t.name_lines:
        c.text(t.x + 15, ny, line, size=S_TITLE, color=(255, 255, 255), bold=True)
        ny += S_TITLE + 3

    y = t.y + hh
    for key, attr, desc in t.rows:
        c.line(t.x + 2, y, t.x + t.w - 2, y, stroke=SEP, sw=1.0)
        if key:
            col = pal[KEY_COLOR.get(key, "line")] if t.kind == "ER" else (86, 96, 106)
            c.text(t.x + 13, y + 7, key, size=S_DESC, color=col, bold=True)
        c.text(t.x + KEY_COL + 14, y + 7, attr, size=S_ROW, color=INK, mono=True)
        if desc and t.show_types:
            c.text(t.x + KEY_COL + 14 + tw(attr, F_MONO, S_ROW) + 16, y + 8,
                   desc, size=S_DESC, color=MUTED, italic=True)
        y += ROW_H


# ===========================================================================
# Маршрутизация связей
# ===========================================================================
def _seg_hits_rect(p1, p2, r, pad=5):
    x1, y1 = p1
    x2, y2 = p2
    rx1, ry1, rx2, ry2 = r[0] - pad, r[1] - pad, r[2] + pad, r[3] + pad
    sx1, sx2 = min(x1, x2), max(x1, x2)
    sy1, sy2 = min(y1, y2), max(y1, y2)
    return sx2 > rx1 and sx1 < rx2 and sy2 > ry1 and sy1 < ry2


def _ok(pts, obstacles):
    for i in range(len(pts) - 1):
        for r in obstacles:
            if _seg_hits_rect(pts[i], pts[i + 1], r):
                return False
    return True


def _length(pts):
    return sum(abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1])
               for i in range(len(pts) - 1))


def _candidates(a, sa, b, sb, x_chan, y_chan, gap):
    """Набор ортогональных маршрутов между таблицами для пары сторон."""
    ax, ay = a.anchor(sa)
    bx, by = b.anchor(sb)
    oa = {"l": (ax - gap, ay), "r": (ax + gap, ay),
          "t": (ax, ay - gap), "b": (ax, ay + gap)}[sa]
    ob = {"l": (bx - gap, by), "r": (bx + gap, by),
          "t": (bx, by - gap), "b": (bx, by + gap)}[sb]

    cands = []
    # прямой маршрут
    if sa in "lr" and sb in "lr":
        mx = (oa[0] + ob[0]) / 2
        cands.append([(ax, ay), oa, (mx, oa[1]), (mx, ob[1]), ob, (bx, by)])
    elif sa in "tb" and sb in "tb":
        my = (oa[1] + ob[1]) / 2
        cands.append([(ax, ay), oa, (oa[0], my), (ob[0], my), ob, (bx, by)])
    elif sa in "lr":
        cands.append([(ax, ay), oa, (ob[0], oa[1]), ob, (bx, by)])
    else:
        cands.append([(ax, ay), oa, (oa[0], ob[1]), ob, (bx, by)])

    # маршруты через свободные каналы
    for yc in y_chan:
        for xc in x_chan:
            cands.append([(ax, ay), oa, (oa[0], yc), (xc, yc), (xc, ob[1]), ob,
                          (bx, by)])
            cands.append([(ax, ay), oa, (xc, oa[1]), (xc, yc), (ob[0], yc), ob,
                          (bx, by)])
    return cands


def route(a, sa, b, sb, obstacles, x_chan, y_chan, gap=22):
    """Ортогональный маршрут между таблицами a и b.

    Сначала пробуются запрошенные стороны привязки. Если ни один маршрут не
    свободен, перебираются остальные комбинации сторон: это позволяет обойти
    рамку таблицы, стоящую на пути, без ручной подгонки координат.
    Возвращает (точки, сторона_a, сторона_b).
    """
    sides = [(sa, sb)]
    for x in "lrtb":
        for y in "lrtb":
            if (x, y) not in sides:
                sides.append((x, y))

    best = None
    best_sides = (sa, sb)
    for k, (x, y) in enumerate(sides):
        for pts in _candidates(a, x, b, y, x_chan, y_chan, gap):
            pts = _dedup(pts)
            if not _ok(pts, obstacles):
                continue
            # небольшой штраф за смену запрошенной стороны: сначала пробуем
            # исходную привязку, затем альтернативы
            score = _length(pts) + k * 25
            if best is None or score < best - 0.5:
                best = score
                best_sides = (x, y)
                best_pts = pts
    if best is None:
        return [(a.anchor(sa)), (a.anchor(sa))], sa, sb
    return best_pts, best_sides[0], best_sides[1]


def _dedup(pts):
    out = [pts[0]]
    for p in pts[1:]:
        if abs(p[0] - out[-1][0]) > 0.6 or abs(p[1] - out[-1][1]) > 0.6:
            out.append(p)
    return out


def label_box(x, y, txt, anchor="middle"):
    w = tw(txt, F_BOLD, S_CARD)
    x0 = x - w / 2 if anchor == "middle" else x
    return (x0, y - S_CARD, x0 + w, y + S_CARD * 0.3)


def place_label(c, anchor_pt, stub_pt, side, txt, color, table_rects, bounds):
    """Размещает подпись кардинальности так, чтобы она не попадала на рамки
    таблиц и не выходила за границы холста.

    Сначала перебираются точки вдоль выводного отрезка, затем - окрестность
    точки привязки. Первая свободная позиция используется.
    """
    xmin, ymin, xmax, ymax = bounds
    ax, ay = anchor_pt
    sx, sy = stub_pt
    offsets = [(0, -S_CARD * 1.1), (0, S_CARD * 1.2),
               (S_CARD * 1.5, 0), (-S_CARD * 1.5, 0),
               (S_CARD * 1.5, -S_CARD * 1.1), (-S_CARD * 1.5, -S_CARD * 1.1),
               (S_CARD * 1.5, S_CARD * 1.2), (-S_CARD * 1.5, S_CARD * 1.2)]

    def fits(lx, ly):
        box = label_box(lx, ly, txt)
        if box[0] < xmin + 1 or box[2] > xmax - 1:
            return False
        if box[1] < ymin + 1 or box[3] > ymax - 1:
            return False
        # подпись не должна даже касаться рамки таблицы
        return not any(rects_overlap(box, r, pad=2.5) for r in table_rects)

    # точки вдоль выводного отрезка, включая продолжение за его конец:
    # это дает свободные места, если сам отрезок проходит вдоль рамки
    candidates = []
    for k in (0.75, 0.9, 1.0, 1.15, 1.3, 0.6, 0.45):
        candidates.append((ax + (sx - ax) * k, ay + (sy - ay) * k))
    candidates.append((ax, ay))
    for cx, cy in candidates:
        for dx, dy in offsets:
            if fits(cx + dx, cy + dy):
                c.text(cx + dx, cy + dy, txt, size=S_CARD, color=color,
                       bold=True, anchor="middle")
                return
    # последний вариант: сдвиг в сторону от таблицы с удержанием в холсте
    dx = {"l": -S_CARD, "r": S_CARD, "t": 0, "b": 0}[side]
    dy = {"l": -S_CARD, "r": -S_CARD, "t": -S_CARD, "b": S_CARD * 1.5}[side]
    w = tw(txt, F_BOLD, S_CARD)
    x = min(max(ax + dx, xmin + w / 2 + 2), xmax - w / 2 - 2)
    y = min(max(ay + dy, ymin + S_CARD), ymax - 2)
    c.text(x, y, txt, size=S_CARD, color=color, bold=True, anchor="middle")


def rects_overlap(a, b, pad=1.0):
    return (a[0] - pad < b[2] and b[0] - pad < a[2] and
            a[1] - pad < b[3] and b[1] - pad < a[3])


def draw_edge(c, a, sa, b, sb, color, card_a="1", card_b="N", dash=None, sw=1.8,
              obstacles=(), x_chan=(), y_chan=(), bounds=None, table_rects=()):
    pts, sa, sb = route(a, sa, b, sb, obstacles, x_chan, y_chan)
    c.poly(pts, stroke=color, sw=sw, dash=dash)

    xmin, ymin, xmax, ymax = bounds or (0, 0, 10 ** 6, 10 ** 6)
    rects = list(table_rects)

    place_label(c, pts[0], pts[1], sa, card_a, color, rects,
                (xmin, ymin, xmax, ymax))
    place_label(c, pts[-1], pts[-2], sb, card_b, color, rects,
                (xmin, ymin, xmax, ymax))
    return pts


# ===========================================================================
# МОДЕЛЬ 3NF
# ===========================================================================
def tables_3nf():
    T = {}
    T["tariff"] = Table("tariff", "Тарифы (прайс-лист)", [
        ("PK", "tariff_id", "int"), ("UQ", "code", "varchar"),
        ("", "name", "varchar"), ("", "daily_rate", "numeric"),
        ("", "max_rental_days", "smallint"), ("", "late_fee_per_day", "numeric"),
        ("", "valid_from", "date"), ("", "valid_to", "date")])

    T["genre"] = Table("genre", "Жанры", [
        ("PK", "genre_id", "int"), ("UQ", "code", "varchar"),
        ("", "name", "varchar"), ("", "description", "varchar")])

    T["film"] = Table("film", "Каталог фильмов", [
        ("PK", "film_id", "int"), ("UQ", "catalog_number", "varchar"),
        ("", "title", "varchar"), ("", "original_title", "varchar"),
        ("", "release_year", "smallint"), ("", "duration_min", "smallint"),
        ("", "age_rating", "varchar"), ("", "media_type", "varchar"),
        ("FK", "tariff_id", "int"), ("", "added_on", "date")])

    T["film_genre"] = Table("film_genre", "Фильм - жанр (M:N)", [
        ("PK,FK", "film_id", "int"), ("PK,FK", "genre_id", "int"),
        ("", "is_primary", "bool")])

    T["video_copy"] = Table("video_copy", "Физические экземпляры", [
        ("PK", "copy_id", "int"), ("FK", "film_id", "int"),
        ("UQ", "inventory_code", "varchar"), ("", "acquisition_date", "date"),
        ("", "purchase_price", "numeric"), ("", "condition", "varchar"),
        ("", "storage_location", "varchar")])

    T["rental"] = Table("rental", "Операции проката", [
        ("PK", "rental_id", "int"), ("UQ", "rental_number", "varchar"),
        ("FK", "customer_id", "int"), ("FK", "employee_id", "int"),
        ("", "issue_date", "date"), ("", "planned_return_date", "date"),
        ("", "actual_return_date", "date"), ("", "deposit_amount", "numeric"),
        ("", "status", "varchar"), ("", "note", "varchar")])

    T["rental_item"] = Table("rental_item", "Позиции проката", [
        ("PK", "rental_item_id", "int"), ("FK", "rental_id", "int"),
        ("FK", "copy_id", "int"), ("", "daily_rate", "numeric"),
        ("", "status", "varchar"), ("", "actual_return_date", "date"),
        ("", "condition_on_return", "varchar")])

    T["payment"] = Table("payment", "Платежи", [
        ("PK", "payment_id", "int"), ("UQ", "payment_number", "varchar"),
        ("FK", "rental_id", "int"), ("", "payment_date", "timestamp"),
        ("", "amount", "numeric"), ("", "method", "varchar"),
        ("", "payment_type", "varchar")])

    T["customer"] = Table("customer", "Клиенты", [
        ("PK", "customer_id", "int"), ("UQ", "card_number", "varchar"),
        ("", "last_name", "varchar"), ("", "first_name", "varchar"),
        ("", "middle_name", "varchar"), ("UQ", "phone", "varchar"),
        ("", "email", "varchar"), ("", "birth_date", "date"),
        ("", "registration_date", "date"), ("", "status", "varchar")])

    T["employee"] = Table("employee", "Сотрудники", [
        ("PK", "employee_id", "int"), ("UQ", "personnel_number", "varchar"),
        ("", "last_name", "varchar"), ("", "first_name", "varchar"),
        ("", "middle_name", "varchar"), ("", "position", "varchar"),
        ("", "phone", "varchar"), ("", "hire_date", "date"),
        ("", "dismissal_date", "date"), ("", "status", "varchar")])
    return T


def render_3nf():
    T = tables_3nf()
    rows = [
        [T["genre"], T["film"], T["film_genre"], T["tariff"]],
        [T["customer"], T["employee"], T["video_copy"], T["payment"]],
        [T["rental"], T["rental_item"], None, None],
    ]
    W, H, bands, cols = layout(rows, margin_x=12, margin_y=10, gap_x=20, gap_y=30, top=74)
    x_chan, y_chan = channel_lines(bands, cols, W, H, tables=T.values())

    svg, png = Svg(W, H), Png(W, H)
    svg.channels = (x_chan, y_chan)
    title = "Даталогическая модель предметной области «Система учета в видеопрокате» в 3NF"
    for c in (svg, png):
        c.text(20, 32, title, size=21, color=TITLE_INK, bold=True)
        c.text(20, 56, "PK - первичный ключ;  FK - внешний ключ;  UQ - уникальное "
                       "ограничение;  1 : N - кардинальность связи",
               size=13, color=MUTED)
        for t in T.values():
            draw_table(c, t)

    edges = [
        ("film", "r", "film_genre", "l", "1", "N"),
        ("genre", "b", "film_genre", "b", "1", "N"),
        ("tariff", "b", "payment", "t", "1", "N"),
        ("video_copy", "b", "rental_item", "t", "1", "N"),
        ("customer", "b", "rental", "b", "1", "N"),
        ("employee", "t", "rental", "b", "1", "N"),
        ("film", "l", "video_copy", "l", "1", "N"),
        ("rental", "r", "rental_item", "l", "1", "N"),
        ("tariff", "b", "payment", "t", "1", "N"),
        ("rental_item", "r", "payment", "l", "1", "N"),
    ]
    for c in (svg, png):
        for a, sa, b, sb, ca, cb in edges:
            obstacles = [t.rect() for k, t in T.items() if k not in (a, b)]
            draw_edge(c, T[a], sa, T[b], sb, PAL_ER["line"], ca, cb,
                      obstacles=obstacles, x_chan=x_chan, y_chan=y_chan, sw=1.7,
                      bounds=(0, 0, W, H),
                      table_rects=[t.rect() for t in T.values()])

    svg.save(os.path.join(HERE, "3nf_model.svg"))
    png.save(os.path.join(HERE, "3nf_model.png"))
    print(f"3NF: {int(W)} x {int(H)}  (соотношение {W / H:.2f})")
    return {"name": "3NF", "w": int(W), "h": int(H), "tables": T,
            "edges": edges, "svg": svg}


# ===========================================================================
# МОДЕЛЬ DATA VAULT
# ===========================================================================
def tables_dv():
    T = {}
    hubs = [
        ("hub_customer",   "customer_hk",   "card_number"),
        ("hub_employee",   "employee_hk",   "personnel_number"),
        ("hub_film",       "film_hk",       "catalog_number"),
        ("hub_video_copy", "copy_hk",       "inventory_code"),
        ("hub_rental",     "rental_hk",     "rental_number"),
        ("hub_payment",    "payment_hk",    "payment_number"),
        ("hub_genre",      "genre_hk",      "genre_code"),
        ("hub_tariff",     "tariff_hk",     "tariff_code"),
    ]
    for name, hk, bk in hubs:
        T[name] = Table(name, "HUB", [
            ("PK", hk, "char(32)"), ("UQ", bk, "бизнес-ключ"),
            ("", "load_dts", "timestamp"), ("", "record_source", "varchar(50)")],
            kind="HUB", show_types=False)

    links = [
        ("link_film_copy",       "film_copy_hk",       "film_hk",   "copy_hk"),
        ("link_film_genre",      "film_genre_hk",      "film_hk",   "genre_hk"),
        ("link_film_tariff",     "film_tariff_hk",     "film_hk",   "tariff_hk"),
        ("link_rental_customer", "rental_customer_hk", "rental_hk", "customer_hk"),
        ("link_rental_employee", "rental_employee_hk", "rental_hk", "employee_hk"),
        ("link_rental_copy",     "rental_copy_hk",     "rental_hk", "copy_hk"),
        ("link_rental_payment",  "rental_payment_hk",  "rental_hk", "payment_hk"),
    ]
    for name, lk, h1, h2 in links:
        T[name] = Table(name, "LINK", [
            ("PK", lk, "char(32)"), ("FK", h1, "char(32)"), ("FK", h2, "char(32)"),
            ("", "load_dts", "timestamp"), ("", "record_source", "varchar(50)")],
            kind="LINK", show_types=False)

    sats = [
        ("sat_customer_details",       "customer_hk",    "ФИО, дата рождения"),
        ("sat_customer_contact",       "customer_hk",    "контакты, статус"),
        ("sat_employee_details",       "employee_hk",    "должность, даты, статус"),
        ("sat_film_details",           "film_hk",        "карточка фильма"),
        ("sat_video_copy_acquisition", "copy_hk",        "поступление, цена"),
        ("sat_video_copy_details",     "copy_hk",        "состояние, место"),
        ("sat_genre_details",          "genre_hk",       "название, описание"),
        ("sat_tariff_details",         "tariff_hk",      "условия тарифа"),
        ("sat_rental_details",         "rental_hk",      "сроки, статус, залог"),
        ("sat_rental_item_details",    "rental_copy_hk", "цена, статус позиции"),
        ("sat_payment_details",        "payment_hk",     "сумма, способ, тип"),
        ("sat_film_genre_details",     "film_genre_hk",  "основной жанр"),
    ]
    for name, pk, desc in sats:
        T[name] = Table(name, "SATELLITE", [
            ("PK,FK", pk, "char(32)"), ("PK", "load_dts", "timestamp"),
            ("", "hashdiff", "char(32)"), ("", "record_source", "varchar(50)"),
            ("", "(атрибуты)", desc)], kind="SAT", show_types=False)
    return T


def render_dv():
    T = tables_dv()
    rows = [
        [T["hub_customer"], T["hub_employee"], T["hub_film"], T["hub_video_copy"]],
        [T["hub_rental"], T["hub_payment"], T["hub_genre"], T["hub_tariff"]],
        [T["link_film_copy"], T["link_film_genre"], T["link_film_tariff"],
         T["link_rental_customer"], T["link_rental_employee"], T["link_rental_copy"],
         T["link_rental_payment"]],
        [T["sat_customer_details"], T["sat_customer_contact"],
         T["sat_employee_details"], T["sat_film_details"],
         T["sat_video_copy_acquisition"], T["sat_video_copy_details"]],
        [T["sat_genre_details"], T["sat_tariff_details"], T["sat_rental_details"],
         T["sat_rental_item_details"], T["sat_payment_details"],
         T["sat_film_genre_details"]],
    ]
    W, H, bands, cols = layout(rows, margin_x=8, margin_y=6, gap_x=12, gap_y=24, top=90)
    x_chan, y_chan = channel_lines(bands, cols, W, H, tables=T.values())

    svg, png = Svg(W, H), Png(W, H)
    svg.channels = (x_chan, y_chan)
    title = ("Даталогическая модель предметной области «Система учета в видеопрокате» "
             "в нотации Data Vault")
    for c in (svg, png):
        c.text(22, 34, title, size=23, color=TITLE_INK, bold=True)
        x, y = 22, 60
        bw, bh = 26, 16
        for label, key in (("HUB - устойчивый бизнес-ключ", "HUB"),
                           ("LINK - связь между Хабами", "LINK"),
                           ("SATELLITE - историзируемые атрибуты", "SAT")):
            c.rect(x, y - 12, bw, bh, fill=PAL_DV[key]["body"],
                   stroke=PAL_DV[key]["border"], sw=1.6, rx=3)
            c.text(x + bw + 8, y + 1, label, size=14, color=INK)
            x += bw + 8 + tw(label, F_REG, 14) + 30
        c.line(x, y - 4, x + 44, y - 4, stroke=(176, 122, 30), sw=1.6)
        c.text(x + 52, y + 1, "пунктир - Спутник родителя", size=14, color=(176, 122, 30))
        for t in T.values():
            draw_table(c, t)

    hub_edges = [
        ("hub_film", "link_film_copy"), ("hub_video_copy", "link_film_copy"),
        ("hub_film", "link_film_genre"), ("hub_genre", "link_film_genre"),
        ("hub_film", "link_film_tariff"), ("hub_tariff", "link_film_tariff"),
        ("hub_rental", "link_rental_customer"), ("hub_customer", "link_rental_customer"),
        ("hub_rental", "link_rental_employee"), ("hub_employee", "link_rental_employee"),
        ("hub_rental", "link_rental_copy"), ("hub_video_copy", "link_rental_copy"),
        ("hub_rental", "link_rental_payment"), ("hub_payment", "link_rental_payment"),
    ]
    for c in (svg, png):
        for a, b in hub_edges:
            obstacles = [t.rect() for k, t in T.items() if k not in (a, b)]
            draw_edge(c, T[a], "b", T[b], "t", (62, 76, 90), "1", "N",
                      obstacles=obstacles, x_chan=x_chan, y_chan=y_chan, sw=1.6,
                      bounds=(0, 0, W, H),
                      table_rects=[t.rect() for t in T.values()])

    sat_edges = [
        ("hub_customer", "sat_customer_details"),
        ("hub_customer", "sat_customer_contact"),
        ("hub_employee", "sat_employee_details"),
        ("hub_film", "sat_film_details"),
        ("hub_video_copy", "sat_video_copy_acquisition"),
        ("hub_video_copy", "sat_video_copy_details"),
        ("hub_genre", "sat_genre_details"),
        ("hub_tariff", "sat_tariff_details"),
        ("hub_rental", "sat_rental_details"),
        ("link_rental_copy", "sat_rental_item_details"),
        ("hub_payment", "sat_payment_details"),
        ("link_film_genre", "sat_film_genre_details"),
    ]
    for c in (svg, png):
        for a, b in sat_edges:
            obstacles = [t.rect() for k, t in T.items() if k not in (a, b)]
            draw_edge(c, T[a], "b", T[b], "t", (176, 122, 30), "1", "N",
                      dash="8,6", obstacles=obstacles, x_chan=x_chan, y_chan=y_chan,
                      sw=1.6, bounds=(0, 0, W, H),
                      table_rects=[t.rect() for t in T.values()])

    svg.save(os.path.join(HERE, "data_vault_model.svg"))
    png.save(os.path.join(HERE, "data_vault_model.png"))
    print(f"Data Vault: {int(W)} x {int(H)}  (соотношение {W / H:.2f})")
    return {"name": "Data Vault", "w": int(W), "h": int(H), "tables": T,
            "edges": [(a, "b", b, "t", "1", "N") for a, b in hub_edges]
                     + [(a, "b", b, "t", "1", "N") for a, b in sat_edges],
            "svg": svg}


if __name__ == "__main__":
    render_3nf()
    render_dv()
    print("Диаграммы сохранены в", HERE)
