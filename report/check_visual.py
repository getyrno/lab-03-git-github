#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Попиксельная проверка отрендеренных страниц отчета.

Проверяется то, что обычно ломается при верстке:
  * контент не выходит за пределы полосы набора (признак обрезанного текста);
  * нет строк с аномальной плотностью (наложение текста на текст);
  * номер страницы есть на всех страницах, кроме титульной;
  * нет пустых страниц;
  * диаграммы на страницах приложений не касаются краев листа.

Запуск: python3 report/check_visual.py <каталог с page-N.png>
"""
import glob
import os
import re
import sys

from PIL import Image

# поля документа в мм (совпадают с docx_helpers.set_margins)
PORTRAIT = dict(left=30, right=10, top=20, bottom=20)
LANDSCAPE = dict(left=15, right=15, top=15, bottom=15)
TOL_MM = 1.5          # допуск: рамка таблицы может заходить в поле на 1.5 мм

# Номер страницы стоит в нижнем колонтитуле: он размещен на расстоянии
# footer_distance от нижнего края листа. Ищем его как последний обособленный
# блок чернил в нижней части листа; блок должен быть узким (одно-двузначное
# число) и невысоким.
FOOTER_MAX_WIDTH = 0.18      # доля ширины страницы, допустимая для номера
FOOTER_DISTANCE_MM = 15.0    # как в docx_helpers.set_margins

problems = []


def main():
    outdir = sys.argv[1]
    files = sorted(glob.glob(os.path.join(outdir, "page-*.png")),
                   key=lambda f: int(re.search(r"page-(\d+)", f).group(1)))
    print(f"Проверено страниц: {len(files)}")

    for i, f in enumerate(files, 1):
        im = Image.open(f).convert("L")
        W, H = im.size
        px = im.load()
        landscape = W > H
        m = LANDSCAPE if landscape else PORTRAIT
        px_per_mm = W / (297.0 if landscape else 210.0)

        left_lim = int((m["left"] - TOL_MM) * px_per_mm)
        right_lim = W - int((m["right"] - TOL_MM) * px_per_mm)
        top_lim = int((m["top"] - TOL_MM) * px_per_mm)
        bottom_lim = H - int((m["bottom"] - TOL_MM) * px_per_mm)
        # полоса колонтитула совпадает с нижним полем
        footer_top = bottom_lim

        rows = [0] * H
        cols = [0] * W
        for y in range(H):
            c = 0
            for x in range(W):
                if px[x, y] < 200:
                    c += 1
                    cols[x] += 1
            rows[y] = c

        # 1. выход за пределы полосы набора.
        #    Нижняя полоса листа может содержать только номер страницы,
        #    поэтому контент там считается выходом в поле, если он шире номера.
        # нижняя граница полосы колонтитула: чуть ниже footer_distance
        zone_top = H - int((FOOTER_DISTANCE_MM + 8) * px_per_mm)
        zone_rows = [y for y in range(max(zone_top, 0), H) if rows[y] > 0]
        blocks = []
        for y in zone_rows:
            if blocks and y - blocks[-1][-1] <= 3:
                blocks[-1].append(y)
            else:
                blocks.append([y])
        footer_block = blocks[-1] if blocks else []
        footer_span = []
        if footer_block:
            xs = [x for x in range(W)
                  if any(px[x, y] < 200 for y in footer_block)]
            footer_span = (min(xs), max(xs))
        footer_width = ((footer_span[1] - footer_span[0] + 1)
                        if footer_span else 0)
        footer_is_number = (bool(footer_block) and
                            footer_width <= W * FOOTER_MAX_WIDTH and
                            len(footer_block) <= 0.03 * H)

        # текст в поле: исключаем строки, занятые номером страницы
        footer_rows = set(footer_block)
        bleed = (sum(cols[:max(left_lim, 0)]) + sum(cols[min(right_lim, W):]) +
                 sum(rows[:max(top_lim, 0)]) +
                 sum(rows[y] for y in range(min(bottom_lim, H), H)
                     if y not in footer_rows))
        if bleed:
            problems.append(f"страница {i}: контент в поле ({bleed} px)")
            print(f"   стр. {i}: ВЫХОД В ПОЛЕ ({bleed} px)")

        # 2. пустая страница
        content = [y for y, c in enumerate(rows) if c > 0]
        if not content:
            problems.append(f"страница {i}: пустая")
            print(f"   стр. {i}: ПУСТАЯ")
            continue

        # 3. колонтитул с номером страницы
        has_footer = footer_is_number and bool(footer_span)
        if i > 1 and not has_footer:
            problems.append(f"страница {i}: нет номера страницы")
            print(f"   стр. {i}: НЕТ НОМЕРА СТРАНИЦЫ")
        if i == 1 and has_footer:
            problems.append("титульная страница содержит номер")
            print("   стр. 1: номер на титульной странице")

        # 4. аномальная плотность строки (наложение)
        dense = [c for c in rows if c > W * 0.85]
        if dense:
            problems.append(f"страница {i}: {len(dense)} строк с плотностью >85%")
            print(f"   стр. {i}: возможное наложение ({len(dense)} строк)")

    # 5. диаграммы в приложениях не касаются краев
    print("Диаграммы на альбомных страницах:")
    for i, f in enumerate(files, 1):
        im = Image.open(f).convert("L")
        W, H = im.size
        if W <= H:
            continue
        px = im.load()
        edge = int(min(W, H) * 0.02)
        touch = 0
        for y in range(H):
            for x in list(range(edge)) + list(range(W - edge, W)):
                if px[x, y] < 200:
                    touch += 1
        for x in range(W):
            for y in list(range(edge)) + list(range(H - edge, H)):
                if px[x, y] < 200:
                    touch += 1
        print(f"   стр. {i}: тёмных пикселей у края листа = {touch}")
        if touch:
            problems.append(f"страница {i}: диаграмма касается края листа")

    # 6. номер страницы выровнен по центру
    print("Выравнивание номеров страниц:")
    off = []
    for i, f in enumerate(files, 1):
        if i == 1:
            continue
        im = Image.open(f).convert("L")
        W, H = im.size
        px = im.load()
        px_per_mm = W / (297.0 if W > H else 210.0)
        zone_top = H - int((FOOTER_DISTANCE_MM + 8) * px_per_mm)
        # выделяем именно нижний обособленный блок чернил (номер страницы),
        # а не любой текст в нижней зоне: тело текста может доходить близко
        # к колонтитулу и искажать центр.
        ink_rows = [y for y in range(max(zone_top, 0), H)
                    if any(px[x, y] < 200 for x in range(W))]
        blocks = []
        for y in ink_rows:
            if blocks and y - blocks[-1][-1] <= 3:
                blocks[-1].append(y)
            else:
                blocks.append([y])
        # номер страницы - нижний блок, узкий и невысокий
        num_block = None
        for b in reversed(blocks):
            xs = [x for x in range(W)
                  if any(px[x, y] < 200 for y in b)]
            width = xs[-1] - xs[0] + 1 if xs else 0
            if width <= W * FOOTER_MAX_WIDTH and len(b) <= 0.03 * H:
                num_block = (b, xs)
                break
        if num_block is None:
            continue
        _, xs = num_block
        center = (min(xs) + max(xs)) / 2
        delta = abs(center - W / 2) / W * 100
        if delta > 3:
            off.append((i, round(delta, 1)))
    print("   смещение от центра >3%:", off if off else "нет")
    problems.extend(("номер страницы не по центру", x) for x in off)

    print()
    print("=" * 70)
    if problems:
        print(f"ИТОГ: обнаружено {len(problems)} замечаний")
        for p in problems:
            print("  -", p)
        return 1
    print("ИТОГ: замечаний нет")
    return 0


if __name__ == "__main__":
    sys.exit(main())
