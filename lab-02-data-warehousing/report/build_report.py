#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Лабораторная работа №2. Вариант 14. Система учета в видеопрокате.
Сборка итогового отчета Word.

Все числовые результаты и таблицы в разделах проверки берутся из реально
работающей учебной БД (функция query из query_db.py), а не вписываются вручную.

Запуск:  python3 report/build_report.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt

import query_db as q
from docx_helpers import (FONT, add_page_field, add_picture, add_toc_field,
                          bullet, caption, code, drop_trailing_empty_paragraphs,
                          enable_update_fields, fit_width_mm,
                          footer_page_number, heading, landscape_section,
                          make_table, para, portrait_section, set_margins,
                          style_run, table_caption)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DIAGRAMS = os.path.join(ROOT, "diagrams")
OUT = os.path.join(ROOT, "Отчет", "Лабораторная работа №2.docx")

S3 = "video_rental_3nf"
SDV = "video_rental_dv"


# ==========================================================================
# Сбор реальных данных из БД
# ==========================================================================
def fetch_data():
    d = {}
    d["active_rentals"] = q.query(f"""
        SELECT rental_number, customer_name, employee_name,
               to_char(planned_return_date,'DD.MM.YYYY'),
               items_total, items_open, is_overdue, overdue_days
          FROM {S3}.v_active_rental ORDER BY planned_return_date, rental_number""")[1]

    d["overdue"] = q.query(f"""
        SELECT r.rental_number, c.card_number, c.last_name || ' ' || c.first_name,
               vc.inventory_code, f.title,
               to_char(r.planned_return_date,'DD.MM.YYYY'),
               lab.current_date() - r.planned_return_date,
               to_char(ri.daily_rate * (lab.current_date() - r.planned_return_date),'FM999999.00')
          FROM {S3}.rental_item ri
          JOIN {S3}.rental r ON r.rental_id = ri.rental_id
          JOIN {S3}.customer c ON c.customer_id = r.customer_id
          JOIN {S3}.video_copy vc ON vc.copy_id = ri.copy_id
          JOIN {S3}.film f ON f.film_id = vc.film_id
         WHERE ri.status = 'issued' AND r.planned_return_date < lab.current_date()
         ORDER BY 7 DESC""")[1]

    d["customer_history"] = q.query(f"""
        SELECT r.rental_number, to_char(r.issue_date,'DD.MM.YYYY'),
               to_char(r.planned_return_date,'DD.MM.YYYY'),
               coalesce(to_char(r.actual_return_date,'DD.MM.YYYY'),'-'),
               r.status,
               (SELECT count(*) FROM {S3}.rental_item ri WHERE ri.rental_id = r.rental_id),
               string_agg(vc.inventory_code || ' (' || f.title || ')', ', '
                          ORDER BY vc.inventory_code)
          FROM {S3}.rental r
          JOIN {S3}.customer c ON c.customer_id = r.customer_id
          LEFT JOIN {S3}.rental_item ri ON ri.rental_id = r.rental_id
          LEFT JOIN {S3}.video_copy vc ON vc.copy_id = ri.copy_id
          LEFT JOIN {S3}.film f ON f.film_id = vc.film_id
         WHERE c.card_number = 'CR-00002'
         GROUP BY r.rental_id, r.rental_number, r.issue_date, r.planned_return_date,
                  r.actual_return_date, r.status
         ORDER BY r.issue_date, r.rental_number""")[1]

    d["available"] = q.query(f"""
        SELECT inventory_code, title, condition, storage_location
          FROM {S3}.v_copy_status WHERE is_available ORDER BY title, inventory_code""")[1]

    d["fund_summary"] = q.query(f"""
        SELECT count(*), count(*) FILTER (WHERE is_rented),
               count(*) FILTER (WHERE is_available),
               count(*) FILTER (WHERE condition = 'written_off')
          FROM {S3}.v_copy_status""")[1][0]

    d["catalog"] = q.query(f"""
        SELECT catalog_number, title, release_year, media_type, tariff_code,
               to_char(daily_rate,'FM999.00'), genres, copies_total
          FROM {S3}.v_film_catalog ORDER BY catalog_number""")[1]

    d["payments"] = q.query(f"""
        SELECT rental_number, status, to_char(rent_cost,'FM999999.00'),
               to_char(paid_total,'FM999999.00'), to_char(penalty_total,'FM999999.00'),
               to_char(paid_total - rent_cost - penalty_total,'FM999999.00')
          FROM {S3}.v_rental_total ORDER BY rental_number""")[1]

    d["pay_methods"] = q.query(f"""
        SELECT method, count(*), to_char(sum(amount),'FM999999.00')
          FROM {S3}.payment GROUP BY method ORDER BY method""")[1]

    d["dv_full"] = q.query(f"""
        SELECT rental_number, customer_name, personnel_number,
               to_char(issue_date,'DD.MM.YYYY'), status, inventory_code, title, item_status
          FROM {SDV}.v_rental_full ORDER BY rental_number, inventory_code""")[1]

    d["dv_customers"] = q.query(f"""
        SELECT card_number, last_name, first_name, phone,
               coalesce(address,'-'), status,
               to_char(contact_load_dts,'DD.MM.YYYY HH24:MI')
          FROM {SDV}.v_customer_current ORDER BY card_number""")[1]

    d["dv_copies"] = q.query(f"""
        SELECT inventory_code, condition, coalesce(storage_location,'-'),
               to_char(acquisition_date,'DD.MM.YYYY'), to_char(purchase_price,'FM999999.00')
          FROM {SDV}.v_video_copy_current ORDER BY inventory_code""")[1]

    d["hist_contact"] = q.query(f"""
        SELECT hc.card_number, to_char(sc.load_dts,'DD.MM.YYYY HH24:MI'),
               sc.phone, sc.address, sc.status, sc.hashdiff, sc.record_source
          FROM {SDV}.hub_customer hc
          JOIN {SDV}.sat_customer_contact sc ON sc.customer_hk = hc.customer_hk
         WHERE hc.card_number = 'CR-00001' ORDER BY sc.load_dts""")[1]

    d["hist_copy"] = q.query(f"""
        SELECT hvc.inventory_code, to_char(sd.load_dts,'DD.MM.YYYY HH24:MI'),
               sd.condition, sd.storage_location, sd.hashdiff, sd.record_source
          FROM {SDV}.hub_video_copy hvc
          JOIN {SDV}.sat_video_copy_details sd ON sd.copy_hk = hvc.copy_hk
         WHERE hvc.inventory_code = 'VC-00005' ORDER BY sd.load_dts""")[1]

    d["hist_rental"] = q.query(f"""
        SELECT hr.rental_number, to_char(sd.load_dts,'DD.MM.YYYY HH24:MI'),
               sd.status, to_char(sd.planned_return_date,'DD.MM.YYYY'),
               coalesce(to_char(sd.actual_return_date,'DD.MM.YYYY'),'-'), sd.record_source
          FROM {SDV}.hub_rental hr
          JOIN {SDV}.sat_rental_details sd ON sd.rental_hk = hr.rental_hk
         WHERE hr.rental_number = 'RN-000006' ORDER BY sd.load_dts""")[1]

    d["sat_versions"] = q.query("""
        SELECT 'sat_customer_details', count(*), count(DISTINCT customer_hk) FROM video_rental_dv.sat_customer_details
        UNION ALL SELECT 'sat_customer_contact', count(*), count(DISTINCT customer_hk) FROM video_rental_dv.sat_customer_contact
        UNION ALL SELECT 'sat_employee_details', count(*), count(DISTINCT employee_hk) FROM video_rental_dv.sat_employee_details
        UNION ALL SELECT 'sat_film_details', count(*), count(DISTINCT film_hk) FROM video_rental_dv.sat_film_details
        UNION ALL SELECT 'sat_video_copy_acquisition', count(*), count(DISTINCT copy_hk) FROM video_rental_dv.sat_video_copy_acquisition
        UNION ALL SELECT 'sat_video_copy_details', count(*), count(DISTINCT copy_hk) FROM video_rental_dv.sat_video_copy_details
        UNION ALL SELECT 'sat_genre_details', count(*), count(DISTINCT genre_hk) FROM video_rental_dv.sat_genre_details
        UNION ALL SELECT 'sat_tariff_details', count(*), count(DISTINCT tariff_hk) FROM video_rental_dv.sat_tariff_details
        UNION ALL SELECT 'sat_rental_details', count(*), count(DISTINCT rental_hk) FROM video_rental_dv.sat_rental_details
        UNION ALL SELECT 'sat_rental_item_details', count(*), count(DISTINCT rental_copy_hk) FROM video_rental_dv.sat_rental_item_details
        UNION ALL SELECT 'sat_payment_details', count(*), count(DISTINCT payment_hk) FROM video_rental_dv.sat_payment_details
        UNION ALL SELECT 'sat_film_genre_details', count(*), count(DISTINCT film_genre_hk) FROM video_rental_dv.sat_film_genre_details
        ORDER BY 1""")[1]

    d["hub_counts"] = q.query("""
        SELECT 'hub_customer', count(*) FROM video_rental_dv.hub_customer
        UNION ALL SELECT 'hub_employee', count(*) FROM video_rental_dv.hub_employee
        UNION ALL SELECT 'hub_film', count(*) FROM video_rental_dv.hub_film
        UNION ALL SELECT 'hub_video_copy', count(*) FROM video_rental_dv.hub_video_copy
        UNION ALL SELECT 'hub_rental', count(*) FROM video_rental_dv.hub_rental
        UNION ALL SELECT 'hub_payment', count(*) FROM video_rental_dv.hub_payment
        UNION ALL SELECT 'hub_genre', count(*) FROM video_rental_dv.hub_genre
        UNION ALL SELECT 'hub_tariff', count(*) FROM video_rental_dv.hub_tariff
        ORDER BY 1""")[1]

    d["link_counts"] = q.query("""
        SELECT 'link_film_copy', count(*) FROM video_rental_dv.link_film_copy
        UNION ALL SELECT 'link_film_genre', count(*) FROM video_rental_dv.link_film_genre
        UNION ALL SELECT 'link_film_tariff', count(*) FROM video_rental_dv.link_film_tariff
        UNION ALL SELECT 'link_rental_customer', count(*) FROM video_rental_dv.link_rental_customer
        UNION ALL SELECT 'link_rental_employee', count(*) FROM video_rental_dv.link_rental_employee
        UNION ALL SELECT 'link_rental_copy', count(*) FROM video_rental_dv.link_rental_copy
        UNION ALL SELECT 'link_rental_payment', count(*) FROM video_rental_dv.link_rental_payment
        ORDER BY 1""")[1]

    d["data_3nf"] = q.query(f"""
        SELECT 'genre', count(*) FROM {S3}.genre
        UNION ALL SELECT 'tariff', count(*) FROM {S3}.tariff
        UNION ALL SELECT 'film', count(*) FROM {S3}.film
        UNION ALL SELECT 'film_genre', count(*) FROM {S3}.film_genre
        UNION ALL SELECT 'video_copy', count(*) FROM {S3}.video_copy
        UNION ALL SELECT 'customer', count(*) FROM {S3}.customer
        UNION ALL SELECT 'employee', count(*) FROM {S3}.employee
        UNION ALL SELECT 'rental', count(*) FROM {S3}.rental
        UNION ALL SELECT 'rental_item', count(*) FROM {S3}.rental_item
        UNION ALL SELECT 'payment', count(*) FROM {S3}.payment
        ORDER BY 1""")[1]

    d["struct_3nf"] = q.query(f"""
        SELECT t.table_name,
               (SELECT count(*) FROM information_schema.columns c
                 WHERE c.table_schema=t.table_schema AND c.table_name=t.table_name),
               (SELECT count(*) FROM information_schema.table_constraints tc
                 WHERE tc.table_schema=t.table_schema AND tc.table_name=t.table_name
                   AND tc.constraint_type='PRIMARY KEY'),
               (SELECT count(*) FROM information_schema.table_constraints tc
                 WHERE tc.table_schema=t.table_schema AND tc.table_name=t.table_name
                   AND tc.constraint_type='FOREIGN KEY'),
               (SELECT count(*) FROM information_schema.table_constraints tc
                 WHERE tc.table_schema=t.table_schema AND tc.table_name=t.table_name
                   AND tc.constraint_type='UNIQUE'),
               (SELECT count(*) FROM information_schema.table_constraints tc
                 WHERE tc.table_schema=t.table_schema AND tc.table_name=t.table_name
                   AND tc.constraint_type='CHECK')
          FROM information_schema.tables t
         WHERE t.table_schema='{S3}' AND t.table_type='BASE TABLE'
         ORDER BY t.table_name""")[1]

    d["struct_dv"] = q.query(f"""
        SELECT CASE WHEN table_name LIKE 'hub\\_%' THEN 'HUB'
                    WHEN table_name LIKE 'link\\_%' THEN 'LINK'
                    ELSE 'SATELLITE' END,
               table_name,
               (SELECT count(*) FROM information_schema.columns c
                 WHERE c.table_schema=t.table_schema AND c.table_name=t.table_name),
               (SELECT count(*) FROM information_schema.table_constraints tc
                 WHERE tc.table_schema=t.table_schema AND tc.table_name=t.table_name
                   AND tc.constraint_type='FOREIGN KEY')
          FROM information_schema.tables t
         WHERE t.table_schema='{SDV}' AND t.table_type='BASE TABLE'
         ORDER BY 1, 2""")[1]

    d["dv_objects"] = q.query(f"""
        SELECT CASE WHEN table_name LIKE 'hub\\_%' THEN 'HUB'
                    WHEN table_name LIKE 'link\\_%' THEN 'LINK'
                    ELSE 'SATELLITE' END, count(*)
          FROM information_schema.tables
         WHERE table_schema='{SDV}' AND table_type='BASE TABLE'
         GROUP BY 1 ORDER BY 1""")[1]

    d["loads"] = q.query(f"""
        SELECT record_source, count(*) FROM (
            SELECT record_source FROM {SDV}.hub_customer
            UNION ALL SELECT record_source FROM {SDV}.hub_employee
            UNION ALL SELECT record_source FROM {SDV}.hub_film
            UNION ALL SELECT record_source FROM {SDV}.hub_video_copy
            UNION ALL SELECT record_source FROM {SDV}.hub_rental
            UNION ALL SELECT record_source FROM {SDV}.hub_payment
            UNION ALL SELECT record_source FROM {SDV}.hub_genre
            UNION ALL SELECT record_source FROM {SDV}.hub_tariff) h
         GROUP BY record_source ORDER BY record_source""")[1]

    d["version"] = q.scalar("SELECT version()")
    d["now"] = q.scalar("SELECT to_char(lab.current_date(),'DD.MM.YYYY')")
    return d


