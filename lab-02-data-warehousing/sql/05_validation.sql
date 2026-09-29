-- =============================================================================
-- Лабораторная работа №2. Вариант 14. Система учета в видеопрокате.
-- Файл 05: проверка моделей 3NF и Data Vault реальными запросами
--          и проверка ограничений целостности.
--
-- Текущая дата системы зафиксирована функцией lab.current_date() = 2026-09-28.
-- Файл можно запускать повторно: раздел проверки ограничений откатывается
-- (SAVEPOINT/ROLLBACK TO SAVEPOINT) и не меняет данные.
-- =============================================================================

\set ON_ERROR_STOP on
SET search_path TO video_rental_3nf, video_rental_dv, lab;
\pset pager off

-- =============================================================================
-- ЧАСТЬ 1. ПРОВЕРКА МОДЕЛИ 3NF
-- =============================================================================

\echo ''
\echo '########################################################################'
\echo '# ЗАПРОС 1. Список активных прокатов'
\echo '########################################################################'
SELECT rental_number,
       customer_name,
       employee_name,
       issue_date,
       planned_return_date,
       items_total,
       items_open,
       is_overdue,
       overdue_days
  FROM v_active_rental
 ORDER BY planned_return_date, rental_number;

\echo ''
\echo '########################################################################'
\echo '# ЗАПРОС 2. Список просроченных экземпляров'
\echo '########################################################################'
SELECT r.rental_number,
       c.card_number,
       c.last_name || ' ' || c.first_name AS customer_name,
       c.phone,
       vc.inventory_code,
       f.title,
       r.planned_return_date,
       lab.current_date() - r.planned_return_date AS overdue_days,
       round(ri.daily_rate * (lab.current_date() - r.planned_return_date), 2) AS penalty_accrued
  FROM rental_item ri
  JOIN rental r      ON r.rental_id = ri.rental_id
  JOIN customer c    ON c.customer_id = r.customer_id
  JOIN video_copy vc ON vc.copy_id = ri.copy_id
  JOIN film f        ON f.film_id = vc.film_id
 WHERE ri.status = 'issued'
   AND r.planned_return_date < lab.current_date()
 ORDER BY overdue_days DESC, vc.inventory_code;

\echo ''
\echo '########################################################################'
\echo '# ЗАПРОС 3. История прокатов конкретного клиента (CR-00002, Петрова Анна)'
\echo '########################################################################'
SELECT r.rental_number,
       r.issue_date,
       r.planned_return_date,
       r.actual_return_date,
       r.status,
       (SELECT count(*) FROM rental_item ri WHERE ri.rental_id = r.rental_id) AS items,
       string_agg(vc.inventory_code || ' (' || f.title || ')', ', ' ORDER BY vc.inventory_code) AS copies
  FROM rental r
  JOIN customer c ON c.customer_id = r.customer_id
  LEFT JOIN rental_item ri ON ri.rental_id = r.rental_id
  LEFT JOIN video_copy vc  ON vc.copy_id = ri.copy_id
  LEFT JOIN film f         ON f.film_id = vc.film_id
 WHERE c.card_number = 'CR-00002'
 GROUP BY r.rental_number, r.issue_date, r.planned_return_date, r.actual_return_date, r.status, r.rental_id
 ORDER BY r.issue_date, r.rental_number;

\echo ''
\echo '########################################################################'
\echo '# ЗАПРОС 4. Доступные сейчас экземпляры'
\echo '########################################################################'
SELECT cs.inventory_code, cs.title, cs.condition, cs.storage_location
  FROM v_copy_status cs
 WHERE cs.is_available
 ORDER BY cs.title, cs.inventory_code;

\echo '--- Сводка по фонду ---'
SELECT count(*) AS copies_total,
       count(*) FILTER (WHERE is_rented)   AS copies_rented,
       count(*) FILTER (WHERE is_available) AS copies_available,
       count(*) FILTER (WHERE condition = 'written_off') AS copies_written_off
  FROM v_copy_status;

\echo ''
\echo '########################################################################'
\echo '# ЗАПРОС 5. Фильмы и их жанры'
\echo '########################################################################'
SELECT catalog_number, title, release_year, media_type, tariff_code, daily_rate, genres, copies_total
  FROM v_film_catalog
 ORDER BY catalog_number;

\echo ''
\echo '########################################################################'
\echo '# ЗАПРОС 6. Суммы платежей по операциям проката'
\echo '########################################################################'
SELECT rental_number, status, rent_cost, paid_total, penalty_total,
       round(paid_total - rent_cost - penalty_total, 2) AS deposit_balance
  FROM v_rental_total
 ORDER BY rental_number;

