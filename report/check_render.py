#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Проверка отрендеренных страниц отчета.

Проверяется:
  * отсутствие пустых и почти пустых страниц;
  * отсутствие страниц с «обрезанным» контентом;
  * наличие диаграмм на страницах приложений и достаточный размер;
  * соответствие номеров страниц в оглавлении фактическим.

Запуск: python3 report/check_render.py <report.txt> <каталог с page-N.png>
"""
import glob
import os
import re
import sys

from PIL import Image

problems = []


def page_geometry(path):
    im = Image.open(path).convert("L")
    W, H = im.size
    px = im.load()
    lim = int(H * 0.92)          # исключаем зону колонтитула
    rows = [sum(1 for x in range(0, W, 2) if px[x, y] < 200) for y in range(lim)]
    nz = [y for y, c in enumerate(rows) if c >= 3]
    if not nz:
        return W, H, 0.0, None
    return W, H, (nz[-1] - nz[0]) / lim, (nz[0], nz[-1])


def main():
    txt_path, outdir = sys.argv[1], sys.argv[2]
    pages_txt = open(txt_path, encoding="utf-8").read().split("\f")
    files = sorted(glob.glob(os.path.join(outdir, "page-*.png")),
                   key=lambda f: int(re.search(r"page-(\d+)", f).group(1)))
    print(f"1. Отрендеровано страниц: {len(files)}")

    print("2. Заполнение страниц")
    for i, f in enumerate(files, 1):
        W, H, fill, span = page_geometry(f)
        if span is None:
            problems.append(f"страница {i}: нет содержимого")
            print(f"   стр. {i}: ПУСТАЯ")
            continue
        # считаем содержательные текстовые строки страницы: короткий
        # раздел (например, список источников) занимает меньше половины
        # листа, но не является «случайно почти пустой» страницей
        page_lines = 0
        if i <= len(pages_txt):
            page_lines = len([ln for ln in pages_txt[i - 1].split("\n")
                              if ln.strip()])
        mark = ""
        if fill < 0.45 and page_lines < 5:
            mark = "  <-- мало содержимого"
            problems.append(f"страница {i}: заполнение {fill * 100:.0f}%, "
                            f"строк {page_lines}")
        print(f"   стр. {i}: {W}x{H}, заполнение {fill * 100:5.1f}%{mark}")

    print("3. Диаграммы на страницах приложений")
    for i, f in enumerate(files, 1):
        W, H, fill, span = page_geometry(f)
        if span is None:
            continue
        # страница-рисунок: почти вся полоса занята плотной графикой
        if H > W and fill > 0.85 and W > 1200:
            continue
        if W > H and fill > 0.85:
            im = Image.open(f).convert("L")
            px = im.load()
            dense = sum(1 for y in range(0, H, 4) for x in range(0, W, 4)
                        if px[x, y] < 200)
            tot = (H // 4 + 1) * (W // 4 + 1)
            if dense / tot > 0.05:
                print(f"   стр. {i}: диаграмма занимает "
                      f"{dense / tot * 100:.1f}% площади")

    print("4. Номера страниц в оглавлении")
    toc = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "toc_pages.json"), encoding="utf-8").read()
    import json
    entries = json.loads(toc)
    bad = 0
    # страница содержания содержит те же заголовки, что и текст: исключаем её
    toc_pages = {i for i, p in enumerate(pages_txt, 1) if "СОДЕРЖАНИЕ" in p}
    for title, page, _ in entries:
        found = None
        for i, p in enumerate(pages_txt, 1):
            if i in toc_pages:
                continue
            for line in p.split("\n"):
                s = line.strip()
                if s.startswith(title) and len(s) < len(title) + 40:
                    found = i
                    break
            if found:
                break
        ok = found == page
        if not ok:
            bad += 1
            problems.append(f"оглавление: «{title}» указано на стр. {page}, "
                            f"фактически {found}")
        print(f"   {'OK ' if ok else 'НЕ '} {title}: {page} / {found}")
    if bad:
        print(f"   расхождений: {bad}")

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
