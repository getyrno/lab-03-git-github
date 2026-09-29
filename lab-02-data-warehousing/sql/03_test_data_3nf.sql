-- =============================================================================
-- Лабораторная работа №2. Вариант 14. Система учета в видеопрокате.
-- Файл 03: тестовые (синтетические) данные для схемы 3NF.
-- Все данные вымышлены и предназначены только для проверки модели.
-- Скрипт идемпотентен: повторный запуск пересоздает данные с нуля.
-- =============================================================================

\set ON_ERROR_STOP on
SET search_path TO video_rental_3nf;

TRUNCATE payment, rental_item, rental, video_copy, film_genre, film, tariff, customer, employee, genre
    RESTART IDENTITY CASCADE;

-- -----------------------------------------------------------------------------
-- 1. Жанры
-- -----------------------------------------------------------------------------
INSERT INTO genre (genre_id, code, name, description) OVERRIDING SYSTEM VALUE VALUES
    (1, 'ACTION',  'Боевик',        'Динамичные фильмы с акцентом на действие и погони'),
    (2, 'DRAMA',   'Драма',         'Фильмы с серьёзным сюжетом и психологической глубиной'),
    (3, 'COMEDY',  'Комедия',       'Фильмы, основной целью которых является рассмешить зрителя'),
    (4, 'SCIFI',   'Фантастика',    'Фильмы о вымышленных технологиях и будущем'),
    (5, 'THRILLER','Триллер',       'Фильмы, удерживающие зрителя в напряжении'),
    (6, 'ANIMATION','Анимация',     'Мультипликационные фильмы'),
    (7, 'DOC',     'Документальный','Неигровое кино о реальных событиях и явлениях');

-- -----------------------------------------------------------------------------
-- 2. Тарифы
-- -----------------------------------------------------------------------------
INSERT INTO tariff (tariff_id, code, name, daily_rate, max_rental_days, late_fee_per_day, valid_from, valid_to)
OVERRIDING SYSTEM VALUE VALUES
    (1, 'STD',  'Стандарт',      60.00, 5,  20.00, DATE '2024-01-01', NULL),
    (2, 'NEW',  'Новинка',       90.00, 3,  30.00, DATE '2024-01-01', NULL),
    (3, 'CLAS', 'Классика',      40.00, 7,  15.00, DATE '2024-01-01', NULL),
    (4, 'PROMO','Акция выходного дня', 25.00, 2, 10.00, DATE '2025-06-01', DATE '2026-06-01');

-- -----------------------------------------------------------------------------
-- 3. Фильмы (10 наименований; часть - с несколькими жанрами)
-- -----------------------------------------------------------------------------
INSERT INTO film (film_id, catalog_number, title, original_title, release_year, duration_min,
                  age_rating, media_type, tariff_id, synopsis, added_on)
OVERRIDING SYSTEM VALUE VALUES
    (1,  'FM-0001', 'Побег из Шоушенка',        'The Shawshank Redemption', 1994, 142, '16+', 'DVD',     3,
     'История о надежде и дружбе в стенах тюрьмы.', DATE '2024-02-05'),
    (2,  'FM-0002', 'Крепкий орешек',           'Die Hard',                 1988, 132, '16+', 'DVD',     3,
     'Полицейский противостоит террористам в небоскрёбе.', DATE '2024-02-05'),
    (3,  'FM-0003', 'Терминатор 2: Судный день','Terminator 2: Judgment Day', 1991, 137, '16+', 'Blu-ray', 2,
     'Борьба за будущее человечества против машин.', DATE '2024-03-11'),
    (4,  'FM-0004', 'Матрица',                  'The Matrix',               1999, 136, '16+', 'Blu-ray', 2,
     'Хакер узнаёт, что реальность - симуляция.', DATE '2024-03-11'),
    (5,  'FM-0005', 'Один дома',                'Home Alone',               1990, 103, '6+',  'VHS',     1,
     'Мальчик остаётся дома один и даёт отпор грабителям.', DATE '2024-01-20'),
    (6,  'FM-0006', 'Король Лев',               'The Lion King',            1994,  88, '0+',  'VHS',     1,
     'Львёнок Симба возвращается, чтобы занять своё место.', DATE '2024-01-20'),
    (7,  'FM-0007', 'Список Шиндлера',          'Schindler''s List',        1993, 195, '18+', 'DVD',     3,
     'История спасения евреев во время Холокоста.', DATE '2024-04-08'),
    (8,  'FM-0008', 'Начало',                   'Inception',                2010, 148, '16+', 'Blu-ray', 2,
     'Команда специалистов проникает в сны, чтобы украсть идею.', DATE '2024-05-15'),
    (9,  'FM-0009', 'Планета Земля',            'Planet Earth',             2006,  50, '0+',  'DVD',     1,
     'Документальный сериал о природе нашей планеты.', DATE '2024-06-02'),
    (10, 'FM-0010', 'Тайна Коко',               'Coco',                     2017, 105, '6+',  'Blu-ray', 2,
     'Мальчик попадает в страну мёртвых и ищет своего прадеда.', DATE '2025-01-14');

