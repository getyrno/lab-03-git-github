-- =============================================================================
-- Лабораторная работа №2. Вариант 14. Система учета в видеопрокате.
-- Файл 04: загрузка Data Vault и демонстрация историзации Спутников.
--
-- Сценарий:
--   загрузка 1 (2026-09-28 08:00) - первичное наполнение хранилища;
--   изменение источника            - клиент сменил телефон и адрес,
--                                    экземпляр VC-00005 получил износ;
--   загрузка 2 (2026-09-28 09:15) - новая версия Спутников (старые строки сохранены);
--   новое событие в источнике      - оформлен прокат RN-000007, закрыт прокат RN-000006;
--   загрузка 3 (2026-09-28 10:30) - новые Хабы/Связи и новые версии Спутников;
--   загрузка 4 (2026-09-28 11:00) - в источнике нет изменений: вставок нет.
-- =============================================================================

\set ON_ERROR_STOP on
SET search_path TO video_rental_dv, video_rental_3nf, lab;

-- -----------------------------------------------------------------------------
-- 1. Первичная загрузка хранилища
-- -----------------------------------------------------------------------------
\echo '=== Загрузка 1: первичное наполнение Data Vault (2026-09-28 08:00) ==='
SELECT * FROM dv_load_all(TIMESTAMP '2026-09-28 08:00:00', 'video_rental_3nf#initial');

\echo '--- Количество строк в Хабах после первичной загрузки ---'
SELECT 'hub_customer' AS hub, count(*) FROM hub_customer
UNION ALL SELECT 'hub_employee',   count(*) FROM hub_employee
UNION ALL SELECT 'hub_film',       count(*) FROM hub_film
UNION ALL SELECT 'hub_video_copy', count(*) FROM hub_video_copy
UNION ALL SELECT 'hub_rental',     count(*) FROM hub_rental
UNION ALL SELECT 'hub_payment',    count(*) FROM hub_payment
UNION ALL SELECT 'hub_genre',      count(*) FROM hub_genre
UNION ALL SELECT 'hub_tariff',     count(*) FROM hub_tariff
ORDER BY hub;

\echo '--- Количество строк в Связях после первичной загрузки ---'
SELECT 'link_film_copy' AS link, count(*) FROM link_film_copy
UNION ALL SELECT 'link_film_genre',     count(*) FROM link_film_genre
UNION ALL SELECT 'link_film_tariff',    count(*) FROM link_film_tariff
UNION ALL SELECT 'link_rental_customer',count(*) FROM link_rental_customer
UNION ALL SELECT 'link_rental_employee',count(*) FROM link_rental_employee
UNION ALL SELECT 'link_rental_copy',    count(*) FROM link_rental_copy
UNION ALL SELECT 'link_rental_payment', count(*) FROM link_rental_payment
ORDER BY link;

-- -----------------------------------------------------------------------------
-- 2. Изменения в системе-источнике (операционная схема 3NF)
--    Бизнес-события: клиент сменил телефон и адрес;
--    экземпляр VC-00005 вернулся с износом (состояние good -> worn).
-- -----------------------------------------------------------------------------
\echo '=== Изменение данных в источнике (3NF) ==='
UPDATE customer
   SET phone   = '+79161234599',
       address = 'г. Москва, ул. Ленина, д. 1, кв. 6'
 WHERE card_number = 'CR-00001';

UPDATE video_copy
   SET condition = 'worn'
 WHERE inventory_code = 'VC-00005';

SELECT card_number, phone, address FROM customer WHERE card_number = 'CR-00001';
SELECT inventory_code, condition FROM video_copy WHERE inventory_code = 'VC-00005';

-- -----------------------------------------------------------------------------
-- 3. Загрузка 2: только изменившиеся атрибуты попадают в Спутники
-- -----------------------------------------------------------------------------
\echo '=== Загрузка 2: изменение атрибутов (2026-09-28 09:15) ==='
SELECT * FROM dv_load_all(TIMESTAMP '2026-09-28 09:15:00', 'video_rental_3nf#daily');

\echo '--- История изменения контактов клиента CR-00001 (Спутник sat_customer_contact) ---'
SELECT hc.card_number,
       sc.load_dts,
       sc.phone,
       sc.address,
       sc.status,
       sc.record_source
  FROM hub_customer hc
  JOIN sat_customer_contact sc ON sc.customer_hk = hc.customer_hk
 WHERE hc.card_number = 'CR-00001'
 ORDER BY sc.load_dts;

\echo '--- История изменения состояния экземпляра VC-00005 (Спутник sat_video_copy_details) ---'
SELECT hvc.inventory_code,
       sd.load_dts,
       sd.condition,
       sd.storage_location,
       sd.record_source
  FROM hub_video_copy hvc
  JOIN sat_video_copy_details sd ON sd.copy_hk = hvc.copy_hk
 WHERE hvc.inventory_code = 'VC-00005'
 ORDER BY sd.load_dts;

-- -----------------------------------------------------------------------------
-- 4. Новые бизнес-события: оформлен прокат RN-000007, закрыт прокат RN-000006
-- -----------------------------------------------------------------------------
\echo '=== Новые бизнес-события в источнике (3NF) ==='
-- 4.1 Возврат обоих экземпляров по операции RN-000006
UPDATE rental_item
   SET status = 'returned',
       actual_return_date = DATE '2026-09-28',
       condition_on_return = CASE copy_id WHEN 2 THEN 'good' ELSE 'worn' END
 WHERE rental_id = (SELECT rental_id FROM rental WHERE rental_number = 'RN-000006');

