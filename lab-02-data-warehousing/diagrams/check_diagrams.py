#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Автоматическая проверка даталогических диаграмм.

Проверяется:
  * отсутствие пересечений рамок таблиц;
  * отсутствие выхода таблиц и подписей за границы холста;
  * отсутствие наложения текста на рамки таблиц;
  * отсутствие прохождения линий связи сквозь рамки таблиц;
  * достаточное заполнение холста (нет огромного пустого пространства).

Запуск:  python3 check_diagrams.py
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("md", os.path.join(HERE, "make_diagrams.py"))
md = importlib.util.module_from_spec(spec)
spec.loader.exec_module(md)

problems = []


def rects_overlap(a, b, pad=0.0):
    return (a[0] - pad < b[2] and b[0] - pad < a[2] and
            a[1] - pad < b[3] and b[1] - pad < a[3])


def seg_rect(p1, p2, r, pad=4.0):
    rx1, ry1, rx2, ry2 = r[0] - pad, r[1] - pad, r[2] + pad, r[3] + pad
    sx1, sx2 = min(p1[0], p2[0]), max(p1[0], p2[0])
    sy1, sy2 = min(p1[1], p2[1]), max(p1[1], p2[1])
    return sx2 > rx1 and sx1 < rx2 and sy2 > ry1 and sy1 < ry2


def check(d):
    name, W, H = d["name"], d["w"], d["h"]
    T = d["tables"]
    print("=" * 74)
    print(f"Диаграмма «{name}»: холст {W} x {H}, соотношение {W / H:.2f}")
    print("=" * 74)

    items = list(T.items())
    rects = {n: t.rect() for n, t in items}

    # 1. Пересечения рамок таблиц
    ov = [(items[i][0], items[j][0])
          for i in range(len(items)) for j in range(i + 1, len(items))
          if rects_overlap(rects[items[i][0]], rects[items[j][0]], pad=-1)]
    print("1. Пересечения таблиц:", ov if ov else "нет")
    problems.extend(("пересечение таблиц", x) for x in ov)

    # 2. Границы холста
    out = [n for n, t in items
           if t.x < 2 or t.y < 2 or t.x + t.w > W - 2 or t.y + t.h > H - 2]
    print("2. Выход за границы холста:", out if out else "нет")
    problems.extend(("выход за холст", x) for x in out)

    # 3. Линии связи сквозь таблицы
    bad = []
    for a, sa, b, sb, _, _ in d["edges"]:
        obs = [t.rect() for k, t in items if k not in (a, b)]
        pts, _, _ = md.route(T[a], sa, T[b], sb, obs, d["x_chan"], d["y_chan"])
        for i in range(len(pts) - 1):
            for (n, t) in items:
                if n in (a, b):
                    continue
                if seg_rect(pts[i], pts[i + 1], t.rect()):
                    bad.append((a, b, n))
    print("3. Линии связи сквозь таблицы:",
          f"{len(bad)} случаев" if bad else "нет")
    for x in bad[:12]:
        print("     ", x)
    problems.extend(("линия сквозь таблицу", x) for x in bad)

    # 4. Текст за пределами холста
    over = []
    for prim in d["svg"].log:
        if prim[0] != "text":
            continue
        _, x, y, s, size, *_ = prim
        w = md.tw(s, md.F_MONO if prim[8] else (md.F_BOLD if prim[6] else md.F_REG), size)
        if prim[9] == "middle":
            x -= w / 2
        if x < 0 or x + w > W or y < 0 or y > H:
            over.append(s[:40])
    print("4. Текст за границами холста:", over if over else "нет")
    problems.extend(("текст за холстом", x) for x in over)

    # 5. Заполнение холста
    minx = min(t.x for _, t in items)
    maxx = max(t.x + t.w for _, t in items)
    miny = min(t.y for _, t in items)
    maxy = max(t.y + t.h for _, t in items)
    fill = ((maxx - minx) * (maxy - miny)) / (W * H)
    print(f"5. Заполнение холста рамками таблиц: {fill * 100:.1f}%")
    if fill < 0.55:
        problems.append(("мало заполнения", f"{fill * 100:.1f}%"))

    # 6. Ширина строк внутри рамки
    narrow = []
    for n, t in items:
        for k, a, desc in t.rows:
            need = t.key_col + 14 + md.tw(a, md.F_MONO, t.s_row)
            if desc and t.show_types:
                need += 16 + md.tw(desc, md.F_ITAL, t.s_desc)
            if need + 10 > t.w:
                narrow.append((n, a))
    print("6. Строки шире рамки:", narrow if narrow else "нет")
    problems.extend(("строка шире рамки", x) for x in narrow)

    # 7. Текст, попадающий на чужие рамки таблиц
    hits = []
    for prim in d["svg"].log:
        if prim[0] != "text":
            continue
        _, x, y, s, size, color, bold, italic, mono, anchor = prim
        path = md.F_MONO if mono else (md.F_BOLD if bold else (md.F_ITAL if italic else md.F_REG))
        w = md.tw(s, path, size)
        x0 = x - w / 2 if anchor == "middle" else (x - w if anchor == "end" else x)
        box = (x0, y - size, x0 + w, y + size * 0.28)
        for n, t in items:
            r = t.rect()
            # текст внутри своей таблицы допустим
            inside_own = (box[0] >= r[0] - 1 and box[2] <= r[2] + 1 and
                          box[1] >= r[1] - 1 and box[3] <= r[3] + 1)
            if inside_own:
                continue
            if rects_overlap(box, r, pad=-1):
                hits.append((s[:36], n))
    print("7. Текст на чужих рамках таблиц:", hits if hits else "нет")
    problems.extend(("текст на рамке", x) for x in hits)

    # 8. Наложение подписей кардинальности на текст заголовков
    print()


def main():
    d3 = md.render_3nf()
    d3["x_chan"], d3["y_chan"] = d3["svg"].channels
    ddv = md.render_dv()
    ddv["x_chan"], ddv["y_chan"] = ddv["svg"].channels
    check(d3)
    check(ddv)
    print("=" * 74)
    if problems:
        print(f"ИТОГ: обнаружено {len(problems)} замечаний")
        for p in problems[:20]:
            print("  -", p)
        return 1
    print("ИТОГ: замечаний нет")
    return 0


if __name__ == "__main__":
    sys.exit(main())
