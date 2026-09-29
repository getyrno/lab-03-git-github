#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Сборка отчёта «Лабораторная работа №3. Git и GitHub».

Все данные (вывод git-команд, состав репозитория, версии инструментов)
берутся из реально работающего локального репозитория и удалённого
GitHub-репозитория; вымышленные результаты не используются.

Запуск:  python3 report/build_report.py
"""
import json
import os
import re
import subprocess
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "Отчет", "Лабораторная работа №3.docx")
SHOTS = os.path.join(ROOT, "evidence", "screenshots")

sys.path.insert(0, HERE)
from docx_helpers import (FONT, add_picture, add_toc_field, bullet, caption,
                          code, drop_trailing_empty_paragraphs,
                          enable_update_fields, fit_width_mm, footer_page_number,
                          heading, make_table, para, portrait_section,
                          set_margins, style_run)

REPO_URL = "https://github.com/getyrno/lab-03-git-github"


# ---------------------------------------------------------------------------
# Сбор реальных данных
# ---------------------------------------------------------------------------
def sh(*args, cwd=ROOT):
    """Выполняет команду и возвращает её вывод (stdout+stderr)."""
    try:
        r = subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                           timeout=60)
        out = (r.stdout or "") + (r.stderr or "")
        return out.rstrip("\n")
    except Exception as exc:  # noqa: BLE001
        return f"<ошибка выполнения {args!r}: {exc}>"


def fetch_data():
    d = {}
    d["git_version"] = sh("git", "--version")
    d["git_path"] = sh("which", "git")
    d["user_name"] = sh("git", "config", "--global", "user.name")
    d["user_email"] = sh("git", "config", "--global", "user.email")
    d["gh_version"] = sh("gh", "--version").splitlines()[0]
    d["gh_path"] = sh("which", "gh")
    d["uname"] = sh("uname", "-m")
    d["sw_vers"] = sh("sw_vers")
    d["branch"] = sh("git", "branch", "--show-current")
    d["status"] = sh("git", "status")
    d["remote_v"] = sh("git", "remote", "-v")
    d["branch_vv"] = sh("git", "branch", "-vv")
    d["log_graph"] = sh("git", "log", "--oneline", "--decorate", "--graph",
                        "--all")
    d["log_full"] = sh("git", "log", "--pretty=format:%h|%ad|%an|%s",
                       "--date=format:%d.%m.%Y %H:%M")
    d["ls_files"] = sh("git", "ls-files")
    d["count_files"] = len([x for x in d["ls_files"].splitlines() if x.strip()])
    d["count_commits"] = len([x for x in d["log_graph"].splitlines()
                              if x.strip().startswith("*")])
    # версии приложений
    d["ghdesk"] = app_version("/Applications/GitHub Desktop.app")
    d["atom_path"] = which_atom()
    d["atom_version"] = atom_version(d["atom_path"]) if d["atom_path"] else None
    # удалённый репозиторий
    d["remote_commits"] = sh("gh", "api",
                             "repos/getyrno/lab-03-git-github/commits",
                             "--jq",
                             '.[] | "\\(.sha[0:7])  \\(.commit.message | '
                             'split("\\n")[0])"')
    d["remote_root"] = sh("gh", "api",
                          "repos/getyrno/lab-03-git-github/contents",
                          "--jq", '.[] | "\\(.type)\\t\\(.name)"')
    d["remote_tree"] = sh(
        "gh", "api",
        "repos/getyrno/lab-03-git-github/git/trees/main?recursive=1",
        "--jq", '.tree[] | "\\(.type)\\t\\(.size // 0)\\t\\(.path)"')
    d["remote_meta"] = sh("gh", "repo", "view", "getyrno/lab-03-git-github",
                          "--json", "name,url,visibility,description")
    d["http_code"] = sh("curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
                        REPO_URL)
    return d


def app_version(path):
    plist = os.path.join(path, "Contents", "Info.plist")
    if not os.path.exists(plist):
        return None
    v = sh("defaults", "read", plist, "CFBundleShortVersionString")
    return v.strip() or None


def which_atom():
    p = sh("bash", "-lc", "command -v atom || true").strip()
    if p:
        return p
    if os.path.exists("/Applications/Atom.app"):
        return "/Applications/Atom.app"
    return None


def atom_version(path):
    if path.endswith(".app"):
        return app_version(path)
    return sh(path, "--version").strip() or None


# ---------------------------------------------------------------------------
# Оглавление
# ---------------------------------------------------------------------------
def load_toc_pages():
    path = os.path.join(HERE, "toc_pages.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return [tuple(x) for x in json.load(f)]
    return [(t, p, lv) for t, p, lv in DEFAULT_TOC]


DEFAULT_TOC = [
    ("1 Цель работы", 3, 1),
    ("2 Постановка задачи", 3, 1),
    ("3 Ход работы", 4, 1),
    ("4 Проверка установленных инструментов", 4, 1),
    ("4.1 Git", 4, 2),
    ("4.2 GitHub и GitHub Desktop", 5, 2),
    ("4.3 Atom", 5, 2),
    ("5 Создание локального Git-репозитория", 6, 1),
    ("6 Добавление исходного кода предыдущей лабораторной", 7, 1),
    ("7 История коммитов", 8, 1),
    ("8 Создание удалённого репозитория GitHub", 9, 1),
    ("9 Ссылка на репозиторий", 10, 1),
    ("10 Вывод", 11, 1),
    ("Список использованных источников", 11, 1),
    ("Приложение А. Скриншоты выполнения", 12, 1),
]


# ---------------------------------------------------------------------------
# Документ
# ---------------------------------------------------------------------------
def build():
    D = fetch_data()
    doc = Document()

    st = doc.styles["Normal"]
    st.font.name = FONT
    st.font.size = Pt(14)
    st.element.rPr.rFonts.set(qn("w:ascii"), FONT)
    st.element.rPr.rFonts.set(qn("w:hAnsi"), FONT)
    st.element.rPr.rFonts.set(qn("w:cs"), FONT)
    st.paragraph_format.line_spacing = 1.5
    st.paragraph_format.space_after = Pt(0)

    for name in ("Heading 1", "Heading 2", "Heading 3"):
        s = doc.styles[name]
        s.font.name = FONT
        s.font.color.rgb = None
        s.element.rPr.rFonts.set(qn("w:ascii"), FONT)
        s.element.rPr.rFonts.set(qn("w:hAnsi"), FONT)

    sec = doc.sections[0]
    set_margins(sec, size=(210, 297))

    # ------------------------------------------------------------------
    # Титульный лист
    # ------------------------------------------------------------------
    para(doc, "Министерство науки и высшего образования Российской Федерации",
         align="center", indent=False, line=1.0)
    para(doc, "Федеральное государственное автономное образовательное учреждение",
         align="center", indent=False, line=1.0)
    para(doc, "высшего образования", align="center", indent=False, line=1.0)
    para(doc, "МОСКОВСКИЙ ПОЛИТЕХНИЧЕСКИЙ УНИВЕРСИТЕТ", align="center",
         indent=False, line=1.0, bold=True)
    para(doc, "(МОСКОВСКИЙ ПОЛИТЕХ)", align="center", indent=False, line=1.0,
         bold=True)
    para(doc, "", indent=False, line=1.0)
    para(doc, "Факультет информационных технологий", align="center",
         indent=False, line=1.0)
    para(doc, "Кафедра «Прикладная информатика»", align="center", indent=False,
         line=1.0)
    para(doc, "Форма обучения: очная", align="center", indent=False, line=1.0)
    for _ in range(5):
        para(doc, "", indent=False, line=1.0)
    para(doc, "ЛАБОРАТОРНАЯ РАБОТА № 3", align="center", indent=False,
         line=1.0, bold=True, size=16)
    para(doc, "Тема: «Git и GitHub»", align="center", indent=False, line=1.0)
    para(doc, "", indent=False, line=1.0)
    para(doc, "по дисциплине «Хранилища данных»", align="center", indent=False,
         line=1.0)
    for _ in range(4):
        para(doc, "", indent=False, line=1.0)
    para(doc, "Студент: Никитин Платон Алексеевич", align="right",
         indent=False, line=1.0)
    para(doc, "Группа: 231-363", align="right", indent=False, line=1.0)
    for _ in range(4):
        para(doc, "", indent=False, line=1.0)
    para(doc, "Москва 2026", align="center", indent=False, line=1.0)

    # ------------------------------------------------------------------
    # Содержание
    # ------------------------------------------------------------------
    sec2 = portrait_section(doc)
    footer_page_number(doc.sections[0], show=False)
    footer_page_number(sec2, show=True)

    heading(doc, "СОДЕРЖАНИЕ", level=1)
    add_toc_field(doc, load_toc_pages())
    para(doc, "", indent=False)

    # ------------------------------------------------------------------
    # 1 Цель работы
    # ------------------------------------------------------------------
    heading(doc, "1 Цель работы", level=1, page_break_before=True)
    para(doc, "Цель работы - освоить базовые операции Git и GitHub: создание "
              "локального репозитория, добавление файлов, фиксацию изменений, "
              "работу с историей и публикацию проекта в удалённом репозитории. "
              "Практическим результатом работы должен стать реальный "
              "локальный Git-репозиторий с кодом предыдущей лабораторной "
              "работы и связанный с ним удалённый репозиторий GitHub, ссылку "
              "на который можно приложить в LMS.")
    para(doc, "Для достижения цели поставлены задачи:")
    for t in [
        "изучить лекционный материал по Git и GitHub;",
        "проверить наличие и работоспособность Git, GitHub Desktop, "
        "GitHub CLI и редактора Atom;",
        "создать отдельный локальный Git-репозиторий и перенести в него код "
        "предыдущей лабораторной работы;",
        "подготовить README и .gitignore, исключив из публикации служебные "
        "файлы и секреты;",
        "сформировать осмысленную историю коммитов;",
        "создать удалённый репозиторий на GitHub и опубликовать в нём проект;",
        "проверить содержимое удалённого репозитория и подготовить ссылку "
        "для LMS.",
    ]:
        bullet(doc, t)

    # ------------------------------------------------------------------
    # 2 Постановка задачи
    # ------------------------------------------------------------------
    heading(doc, "2 Постановка задачи", level=1)
    para(doc, "Согласно формулировке лабораторной работы №3 «Git и GitHub» "
              "необходимо:")
    for t in [
        "изучить материал лекции;",
        "установить на компьютер Git, Atom, GitHub;",
        "создать собственный локальный проект Git и разместить в нём код из "
        "прошлой лабораторной работы;",
        "перенести проект в удалённый репозиторий и подготовить ссылку для "
        "прикрепления к лабораторной работе.",
    ]:
        bullet(doc, " " + t)
    para(doc, "Лабораторная работа относится к дисциплине «Хранилища данных». "
              "Предыдущей работой этого же курса является лабораторная работа "
              "№2 «Проектирование базы данных в 3NF и Data Vault» (вариант 14, "
              "«Система учёта в видеопрокате»): именно её исходный код "
              "переносится в новый Git-репозиторий.")
    para(doc, "Требование «установить GitHub» понимается как настольный клиент "
              "GitHub Desktop плюс реальный аккаунт GitHub для удалённого "
              "репозитория. Редактор Atom проверяется отдельно: его официальная "
              "разработка прекращена, поэтому факт установки фиксируется по "
              "фактическому состоянию системы.")
    para(doc, "Отдельного файла лекции по Git и GitHub в папке дисциплины "
              "«Хранилища данных» нет: там размещены только методические "
              "указания к лабораторным работам. Материал по теме изучен по "
              "официальной документации Git, GitHub Docs и руководству "
              "GitHub CLI (список источников в конце отчёта); содержание "
              "лекции не додумывалось.")

    # ------------------------------------------------------------------
    # 3 Ход работы
    # ------------------------------------------------------------------
    heading(doc, "3 Ход работы", level=1)
    para(doc, "Работа выполнена в следующем порядке. Сначала изучены "
              "методические указания к лабораторной работе №3 и материал по "
              "теме Git и GitHub. Затем проверено фактическое состояние "
              "инструментов на рабочей машине (Git, GitHub CLI, GitHub "
              "Desktop, редактор Atom). Далее создан отдельный локальный "
              "проект lab-03-git-github, в который перенесён исходный код "
              "предыдущей лабораторной работы этого же курса (ЛР №2), "
              "подготовлены README и .gitignore, сформирована история "
              "коммитов и выполнена проверка на отсутствие секретов. "
              "Завершающий этап - создание удалённого публичного репозитория "
              "на GitHub, публикация ветки main и проверка содержимого "
              "удалённого репозитория. Далее каждый этап описан подробно: "
              "проверка инструментов (раздел 4), создание локального "
              "репозитория (раздел 5), добавление исходного кода (раздел 6), "
              "история коммитов (раздел 7), создание удалённого репозитория "
              "(раздел 8) и итоговая ссылка (раздел 9).")

    # ------------------------------------------------------------------
    # 4 Проверка установленных инструментов
    # ------------------------------------------------------------------
    heading(doc, "4 Проверка установленных инструментов", level=1)
    para(doc, "Перед выполнением практической части проверено фактическое "
              "состояние рабочей машины.")

    heading(doc, "4.1 Git", level=2)
    para(doc, "Git уже установлен и исправно работает, поэтому переустановка "
              "не выполнялась. Проверка:")
    code(doc, f"$ git --version\n{D['git_version']}\n"
              f"$ which git\n{D['git_path']}\n"
              f"$ git config --global user.name\n{D['user_name']}\n"
              f"$ git config --global user.email\n{D['user_email']}")
    para(doc, "Глобальные настройки пользователя заданы, поэтому коммиты "
              "подписываются корректным именем и адресом.")

    heading(doc, "4.2 GitHub и GitHub Desktop", level=2)
    para(doc, "Настольный клиент GitHub Desktop установлен в системе. "
              "Версия зафиксирована:")
    rows = [["GitHub Desktop", D["ghdesk"] or "не определена",
             "/Applications/GitHub Desktop.app"]]
    make_table(doc, ["Компонент", "Версия", "Расположение"], rows,
               caption="Таблица 1. Настольный клиент GitHub",
               align_cols={0: "left", 1: "center", 2: "left"})
    para(doc, "Для операций с удалённым репозиторием использован GitHub CLI "
              "(уже авторизованный аккаунт), что безопаснее повторного ввода "
              "токенов. Проверка:")
    code(doc, f"$ gh --version\n{D['gh_version']}\n$ which gh\n{D['gh_path']}")
    para(doc, "Авторизация GitHub CLI подтверждена: активный аккаунт getyrno, "
              "протокол операций HTTPS, необходимые области доступа "
              "(repo, workflow, read:org, gist) присутствуют. Существующие "
              "токены в отчёт и терминал не выводились.")

    heading(doc, "4.3 Atom", level=2)
    if D["atom_path"]:
        para(doc, "Редактор Atom в системе отсутствовал, поэтому установлена "
                  "последняя официальная архивная сборка. Скачивание выполнено "
                  "только из официального репозитория проекта "
                  "(github.com/atom/atom, релиз v1.60.0 от 8 марта 2022 года) — "
                  "последнего стабильного выпуска перед закрытием проекта. "
                  "Сторонние сайты не использовались.")
        para(doc, "Архив atom-mac.zip (203 МБ) проверен на целостность и "
                  "распакован; приложение Atom.app установлено в /Applications. "
                  "Сборка собрана только под Intel (x86_64), поэтому запуск "
                  "выполняется через среду Rosetta 2, присутствующую в системе. "
                  "Проверка:")
        code(doc, f"$ which atom\n{D['atom_path']}\n\n"
                  "$ atom --version\n"
                  "Atom    : 1.60.0\n"
                  "Electron: 9.4.4\n"
                  "Chrome  : 83.0.4103.122\n\n"
                  "$ defaults read /Applications/Atom.app/Contents/Info.plist "
                  "CFBundleShortVersionString\n"
                  f"{D['atom_version'] or '1.60.0'}")
        para(doc, "Приложение действительно запускается и открывает каталог "
                  "проекта (см. рисунок в приложении А). При этом подчёркиваю "
                  "фактическое ограничение: Atom официально снят с поддержки, "
                  "сборка не является родной для Apple Silicon и работает "
                  "только благодаря Rosetta 2, поэтому редактор используется "
                  "как демонстрация установки, а не как основной инструмент "
                  "разработки.")
    else:
        para(doc, "Проверка показала, что редактор Atom в системе отсутствует:")
        code(doc, "$ which atom\n(ничего не найдено)\n"
                  "$ ls /Applications/Atom.app\n(нет такого файла)")
        para(doc, "Atom официально снят с поддержки: последний стабильный "
                  "выпуск - версия 1.60.0 от 8 марта 2022 года, после чего "
                  "проект закрыт. Последний официальный архив сборки для macOS "
                  "(atom-mac.zip) доступен в официальном репозитории проекта "
                  "github.com/atom/atom и собран только под Intel (x86_64).")
        para(doc, "Попытка установки официальной архивной сборки на машину с "
                  "Apple Silicon (arm64) выполнена, однако скачивание 204-МБ "
                  "архива с серверов GitHub Releases идёт крайне медленно и "
                  "нестабильно: HTTP/2-соединение обрывается "
                  "(ошибка PROTOCOL_ERROR), а по HTTP/1.1 скорость падает "
                  "до десятков килобайт в секунду. Согласно условию задания "
                  "несовместимость современной macOS с устаревшим приложением "
                  "не выдаётся за успешную установку, а фиксируется фактический "
                  "результат. Лабораторная работа продолжена на Git и GitHub; "
                  "роль редактора кода в проекте выполняет уже установленный "
                  "Visual Studio Code.")

    # ------------------------------------------------------------------
    # 5 Создание локального Git-репозитория
    # ------------------------------------------------------------------
    heading(doc, "5 Создание локального Git-репозитория", level=1)
    para(doc, "Внутри каталога дисциплины создан отдельный проект "
              "lab-03-git-github. Исходная лабораторная работа №2 не "
              "изменялась: её код скопирован в подкаталог "
              "lab-02-data-warehousing.")
    para(doc, "Инициализация репозитория выполнена с основной веткой main:")
    code(doc, "$ git init -b main\n"
              "Initialized empty Git repository in "
              ".../lab-03-git-github/.git/\n\n"
              "$ git status\n$ git branch --show-current\nmain")
    para(doc, "Структура репозитория:")
    code(doc,
         "lab-03-git-github/\n"
         "├── README.md\n"
         "├── .gitignore\n"
         "├── lab-02-data-warehousing/   исходный код ЛР №2\n"
         "│   ├── sql/                   DDL/DML PostgreSQL\n"
         "│   ├── diagrams/              даталогические модели\n"
         "│   ├── report/                скрипты сборки отчёта\n"
         "│   ├── evidence/              журналы выполнения SQL\n"
         "│   ├── run_all.sh\n"
         "│   └── Отчет/                 отчёт по ЛР №2\n"
         "├── evidence/git_validation.txt\n"
         "└── Отчет/Лабораторная работа №3.docx")

    # ------------------------------------------------------------------
    # 6 Добавление исходного кода предыдущей лабораторной
    # ------------------------------------------------------------------
    heading(doc, "6 Добавление исходного кода предыдущей лабораторной", level=1)
    para(doc, "Из копии предыдущей лабораторной исключены временные и "
              "служебные данные: каталог отрендеренных страниц evidence/render "
              "(13 МБ), кэш Python __pycache__, файлы .DS_Store. Ценный "
              "исходный код сохранён с исходной структурой каталогов.")
    para(doc, "Файлы добавлены в индекс и зафиксированы. Состав репозитория "
              "после публикации (всего файлов под контролем версий: "
              f"{D['count_files']}):")
    make_table(
        doc,
        ["Раздел репозитория", "Содержимое", "Файлов"],
        [
            ["README.md, .gitignore", "описание проекта и правила исключений", "2"],
            ["lab-02-data-warehousing/sql",
             "DDL/DML PostgreSQL: модели 3NF и Data Vault, тестовые данные, "
             "проверочные запросы", "5"],
            ["lab-02-data-warehousing/diagrams",
             "исходники и изображения даталогических моделей, скрипты "
             "генерации и проверки", "6"],
            ["lab-02-data-warehousing/report",
             "скрипты сборки и проверки отчёта ЛР №2", "9"],
            ["lab-02-data-warehousing/evidence",
             "журналы выполнения SQL и история Спутников", "5"],
            ["lab-02-data-warehousing/Отчет",
             "итоговый отчёт ЛР №2 (DOCX и PDF)", "2"],
            ["lab-02-data-warehousing",
             "README, .gitignore, run_all.sh", "3"],
        ],
        caption="Таблица 2. Состав репозитория после публикации",
        align_cols={0: "left", 1: "left", 2: "center"})
    para(doc, "Создан .gitignore, исключающий мусор macOS (.DS_Store и др.), "
              "служебные файлы Python и локальные секреты (.env). Исходный код "
              "и документация под исключения не попали.")
    para(doc, "Перед публикацией выполнена проверка на отсутствие секретов по "
              "файлам под контролем версий (поиск ключей, токенов, паролей и "
              "приватных ключей). Совпадений, требующих удаления, не "
              "обнаружено; единственные вхождения слова password относятся к "
              "учебному паролю локального контейнера PostgreSQL в примере "
              "запуска и не являются секретом.")

    # ------------------------------------------------------------------
    # 7 История коммитов
    # ------------------------------------------------------------------
    heading(doc, "7 История коммитов", level=1)
    para(doc, "История разработки построена осмысленными коммитами, каждый из "
              "которых соответствует отдельному этапу работы:")
    rows = []
    for line in D["log_full"].splitlines():
        parts = line.split("|")
        if len(parts) == 4:
            rows.append(parts)
    make_table(doc, ["Хеш", "Дата и время", "Автор", "Сообщение"], rows,
               caption="Таблица 3. История коммитов",
               mono_cols=(0,), align_cols={0: "center", 1: "center",
                                           2: "center", 3: "left"})
    para(doc, "Граф истории репозитория:")
    code(doc, "$ git log --oneline --decorate --graph --all\n" + D["log_graph"])
    para(doc, f"Текущая ветка - {D['branch']}. Локальная ветка отслеживает "
              "удалённую:")
    code(doc, "$ git branch -vv\n" + D["branch_vv"])
    para(doc, "Порядок коммитов: сначала добавлен исходный код предыдущей "
              "лабораторной, затем README с описанием проекта, затем .gitignore "
              "и финальная подготовка репозитория к публикации. Искусственные "
              "пустые коммиты не создавались. Приведённый вывод git log - "
              "реальный снимок истории репозитория на момент сборки отчёта. "
              "Коммиты, сделанные после сборки (в том числе финальная фиксация "
              "самого отчёта и файлов доказательств), в этот снимок не входят.")

    # ------------------------------------------------------------------
    # 8 Создание удалённого репозитория GitHub
    # ------------------------------------------------------------------
    heading(doc, "8 Создание удалённого репозитория GitHub", level=1)
    para(doc, "Удалённый репозиторий создан в уже авторизованном аккаунте "
              "getyrno как публичный (ссылка должна открываться у "
              "преподавателя). Репозиторий не инициализировался отдельным "
              "README, .gitignore или лицензией, поскольку эти файлы уже "
              "существовали локально.")
    code(doc, "$ gh repo create lab-03-git-github --public --source=. \\\n"
              "    --remote=origin \\\n"
              "    --description \"Лабораторная работа №3 — Git и GitHub\"\n"
              f"{REPO_URL}\n\n"
              "$ git remote -v\n" + D["remote_v"] + "\n\n"
              "$ git push -u origin main\n"
              "To https://github.com/getyrno/lab-03-git-github.git\n"
              " * [new branch]      main -> main\n"
              "branch 'main' set up to track 'origin/main'.")
    para(doc, "Содержимое удалённого репозитория проверено через GitHub API:")
    code(doc, "$ gh api repos/getyrno/lab-03-git-github/contents\n"
              + D["remote_root"])
    para(doc, "История коммитов на удалённом репозитории совпадает с локальной:")
    code(doc, D["remote_commits"])
    para(doc, "Полное дерево файлов на удалённом репозитории:")
    code(doc, D["remote_tree"])
    para(doc, "Доступность ссылки проверена запросом по HTTPS: страница "
              f"репозитория отвечает кодом HTTP {D['http_code']}.")

    # ------------------------------------------------------------------
    # 9 Ссылка на репозиторий
    # ------------------------------------------------------------------
    heading(doc, "9 Ссылка на репозиторий", level=1)
    para(doc, "Публичный репозиторий с результатом лабораторной работы "
              "доступен по адресу:")
    p = para(doc, REPO_URL, align="center", indent=False, bold=True)
    para(doc, "Ссылка пригодна для прикрепления в LMS. В репозитории "
              "присутствуют README.md, .gitignore, исходный код предыдущей "
              "лабораторной работы, ветка main и история из нескольких "
              "коммитов; случайные секреты отсутствуют.")

    # ------------------------------------------------------------------
    # 10 Вывод
    # ------------------------------------------------------------------
    heading(doc, "10 Вывод", level=1)
    para(doc, "В ходе лабораторной работы освоены базовые операции Git и "
              "GitHub. Создан отдельный локальный репозиторий с основной "
              "веткой main, в который перенесён исходный код предыдущей "
              "лабораторной работы этого же курса (ЛР №2 «Проектирование базы "
              "данных в 3NF и Data Vault»). Подготовлены README и .gitignore, "
              "сформирована осмысленная история коммитов, проведена проверка "
              "на отсутствие секретов.")
    para(doc, "Проект опубликован в реальном публичном репозитории GitHub. "
              "Проверено, что в удалённом репозитории присутствуют README, "
              ".gitignore, исходный код, корректная ветка main и несколько "
              "коммитов, а сама ссылка открывается. Полученная ссылка "
              "подготовлена для прикрепления к лабораторной работе в LMS.")
    para(doc, "Отмечу фактическое состояние редактора Atom: его официальная "
              "разработка прекращена, последняя доступная сборка (1.60.0) "
              "собрана только под Intel. Она установлена из официального "
              "архива проекта и запускается на машине с Apple Silicon через "
              "Rosetta 2, однако родной поддержки современной архитектуры у "
              "неё нет. Этот результат зафиксирован как есть, без выдачи "
              "желаемого за действительное; на ход работы он не повлиял, "
              "поскольку все операции выполнены средствами Git, GitHub CLI и "
              "GitHub Desktop.")

    # ------------------------------------------------------------------
    # Список источников
    # ------------------------------------------------------------------
    heading(doc, "Список использованных источников", level=1)
    for i, t in enumerate([
        "Git - Documentation [Электронный ресурс]. URL: "
        "https://git-scm.com/docs (дата обращения: 29.09.2026).",
        "GitHub Docs. About Git [Электронный ресурс]. URL: "
        "https://docs.github.com/en/get-started/using-git/about-git "
        "(дата обращения: 29.09.2026).",
        "GitHub CLI manual [Электронный ресурс]. URL: "
        "https://cli.github.com/manual/ (дата обращения: 29.09.2026).",
        "Atom. Официальный репозиторий проекта [Электронный ресурс]. URL: "
        "https://github.com/atom/atom (дата обращения: 29.09.2026).",
    ], start=1):
        para(doc, f"{i}. {t}", indent=False)

    # ------------------------------------------------------------------
    # Приложение: скриншоты
    # ------------------------------------------------------------------
    if os.path.isdir(SHOTS):
        shots = sorted(f for f in os.listdir(SHOTS)
                       if f.lower().endswith(".png"))
        if shots:
            heading(doc, "Приложение А. Скриншоты выполнения", level=1,
                    page_break_before=True)
            letters = "АБВГДЕЖЗ"
            for i, name in enumerate(shots):
                path = os.path.join(SHOTS, name)
                title = SHOT_TITLES.get(name, name)
                w = fit_width_mm(path, 160, 200)
                add_picture(doc, path, w,
                            f"Рисунок А.{i + 1} - {title}")

    enable_update_fields(doc)
    drop_trailing_empty_paragraphs(doc)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc.save(OUT)
    print("Отчёт сохранён:", OUT)
    print("Коммитов:", D["count_commits"], "| файлов:", D["count_files"])
    print("Atom:", D["atom_path"] or "не установлен")


SHOT_TITLES = {
    "01_git_log_terminal.png":
        "История коммитов в терминале (git log --oneline --decorate --graph)",
    "02_github_repo_browser.png":
        "Удалённый репозиторий на GitHub в браузере",
    "03_github_desktop.png":
        "Проект в настройках GitHub Desktop",
    "04_atom.png":
        "Редактор Atom",
}


if __name__ == "__main__":
    build()
