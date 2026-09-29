#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Определяет реальные номера страниц разделов отчета по тексту PDF
и записывает их в report/toc_pages.json для следующей сборки DOCX."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SECTIONS = [
    ("1 Цель работы", 1),
    ("2 Постановка задачи", 1),
    ("3 Анализ предметной области", 1),
    ("4 Проектирование модели в 3NF", 1),
    ("5 Реализация 3NF в PostgreSQL", 1),
    ("6 Проектирование модели Data Vault", 1),
    ("7 Реализация Data Vault в PostgreSQL", 1),
    ("8 Проверка работы", 1),
    ("9 Сравнение подходов", 1),
    ("10 Заключение", 1),
    ("Список использованных источников", 1),
    ("Приложение А. Диаграмма модели 3NF", 1),
    ("Приложение Б. Диаграмма модели Data Vault", 1),
]


def main():
    text = open(sys.argv[1], encoding="utf-8").read()
    pages = text.split("\f")
    out = []
    for title, level in SECTIONS:
        page = None
        for i, p in enumerate(pages, 1):
            for line in p.split("\n"):
                s = line.strip()
                if s.startswith(title) and len(s) < len(title) + 40:
                    page = i
                    break
            if page:
                break
        out.append([title, page or 1, level])
    path = os.path.join(HERE, "toc_pages.json")
    json.dump(out, open(path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    for t, p, _ in out:
        print(f"   стр. {p:>3}  {t}")


if __name__ == "__main__":
    main()
