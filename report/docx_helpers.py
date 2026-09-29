#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Вспомогательные функции для сборки отчета Word в стиле учебных работ."""
from PIL import ImageFont as _TTF

from docx.enum.section import WD_ORIENT, WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import (WD_ALIGN_PARAGRAPH, WD_BREAK,
                            WD_TAB_ALIGNMENT, WD_TAB_LEADER)
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Mm, Pt, RGBColor

FONT = "Times New Roman"
BODY_PT = 14
TABLE_PT = 12
CAPTION_PT = 12


# --------------------------------------------------------------------------
# Оформление символов и абзацев
# --------------------------------------------------------------------------
def style_run(run, size=BODY_PT, bold=False, italic=False, color=None,
              font=FONT):
    run.font.name = font
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)
    rpr = run._element.get_or_add_rPr()
    rf = rpr.find(qn("w:rFonts"))
    if rf is None:
        rf = OxmlElement("w:rFonts")
        rpr.insert(0, rf)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        rf.set(qn(attr), font)
    return run


def para(doc, text="", size=BODY_PT, bold=False, italic=False, align="justify",
         indent=True, space_after=0, space_before=0, line=1.5, style=None,
         color=None, keep_with_next=False):
    p = doc.add_paragraph(style=style)
    pf = p.paragraph_format
    pf.alignment = {"justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
                    "center": WD_ALIGN_PARAGRAPH.CENTER,
                    "left": WD_ALIGN_PARAGRAPH.LEFT,
                    "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
    pf.line_spacing = line
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(space_before)
    # отступ первой строки задается свойством абзаца, а не пробелами
    pf.first_line_indent = Cm(1.25) if (indent and align == "justify") else Cm(0)
    pf.keep_with_next = keep_with_next
    if text:
        style_run(p.add_run(text), size=size, bold=bold, italic=italic, color=color)
    return p


def heading(doc, text, level=1, page_break_before=False):
    """Заголовок с настоящей иерархией стилей Word.

    Разрыв страницы задается свойством абзаца page_break_before, а не
    отдельным абзацем с разрывом: иначе на стыке страниц появляется
    пустая страница.
    """
    p = doc.add_heading(text, level=level)
    pf = p.paragraph_format
    if page_break_before:
        pf.page_break_before = True
    pf.line_spacing = 1.5
    pf.space_before = Pt(12 if level == 1 else 8)
    pf.space_after = Pt(6)
    pf.first_line_indent = Cm(0)
    pf.keep_with_next = True
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in p.runs:
        style_run(run, size=16 if level == 1 else (15 if level == 2 else 14),
                  bold=True, color=(0, 0, 0))
    return p


def bullet(doc, text, size=BODY_PT):
    p = doc.add_paragraph(style="List Bullet")
    pf = p.paragraph_format
    pf.line_spacing = 1.5
    pf.space_after = Pt(0)
    pf.first_line_indent = Cm(0)
    pf.left_indent = Cm(1.25)
    style_run(p.add_run(text), size=size)
    return p


def code(doc, text, size=10):
    """Фрагмент SQL: монospace, без отступа первой строки, одинарный интервал."""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = 1.0
    pf.space_before = Pt(4)
    pf.space_after = Pt(6)
    pf.first_line_indent = Cm(0)
    pf.left_indent = Cm(0.5)
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for i, line in enumerate(text.rstrip("\n").split("\n")):
        if i:
            style_run(p.add_run(), size=size).add_break()
        style_run(p.add_run(line), size=size, font="Courier New")
    return p


def caption(doc, text, size=CAPTION_PT):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.line_spacing = 1.0
    pf.space_before = Pt(4)
    pf.space_after = Pt(8)
    pf.first_line_indent = Cm(0)
    pf.keep_with_next = True
    style_run(p.add_run(text), size=size)
    return p


def table_caption(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf.line_spacing = 1.0
    pf.space_before = Pt(8)
    pf.space_after = Pt(4)
    pf.first_line_indent = Cm(0)
    pf.keep_with_next = True
    style_run(p.add_run(text), size=CAPTION_PT)
    return p


# --------------------------------------------------------------------------
# Таблицы
# --------------------------------------------------------------------------
def set_cell(cell, text, size=TABLE_PT, bold=False, align="left", mono=False,
             shade=None):
    cell.text = ""
    p = cell.paragraphs[0]
    pf = p.paragraph_format
    pf.alignment = {"left": WD_ALIGN_PARAGRAPH.LEFT,
                    "center": WD_ALIGN_PARAGRAPH.CENTER,
                    "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
    pf.line_spacing = 1.0
    pf.space_before = Pt(2)
    pf.space_after = Pt(2)
    pf.first_line_indent = Cm(0)
    style_run(p.add_run(str(text)), size=size, bold=bold,
              font="Courier New" if mono else FONT)
    if shade:
        tcpr = cell._tc.get_or_add_tcPr()
        sh = OxmlElement("w:shd")
        sh.set(qn("w:val"), "clear")
        sh.set(qn("w:color"), "auto")
        sh.set(qn("w:fill"), shade)
        tcpr.append(sh)


def make_table(doc, headers, rows, widths=None, size=TABLE_PT, mono_cols=(),
               align_cols=None, shade_header="DCE6F1", caption=None,
               repeat_header=True, total_cm=17.0):
    """Таблица с реально примененными ширинами колонок.

    Ширины задаются одновременно в tblGrid, в свойствах колонок и в каждой
    ячейке: иначе Word и LibreOffice пересчитывают сетку по содержимому и
    заголовки начинают переноситься посреди слова.
    """
    if caption:
        table_caption(doc, caption)
    # кегль уменьшается, пока заголовки не перестанут переноситься посреди слова
    rows = [[breakable(v) for v in r] for r in rows]
    headers = [breakable(h) for h in headers]
    size = fit_font_size(headers, rows, total_cm, size, mono_cols)
    if widths is None:
        widths = auto_widths(headers, rows, total_cm, size, mono_cols, align_cols)
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False

    align_cols = align_cols or {}
    for i, h in enumerate(headers):
        set_cell(t.rows[0].cells[i], h, size=size, bold=True,
                 align=align_cols.get(i, "center"), shade=shade_header)
    if repeat_header:
        trpr = t.rows[0]._tr.get_or_add_trPr()
        th = OxmlElement("w:tblHeader")
        th.set(qn("w:val"), "true")
        trpr.append(th)

    for r in rows:
        cells = t.add_row().cells
        for i, v in enumerate(r):
            set_cell(cells[i], breakable(v), size=size, mono=(i in mono_cols),
                     align=align_cols.get(i, "left"))

    apply_table_widths(t, widths)
    # Небольшие таблицы держим целиком на одной странице, длинные разрешаем
    # разрывать: иначе на стыке появляются страницы из одной-двух строк.
    if len(rows) <= 11:
        keep_table_together(t)
    else:
        # у длинных таблиц запрещаем только разрыв внутри строки и
        # повторяем строку заголовков на новой странице
        for row in t.rows:
            trpr = row._tr.get_or_add_trPr()
            cant = OxmlElement("w:cantSplit")
            trpr.append(cant)
    return t


def keep_table_together(t):
    """Запрещает разрыв строк таблицы и удерживает ее целиком на странице."""
    for i, row in enumerate(t.rows):
        trpr = row._tr.get_or_add_trPr()
        cant = OxmlElement("w:cantSplit")
        trpr.append(cant)
        if i < len(t.rows) - 1:
            for c in row.cells:
                for p in c.paragraphs:
                    p.paragraph_format.keep_with_next = True
    # заголовок таблицы тоже удерживаем со следующим абзацем
    for c in t.rows[0].cells:
        for p in c.paragraphs:
            p.paragraph_format.keep_with_next = True


def measure_cm(text, size_pt, bold=False, mono=False):
    """Ширина строки в сантиметрах для шрифта Times New Roman / Courier New."""
    path = ("/System/Library/Fonts/Supplemental/Courier New%s.ttf"
            % (" Bold" if bold else "")) if mono else \
           ("/System/Library/Fonts/Supplemental/Times New Roman%s.ttf"
            % (" Bold" if bold else ""))
    key = (path, int(round(size_pt * 4)))
    if key not in _FONT_CACHE:
        _FONT_CACHE[key] = _TTF.truetype(path, key[1])
    return _FONT_CACHE[key].getlength(text) / 4 / 72 * 2.54


_FONT_CACHE = {}


# Внутренние отступы ячейки задаются явно (w:tblCellMar): по умолчанию Word
# резервирует 0.19 см с каждой стороны, из-за чего широкие таблицы не
# помещаются в полосу набора при кегле 12 pt. 0.08 см достаточно, чтобы текст
# не касался рамки, и оставляет место для данных.
CELL_MARGIN_TWIPS = 45          # 0.079 см
PAD_CM = CELL_MARGIN_TWIPS / 567 * 2 + 0.05
ZWSP = "\u200b"                 # мягкий перенос внутри длинных токенов


def breakable(text, limit=14):
    """Разрешает перенос длинных неразрывных токенов.

    Значения вида video_rental_3nf#initial, 4272ee9344a657979d817c13c397d829
    или user@example.com не содержат пробелов, поэтому Word вынужден
    расширять колонку под самый длинный токен. Мягкий перенос (U+200B)
    после разделителей и через равные интервалы не меняет отображаемый
    текст, но позволяет колонке быть узкой.
    """
    out = []
    for word in str(text).split(" "):
        if len(word) <= limit:
            out.append(word)
            continue
        buf = ""
        for i, ch in enumerate(word):
            buf += ch
            if ch in "#-/:@._," and i + 1 < len(word):
                buf += ZWSP
            elif (i + 1) % limit == 0 and i + 1 < len(word):
                buf += ZWSP
        out.append(buf)
    return " ".join(out)


def column_minimums(headers, rows, size, mono_cols=()):
    """Минимальные ширины колонок: самое длинное слово в колонке.

    Заголовки полужирные, данные - моноширинные в колонках mono_cols.
    """
    n = len(headers)
    mins, wants = [], []
    for i in range(n):
        texts = [headers[i]] + [r[i] if i < len(r) else "" for r in rows]
        m = w = 0.0
        for k, txt in enumerate(texts):
            mono = (i in mono_cols) and k > 0
            bold = (k == 0)
            for line in str(txt).split("\n"):
                if line.strip():
                    w = max(w, measure_cm(line, size, bold, mono))
                for word in line.replace(ZWSP, " ").split():
                    m = max(m, measure_cm(word, size, bold, mono))
        mins.append(m + PAD_CM)
        wants.append(max(w + PAD_CM, m + PAD_CM))
    return mins, wants


def fit_font_size(headers, rows, total_cm, size, mono_cols=(), min_size=9.0):
    """Уменьшает кегль таблицы, пока минимальные ширины колонок помещаются
    в полосу набора. Возвращает выбранный кегль."""
    s = size
    while s > min_size:
        mins, _ = column_minimums(headers, rows, s, mono_cols)
        if sum(mins) <= total_cm:
            return s
        s -= 0.5
    return min_size


def auto_widths(headers, rows, total_cm, size=TABLE_PT, mono_cols=(),
                align_cols=None):
    """Подбирает ширины колонок так, чтобы ни одно слово не переносилось."""
    mins, wants = column_minimums(headers, rows, size, mono_cols)
    if sum(mins) > total_cm:        # страховка: сжимаем пропорционально
        k = total_cm / sum(mins)
        return [round(x * k, 2) for x in mins]
    extra = total_cm - sum(mins)
    span = sum(w - m for w, m in zip(wants, mins)) or 1.0
    widths = [round(m + extra * (w - m) / span, 2) for w, m in zip(wants, mins)]
    diff = round(total_cm - sum(widths), 2)
    widths[-1] = round(widths[-1] + diff, 2)
    return widths


def apply_table_widths(t, widths_cm):
    """Жестко фиксирует сетку таблицы (tblGrid + колонки + ячейки)."""
    tbl = t._tbl
    tblpr = tbl.tblPr

    for tag in ("w:tblLayout", "w:tblW"):
        el = tblpr.find(qn(tag))
        if el is not None:
            tblpr.remove(el)
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tblpr.append(layout)
    tblw = OxmlElement("w:tblW")
    tblw.set(qn("w:type"), "dxa")
    tblw.set(qn("w:w"), str(int(sum(widths_cm) * 567)))
    tblpr.append(tblw)

    # внутренние отступы ячеек
    for tag in ("w:tblCellMar",):
        el = tblpr.find(qn(tag))
        if el is not None:
            tblpr.remove(el)
    cellmar = OxmlElement("w:tblCellMar")
    for edge, val in (("top", 15), ("left", CELL_MARGIN_TWIPS),
                      ("bottom", 15), ("right", CELL_MARGIN_TWIPS)):
        e = OxmlElement(f"w:{edge}")
        e.set(qn("w:w"), str(val))
        e.set(qn("w:type"), "dxa")
        cellmar.append(e)
    tblpr.append(cellmar)

    grid = tbl.find(qn("w:tblGrid"))
    if grid is not None:
        tbl.remove(grid)
    grid = OxmlElement("w:tblGrid")
    for w in widths_cm:
        gc = OxmlElement("w:gridCol")
        gc.set(qn("w:w"), str(int(w * 567)))
        grid.append(gc)
    tblpr.addnext(grid)

    for i, w in enumerate(widths_cm):
        if i < len(t.columns):
            t.columns[i].width = Cm(w)
        for row in t.rows:
            if i < len(row.cells):
                row.cells[i].width = Cm(w)


# --------------------------------------------------------------------------
# Секции, поля, нумерация страниц
# --------------------------------------------------------------------------
def set_margins(section, top=20, bottom=20, left=30, right=10,
                header=15, footer=15, size=None):
    """Поля страницы в миллиметрах. size - размер листа в мм (по умолчанию A4
    с учетом уже установленной ориентации раздела)."""
    if size is None:
        landscape = (section.page_width is not None
                     and section.page_width > section.page_height)
        size = (297, 210) if landscape else (210, 297)
    section.page_width, section.page_height = Mm(size[0]), Mm(size[1])
    section.top_margin = Mm(top)
    section.bottom_margin = Mm(bottom)
    section.left_margin = Mm(left)
    section.right_margin = Mm(right)
    section.header_distance = Mm(header)
    section.footer_distance = Mm(footer)


def add_page_field(paragraph):
    run = paragraph.add_run()
    fld = OxmlElement("w:fldSimple")
    fld.set(qn("w:instr"), "PAGE   \\* MERGEFORMAT")
    r = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    rf = OxmlElement("w:rFonts")
    for a in ("w:ascii", "w:hAnsi", "w:cs"):
        rf.set(qn(a), FONT)
    rpr.append(rf)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), "24")
    rpr.append(sz)
    r.append(rpr)
    fld.append(r)
    paragraph._p.append(fld)
    return paragraph


def footer_page_number(section, show=True):
    """Номер страницы по центру листа.

    Колонтитул размещается в полосе набора, поэтому при несимметричных полях
    (слева 30 мм, справа 10 мм) обычное центрирование сдвигает номер вправо.
    Отрицательный отступ первой строки расширяет полосу абзаца до левого края
    симметрично полям, и номер встает ровно по центру листа.
    """
    footer = section.footer
    footer.is_linked_to_previous = False
    p = footer.paragraphs[0] if footer.paragraphs else footer.add_paragraph()
    for r in list(p.runs):
        r._element.getparent().remove(r._element)
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    shift = section.left_margin - section.right_margin
    pf.left_indent = -shift if shift > 0 else Cm(0)
    pf.line_spacing = 1.0
    pf.first_line_indent = Cm(0)
    pf.space_after = Pt(0)
    pf.space_before = Pt(0)
    if show:
        add_page_field(p)


def enable_update_fields(doc):
    """Word обновит оглавление и поля при открытии документа."""
    settings = doc.settings.element
    for tag in ("w:updateFields",):
        el = settings.find(qn(tag))
        if el is None:
            el = OxmlElement(tag)
            settings.append(el)
        el.set(qn("w:val"), "true")


def add_toc_field(doc, cached_entries=None, levels="1-3"):
    """Вставляет поле оглавления TOC.

    cached_entries - список (текст, номер страницы, уровень). Кэшированное
    содержимое показывается любым просмотрщиком, а Word может пересчитать
    оглавление самостоятельно при открытии документа.
    """
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = 1.5
    pf.first_line_indent = Cm(0)
    pf.space_after = Pt(0)

    def fld(kind):
        r = OxmlElement("w:r")
        fc = OxmlElement("w:fldChar")
        fc.set(qn("w:fldCharType"), kind)
        r.append(fc)
        return r

    p._p.append(fld("begin"))
    instr_r = OxmlElement("w:r")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f' TOC \\o "{levels}" \\h \\z \\u '
    instr_r.append(instr)
    p._p.append(instr_r)
    p._p.append(fld("separate"))

    # абзацы кэшированного оглавления создаются сразу после абзаца с полем
    anchor = p._p
    body = anchor.getparent()
    idx = list(body).index(anchor)
    made = []
    for text, page, lvl in (cached_entries or []):
        tp = doc.add_paragraph()
        tpf = tp.paragraph_format
        tpf.line_spacing = 1.5
        tpf.first_line_indent = Cm(0)
        tpf.left_indent = Cm(0.75 * (lvl - 1))
        tpf.space_after = Pt(0)
        tpf.tab_stops.add_tab_stop(Cm(16.0), WD_TAB_ALIGNMENT.RIGHT,
                                   WD_TAB_LEADER.DOTS)
        style_run(tp.add_run(f"{text}\t{page}"), size=BODY_PT)
        made.append(tp._p)

    for i, el in enumerate(made):
        body.remove(el)
        body.insert(idx + 1 + i, el)

    # завершение поля ставится после кэшированных абзацев
    end_el = fld("end")
    body.remove(end_el) if end_el.getparent() is not None else None
    last = made[-1] if made else anchor
    last.addnext(end_el)
    return p


def landscape_section(doc):
    """Новый раздел с альбомной ориентацией и узкими полями (для диаграмм)."""
    s = doc.add_section(WD_SECTION.NEW_PAGE)
    s.orientation = WD_ORIENT.LANDSCAPE
    set_margins(s, top=15, bottom=15, left=15, right=15, size=(297, 210))
    return s


def portrait_section(doc):
    s = doc.add_section(WD_SECTION.NEW_PAGE)
    s.orientation = WD_ORIENT.PORTRAIT
    set_margins(s, size=(210, 297))
    return s


def fit_width_mm(path, max_w_mm, max_h_mm):
    """Ширина рисунка по его пропорциям, чтобы он помещался в отведенную
    область (ширина x высота)."""
    from PIL import Image as _Img
    with _Img.open(path) as im:
        w, h = im.size
    by_w = max_w_mm
    by_h = max_h_mm * w / h
    return round(min(by_w, by_h), 1)


def add_picture(doc, path, width_mm, caption_text=None):
    """Вставляет рисунок и подпись как единый неразрывный блок.

    Блок оформлен невидимой таблицей из одной ячейки с запретом разрыва
    строки (w:cantSplit): если рисунок с подписью не помещается на текущей
    странице, Word и LibreOffice переносят их на следующую целиком, поэтому
    подпись никогда не отрывается от рисунка.
    """
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    cell = t.rows[0].cells[0]
    cell.width = Mm(width_mm)

    trpr = t.rows[0]._tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    trpr.append(cant)

    # невидимые границы
    tblpr = t._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "none")
        el.set(qn("w:sz"), "0")
        borders.append(el)
    tblpr.append(borders)

    # рисунок
    p1 = cell.paragraphs[0]
    p1.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p1.paragraph_format.first_line_indent = Cm(0)
    p1.paragraph_format.space_before = Pt(6)
    p1.paragraph_format.space_after = Pt(2)
    p1.paragraph_format.line_spacing = 1.0
    p1.add_run().add_picture(path, width=Mm(width_mm))

    # подпись
    if caption_text:
        p2 = cell.add_paragraph()
        p2.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.first_line_indent = Cm(0)
        p2.paragraph_format.space_before = Pt(0)
        p2.paragraph_format.space_after = Pt(6)
        p2.paragraph_format.line_spacing = 1.0
        style_run(p2.add_run(caption_text), size=CAPTION_PT)

    # пустой абзац после таблицы, чтобы следующий текст не прилипал
    after = doc.add_paragraph()
    after.paragraph_format.space_after = Pt(0)
    after.paragraph_format.space_before = Pt(0)
    after.paragraph_format.line_spacing = 1.0
    return t


