#!/usr/bin/env bash
# Сбор доказательств выполнения лабораторной работы №2 из работающей БД.
# Требования: контейнер video_rental_lab_pg с уже выполненным run_all.sh.
set -euo pipefail

CONTAINER="${CONTAINER:-video_rental_lab_pg}"
DB="${DB:-video_rental_lab}"
DB_USER="${DB_USER:-labuser}"
HERE="$(cd "$(dirname "$0")" && pwd)"

PSQL=(docker exec -i "$CONTAINER" psql -U "$DB_USER" -d "$DB" -v ON_ERROR_STOP=1)

echo "==> Схема 3NF: структура таблиц"
"${PSQL[@]}" -c "\d+ video_rental_3nf.*" > "$HERE/postgres_schema_3nf.txt"

echo "==> Схема Data Vault: структура таблиц"
"${PSQL[@]}" -c "\d+ video_rental_dv.*" > "$HERE/postgres_schema_dv.txt"

echo "==> Полный журнал прогона (создание схем, загрузка данных, проверки)"
"$HERE/../run_all.sh" > "$HERE/postgres_validation.txt" 2>&1

echo "==> История изменений в Спутниках"
"${PSQL[@]}" -f - > "$HERE/data_vault_history.txt" <<'SQL'
\echo '=== История контактов клиента CR-00001 (sat_customer_contact) ==='
SELECT hc.card_number, sc.load_dts, sc.phone, sc.address, sc.hashdiff, sc.record_source
  FROM video_rental_dv.hub_customer hc
  JOIN video_rental_dv.sat_customer_contact sc ON sc.customer_hk = hc.customer_hk
 WHERE hc.card_number = 'CR-00001' ORDER BY sc.load_dts;

\echo '=== История состояния экземпляра VC-00005 (sat_video_copy_details) ==='
SELECT hvc.inventory_code, sd.load_dts, sd.condition, sd.storage_location, sd.hashdiff, sd.record_source
  FROM video_rental_dv.hub_video_copy hvc
  JOIN video_rental_dv.sat_video_copy_details sd ON sd.copy_hk = hvc.copy_hk
 WHERE hvc.inventory_code = 'VC-00005' ORDER BY sd.load_dts;

\echo '=== История статуса проката RN-000006 (sat_rental_details) ==='
SELECT hr.rental_number, sd.load_dts, sd.status, sd.planned_return_date, sd.actual_return_date, sd.record_source
  FROM video_rental_dv.hub_rental hr
  JOIN video_rental_dv.sat_rental_details sd ON sd.rental_hk = hr.rental_hk
 WHERE hr.rental_number = 'RN-000006' ORDER BY sd.load_dts;
SQL

echo "==> Готово. Файлы:"
ls -1 "$HERE"