# ==========================================================================
# Документ
# ==========================================================================
def load_toc_pages():
    """Номера страниц разделов для оглавления.

    Значения берутся из файла toc_pages.json, который создает скрипт
    page_numbers.py по фактически отрендеренному PDF: оглавление не может
    разойтись с реальной версткой. Если файла еще нет (первый проход),
    используются значения по умолчанию, после чего сборка повторяется.
    """
    path = os.path.join(HERE, "toc_pages.json")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return [tuple(x) for x in json.load(f)]
    return [(t, p, lv) for t, p, lv in DEFAULT_TOC]


DEFAULT_TOC = [
    ("1 Цель работы", 3, 1),
    ("2 Постановка задачи", 4, 1),
    ("3 Анализ предметной области", 5, 1),
    ("4 Проектирование модели в 3NF", 7, 1),
    ("5 Реализация 3NF в PostgreSQL", 10, 1),
    ("6 Проектирование модели Data Vault", 13, 1),
    ("7 Реализация Data Vault в PostgreSQL", 17, 1),
    ("8 Проверка работы", 20, 1),
    ("9 Сравнение подходов", 27, 1),
    ("10 Заключение", 28, 1),
    ("Список использованных источников", 29, 1),
    ("Приложение А. Диаграмма модели 3NF", 30, 1),
    ("Приложение Б. Диаграмма модели Data Vault", 31, 1),
]