def drop_trailing_empty_paragraphs(doc):
    """Удаляет пустые абзацы в конце разделов (иначе появляются пустые
    страницы, особенно в альбомных приложениях)."""
    body = doc.element.body
    for sect in body.findall(qn("w:sectPr")):
        prev = sect.getprevious()
        while prev is not None and prev.tag == qn("w:p"):
            if prev.xpath(".//w:t") or prev.xpath(".//w:drawing") \
                    or prev.xpath(".//w:br"):
                break
            nxt = prev.getprevious()
            body.remove(prev)
            prev = nxt


def landscape_section(doc):
    """Новый раздел с альбомной ориентацией и узкими полями (для диаграмм)."""
    s = doc.add_section(WD_SECTION.NEW_PAGE)
    s.orientation = WD_ORIENT.LANDSCAPE
    set_margins(s, top=15, bottom=15, left=15, right=15, size=(297, 210))
    return s


def portrait_section(doc):
    s = doc.add_section(WD_SECTION.NEW_PAGE)
    s.orientation = WD_ORIENT.PORTRAIT
    set_margins(s, size=(210, 297))
    return s


def fit_width_mm(path, max_w_mm, max_h_mm):
    """Ширина рисунка по его пропорциям, чтобы он помещался в отведенную
    область (ширина x высота)."""
    from PIL import Image as _Img
    with _Img.open(path) as im:
        w, h = im.size
    by_w = max_w_mm
    by_h = max_h_mm * w / h
    return round(min(by_w, by_h), 1)