-- 4.2 Новая операция проката
INSERT INTO rental (rental_number, customer_id, employee_id, issue_date,
                    planned_return_date, deposit_amount, status)
VALUES ('RN-000007',
        (SELECT customer_id FROM customer WHERE card_number = 'CR-00002'),
        (SELECT employee_id FROM employee WHERE personnel_number = 'EMP-0001'),
        DATE '2026-09-28', DATE '2026-10-01', 300.00, 'issued');

INSERT INTO rental_item (rental_id, copy_id, daily_rate, status)
VALUES ((SELECT rental_id FROM rental WHERE rental_number = 'RN-000007'),
        (SELECT copy_id FROM video_copy WHERE inventory_code = 'VC-00006'),
        90.00, 'issued');

INSERT INTO payment (payment_number, rental_id, payment_date, amount, method, payment_type)
VALUES ('PM-000011',
        (SELECT rental_id FROM rental WHERE rental_number = 'RN-000007'),
        TIMESTAMP '2026-09-28 10:05:00', 300.00, 'card', 'deposit');

SELECT rental_number, status, actual_return_date FROM rental ORDER BY rental_id;

-- -----------------------------------------------------------------------------
-- 5. Загрузка 3: новые ключи в Хабах и Связях + новые версии Спутников
-- -----------------------------------------------------------------------------
\echo '=== Загрузка 3: новые события и новые версии (2026-09-28 10:30) ==='
SELECT * FROM dv_load_all(TIMESTAMP '2026-09-28 10:30:00', 'video_rental_3nf#daily');

\echo '--- История изменения статуса проката RN-000006 (Спутник sat_rental_details) ---'
SELECT hr.rental_number, sd.load_dts, sd.status, sd.planned_return_date,
       sd.actual_return_date, sd.record_source
  FROM hub_rental hr
  JOIN sat_rental_details sd ON sd.rental_hk = hr.rental_hk
 WHERE hr.rental_number = 'RN-000006'
 ORDER BY sd.load_dts;

\echo '--- История позиции проката: экземпляр VC-00002 в операции RN-000006 ---'
SELECT hr.rental_number, hvc.inventory_code, sid.load_dts, sid.status,
       sid.actual_return_date, sid.condition_on_return
  FROM link_rental_copy lrc
  JOIN hub_rental hr      ON hr.rental_hk = lrc.rental_hk
  JOIN hub_video_copy hvc ON hvc.copy_hk = lrc.copy_hk
  JOIN sat_rental_item_details sid ON sid.rental_copy_hk = lrc.rental_copy_hk
 WHERE hr.rental_number = 'RN-000006' AND hvc.inventory_code = 'VC-00002'
 ORDER BY sid.load_dts;

\echo '--- Новый прокат RN-000007, собранный из Hub + Link + Satellite ---'
SELECT * FROM v_rental_full WHERE rental_number = 'RN-000007' ORDER BY inventory_code;

-- -----------------------------------------------------------------------------
-- 6. Загрузка 4: в источнике нет изменений -> новых версий Спутников нет
-- -----------------------------------------------------------------------------
\echo '=== Загрузка 4: повторная загрузка без изменений (2026-09-28 11:00) ==='
SELECT * FROM dv_load_all(TIMESTAMP '2026-09-28 11:00:00', 'video_rental_3nf#daily')
 WHERE rows_inserted <> 0;

\echo '(пустой результат выше означает, что ни один объект хранилища не изменился)'

-- -----------------------------------------------------------------------------
-- 7. Итоговый состав Data Vault
-- -----------------------------------------------------------------------------
\echo '--- Количество версий в Спутниках (историзация) ---'
SELECT 'sat_customer_details' AS satellite, count(*) AS versions,
       count(DISTINCT customer_hk) AS parents FROM sat_customer_details
UNION ALL SELECT 'sat_customer_contact', count(*), count(DISTINCT customer_hk) FROM sat_customer_contact
UNION ALL SELECT 'sat_employee_details', count(*), count(DISTINCT employee_hk) FROM sat_employee_details
UNION ALL SELECT 'sat_film_details',     count(*), count(DISTINCT film_hk)     FROM sat_film_details
UNION ALL SELECT 'sat_video_copy_details', count(*), count(DISTINCT copy_hk)   FROM sat_video_copy_details
UNION ALL SELECT 'sat_video_copy_acquisition', count(*), count(DISTINCT copy_hk) FROM sat_video_copy_acquisition
UNION ALL SELECT 'sat_genre_details',    count(*), count(DISTINCT genre_hk)    FROM sat_genre_details
UNION ALL SELECT 'sat_tariff_details',   count(*), count(DISTINCT tariff_hk)   FROM sat_tariff_details
UNION ALL SELECT 'sat_rental_details',   count(*), count(DISTINCT rental_hk)   FROM sat_rental_details
UNION ALL SELECT 'sat_rental_item_details', count(*), count(DISTINCT rental_copy_hk) FROM sat_rental_item_details
UNION ALL SELECT 'sat_payment_details',  count(*), count(DISTINCT payment_hk)  FROM sat_payment_details
UNION ALL SELECT 'sat_film_genre_details', count(*), count(DISTINCT film_genre_hk) FROM sat_film_genre_details
ORDER BY satellite;