-- Жанры фильмов (у части фильмов более одного жанра)
INSERT INTO film_genre (film_id, genre_id, is_primary) VALUES
    (1,  2, true), (1,  5, false),
    (2,  1, true), (2,  5, false),
    (3,  1, true), (3,  4, false),
    (4,  4, true), (4,  1, false), (4, 5, false),
    (5,  3, true), (5,  1, false),
    (6,  6, true), (6,  2, false),
    (7,  2, true),
    (8,  4, true), (8,  5, false),
    (9,  7, true),
    (10, 6, true), (10, 2, false);

-- -----------------------------------------------------------------------------
-- 4. Физические экземпляры (для части фильмов - по несколько копий)
-- -----------------------------------------------------------------------------
INSERT INTO video_copy (copy_id, film_id, inventory_code, acquisition_date, purchase_price, condition, storage_location)
OVERRIDING SYSTEM VALUE VALUES
    (1,  1,  'VC-00001', DATE '2024-02-06', 450.00, 'good',    'Зал A, ст. 1'),
    (2,  1,  'VC-00002', DATE '2025-02-10', 520.00, 'new',     'Зал A, ст. 1'),
    (3,  2,  'VC-00003', DATE '2024-02-06', 450.00, 'worn',    'Зал A, ст. 2'),
    (4,  3,  'VC-00004', DATE '2024-03-12', 890.00, 'good',    'Зал A, ст. 3'),
    (5,  4,  'VC-00005', DATE '2024-03-12', 890.00, 'good',    'Зал A, ст. 3'),
    (6,  4,  'VC-00006', DATE '2025-03-01', 950.00, 'new',     'Зал A, ст. 3'),
    (7,  5,  'VC-00007', DATE '2024-01-21', 200.00, 'worn',    'Зал B, ст. 1'),
    (8,  5,  'VC-00008', DATE '2024-01-21', 200.00, 'damaged', 'Зал B, ст. 1'),
    (9,  6,  'VC-00009', DATE '2024-01-21', 220.00, 'good',    'Зал B, ст. 2'),
    (10, 7,  'VC-00010', DATE '2024-04-09', 480.00, 'good',    'Зал B, ст. 3'),
    (11, 8,  'VC-00011', DATE '2024-05-16', 900.00, 'good',    'Зал A, ст. 4'),
    (12, 8,  'VC-00012', DATE '2024-05-16', 900.00, 'worn',    'Зал A, ст. 4'),
    (13, 9,  'VC-00013', DATE '2024-06-03', 300.00, 'good',    'Зал B, ст. 4'),
    (14, 10, 'VC-00014', DATE '2025-01-15', 980.00, 'new',     'Зал A, ст. 5'),
    (15, 10, 'VC-00015', DATE '2025-01-15', 980.00, 'good',    'Зал A, ст. 5'),
    (16, 2,  'VC-00016', DATE '2024-02-06', 450.00, 'written_off', 'Архив');

-- -----------------------------------------------------------------------------
-- 5. Клиенты
-- -----------------------------------------------------------------------------
INSERT INTO customer (customer_id, card_number, last_name, first_name, middle_name, phone, email,
                      birth_date, address, registration_date, status)
