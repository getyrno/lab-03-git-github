#!/usr/bin/env bash
# =============================================================================
# Лабораторная работа №2. Сборка отчета и его проверка.
#
# Порядок:
#   1) сборка DOCX с оглавлением из предыдущего прохода (если есть);
#   2) рендер DOCX -> PDF -> PNG штатным рендерером Codex;
#   3) извлечение реальных номеров страниц разделов из PDF;
#   4) повторная сборка с точными номерами страниц в оглавлении;
#   5) финальный рендер и проверки: структура DOCX, пустые страницы,
#      выход текста за границы, читаемость диаграмм.
#
# Требования: docker-контейнер video_rental_lab_pg с выполненным run_all.sh.
# Запуск:  ./report/build_and_verify.sh
# =============================================================================
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
RUNTIME="/Users/getyrno/.cache/codex-runtimes/codex-primary-runtime/dependencies"
PY="$RUNTIME/python/bin/python3"
RENDER="/Users/getyrno/.codex/plugins/cache/openai-primary-runtime/documents/26.927.11222/skills/documents/render_docx.py"
PDFTOTEXT="$RUNTIME/native/poppler/poppler/bin/pdftotext"
OUTDIR="$ROOT/evidence/render"

echo "=== [1/5] Сборка DOCX ==="
"$PY" "$HERE/build_report.py"

echo "=== [2/5] Рендер DOCX -> PNG ==="
mkdir -p "$OUTDIR"
# очистка предыдущих страниц: иначе остаются устаревшие page-N.png
find "$OUTDIR" -maxdepth 1 -name 'page-*.png' -delete
"$PY" "$RENDER" "$ROOT/Отчет/Лабораторная работа №2.docx" \
      --output_dir "$OUTDIR" --emit_pdf >/dev/null

echo "=== [3/5] Определение номеров страниц разделов ==="
"$PDFTOTEXT" -layout "$OUTDIR/Лабораторная работа №2.pdf" "$OUTDIR/report.txt"
"$PY" "$HERE/page_numbers.py" "$OUTDIR/report.txt"

echo "=== [4/5] Повторная сборка с точным оглавлением ==="
"$PY" "$HERE/build_report.py"

echo "=== [5/5] Проверки ==="
find "$OUTDIR" -maxdepth 1 -name 'page-*.png' -delete
"$PY" "$RENDER" "$ROOT/Отчет/Лабораторная работа №2.docx" \
      --output_dir "$OUTDIR" --emit_pdf >/dev/null
"$PDFTOTEXT" -layout "$OUTDIR/Лабораторная работа №2.pdf" "$OUTDIR/report.txt"
"$PY" "$HERE/check_docx.py"
"$PY" "$HERE/check_render.py" "$OUTDIR/report.txt" "$OUTDIR"
"$PY" "$HERE/check_visual.py" "$OUTDIR"
echo "Готово."
