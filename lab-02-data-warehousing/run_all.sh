#!/usr/bin/env bash
# =============================================================================
# Лабораторная работа №2. Вариант 14. Система учета в видеопрокате.
# Полный прогон: создание схем, загрузка данных, проверки.
#
# Требования: Docker, образ postgres:17.
# Запуск из каталога лабораторной работы:  ./run_all.sh
# =============================================================================
set -euo pipefail

CONTAINER="${CONTAINER:-video_rental_lab_pg}"
DB="${DB:-video_rental_lab}"
DB_USER="${DB_USER:-labuser}"
HERE="$(cd "$(dirname "$0")" && pwd)"

psql_file() {
    docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB" -v ON_ERROR_STOP=1 -f -
}

echo "=== [0/6] Проверка контейнера PostgreSQL ==="
docker exec "$CONTAINER" psql -U "$DB_USER" -d "$DB" -c "SELECT version();"

echo
echo "=== [1/6] Создание схемы 3NF ==="
psql_file < "$HERE/sql/01_create_3nf.sql"

echo
echo "=== [2/6] Создание схемы Data Vault ==="
psql_file < "$HERE/sql/02_create_data_vault.sql"

echo
echo "=== [3/6] Загрузка тестовых данных (3NF) ==="
psql_file < "$HERE/sql/03_test_data_3nf.sql"

echo
echo "=== [4/6] Загрузка Data Vault и историзация Спутников ==="
psql_file < "$HERE/sql/04_test_data_data_vault.sql"

echo
echo "=== [5/6] Проверочные запросы и проверка ограничений ==="
psql_file < "$HERE/sql/05_validation.sql"

echo
echo "=== [6/6] Готово ==="