OVERRIDING SYSTEM VALUE VALUES
    (1, 'CR-00001', 'Иванов',   'Сергей',   'Петрович',  '+79161234501', 'ivanov@example.com',
     DATE '1985-04-12', 'г. Москва, ул. Ленина, д. 1, кв. 5', DATE '2024-01-15', 'active'),
    (2, 'CR-00002', 'Петрова',  'Анна',     'Ивановна',  '+79161234502', 'petrova@example.com',
     DATE '1992-07-30', 'г. Москва, ул. Мира, д. 14, кв. 62', DATE '2024-02-20', 'active'),
    (3, 'CR-00003', 'Сидоров',  'Максим',   'Олегович',  '+79161234503', 'sidorov@example.com',
     DATE '1978-11-05', 'г. Москва, пр. Вернадского, д. 33', DATE '2024-03-05', 'active'),
    (4, 'CR-00004', 'Кузнецова','Ольга',    'Дмитриевна','+79161234504', 'kuznetsova@example.com',
     DATE '2001-02-18', 'г. Москва, ул. Строителей, д. 7, кв. 12', DATE '2024-04-11', 'active'),
    (5, 'CR-00005', 'Смирнов',  'Дмитрий',  NULL,        '+79161234505', NULL,
     DATE '1990-09-25', 'г. Москва, ул. Гагарина, д. 9', DATE '2024-05-02', 'active'),
    (6, 'CR-00006', 'Морозов',  'Артём',    'Сергеевич','+79161234506', 'morozov@example.com',
     DATE '1996-12-01', 'г. Москва, ул. Пушкина, д. 3, кв. 44', DATE '2024-06-18', 'blocked');

-- -----------------------------------------------------------------------------
-- 6. Сотрудники
-- -----------------------------------------------------------------------------
INSERT INTO employee (employee_id, personnel_number, last_name, first_name, middle_name, position,
                      phone, hire_date, dismissal_date, status)
OVERRIDING SYSTEM VALUE VALUES
    (1, 'EMP-0001', 'Егорова',  'Мария',  'Алексеевна', 'administrator', '+74951234501',
     DATE '2022-03-01', NULL, 'active'),
    (2, 'EMP-0002', 'Волков',   'Игорь',  'Николаевич', 'cashier',       '+74951234502',
     DATE '2023-01-09', NULL, 'active'),
    (3, 'EMP-0003', 'Тихонов',  'Павел',  'Романович',  'storekeeper',   '+74951234503',
     DATE '2021-08-16', DATE '2026-04-30', 'dismissed');

-- -----------------------------------------------------------------------------
-- 7. Операции проката
--    1) RN-000001 - полностью возвращённый прокат без просрочки
--    2) RN-000002 - возвращённый прокат с просрочкой
--    3) RN-000003 - активный прокат в срок
--    4) RN-000004 - активный просроченный прокат
--    5) RN-000005 - возвращённый прокат с несколькими экземплярами
--    6) RN-000006 - активный прокат с несколькими экземплярами
-- -----------------------------------------------------------------------------
INSERT INTO rental (rental_id, rental_number, customer_id, employee_id, issue_date,
                    planned_return_date, actual_return_date, deposit_amount, status, note)
OVERRIDING SYSTEM VALUE VALUES
    (1, 'RN-000001', 1, 1, DATE '2026-08-10', DATE '2026-08-13', DATE '2026-08-12', 300.00, 'issued', NULL),
    (2, 'RN-000002', 2, 2, DATE '2026-08-20', DATE '2026-08-23', DATE '2026-08-27', 300.00, 'issued', NULL),
    (3, 'RN-000003', 3, 1, DATE '2026-09-26', DATE '2026-09-30', NULL,              400.00, 'issued', NULL),
    (4, 'RN-000004', 4, 2, DATE '2026-09-15', DATE '2026-09-18', NULL,              300.00, 'issued', 'Клиент не отвечает на звонки'),
    (5, 'RN-000005', 5, 1, DATE '2026-09-01', DATE '2026-09-04', DATE '2026-09-03', 500.00, 'issued', NULL),
    (6, 'RN-000006', 6, 2, DATE '2026-09-22', DATE '2026-09-29', NULL,              600.00, 'issued', NULL);

-- Позиции проката. Триггер сам переведёт закрытые операции в статус closed.
INSERT INTO rental_item (rental_item_id, rental_id, copy_id, daily_rate, status, actual_return_date, condition_on_return)
OVERRIDING SYSTEM VALUE VALUES
    -- RN-000001: возвращён без просрочки (2 суток)
    (1, 1,  1,  40.00, 'returned', DATE '2026-08-12', 'good'),
    -- RN-000002: возвращён с просрочкой (7 суток вместо 3)
    (2, 2,  4,  90.00, 'returned', DATE '2026-08-27', 'good'),
    -- RN-000003: активный прокат в срок
    (3, 3,  5,  90.00, 'issued',   NULL,              NULL),
    -- RN-000004: активный просроченный прокат
    (4, 4,  9,  40.00, 'issued',   NULL,              NULL),
    -- RN-000005: возвращённый прокат с несколькими экземплярами
    (5, 5, 11,  90.00, 'returned', DATE '2026-09-03', 'good'),
    (6, 5, 13,  60.00, 'returned', DATE '2026-09-03', 'good'),
    (7, 5, 14,  90.00, 'returned', DATE '2026-09-03', 'new'),
    -- RN-000006: активный прокат с несколькими экземплярами
    (8, 6,  2,  40.00, 'issued',   NULL,              NULL),
    (9, 6, 12,  90.00, 'issued',   NULL,              NULL);