def add_picture(doc, path, width_mm, caption_text=None):
    """Вставляет рисунок и его подпись одним абзацем.

    Рисунок и подпись находятся в одном абзаце (подпись отделена переводом
    строки), поэтому ни один просмотрщик не может разорвать их между
    страницами.
    """
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.first_line_indent = Cm(0)
    pf.space_before = Pt(6)
    pf.space_after = Pt(8)
    pf.line_spacing = 1.0
    pf.keep_together = True
    run = p.add_run()
    run.add_picture(path, width=Mm(width_mm))
    if caption_text:
        style_run(run, size=CAPTION_PT)
        run.add_break()
        style_run(p.add_run(caption_text), size=CAPTION_PT)
    return p


def landscape_section(doc):
    """Новый раздел с альбомной ориентацией и узкими полями (для диаграмм)."""
    s = doc.add_section(WD_SECTION.NEW_PAGE)
    s.orientation = WD_ORIENT.LANDSCAPE
    set_margins(s, top=15, bottom=15, left=15, right=15, size=(297, 210))
    return s


def portrait_section(doc):
    s = doc.add_section(WD_SECTION.NEW_PAGE)
    s.orientation = WD_ORIENT.PORTRAIT
    set_margins(s, size=(210, 297))
    return s


def fit_width_mm(path, max_w_mm, max_h_mm):
    """Ширина рисунка по его пропорциям, чтобы он помещался в отведенную
    область (ширина x высота)."""
    from PIL import Image as _Img
    with _Img.open(path) as im:
        w, h = im.size
    by_w = max_w_mm
    by_h = max_h_mm * w / h
    return round(min(by_w, by_h), 1)


def add_picture(doc, path, width_mm, caption_text=None):
    """Вставляет рисунок и удерживает подпись на той же странице."""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf.first_line_indent = Cm(0)
    pf.space_before = Pt(6)
    pf.space_after = Pt(2)
    pf.line_spacing = 1.0
    pf.keep_with_next = bool(caption_text)
    p.add_run().add_picture(path, width=Mm(width_mm))
    if caption_text:
        caption(doc, caption_text)
    return p