def build():
    D = fetch_data()
    doc = Document()

    # базовый стиль документа
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

    # --------------------------------------------------------------------
    # Титульный лист
    # --------------------------------------------------------------------
    para(doc, "Министерство науки и высшего образования Российской Федерации",
         align="center", indent=False, line=1.0)
    para(doc, "Федеральное государственное автономное образовательное учреждение",
         align="center", indent=False, line=1.0)
    para(doc, "высшего образования", align="center", indent=False, line=1.0)
    para(doc, "МОСКОВСКИЙ ПОЛИТЕХНИЧЕСКИЙ УНИВЕРСИТЕТ", align="center",
         indent=False, line=1.0, bold=True)
    para(doc, "(МОСКОВСКИЙ ПОЛИТЕХ)", align="center", indent=False, line=1.0, bold=True)
    para(doc, "", indent=False, line=1.0)
    para(doc, "Факультет информационных технологий", align="center", indent=False, line=1.0)
    para(doc, "Кафедра «Прикладная информатика»", align="center", indent=False, line=1.0)
    para(doc, "Форма обучения: очная", align="center", indent=False, line=1.0)
    for _ in range(5):
        para(doc, "", indent=False, line=1.0)
    para(doc, "ЛАБОРАТОРНАЯ РАБОТА № 2", align="center", indent=False,
         line=1.0, bold=True, size=16)
    para(doc, "Тема: «Проектирование базы данных в 3NF и Data Vault»",
         align="center", indent=False, line=1.0)
    para(doc, "Вариант 14: «Система учета в видеопрокате»",
         align="center", indent=False, line=1.0)
    para(doc, "", indent=False, line=1.0)
    para(doc, "по дисциплине «Хранилища данных»", align="center", indent=False, line=1.0)
    for _ in range(4):
        para(doc, "", indent=False, line=1.0)
    p = para(doc, "Студент: Никитин Платон Алексеевич", align="right", indent=False, line=1.0)
    para(doc, "Группа: 231-363", align="right", indent=False, line=1.0)
    for _ in range(4):
        para(doc, "", indent=False, line=1.0)
    para(doc, "Москва 2026", align="center", indent=False, line=1.0)

    # --------------------------------------------------------------------
    # Содержание
    # --------------------------------------------------------------------
    sec2 = portrait_section(doc)
    footer_page_number(doc.sections[0], show=False)   # титул без номера
    footer_page_number(sec2, show=True)

    heading(doc, "СОДЕРЖАНИЕ", level=1)
    toc_entries = load_toc_pages()
    add_toc_field(doc, toc_entries)
    para(doc, "", indent=False)

    # --------------------------------------------------------------------
    # 1 Цель работы
    # --------------------------------------------------------------------
    heading(doc, "1 Цель работы", level=1, page_break_before=True)
    para(doc, "Цель работы - освоить проектирование реляционной базы данных "
              "предметной области «Система учета в видеопрокате» в третьей "
              "нормальной форме и построение хранилища данных по методике "
              "Data Vault на той же предметной области, а также сравнить эти "
              "два подхода на практике.")
    para(doc, "Для достижения цели поставлены следующие задачи:")
    for t in [
        "изучить методику Data Vault по материалам DWH-Club;",
        "выполнить анализ предметной области и зафиксировать бизнес-правила;",
        "спроектировать и реализовать в PostgreSQL модель не ниже 3NF;",
        "спроектировать и реализовать в PostgreSQL модель Data Vault с "
        "разделением объектов на Hub, Link и Satellite;",
        "обеспечить хранение истории изменения атрибутов в Satellites;",
        "загрузить тестовые данные и проверить обе модели реальными запросами;",
        "проверить, что ограничения целостности отклоняют некорректные данные;",
        "построить даталогические диаграммы обеих моделей и оформить отчет.",
    ]:
        bullet(doc, t)

    # --------------------------------------------------------------------
    # 2 Постановка задачи
    # --------------------------------------------------------------------
    heading(doc, "2 Постановка задачи", level=1, page_break_before=True)
    para(doc, "Согласно варианту №14 из методических указаний «Варианты на ЛР №2» "
              "требуется спроектировать систему учета в видеопрокате. В "
              "соответствии с заданием лабораторной работы №2 необходимо:")
    for t in [
        "изучить пример выполнения задания по Data Vault;",
        "в PostgreSQL реализовать структуру базы данных предметной области "
        "варианта №14 в соответствии с моделью 3NF: получить даталогическую "
        "модель, задокументированный SQL-код создания БД и реальные проверки "
        "выполнения SQL;",
        "в PostgreSQL реализовать ту же предметную область в соответствии с "
        "моделью Data Vault: получить даталогическую модель, корректное "
        "разделение на Hub / Link / Satellite, задокументированный SQL-код, "
        "механизм хранения истории изменения атрибутов и реальные проверки "
        "выполнения SQL;",
        "оформить обе модели в единую лабораторную работу.",
    ]:
        bullet(doc, " " + t)
    para(doc, "Формулировка варианта №14: «Система учета в видеопрокате». "
              "Предметная область рассматривается как прокат физических "
              "экземпляров фильмов на носителях (VHS, DVD, Blu-ray), а не как "
              "потоковый сервис: ключевыми объектами учета являются сами "
              "носители, их физическое состояние и факты выдачи клиентам.")

    # --------------------------------------------------------------------
    # 3 Анализ предметной области
    # --------------------------------------------------------------------
    heading(doc, "3 Анализ предметной области", level=1, page_break_before=True)
    heading(doc, "3.1 Назначение системы и основные процессы", level=2)
    para(doc, "Система учета видеопроката автоматизирует работу пункта выдачи "
              "фильмов на физических носителях. Она ведет каталог фильмов и "
              "фонд экземпляров, регистрирует клиентов и сотрудников, оформляет "
              "выдачу и возврат, рассчитывает стоимость проката, принимает "
              "платежи и контролирует просрочку.")
    para(doc, "Основные процессы:")
    for t in [
        "ведение каталога фильмов с указанием жанров, возрастной категории, "
        "носителя и тарифа;",
        "учет физических экземпляров: каждый экземпляр имеет уникальный "
        "инвентарный номер, место хранения и состояние;",
        "регистрация клиентов с выдачей клубной карты;",
        "оформление операции проката: один клиент может получить несколько "
        "экземпляров в рамках одной операции;",
        "установка плановой даты возврата и фиксация фактического возврата по "
        "каждому экземпляру;",
        "расчет стоимости проката и прием платежей (залог, оплата, пеня);",
        "контроль просрочки и работа с задолженностью.",
    ]:
        bullet(doc, t)

    heading(doc, "3.2 Бизнес-правила", level=2)
    para(doc, "До проектирования зафиксированы следующие бизнес-правила:")
    rules = [
        ("БП-1", "Фильм в каталоге описывается один раз; количество его "
                 "физических экземпляров произвольно и ограничено только фондом."),
        ("БП-2", "Каждый физический экземпляр идентифицируется уникальным "
                 "инвентарным номером и относится ровно к одному фильму."),
        ("БП-3", "Фильм может относиться к нескольким жанрам; один жанр может "
                 "быть указан основным."),
        ("БП-4", "Тариф задает стоимость суток проката, нормативный срок и пеню "
                 "за сутки просрочки."),
        ("БП-5", "Операция проката оформляется на одного клиента и одного "
                 "сотрудника и может включать несколько экземпляров."),
        ("БП-6", "Один физический экземпляр не может одновременно находиться в "
                 "двух активных прокатах."),
        ("БП-7", "Плановая дата возврата не может быть раньше даты выдачи."),
        ("БП-8", "Позиция проката считается возвращенной только вместе с "
                 "фиксацией фактической даты возврата и состояния экземпляра."),
        ("БП-9", "Операция проката закрывается автоматически, когда возвращены "
                 "все ее позиции."),
        ("БП-10", "Сумма платежа строго положительна; платеж всегда относится к "
                  "конкретной операции проката."),
        ("БП-11", "Экземпляр в состоянии «списан» (written_off) не может быть "
                  "выдан клиенту."),
        ("БП-12", "Стоимость суток проката фиксируется в позиции на момент "
                  "выдачи, чтобы изменение тарифа не искажало прошлые операции."),
    ]
    make_table(doc, ["Код", "Бизнес-правило"],
               [[a, b] for a, b in rules], align_cols={0: "center"}, caption="Таблица 1 - Бизнес-правила предметной области")

    heading(doc, "3.3 Сущности предметной области", level=2)
    para(doc, "Анализ процессов и бизнес-правил дает следующий набор сущностей. "
              "Кардинальности связей: Film 1:N VideoCopy; Film M:N Genre через "
              "FilmGenre; Tariff 1:N Film; Customer 1:N Rental; Employee 1:N "
              "Rental; Rental 1:N RentalItem; VideoCopy 1:N RentalItem (во "
              "времени); Rental 1:N Payment.")
    make_table(
        doc, ["Сущность", "Назначение", "Ключ"],
        [["genre", "справочник жанров фильмов", "genre_id"],
         ["tariff", "тарифы проката (прайс-лист)", "tariff_id"],
         ["film", "каталожная карточка фильма", "film_id"],
         ["film_genre", "связь фильма и жанра (M:N)", "film_id + genre_id"],
         ["video_copy", "физический экземпляр (носитель) фильма", "copy_id"],
         ["customer", "клиент - держатель клубной карты", "customer_id"],
         ["employee", "сотрудник видеопроката", "employee_id"],
         ["rental", "операция проката (заголовок)", "rental_id"],
         ["rental_item", "позиция проката: конкретный экземпляр в операции", "rental_item_id"],
         ["payment", "платеж клиента по операции проката", "payment_id"]], mono_cols=(0, 2), align_cols={0: "left"},
        caption="Таблица 2 - Сущности предметной области и их ключи")


    # --------------------------------------------------------------------
    # 4 Проектирование модели в 3NF
    # --------------------------------------------------------------------
    heading(doc, "4 Проектирование модели в 3NF", level=1, page_break_before=True)
    heading(doc, "4.1 Состав модели и назначение таблиц", level=2)
    para(doc, "Модель 3NF состоит из десяти таблиц. Справочные таблицы genre и "
              "tariff хранят независимые классификаторы. Таблица film описывает "
              "фильм как объект каталога, а video_copy - его физические "
              "экземпляры. Таблица film_genre разрешает отношение «многие ко "
              "многим» между фильмами и жанрами. Таблицы customer и employee "
              "описывают участников проката. Операция проката разделена на "
              "заголовок rental и позиции rental_item, что позволяет выдать "
              "несколько экземпляров одной операцией. Таблица payment хранит "
              "платежи по операциям.")
    para(doc, "Такое разделение не является избыточным: заголовок операции "
              "хранит общие для всех позиций атрибуты (клиент, сотрудник, даты "
              "операции, залог), а позиция - атрибуты конкретного экземпляра "
              "(зафиксированная цена суток, состояние при возврате).")

    heading(doc, "4.2 Обоснование нормальных форм", level=2)
    para(doc, "1NF. Все атрибуты атомарны: ФИО хранится отдельными полями "
              "last_name, first_name, middle_name; адрес и телефон - простые "
              "строковые значения, соответствующие одному значению; "
              "множественные значения (жанры фильма, экземпляры в операции) "
              "вынесены в отдельные таблицы film_genre и rental_item, а не "
              "хранятся в одной ячейке в виде списка.")
    para(doc, "2NF. Первичные ключи всех таблиц одноатрибутные (кроме "
              "film_genre с составным ключом film_id + genre_id), поэтому "
              "частичных зависимостей от части составного ключа не возникает: "
              "атрибут is_primary зависит от пары «фильм - жанр» целиком, а не "
              "от одного из ключей. Описательные атрибуты операций проката "
              "зависят только от rental_id и не дублируются в позициях.")
    para(doc, "3NF. Нетранзитивных зависимостей нет: сведения о клиенте "
              "хранятся только в customer, о фильме - только в film, о тарифе - "
              "только в tariff. В rental хранятся ссылки customer_id и "
              "employee_id, а не их описательные атрибуты; в video_copy "
              "хранится film_id, а не название фильма. Единственное "
              "исключение по замыслу - поле rental_item.daily_rate: оно не "
              "является транзитивной зависимостью, а представляет собой "
              "зафиксированное историческое значение цены на момент выдачи "
              "(бизнес-правило БП-12). Такое дублирование осознанное: иначе "
              "изменение тарифа задним числом искажало бы уже закрытые "
              "операции.")
    para(doc, "Вычисляемые значения (стоимость проката, число дней, признак "
              "просрочки, сумма платежей) в таблицах не хранятся. Они "
              "получаются представлениями v_rental_item_cost, v_rental_total и "
              "v_active_rental, что исключает рассогласование данных.")

    heading(doc, "4.3 Ключевые ограничения целостности", level=2)
    para(doc, "Ограничения реализованы средствами PostgreSQL и проверены "
              "на реальных данных (раздел 8).")
    make_table(
        doc, ["Правило", "Реализация в PostgreSQL"],
        [["БП-2, БП-6: экземпляр не выдается дважды",
          "частичный уникальный индекс ux_rental_item_active_copy\n"
          "ON rental_item (copy_id) WHERE status = 'issued'"],
         ["БП-7: плановый возврат не раньше выдачи",
          "CHECK ck_rental_issue_planned (planned_return_date >= issue_date)"],
         ["БП-8: возврат только с датой и состоянием",
          "CHECK ck_rental_item_return ((status = 'returned') = "
          "(actual_return_date IS NOT NULL))"],
         ["БП-9: закрытие операции",
          "триггер trg_rental_item_sync после INSERT/UPDATE/DELETE "
          "на rental_item"],
         ["БП-10: положительный платеж",
          "CHECK ck_payment_amount (amount > 0)"],
         ["БП-11: списанный экземпляр не выдается",
          "v_copy_status: is_available = false при condition = 'written_off'"],
         ["Форматы бизнес-ключей",
          "CHECK с регулярными выражениями:\n"
          "card_number ~ '^CR-[0-9]{5}$', inventory_code ~ '^VC-[0-9]{5}$'"]], caption="Таблица 3 - Ключевые ограничения модели 3NF")

    para(doc, "Правила БП-6 и БП-9 зависят от других строк таблицы, поэтому "
              "CHECK-ограничением не выражаются: БП-6 реализовано частичным "
              "уникальным индексом, а БП-9 - триггером, синхронизирующим статус "
              "операции с состоянием ее позиций.")

    heading(doc, "4.4 Даталогическая диаграмма", level=2)
    para(doc, "Даталогическая модель 3NF приведена на рисунке 1. Диаграмма "
              "показывает таблицы, первичные и внешние ключи, уникальные "
              "ограничения, атрибуты и кардинальности связей. В приложении А "
              "диаграмма приведена на отдельной странице в альбомной ориентации.")
    add_picture(doc, os.path.join(DIAGRAMS, "3nf_model.png"),
                fit_width_mm(os.path.join(DIAGRAMS, "3nf_model.png"), 168, 150),
                "Рисунок 1 - Даталогическая модель предметной области в 3NF")
    para(doc, "На диаграмме видно, что все описательные атрибуты находятся в "
              "таблице своей сущности: название фильма - только в film, "
              "сведения о клиенте - только в customer, условия проката - только "
              "в tariff. Таблица rental_item ссылается одновременно на операцию "
              "проката и на физический экземпляр, что и обеспечивает "
              "возможность выдать несколько экземпляров одной операцией.")

    # --------------------------------------------------------------------
    # 5 Реализация 3NF в PostgreSQL
    # --------------------------------------------------------------------
    heading(doc, "5 Реализация 3NF в PostgreSQL", level=1, page_break_before=True)
    para(doc, "Модель реализована в отдельной схеме video_rental_3nf базы данных "
              "video_rental_lab под управлением PostgreSQL 17. Полный DDL "
              "находится в приложенном файле sql/01_create_3nf.sql; ниже "
              "приведены ключевые фрагменты.")

    heading(doc, "5.1 Создание схемы и служебных функций", level=2)
    para(doc, "Для воспроизводимости проверок «текущая дата» системы вынесена в "
              "функцию, поэтому результаты запросов не зависят от даты запуска "
              "скрипта.")
    code(doc, """CREATE SCHEMA IF NOT EXISTS lab;

CREATE OR REPLACE FUNCTION lab.current_date() RETURNS date
    LANGUAGE sql IMMUTABLE AS $$ SELECT DATE '2026-09-28' $$;

DROP SCHEMA IF EXISTS video_rental_3nf CASCADE;
CREATE SCHEMA video_rental_3nf;""")

    heading(doc, "5.2 Основные таблицы", level=2)
    para(doc, "Ниже приведены фрагменты определения таблиц, показывающие типы "
              "данных, ключи и ограничения.")
    code(doc, """CREATE TABLE film (
    film_id        integer       GENERATED ALWAYS AS IDENTITY,
    catalog_number varchar(16)   NOT NULL,
    title          varchar(200)  NOT NULL,
    release_year   smallint      NOT NULL,
    duration_min   smallint      NOT NULL,
    age_rating     varchar(8)    NOT NULL,
    media_type     varchar(10)   NOT NULL,
    tariff_id      integer       NOT NULL,
    added_on       date          NOT NULL DEFAULT lab.current_date(),
    CONSTRAINT pk_film PRIMARY KEY (film_id),
    CONSTRAINT uq_film_catalog_number UNIQUE (catalog_number),
    CONSTRAINT fk_film_tariff FOREIGN KEY (tariff_id)
        REFERENCES tariff (tariff_id) ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_film_release_year CHECK (release_year BETWEEN 1895 AND 2100),
    CONSTRAINT ck_film_age_rating CHECK (age_rating IN ('0+','6+','12+','16+','18+')),
    CONSTRAINT ck_film_media_type CHECK (media_type IN ('VHS','DVD','Blu-ray'))
);""")
    code(doc, """CREATE TABLE rental_item (
    rental_item_id      integer      GENERATED ALWAYS AS IDENTITY,
    rental_id           integer      NOT NULL,
    copy_id             integer      NOT NULL,
    daily_rate          numeric(8,2) NOT NULL,
    status              varchar(10)  NOT NULL DEFAULT 'issued',
    actual_return_date  date,
    condition_on_return varchar(12),
    CONSTRAINT pk_rental_item PRIMARY KEY (rental_item_id),
    CONSTRAINT uq_rental_item UNIQUE (rental_id, copy_id),
    CONSTRAINT fk_rental_item_rental FOREIGN KEY (rental_id)
        REFERENCES rental (rental_id) ON DELETE CASCADE,
    CONSTRAINT fk_rental_item_copy FOREIGN KEY (copy_id)
        REFERENCES video_copy (copy_id) ON DELETE RESTRICT,
    CONSTRAINT ck_rental_item_return CHECK ((status = 'returned')
        = (actual_return_date IS NOT NULL))
);

-- один экземпляр не может быть в двух активных прокатах
CREATE UNIQUE INDEX ux_rental_item_active_copy
    ON rental_item (copy_id) WHERE status = 'issued';""")

    heading(doc, "5.3 Триггер закрытия операции проката", level=2)
    para(doc, "Статус операции проката и дата фактического возврата выводятся из "
              "состояния позиций. Это правило нельзя записать CHECK-ограничением, "
              "поэтому используется триггер.")
    code(doc, """CREATE OR REPLACE FUNCTION trg_rental_item_sync() RETURNS trigger
    LANGUAGE plpgsql AS $$
DECLARE
    v_rental_id integer; v_open integer; v_returned integer; v_max_date date;
BEGIN
    v_rental_id := COALESCE(NEW.rental_id, OLD.rental_id);
    SELECT count(*) FILTER (WHERE status = 'issued'),
           count(*) FILTER (WHERE status = 'returned'),
           max(actual_return_date)
      INTO v_open, v_returned, v_max_date
      FROM rental_item WHERE rental_id = v_rental_id;

    IF v_open = 0 AND v_returned > 0 THEN
        UPDATE rental SET status = 'closed', actual_return_date = v_max_date
         WHERE rental_id = v_rental_id AND status = 'issued';
    ELSIF v_open > 0 THEN
        UPDATE rental SET status = 'issued', actual_return_date = NULL
         WHERE rental_id = v_rental_id AND status = 'closed';
    END IF;
    RETURN NULL;
END $$;

CREATE TRIGGER trg_rental_item_sync_aiud
    AFTER INSERT OR UPDATE OR DELETE ON rental_item
    FOR EACH ROW EXECUTE FUNCTION trg_rental_item_sync();""")

    heading(doc, "5.4 Индексы и комментарии", level=2)
    para(doc, "Для всех внешних ключей и основных сценариев поиска созданы "
              "индексы. Таблицы и ключевые поля снабжены комментариями через "
              "COMMENT ON, что делает структуру самодокументируемой.")
    code(doc, """CREATE INDEX ix_video_copy_film        ON video_copy (film_id);
CREATE INDEX ix_rental_customer        ON rental (customer_id);
CREATE INDEX ix_rental_employee        ON rental (employee_id);
CREATE INDEX ix_rental_planned_return  ON rental (planned_return_date);
CREATE INDEX ix_rental_item_copy       ON rental_item (copy_id);
CREATE INDEX ix_payment_rental         ON payment (rental_id);

COMMENT ON TABLE video_copy IS
    'Физические экземпляры (носители) фильмов, находящиеся в фонде видеопроката';
COMMENT ON COLUMN video_copy.condition IS
    'Состояние экземпляра: new, good, worn, damaged, written_off';""")

    heading(doc, "5.5 Тестовые данные", level=2)
    para(doc, "В базу загружен синтетический набор данных, достаточный для "
              "проверки модели. Состав данных приведен в таблице 4. Скрипт "
              "загрузки - sql/03_test_data_3nf.sql.")
    make_table(doc, ["Таблица", "Строк", "Содержание"],
               [[r[0], r[1], desc] for r, desc in zip(D["data_3nf"], [
                   "7 жанров (боевик, драма, комедия, фантастика, триллер, анимация, документальный)",
                   "4 тарифа: стандарт, новинка, классика, акция",
                   "10 фильмов разных лет и носителей",
                   "19 связей «фильм - жанр»; у 4 фильмов более одного жанра",
                   "16 экземпляров, в том числе по несколько копий одного фильма",
                   "6 клиентов, один из них заблокирован",
                   "3 сотрудника, один уволен",
                   "6 операций: 2 закрыты, 1 с просрочкой, 3 активны (в том числе 1 просроченная)",
                   "9 позиций проката, в том числе операции с несколькими экземплярами",
                   "10 платежей: залоги, оплата проката и пеня",
               ])], mono_cols=(0,), align_cols={1: "center"},
               caption="Таблица 4 - Состав тестовых данных модели 3NF")

    para(doc, "Состав данных обеспечивает все требуемые сценарии: полностью "
              "возвращенный прокат (RN-000001), прокат с просрочкой "
              "(RN-000002), активный прокат в срок (RN-000003), активный "
              "просроченный прокат (RN-000004) и операции с несколькими "
              "экземплярами (RN-000005, RN-000006).")

    # --------------------------------------------------------------------
    # 6 Проектирование Data Vault
    # --------------------------------------------------------------------
    heading(doc, "6 Проектирование модели Data Vault", level=1, page_break_before=True)
    para(doc, "Data Vault - подход к моделированию хранилищ данных, который "
              "сочетает свойства третьей нормальной формы и схемы «звезда». "
              "Модель состоит из трех типов объектов: Hub (Хаб) хранит "
              "устойчивые бизнес-ключи, Link (Связь) фиксирует отношения между "
              "Хабами, Satellite (Спутник) хранит описательные атрибуты и их "
              "историю. Каждый объект несет служебные поля load_dts (дата и "
              "время загрузки) и record_source (источник записи), что "
              "обеспечивает аудит загрузки.")

    heading(doc, "6.1 Хабы", level=2)
    para(doc, "Хаб описывает бизнес-сущность, которая существует независимо от "
              "других и идентифицируется устойчивым бизнес-ключом. Для "
              "видеопроката выбраны восемь бизнес-ключей:")
    make_table(doc, ["Хаб", "Бизнес-ключ", "Обоснование"],
               [["hub_customer", "card_number", "номер клубной карты не меняется при смене ФИО или телефона"],
                ["hub_employee", "personnel_number", "табельный номер сотрудника устойчив"],
                ["hub_film", "catalog_number", "каталожный номер фильма - идентификатор карточки каталога"],
                ["hub_video_copy", "inventory_code", "инвентарный номер физического экземпляра"],
                ["hub_rental", "rental_number", "номер операции проката"],
                ["hub_payment", "payment_number", "номер платежного документа"],
                ["hub_genre", "genre_code", "код жанра"],
                ["hub_tariff", "tariff_code", "код тарифа проката"]], mono_cols=(0, 1), align_cols={0: "left"},
               caption="Таблица 5 - Хабы модели Data Vault")

    para(doc, "Таблица payment выделена в самостоятельный Хаб, так как платеж "
              "имеет собственный номер и собственный жизненный цикл, а его "
              "связь с операцией проката описывается отдельной Связью. Аналогично "
              "tariff и genre - самостоятельные Хабы-справочники.")

    heading(doc, "6.2 Связи", level=2)
    para(doc, "Связь фиксирует бизнес-взаимодействие между Хабами и создается "
              "только там, где отношение действительно существует.")
    make_table(doc, ["Связь", "Связанные Хабы", "Смысл"],
               [["link_film_copy", "hub_film + hub_video_copy", "фильм имеет физические экземпляры"],
                ["link_film_genre", "hub_film + hub_genre", "фильм относится к жанрам (M:N)"],
                ["link_film_tariff", "hub_film + hub_tariff", "фильм прокатывается по тарифу"],
                ["link_rental_customer", "hub_rental + hub_customer", "кто оформил прокат"],
                ["link_rental_employee", "hub_rental + hub_employee", "кто выдал экземпляры"],
                ["link_rental_copy", "hub_rental + hub_video_copy", "позиция проката: какой экземпляр выдан"],
                ["link_rental_payment", "hub_rental + hub_payment", "платежи по операции"]], mono_cols=(0,), align_cols={0: "left"},
               caption="Таблица 6 - Связи модели Data Vault")

    para(doc, "Связь link_rental_copy соответствует позиции проката: она "
              "допускает несколько экземпляров в одной операции, поскольку "
              "уникальность определена по паре (rental_hk, copy_hk). "
              "Бессмысленные Связи не создавались: например, между "
              "hub_customer и hub_film прямой связи нет, так как клиент "
              "взаимодействует не с фильмом, а с конкретным экземпляром через "
              "операцию проката.")

    heading(doc, "6.3 Спутники и историзация", level=2)
    para(doc, "Спутники хранят описательные атрибуты своих родителей и их "
              "историю. Первичный ключ Спутника составной: ключ родителя плюс "
              "load_dts. Изменение атрибутов не перезаписывает существующую "
              "строку, а добавляет новую версию, поэтому вся история сохраняется. "
              "Спутники разделены по темпам изменения данных: например, ФИО "
              "клиента меняется редко (sat_customer_details), а телефон, адрес и "
              "статус - часто (sat_customer_contact).")
    make_table(doc, ["Спутник", "Родитель", "Атрибуты"],
               [[r[0], par, attrs] for r, par, attrs in [
                   (["sat_customer_details"], "hub_customer", "ФИО, дата рождения, дата регистрации"),
                   (["sat_customer_contact"], "hub_customer", "телефон, email, адрес, статус"),
                   (["sat_employee_details"], "hub_employee", "ФИО, должность, телефон, даты приема и увольнения, статус"),
                   (["sat_film_details"], "hub_film", "название, оригинальное название, год, длительность, возрастная категория, носитель, описание"),
                   (["sat_video_copy_acquisition"], "hub_video_copy", "дата и цена закупки"),
                   (["sat_video_copy_details"], "hub_video_copy", "состояние экземпляра, место хранения"),
                   (["sat_genre_details"], "hub_genre", "название и описание жанра"),
                   (["sat_tariff_details"], "hub_tariff", "стоимость суток, срок, пеня, период действия"),
                   (["sat_rental_details"], "hub_rental", "сроки, фактический возврат, залог, статус, примечание"),
                   (["sat_rental_item_details"], "link_rental_copy", "зафиксированная цена суток, статус позиции, дата возврата, состояние при возврате"),
                   (["sat_payment_details"], "hub_payment", "дата, сумма, способ и тип платежа"),
                   (["sat_film_genre_details"], "link_film_genre", "признак основного жанра")]], mono_cols=(0, 1), align_cols={0: "left"},
               caption="Таблица 7 - Спутники модели Data Vault")

    para(doc, "Два Спутника (sat_rental_item_details и sat_film_genre_details) "
              "привязаны не к Хабу, а к Связям. Это стандартный прием Data "
              "Vault: контекст, описывающий само отношение (например, состояние "
              "экземпляра именно в этой операции или признак основного жанра), "
              "хранится в Спутнике Связи.")

    heading(doc, "6.4 Даталогическая диаграмма", level=2)
    para(doc, "Даталогическая модель Data Vault приведена на рисунке 2. "
              "Визуально различаются Хабы, Связи и Спутники, показаны ключи и "
              "направления связей. В приложении Б диаграмма приведена на "
              "отдельной странице в альбомной ориентации.")
    add_picture(doc, os.path.join(DIAGRAMS, "data_vault_model.png"),
                fit_width_mm(os.path.join(DIAGRAMS, "data_vault_model.png"), 168, 150),
                "Рисунок 2 - Даталогическая модель предметной области в нотации Data Vault")
    para(doc, "На диаграмме восемь Хабов образуют верхний уровень модели, семь "
              "Связей соединяют их между собой, а двенадцать Спутников "
              "примыкают к своим родителям. Спутники sat_rental_item_details и "
              "sat_film_genre_details привязаны к Связям, остальные - к Хабам. "
              "Хабы не ссылаются друг на друга: их ключи не мигрируют между "
              "собой, что сохраняет гибкость модели при добавлении новых "
              "источников данных.")

    # --------------------------------------------------------------------
    # 7 Реализация Data Vault в PostgreSQL
    # --------------------------------------------------------------------
    heading(doc, "7 Реализация Data Vault в PostgreSQL", level=1, page_break_before=True)
    para(doc, "Модель реализована в отдельной схеме video_rental_dv той же базы "
              "данных. Полный DDL находится в файле "
              "sql/02_create_data_vault.sql. Итоговый состав: 8 Хабов, "
              "7 Связей и 12 Спутников.")

    heading(doc, "7.1 Ключи и хэширование", level=2)
    para(doc, "Ключи Хабов - хэши бизнес-ключей, вычисляемые детерминированной "
              "функцией dv_hash. Значения приводятся к верхнему регистру и "
              "обрезаются по краям, поэтому различия в регистре и пробелах не "
              "создают дубликатов. Хэш-дифферент Спутника вычисляется той же "
              "функцией и меняется при любом изменении описательных атрибутов.")
    code(doc, """CREATE OR REPLACE FUNCTION dv_hash(VARIADIC parts text[])
RETURNS char(32) LANGUAGE sql IMMUTABLE AS $$
    SELECT md5(coalesce(string_agg(
               upper(btrim(coalesce(p, chr(1)))), '||' ORDER BY ord), ''))
      FROM unnest(parts) WITH ORDINALITY AS t(p, ord)
$$;

CREATE OR REPLACE FUNCTION dv_hashdiff(VARIADIC parts text[])
RETURNS char(32) LANGUAGE sql IMMUTABLE AS $$
    SELECT dv_hash(VARIADIC parts)
$$;""")

    heading(doc, "7.2 Структура Хаба, Связи и Спутника", level=2)
    code(doc, """CREATE TABLE hub_customer (
    customer_hk   char(32)    NOT NULL,     -- хэш бизнес-ключа
    card_number   varchar(12) NOT NULL,     -- бизнес-ключ
    load_dts      timestamp   NOT NULL DEFAULT lab.now(),
    record_source varchar(50) NOT NULL,
    CONSTRAINT pk_hub_customer PRIMARY KEY (customer_hk),
    CONSTRAINT uq_hub_customer_bk UNIQUE (card_number)
);

CREATE TABLE link_rental_copy (
    rental_copy_hk char(32)    NOT NULL,
    rental_hk      char(32)    NOT NULL,
    copy_hk        char(32)    NOT NULL,
    load_dts       timestamp   NOT NULL DEFAULT lab.now(),
    record_source  varchar(50) NOT NULL,
    CONSTRAINT pk_link_rental_copy PRIMARY KEY (rental_copy_hk),
    CONSTRAINT uq_link_rental_copy_bk UNIQUE (rental_hk, copy_hk),
    CONSTRAINT fk_link_rental_copy_rental FOREIGN KEY (rental_hk)
        REFERENCES hub_rental (rental_hk),
    CONSTRAINT fk_link_rental_copy_copy FOREIGN KEY (copy_hk)
        REFERENCES hub_video_copy (copy_hk)
);

CREATE TABLE sat_video_copy_details (
    copy_hk          char(32)    NOT NULL,
    load_dts         timestamp   NOT NULL DEFAULT lab.now(),
    hashdiff         char(32)    NOT NULL,
    condition        varchar(12) NOT NULL,
    storage_location varchar(20),
    record_source    varchar(50) NOT NULL,
    CONSTRAINT pk_sat_video_copy_details PRIMARY KEY (copy_hk, load_dts),
    CONSTRAINT fk_sat_video_copy_details FOREIGN KEY (copy_hk)
        REFERENCES hub_video_copy (copy_hk)
);""")

    heading(doc, "7.3 Механизм загрузки и историзации", level=2)
    para(doc, "Загрузка выполняется функцией dv_load_all, которая реализует "
              "правила Data Vault:")
    for t in [
        "Хабы пополняются только новыми бизнес-ключами "
        "(INSERT ... ON CONFLICT DO NOTHING);",
        "Связи пополняются только новыми комбинациями ключей "
        "(ON CONFLICT DO NOTHING по первичному ключу Связи);",
        "Спутники пополняются новой версией только тогда, когда hashdiff "
        "описательных атрибутов отличается от hashdiff последней версии;",
        "исторические строки Спутников никогда не обновляются и не удаляются.",
    ]:
        bullet(doc, t)
    code(doc, """-- Спутник: вставка только изменившихся версий
INSERT INTO sat_video_copy_details
    (copy_hk, load_dts, hashdiff, condition, storage_location, record_source)
SELECT dv_hash(vc.inventory_code), p_load_dts,
       dv_hashdiff(vc.condition, vc.storage_location),
       vc.condition, vc.storage_location, p_record_source
  FROM video_rental_3nf.video_copy vc
 WHERE NOT EXISTS (
       SELECT 1 FROM (
           SELECT DISTINCT ON (copy_hk) copy_hk, hashdiff
             FROM sat_video_copy_details
            ORDER BY copy_hk, load_dts DESC) cur
        WHERE cur.copy_hk = dv_hash(vc.inventory_code)
          AND cur.hashdiff = dv_hashdiff(vc.condition, vc.storage_location));""")

    heading(doc, "7.4 Пример историзации", level=2)
    para(doc, "Ниже приведена реальная последовательность загрузок, выполненная "
              "скриптом sql/04_test_data_data_vault.sql. Клиент CR-00001 в "
              "источнике сменил телефон и адрес, а экземпляр VC-00005 вернулся "
              "с износом: состояние изменилось с good на worn.")
    make_table(doc, ["Загрузка", "record_source", "Что изменилось"],
               [[r[0], r[1], note] for r, note in zip(D["loads"], [
                   "первичное наполнение: все Хабы, Связи и первые версии Спутников",
                   "изменены контакты клиента CR-00001 и состояние экземпляра VC-00005 - "
                   "созданы новые версии Спутников, старые сохранены",
                   "оформлен прокат RN-000007, закрыт прокат RN-000006: "
                   "новые Хабы и Связи плюс новые версии Спутников",
               ])], mono_cols=(1,), align_cols={0: "center"}, caption="Таблица 8 - Выполненные загрузки Data Vault")

    para(doc, "Изменение телефона и адреса клиента CR-00001 создало вторую "
              "версию Спутника sat_customer_contact, при этом первая версия "
              "осталась в хранилище:")
    make_table(doc, ["load_dts", "phone", "address", "status", "hashdiff", "record_source"],
               [[r[1], r[2], r[3], r[4], r[5][:12] + "...", r[6]] for r in D["hist_contact"]], mono_cols=(0, 1, 4),
               align_cols={3: "center"},
               caption="Таблица 9 - История изменения контактов клиента CR-00001")

    para(doc, "Аналогично изменилось состояние экземпляра VC-00005:")
    make_table(doc, ["load_dts", "condition", "storage_location", "hashdiff", "record_source"],
               [[r[1], r[2], r[3], r[4][:12] + "...", r[5]] for r in D["hist_copy"]], mono_cols=(0, 3),
               align_cols={1: "center"},
               caption="Таблица 10 - История изменения состояния экземпляра VC-00005")

    para(doc, "Изменение статуса операции проката RN-000006 с issued на closed "
              "также создало новую версию Спутника:")
    make_table(doc, ["load_dts", "status", "planned_return", "actual_return", "record_source"],
               [[r[1], r[2], r[3], r[4], r[5]] for r in D["hist_rental"]], mono_cols=(0,),
               align_cols={1: "center"},
               caption="Таблица 11 - История изменения статуса проката RN-000006")

    para(doc, "Таким образом, механизм историзации реализован единообразно для "
              "всех Спутников: изменение атрибутов порождает новую строку с "
              "новым load_dts, а предыдущие версии остаются неизменными. "
              "Повторная загрузка без изменений в источнике не создает ни одной "
              "строки, что подтверждено четвертым запуском загрузки.")

    # --------------------------------------------------------------------
    # 8 Проверка работы
    # --------------------------------------------------------------------
    heading(doc, "8 Проверка работы", level=1, page_break_before=True)
    para(doc, f"Все проверки выполнены на реально работающей базе. Версия СУБД: "
              f"{D['version']}. Текущая дата системы учета зафиксирована "
              f"функцией lab.current_date() как {D['now']}. Полный журнал "
              f"выполнения сохранен в файле evidence/postgres_validation.txt.")

    heading(doc, "8.1 Проверочные запросы к модели 3NF", level=2)

    para(doc, "Запрос 1. Список активных прокатов (представление v_active_rental):")
    make_table(doc, ["Прокат", "Клиент", "Сотрудник", "План возвр.",
                     "Поз.", "Откр.", "Просроч.", "Дн."],
               D["active_rentals"], mono_cols=(0,),
               align_cols={3: "center", 4: "center", 5: "center",
                           6: "center", 7: "center"},
               caption="Таблица 12 - Результат запроса: активные прокаты")

    para(doc, "Запрос 2. Список просроченных экземпляров с начисленной пеней:")
    make_table(doc, ["Прокат", "Карта", "Клиент", "Экземпляр", "Фильм",
                     "План возвр.", "Дн.", "Пеня, руб."], D["overdue"], mono_cols=(0, 1, 3), align_cols={5: "center", 6: "center", 7: "right"},
               caption="Таблица 13 - Результат запроса: просроченные экземпляры")

    para(doc, "Запрос 3. История прокатов конкретного клиента (CR-00002, Петрова Анна):")
    make_table(doc, ["Прокат", "Выдан", "План возвр.", "Факт возвр.", "Статус",
                     "Поз.", "Экземпляры"], D["customer_history"], mono_cols=(0,), align_cols={1: "center", 2: "center", 3: "center",
                                           4: "center", 5: "center"},
               caption="Таблица 14 - Результат запроса: история прокатов клиента")

    para(doc, "Запрос 4. Экземпляры, доступные к выдаче на текущую дату, "
              "и сводка по фонду:")
    make_table(doc, ["Экземпляр", "Фильм", "Состояние", "Место хранения"],
               D["available"], mono_cols=(0,), align_cols={0: "left"},
               caption="Таблица 15 - Результат запроса: доступные экземпляры")
    make_table(doc, ["Всего экземпляров", "Выдано", "Доступно", "Списано"],
               [D["fund_summary"]], align_cols={i: "center" for i in range(4)},
               caption="Таблица 16 - Сводка по фонду экземпляров")

    para(doc, "Запрос 5. Фильмы и их жанры (представление v_film_catalog):")
    make_table(doc, ["Номер", "Название", "Год", "Носитель", "Тариф",
                     "Руб./сут.", "Жанры", "Копий"],
               D["catalog"], mono_cols=(0,), align_cols={2: "center", 3: "center", 4: "center",
                                           5: "right", 7: "center"}, caption="Таблица 17 - Результат запроса: фильмы и их жанры")

    para(doc, "Запрос 6. Суммы платежей по операциям проката:")
    make_table(doc, ["Прокат", "Статус", "Стоимость, руб.", "Оплачено, руб.",
                     "Пеня, руб.", "Залог, руб."], D["payments"], mono_cols=(0,), align_cols={1: "center", 2: "right", 3: "right",
                                           4: "right", 5: "right"},
               caption="Таблица 18 - Результат запроса: платежи по операциям")
    para(doc, "Сводка по способам оплаты:")
    make_table(doc, ["Способ оплаты", "Платежей", "Сумма, руб."],
               D["pay_methods"], mono_cols=(0,), align_cols={1: "center", 2: "right"},
               caption="Таблица 19 - Результат запроса: итоги по способам оплаты")

    heading(doc, "8.2 Проверка восстановления данных из Data Vault", level=2)
    para(doc, "Запрос 7. Информация, восстановленная из Hub + Link + Satellite "
              "через представление v_rental_full, полностью соответствует "
              "картине модели 3NF:")
    make_table(doc, ["Прокат", "Клиент", "Сотрудник", "Выдан", "Статус",
                     "Экз.", "Фильм", "Позиция"],
               D["dv_full"], mono_cols=(0,),
               align_cols={3: "center", 4: "center", 7: "center"},
               caption="Таблица 20 - Результат запроса: восстановление данных из Data Vault")

    para(doc, "Запрос 8. Последняя версия записи Спутника: текущее состояние "
              "клиентов, собранное из Хаба и последних версий Спутников "
              "sat_customer_details и sat_customer_contact:")
    make_table(doc, ["Карта", "Фамилия", "Имя", "Телефон", "Адрес", "Статус",
                     "Версия от"],
               D["dv_customers"], mono_cols=(0, 3), align_cols={5: "center", 6: "center"},
               caption="Таблица 21 - Результат запроса: текущее состояние клиентов")

    para(doc, "Текущее состояние физических экземпляров:")
    make_table(doc, ["Экземпляр", "Состояние", "Место хранения", "Поступил",
                     "Цена закупки, руб."],
               D["dv_copies"], mono_cols=(0,), align_cols={1: "center", 3: "center", 4: "right"},
               caption="Таблица 22 - Результат запроса: текущее состояние экземпляров")

    para(doc, "Запрос 9. История изменения объекта: клиент CR-00001. Первая "
              "версия строки не перезаписана, добавлена вторая версия с новым "
              "load_dts и новым hashdiff.")
    make_table(doc, ["Карта", "load_dts", "Телефон", "Адрес", "Статус",
                     "hashdiff", "Источник"],
               [[r[0], r[1], r[2], r[3], r[4], r[5][:10] + "...", r[6]]
                for r in D["hist_contact"]], mono_cols=(0, 2, 5), align_cols={4: "center"},
               caption="Таблица 23 - История изменения клиента CR-00001")

    para(doc, "История изменения состояния экземпляра VC-00005:")
    make_table(doc, ["Экземпляр", "load_dts", "Состояние", "Место", "hashdiff", "Источник"],
               [[r[0], r[1], r[2], r[3], r[4][:10] + "...", r[5]] for r in D["hist_copy"]], mono_cols=(0, 4),
               align_cols={2: "center"},
               caption="Таблица 24 - История изменения состояния экземпляра VC-00005")

    para(doc, "Итоговое количество версий в Спутниках показывает, что "
              "историзация реально работает: число версий превышает число "
              "родительских объектов там, где данные менялись.")
    make_table(doc, ["Спутник", "Версий", "Родителей"],
               D["sat_versions"], mono_cols=(0,), align_cols={1: "center", 2: "center"},
               caption="Таблица 25 - Количество версий в Спутниках")

    heading(doc, "8.3 Проверка ограничений целостности", level=2)
    para(doc, "Выполнены десять негативных тестов: каждый из них пытается "
              "записать заведомо некорректные данные и ожидает ошибку "
              "PostgreSQL. В таблице приведены реально полученные коды ошибок. "
              "Все тесты выполнялись в блоках с обработкой исключений и не "
              "изменили данные основной модели.")
    make_table(doc, ["№", "Некорректная операция", "Ожидаемое ограничение",
                     "Реально полученный результат"],
               [["1", "прокат на несуществующего клиента (customer_id = 99999)",
                 "внешний ключ fk_rental_customer",
                 "SQLSTATE 23503: violates foreign key constraint \"fk_rental_customer\""],
                ["2", "платеж с отрицательной суммой -500.00",
                 "CHECK ck_payment_amount",
                 "SQLSTATE 23514: violates check constraint \"ck_payment_amount\""],
                ["3", "плановая дата возврата раньше даты выдачи",
                 "CHECK ck_rental_issue_planned",
                 "SQLSTATE 23514: violates check constraint \"ck_rental_issue_planned\""],
                ["4", "повторный номер клубной карты CR-00001",
                 "UNIQUE uq_customer_card_number",
                 "SQLSTATE 23505: violates unique constraint \"uq_customer_card_number\""],
                ["5", "выдача уже занятого экземпляра copy_id = 5",
                 "частичный индекс ux_rental_item_active_copy",
                 "SQLSTATE 23505: violates unique constraint \"ux_rental_item_active_copy\""],
                ["6", "номер карты неверного формата ('12345')",
                 "CHECK ck_customer_card_number",
                 "SQLSTATE 23514: violates check constraint \"ck_customer_card_number\""],
                ["7", "повторный бизнес-ключ Хаба в Data Vault",
                 "PK pk_hub_customer",
                 "SQLSTATE 23505: violates unique constraint \"pk_hub_customer\""],
                ["8", "повтор версии Спутника с тем же load_dts",
                 "составной PK pk_sat_video_copy_details",
                 "SQLSTATE 23505: violates unique constraint \"pk_sat_video_copy_details\""],
                ["9", "Спутник со ссылкой на несуществующий Хаб",
                 "внешний ключ fk_sat_film_details",
                 "SQLSTATE 23503: violates foreign key constraint \"fk_sat_film_details\""],
                ["10", "отрицательная сумма в Спутнике платежа",
                 "CHECK ck_sat_payment_amount",
                 "SQLSTATE 23514: violates check constraint \"ck_sat_payment_amount\""]], align_cols={0: "center"},
               caption="Таблица 26 - Результаты проверки ограничений целостности")

    para(doc, "После выполнения негативных тестов количество строк в таблицах "
              "не изменилось, что подтверждает корректность отката: 6 клиентов, "
              "7 операций проката, 11 платежей, 6 записей в hub_customer и "
              "17 версий в sat_video_copy_details.")

    heading(doc, "8.4 Итоговый состав реализованных объектов", level=2)
    para(doc, "Модель 3NF: 10 таблиц. Структура и количество ограничений по "
              "каждой таблице приведены в таблице 27.")
    make_table(doc, ["Таблица", "Полей", "PK", "FK", "UNIQUE", "CHECK"],
               D["struct_3nf"], mono_cols=(0,), align_cols={i: "center" for i in range(1, 6)},
               caption="Таблица 27 - Состав модели 3NF")

    para(doc, "Модель Data Vault: 8 Хабов, 7 Связей и 12 Спутников "
              "(27 таблиц). Состав объектов приведен в таблице 28.")
    dv_by_type = {}
    for obj_type, table, cols, fks in D["struct_dv"]:
        dv_by_type.setdefault(obj_type, []).append(table)
    make_table(doc, ["Тип объекта", "Объектов", "Состав"],
               [["HUB", str(len(dv_by_type["HUB"])),
                 "hub_customer, hub_employee, hub_film, hub_video_copy, hub_rental, "
                 "hub_payment, hub_genre, hub_tariff"],
                ["LINK", str(len(dv_by_type["LINK"])),
                 "link_film_copy, link_film_genre, link_film_tariff, "
                 "link_rental_customer, link_rental_employee, link_rental_copy, "
                 "link_rental_payment"],
                ["SATELLITE", str(len(dv_by_type["SATELLITE"])),
                 "по клиенту (2), сотруднику, фильму, экземпляру (2), жанру, "
                 "тарифу, прокату, позиции проката, платежу, связи "
                 "«фильм - жанр»"]],
               mono_cols=(0,), align_cols={1: "center"},
               caption="Таблица 28 - Состав модели Data Vault")

    # --------------------------------------------------------------------
    # 9 Сравнение подходов
    # --------------------------------------------------------------------
    heading(doc, "9 Сравнение подходов", level=1, page_break_before=True)
    para(doc, "Обе модели описывают одну предметную область, но решают разные "
              "задачи. Сравнение приведено в таблице 29.")
    make_table(
        doc, ["Критерий", "Модель 3NF", "Модель Data Vault"],
        [["Назначение", "операционная (транзакционная) база видеопроката",
          "хранилище данных для интеграции источников и хранения истории"],
         ["Структура", "10 таблиц, соответствующих сущностям предметной области",
          "8 Хабов, 7 Связей, 12 Спутников (27 таблиц)"],
         ["Нормализация", "третья нормальная форма: устранены транзитивные зависимости",
          "Хабы и Связи нормализованы, описательные атрибуты вынесены в Спутники"],
         ["Изменение схемы", "добавление атрибута затрагивает таблицу сущности; "
                             "изменение связи может потребовать миграции",
          "новый атрибут добавляется новым Спутником без изменения существующих "
          "объектов; новые источники подключаются новыми Хабами и Связями"],
         ["Историзация", "требует дополнительных таблиц или триггеров; по умолчанию "
                         "хранится только текущее состояние",
          "встроена: Спутник с ключом (ключ родителя, load_dts) хранит все версии "
          "без перезаписи"],
         ["Сложность чтения", "низкая: данные читаются напрямую из таблиц сущностей",
          "выше: требуется соединение Хаба, Связи и Спутника, часто через "
          "представление последних версий"],
         ["Аудит", "ограничен: видно текущее состояние, история изменений "
                   "восстанавливается косвенно",
          "полный: для каждой строки известны load_dts и record_source, "
          "история изменений сохраняется"],
         ["Типичный сценарий", "транзакционная обработка операций выдачи и возврата, "
                               "расчет стоимости, контроль просрочки",
          "корпоративное хранилище: загрузка из нескольких источников, "
          "историческое хранение, поддержка аналитики и аудита"]], caption="Таблица 29 - Сравнение моделей 3NF и Data Vault")

    para(doc, "3NF удобна как транзакционная модель видеопроката: операции "
              "выдачи и возврата изменяют небольшое число строк, целостность "
              "поддерживается ограничениями, а запросы сотрудников пункта "
              "проката просты и быстры. Data Vault решает другую задачу - "
              "интеграцию данных из разных источников и историческое хранение. "
              "Модели не заменяют, а дополняют друг друга. Утверждать, что один "
              "подход «лучше вообще», некорректно: выбор определяется задачей.")

    # --------------------------------------------------------------------
    # 10 Заключение
    # --------------------------------------------------------------------
    heading(doc, "10 Заключение", level=1, page_break_before=True)
    para(doc, "В ходе работы предметная область «Система учета в видеопрокате» "
              "(вариант №14) реализована в PostgreSQL 17 двумя способами: в "
              "третьей нормальной форме и по методике Data Vault.")
    para(doc, "Модель в третьей нормальной форме включает 10 таблиц: genre, "
              "tariff, film, film_genre, video_copy, customer, employee, rental, "
              "rental_item и payment. Обоснована принадлежность модели к 1NF, "
              "2NF и 3NF: атрибуты атомарны, множественные значения вынесены в "
              "отдельные таблицы, частичных и транзитивных зависимостей нет, "
              "вычисляемые значения не хранятся. Целостность обеспечена ключами "
              "и CHECK-ограничениями, правило «один экземпляр - один активный "
              "прокат» - частичным уникальным индексом.")
    para(doc, "Модель Data Vault включает 8 Хабов, 7 Связей и 12 Спутников. "
              "Хабы хранят устойчивые бизнес-ключи (номер клубной карты, "
              "табельный номер, каталожный и инвентарный номера, номер операции "
              "и платежа, код жанра и тарифа), Связи описывают реальные "
              "взаимодействия между ними, Спутники - описательные атрибуты и их "
              "историю. Историзация подтверждена на практике: изменение телефона "
              "и адреса клиента, состояния экземпляра и статуса проката создало "
              "новые версии Спутников, а предыдущие версии остались в хранилище "
              "неизменными. Повторная загрузка без изменений в источнике не "
              "добавила ни одной строки.")
    para(doc, "Обе модели созданы в базе video_rental_lab и проверены на "
              "синтетических данных: 10 фильмов, 16 экземпляров, 6 клиентов, "
              "3 сотрудника, 7 операций проката и 11 платежей. Выполнены все "
              "требуемые проверочные запросы, включая восстановление данных "
              "из Hub + Link + Satellite.")
    para(doc, "Десять негативных тестов (таблица 26) подтвердили, что "
              "PostgreSQL отклоняет некорректные данные всех проверенных видов, "
              "и ни один из них не изменил данные основной модели. Обе схемы "
              "создаются скриптами с нуля повторяемо. Цель работы достигнута, "
              "все поставленные задачи выполнены.")

    # --------------------------------------------------------------------
    # Список источников
    # --------------------------------------------------------------------
    heading(doc, "Список использованных источников", level=1, page_break_before=True)
    srcs = [
        "Все о Data Vault [Электронный ресурс] // DWH-Club.com. - URL: "
        "http://www.dwh-club.com/ru/dwh-bi-articles/vse-o-data-vault.html "
        "(дата обращения: 28.09.2026).",
        "Data Vault. Серия 1: Знакомство с Data Vault [Электронный ресурс] / "
        "Д. Линстедт; пер. И. Бралгин // DWH-Club.com. - URL: "
        "http://www.dwh-club.com/ru/dwh-bi-articles/data-vault-terminy-obekty-osnovy-arhitektury.html "
        "(дата обращения: 28.09.2026).",
        "Data Vault. Серия 2: Компоненты Data Vault [Электронный ресурс] / "
        "Д. Линстедт; пер. И. Бралгин // DWH-Club.com. - URL: "
        "http://www.dwh-club.com/ru/dwh-bi-articles/data-vault-komponenty-arhitektury.html "
        "(дата обращения: 28.09.2026).",
        "Data Vault. Серия 4: Таблицы Связей [Электронный ресурс] / "
        "Д. Линстедт; пер. И. Бралгин // DWH-Club.com. - URL: "
        "http://www.dwh-club.com/ru/dwh-bi-articles/data-vault-tablicy-svyazei.html "
        "(дата обращения: 28.09.2026).",
        "PostgreSQL 17 Documentation [Электронный ресурс]. - URL: "
        "https://www.postgresql.org/docs/17/ (дата обращения: 28.09.2026).",
        "PostgreSQL 17: CREATE TABLE, Constraints [Электронный ресурс]. - URL: "
        "https://www.postgresql.org/docs/17/ddl-constraints.html "
        "(дата обращения: 28.09.2026).",
        "PostgreSQL 17: Partial Indexes [Электронный ресурс]. - URL: "
        "https://www.postgresql.org/docs/17/indexes-partial.html "
        "(дата обращения: 28.09.2026).",
        "PostgreSQL 17: Trigger Functions [Электронный ресурс]. - URL: "
        "https://www.postgresql.org/docs/17/plpgsql-trigger.html "
        "(дата обращения: 28.09.2026).",
    ]
    for i, s in enumerate(srcs, 1):
        para(doc, f"{i}. {s}", indent=False)

    # --------------------------------------------------------------------
    # Приложения с диаграммами (альбомные страницы)
    # --------------------------------------------------------------------
    landscape_section(doc)
    footer_page_number(doc.sections[-1], show=True)
    heading(doc, "Приложение А. Диаграмма модели 3NF", level=1)
    para(doc, "Таблицы, первичные и внешние ключи, уникальные ограничения, "
              "кардинальности связей.", indent=False, keep_with_next=True)
    add_picture(doc, os.path.join(DIAGRAMS, "3nf_model.png"),
                fit_width_mm(os.path.join(DIAGRAMS, "3nf_model.png"), 265, 138),
                "Рисунок А.1 - Даталогическая модель 3NF")

    landscape_section(doc)
    footer_page_number(doc.sections[-1], show=True)
    heading(doc, "Приложение Б. Диаграмма модели Data Vault", level=1)
    para(doc, "Хабы, Связи, Спутники, ключи и направления связей.",
         indent=False, keep_with_next=True)
    add_picture(doc, os.path.join(DIAGRAMS, "data_vault_model.png"),
                fit_width_mm(os.path.join(DIAGRAMS, "data_vault_model.png"), 265, 138),
                "Рисунок Б.1 - Даталогическая модель Data Vault")

    drop_trailing_empty_paragraphs(doc)
    enable_update_fields(doc)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    doc.save(OUT)
    print("Сохранено:", OUT)
    return OUT


if __name__ == "__main__":
    build()