\echo '--- Итоги по способам оплаты ---'
SELECT method, count(*) AS payments, sum(amount) AS total_amount
  FROM payment
 GROUP BY method
 ORDER BY method;

-- =============================================================================
-- ЧАСТЬ 2. ПРОВЕРКА МОДЕЛИ DATA VAULT
-- =============================================================================

\echo ''
\echo '########################################################################'
\echo '# ЗАПРОС 7. Восстановление информации из Hub + Link + Satellite'
\echo '#           (эквивалент выборки 3NF)'
\echo '########################################################################'
SELECT rental_number, card_number, customer_name, employee_name,
       issue_date, planned_return_date, status, inventory_code, title, item_status
  FROM v_rental_full
 ORDER BY rental_number, inventory_code;

\echo ''
\echo '########################################################################'
\echo '# ЗАПРОС 8. Последняя версия записи Спутника (текущее состояние клиентов)'
\echo '########################################################################'
SELECT card_number, last_name, first_name, phone, email, address, status,
       contact_load_dts AS last_change_dts
  FROM v_customer_current
 ORDER BY card_number;

\echo '--- Последние версии состояния экземпляров ---'
SELECT inventory_code, condition, storage_location, acquisition_date, purchase_price
  FROM v_video_copy_current
 ORDER BY inventory_code;

\echo ''
\echo '########################################################################'
\echo '# ЗАПРОС 9. История изменения объекта: клиент CR-00001 (телефон и адрес)'
\echo '########################################################################'
SELECT hc.card_number,
       sc.load_dts,
       sc.phone,
       sc.address,
       sc.status,
       sc.hashdiff,
       sc.record_source
  FROM hub_customer hc
  JOIN sat_customer_contact sc ON sc.customer_hk = hc.customer_hk
 WHERE hc.card_number = 'CR-00001'
 ORDER BY sc.load_dts;

\echo '--- История изменения состояния экземпляра VC-00005 ---'
SELECT hvc.inventory_code, sd.load_dts, sd.condition, sd.storage_location, sd.hashdiff, sd.record_source
  FROM hub_video_copy hvc
  JOIN sat_video_copy_details sd ON sd.copy_hk = hvc.copy_hk
 WHERE hvc.inventory_code = 'VC-00005'
 ORDER BY sd.load_dts;

\echo '--- История изменения статуса проката RN-000006 ---'
SELECT hr.rental_number, sd.load_dts, sd.status, sd.actual_return_date, sd.record_source
  FROM hub_rental hr
  JOIN sat_rental_details sd ON sd.rental_hk = hr.rental_hk
 WHERE hr.rental_number = 'RN-000006'
 ORDER BY sd.load_dts;

\echo ''
\echo '########################################################################'
\echo '# ЗАПРОС 10. Полный аудит: все объекты, загруженные каждым пакетом'
\echo '########################################################################'
SELECT record_source,
       count(*) AS hub_rows
  FROM (
        SELECT record_source FROM hub_customer
  UNION ALL SELECT record_source FROM hub_employee
  UNION ALL SELECT record_source FROM hub_film
  UNION ALL SELECT record_source FROM hub_video_copy
  UNION ALL SELECT record_source FROM hub_rental
  UNION ALL SELECT record_source FROM hub_payment
  UNION ALL SELECT record_source FROM hub_genre
  UNION ALL SELECT record_source FROM hub_tariff
       ) h
 GROUP BY record_source
 ORDER BY record_source;

-- =============================================================================
-- ЧАСТЬ 3. ПРОВЕРКА ОГРАНИЧЕНИЙ ЦЕЛОСТНОСТИ
-- Каждый негативный тест выполняет заведомо некорректную операцию внутри
-- блока с обработкой исключения: PostgreSQL обязан ее отклонить.
-- В выводе печатается реально полученный код ошибки (SQLSTATE) и сообщение.
-- =============================================================================

\echo ''
\echo '########################################################################'
\echo '# ПРОВЕРКА ОГРАНИЧЕНИЙ (негативные тесты)'
\echo '########################################################################'

DO $$
DECLARE
    v_state text;
    v_msg   text;
