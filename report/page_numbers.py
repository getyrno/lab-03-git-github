#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Определяет реальные номера страниц разделов отчёта ЛР №3 по тексту PDF
и записывает их в report/toc_pages.json для следующей сборки DOCX."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

SECTIONS = [
    ("1 Цель работы", 1),
    ("2 Постановка задачи", 1),
    ("3 Ход работы", 1),
    ("4 Проверка установленных инструментов", 1),
    ("4.1 Git", 2),
    ("4.2 GitHub и GitHub Desktop", 2),
    ("4.3 Atom", 2),
    ("5 Создание локального Git-репозитория", 1),
    ("6 Добавление исходного кода предыдущей лабораторной", 1),
    ("7 История коммитов", 1),
    ("8 Создание удалённого репозитория GitHub", 1),
    ("9 Ссылка на репозиторий", 1),
    ("10 Вывод", 1),
    ("Список использованных источников", 1),
    ("Приложение А. Скриншоты выполнения", 1),
]


def main():
    text = open(sys.argv[1], encoding="utf-8").read()
    pages = text.split("\f")
    # страница содержания не считается местом раздела: на ней перечислены
    # те же заголовки, что и в тексте
    toc_pages = {i for i, p in enumerate(pages, 1)
                 if "СОДЕРЖАНИЕ" in p}
    out = []
    for title, level in SECTIONS:
        page = None
        for i, p in enumerate(pages, 1):
            if i in toc_pages:
                continue
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