-- -----------------------------------------------------------------------------
-- 8. Платежи
-- -----------------------------------------------------------------------------
INSERT INTO payment (payment_id, payment_number, rental_id, payment_date, amount, method, payment_type)
OVERRIDING SYSTEM VALUE VALUES
    (1, 'PM-000001', 1, TIMESTAMP '2026-08-10 11:15:00', 300.00, 'cash', 'deposit'),
    (2, 'PM-000002', 1, TIMESTAMP '2026-08-12 18:40:00', 100.00, 'card', 'rent'),
    (3, 'PM-000003', 2, TIMESTAMP '2026-08-20 12:05:00', 300.00, 'card', 'deposit'),
    (4, 'PM-000004', 2, TIMESTAMP '2026-08-27 19:10:00', 630.00, 'card', 'rent'),
    (5, 'PM-000005', 2, TIMESTAMP '2026-08-27 19:12:00', 120.00, 'card', 'penalty'),
    (6, 'PM-000006', 3, TIMESTAMP '2026-09-26 10:30:00', 400.00, 'cash', 'deposit'),
    (7, 'PM-000007', 4, TIMESTAMP '2026-09-15 16:45:00', 300.00, 'card', 'deposit'),
    (8, 'PM-000008', 5, TIMESTAMP '2026-09-01 09:50:00', 500.00, 'transfer', 'deposit'),
    (9, 'PM-000009', 5, TIMESTAMP '2026-09-03 20:15:00', 540.00, 'transfer', 'rent'),
    (10,'PM-000010', 6, TIMESTAMP '2026-09-22 14:20:00', 600.00, 'card', 'deposit');

-- -----------------------------------------------------------------------------
-- 9. Синхронизация последовательностей после вставки явных идентификаторов
-- -----------------------------------------------------------------------------
SELECT setval(pg_get_serial_sequence('genre', 'genre_id'),          (SELECT max(genre_id) FROM genre));
SELECT setval(pg_get_serial_sequence('tariff', 'tariff_id'),        (SELECT max(tariff_id) FROM tariff));
SELECT setval(pg_get_serial_sequence('film', 'film_id'),            (SELECT max(film_id) FROM film));
SELECT setval(pg_get_serial_sequence('video_copy', 'copy_id'),      (SELECT max(copy_id) FROM video_copy));
SELECT setval(pg_get_serial_sequence('customer', 'customer_id'),    (SELECT max(customer_id) FROM customer));
SELECT setval(pg_get_serial_sequence('employee', 'employee_id'),    (SELECT max(employee_id) FROM employee));
SELECT setval(pg_get_serial_sequence('rental', 'rental_id'),        (SELECT max(rental_id) FROM rental));
SELECT setval(pg_get_serial_sequence('rental_item', 'rental_item_id'), (SELECT max(rental_item_id) FROM rental_item));
SELECT setval(pg_get_serial_sequence('payment', 'payment_id'),      (SELECT max(payment_id) FROM payment));

-- -----------------------------------------------------------------------------
-- 10. Контроль загрузки
-- -----------------------------------------------------------------------------
\echo '--- Загружено строк (3NF) ---'
SELECT 'genre'       AS table_name, count(*) FROM genre
UNION ALL SELECT 'tariff',      count(*) FROM tariff
UNION ALL SELECT 'film',        count(*) FROM film
UNION ALL SELECT 'film_genre',  count(*) FROM film_genre
UNION ALL SELECT 'video_copy',  count(*) FROM video_copy
UNION ALL SELECT 'customer',    count(*) FROM customer
UNION ALL SELECT 'employee',    count(*) FROM employee
UNION ALL SELECT 'rental',      count(*) FROM rental
UNION ALL SELECT 'rental_item', count(*) FROM rental_item
UNION ALL SELECT 'payment',     count(*) FROM payment
ORDER BY table_name;

\echo '--- Статусы операций проката (заполнены триггером) ---'
SELECT rental_number, status, issue_date, planned_return_date, actual_return_date
  FROM rental ORDER BY rental_id;