BEGIN
    BEGIN
        INSERT INTO rental (rental_number, customer_id, employee_id, issue_date, planned_return_date)
        VALUES ('RN-900001', 99999, 1, DATE '2026-09-28', DATE '2026-10-01');
        RAISE EXCEPTION 'ТЕСТ 1 НЕ ПРОШЁЛ: вставка с несуществующим клиентом была принята';
    EXCEPTION WHEN others THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
        RAISE NOTICE 'ТЕСТ 1 (FK, 3NF): ссылка на несуществующего клиента отклонена. SQLSTATE=%, %', v_state, v_msg;
    END;

    BEGIN
        INSERT INTO payment (payment_number, rental_id, payment_date, amount, method, payment_type)
        VALUES ('PM-900001', 1, TIMESTAMP '2026-09-28 12:00:00', -500.00, 'cash', 'rent');
        RAISE EXCEPTION 'ТЕСТ 2 НЕ ПРОШЁЛ: отрицательная сумма платежа была принята';
    EXCEPTION WHEN others THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
        RAISE NOTICE 'ТЕСТ 2 (CHECK, 3NF): отрицательная сумма платежа отклонена. SQLSTATE=%, %', v_state, v_msg;
    END;

    BEGIN
        INSERT INTO rental (rental_number, customer_id, employee_id, issue_date, planned_return_date)
        VALUES ('RN-900002', 1, 1, DATE '2026-09-28', DATE '2026-09-20');
        RAISE EXCEPTION 'ТЕСТ 3 НЕ ПРОШЁЛ: плановая дата возврата раньше даты выдачи была принята';
    EXCEPTION WHEN others THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
        RAISE NOTICE 'ТЕСТ 3 (CHECK, 3NF): плановый возврат раньше выдачи отклонён. SQLSTATE=%, %', v_state, v_msg;
    END;

    BEGIN
        INSERT INTO customer (card_number, last_name, first_name, phone, registration_date)
        VALUES ('CR-00001', 'Дубль', 'Дубль', '+79160000000', DATE '2026-09-28');
        RAISE EXCEPTION 'ТЕСТ 4 НЕ ПРОШЁЛ: дубль номера клубной карты был принят';
    EXCEPTION WHEN others THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
        RAISE NOTICE 'ТЕСТ 4 (UNIQUE, 3NF): повтор номера клубной карты отклонён. SQLSTATE=%, %', v_state, v_msg;
    END;

    BEGIN
        INSERT INTO rental (rental_number, customer_id, employee_id, issue_date, planned_return_date)
        VALUES ('RN-900003', 2, 1, DATE '2026-09-28', DATE '2026-10-01');
        INSERT INTO rental_item (rental_id, copy_id, daily_rate, status)
        VALUES ((SELECT rental_id FROM rental WHERE rental_number = 'RN-900003'), 5, 90.00, 'issued');
        RAISE EXCEPTION 'ТЕСТ 5 НЕ ПРОШЁЛ: экземпляр выдан дважды в параллельных активных прокатах';
    EXCEPTION WHEN others THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
        RAISE NOTICE 'ТЕСТ 5 (частичный UNIQUE, 3NF): повторная выдача занятого экземпляра отклонена. SQLSTATE=%, %', v_state, v_msg;
    END;

    BEGIN
        INSERT INTO customer (card_number, last_name, first_name, phone, registration_date)
        VALUES ('12345', 'Кривой', 'Ключ', '+79160000001', DATE '2026-09-28');
        RAISE EXCEPTION 'ТЕСТ 6 НЕ ПРОШЁЛ: номер карты неверного формата был принят';
    EXCEPTION WHEN others THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
        RAISE NOTICE 'ТЕСТ 6 (CHECK формата, 3NF): некорректный бизнес-ключ отклонён. SQLSTATE=%, %', v_state, v_msg;
    END;

    BEGIN
        INSERT INTO video_rental_dv.hub_customer (customer_hk, card_number, load_dts, record_source)
        VALUES (video_rental_dv.dv_hash('CR-00001'), 'CR-00001', TIMESTAMP '2026-09-28 12:00:00', 'manual');
        RAISE EXCEPTION 'ТЕСТ 7 НЕ ПРОШЁЛ: повтор бизнес-ключа Хаба был принят';
    EXCEPTION WHEN others THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
        RAISE NOTICE 'ТЕСТ 7 (PK/UNIQUE, Data Vault): повтор бизнес-ключа Хаба отклонён. SQLSTATE=%, %', v_state, v_msg;
    END;

    BEGIN
        INSERT INTO video_rental_dv.sat_video_copy_details
            (copy_hk, load_dts, hashdiff, condition, storage_location, record_source)
        SELECT copy_hk, load_dts, hashdiff, condition, storage_location, 'manual'
          FROM video_rental_dv.sat_video_copy_details
         WHERE copy_hk = video_rental_dv.dv_hash('VC-00005')
         ORDER BY load_dts DESC LIMIT 1;
        RAISE EXCEPTION 'ТЕСТ 8 НЕ ПРОШЁЛ: повтор версии Спутника по тому же load_dts был принят';
    EXCEPTION WHEN others THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
        RAISE NOTICE 'ТЕСТ 8 (составной PK, Data Vault): повтор версии Спутника отклонён. SQLSTATE=%, %', v_state, v_msg;
    END;

    BEGIN
        INSERT INTO video_rental_dv.sat_film_details
            (film_hk, load_dts, hashdiff, title, release_year, duration_min, age_rating,
             media_type, added_on, record_source)
        VALUES (video_rental_dv.dv_hash('FM-9999'), TIMESTAMP '2026-09-28 12:00:00',
                video_rental_dv.dv_hashdiff('Несуществующий фильм'), 'Несуществующий фильм',
                2020, 100, '16+', 'DVD', DATE '2026-09-28', 'manual');
        RAISE EXCEPTION 'ТЕСТ 9 НЕ ПРОШЁЛ: Спутник со ссылкой на несуществующий Хаб был принят';
    EXCEPTION WHEN others THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
        RAISE NOTICE 'ТЕСТ 9 (FK, Data Vault): Спутник без родительского Хаба отклонён. SQLSTATE=%, %', v_state, v_msg;
    END;

    BEGIN
        INSERT INTO video_rental_dv.sat_payment_details
            (payment_hk, load_dts, hashdiff, payment_date, amount, method, payment_type, record_source)
        VALUES (video_rental_dv.dv_hash('PM-000001'), TIMESTAMP '2026-09-28 13:00:00',
                video_rental_dv.dv_hashdiff('-100'), TIMESTAMP '2026-09-28 13:00:00',
                -100.00, 'cash', 'rent', 'manual');
        RAISE EXCEPTION 'ТЕСТ 10 НЕ ПРОШЁЛ: отрицательная сумма в Спутнике платежа была принята';
    EXCEPTION WHEN others THEN
        GET STACKED DIAGNOSTICS v_state = RETURNED_SQLSTATE, v_msg = MESSAGE_TEXT;
        RAISE NOTICE 'ТЕСТ 10 (CHECK, Data Vault): отрицательная сумма платежа в Спутнике отклонена. SQLSTATE=%, %', v_state, v_msg;
    END;
END $$;

\echo '--- Контроль: количество строк после негативных тестов не изменилось ---'
SELECT (SELECT count(*) FROM customer) AS customers,
       (SELECT count(*) FROM rental)   AS rentals,
       (SELECT count(*) FROM payment)  AS payments,
       (SELECT count(*) FROM video_rental_dv.hub_customer) AS dv_hub_customers,
       (SELECT count(*) FROM video_rental_dv.sat_video_copy_details) AS dv_copy_versions;

-- =============================================================================
-- ЧАСТЬ 4. ИТОГОВАЯ СВОДКА
-- =============================================================================
\echo ''
\echo '########################################################################'
\echo '# ИТОГ: состав модели 3NF'
\echo '########################################################################'
SELECT t.table_name,
       (SELECT count(*) FROM information_schema.columns c
         WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name) AS columns,
       (SELECT count(*) FROM pg_index i
         WHERE i.indrelid = (quote_ident(t.table_schema) || '.' || quote_ident(t.table_name))::regclass
           AND i.indisprimary) AS pk_count,
       (SELECT count(*) FROM information_schema.table_constraints tc
         WHERE tc.table_schema = t.table_schema AND tc.table_name = t.table_name
           AND tc.constraint_type = 'FOREIGN KEY') AS fk_count,
       (SELECT count(*) FROM information_schema.table_constraints tc
         WHERE tc.table_schema = t.table_schema AND tc.table_name = t.table_name
           AND tc.constraint_type = 'CHECK') AS check_count
  FROM information_schema.tables t
 WHERE t.table_schema = 'video_rental_3nf' AND t.table_type = 'BASE TABLE'
 ORDER BY t.table_name;

\echo ''
\echo '########################################################################'
\echo '# ИТОГ: состав модели Data Vault'
\echo '########################################################################'
SELECT CASE
         WHEN table_name LIKE 'hub\_%'  THEN 'HUB'
         WHEN table_name LIKE 'link\_%' THEN 'LINK'
         WHEN table_name LIKE 'sat\_%'  THEN 'SATELLITE'
       END AS object_type,
       table_name,
       (SELECT count(*) FROM information_schema.columns c
         WHERE c.table_schema = t.table_schema AND c.table_name = t.table_name) AS columns,
       (SELECT count(*) FROM information_schema.table_constraints tc
         WHERE tc.table_schema = t.table_schema AND tc.table_name = t.table_name
           AND tc.constraint_type = 'FOREIGN KEY') AS fk_count
  FROM information_schema.tables t
 WHERE t.table_schema = 'video_rental_dv' AND t.table_type = 'BASE TABLE'
 ORDER BY object_type, table_name;

\echo ''
\echo '=== ВСЕ ПРОВЕРКИ ЗАВЕРШЕНЫ ==='
