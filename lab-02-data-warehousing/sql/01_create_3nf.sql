-- =============================================================================
-- Лабораторная работа №2. Хранилища данных.
-- Вариант 14. Система учета в видеопрокате.
-- Файл 01: создание схемы 3NF (video_rental_3nf).
-- СУБД: PostgreSQL 17.
-- Скрипт идемпотентен: повторный запуск пересоздает схему с нуля.
-- =============================================================================

\set ON_ERROR_STOP on

-- -----------------------------------------------------------------------------
-- 0. Служебная схема lab.
-- "Текущая дата" вынесена в функцию, чтобы результаты проверок были
-- воспроизводимыми независимо от даты запуска скрипта.
-- -----------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS lab;

CREATE OR REPLACE FUNCTION lab.current_date() RETURNS date
    LANGUAGE sql IMMUTABLE AS $$ SELECT DATE '2026-09-28' $$;

CREATE OR REPLACE FUNCTION lab.now() RETURNS timestamp
    LANGUAGE sql IMMUTABLE AS $$ SELECT TIMESTAMP '2026-09-28 12:00:00' $$;

COMMENT ON SCHEMA lab IS 'Служебные объекты лабораторной работы (фиксированная "текущая дата")';
COMMENT ON FUNCTION lab.current_date() IS 'Текущая дата системы учета видеопроката (зафиксирована для воспроизводимости)';
COMMENT ON FUNCTION lab.now() IS 'Текущая отметка времени системы учета видеопроката (зафиксирована)';

-- -----------------------------------------------------------------------------
-- 1. Пересоздание схемы 3NF
-- -----------------------------------------------------------------------------
DROP SCHEMA IF EXISTS video_rental_3nf CASCADE;
CREATE SCHEMA video_rental_3nf;
COMMENT ON SCHEMA video_rental_3nf IS 'Операционная (транзакционная) модель видеопроката в третьей нормальной форме';

SET search_path TO video_rental_3nf;

-- =============================================================================
-- 2. Справочники
-- =============================================================================

-- 2.1 Жанры ---------------------------------------------------------------
CREATE TABLE genre (
    genre_id    integer      GENERATED ALWAYS AS IDENTITY,
    code        varchar(12)  NOT NULL,
    name        varchar(60)  NOT NULL,
    description varchar(300),
    CONSTRAINT pk_genre PRIMARY KEY (genre_id),
    CONSTRAINT uq_genre_code UNIQUE (code),
    CONSTRAINT uq_genre_name UNIQUE (name),
    CONSTRAINT ck_genre_code CHECK (code ~ '^[A-Z0-9_]{2,12}$')
);

COMMENT ON TABLE genre IS 'Справочник жанров фильмов';
COMMENT ON COLUMN genre.genre_id IS 'Суррогатный первичный ключ жанра';
COMMENT ON COLUMN genre.code IS 'Краткий код жанра (бизнес-ключ)';
COMMENT ON COLUMN genre.name IS 'Название жанра';

-- 2.2 Тарифы (прайс-лист проката) -----------------------------------------
CREATE TABLE tariff (
    tariff_id        integer      GENERATED ALWAYS AS IDENTITY,
    code             varchar(12)  NOT NULL,
    name             varchar(80)  NOT NULL,
    daily_rate       numeric(8,2) NOT NULL,
    max_rental_days  smallint     NOT NULL,
    late_fee_per_day numeric(8,2) NOT NULL,
    valid_from       date         NOT NULL,
    valid_to         date,
    CONSTRAINT pk_tariff PRIMARY KEY (tariff_id),
    CONSTRAINT uq_tariff_code UNIQUE (code),
    CONSTRAINT uq_tariff_name UNIQUE (name),
    CONSTRAINT ck_tariff_daily_rate CHECK (daily_rate > 0),
    CONSTRAINT ck_tariff_late_fee CHECK (late_fee_per_day >= 0),
    CONSTRAINT ck_tariff_max_days CHECK (max_rental_days BETWEEN 1 AND 30),
    CONSTRAINT ck_tariff_period CHECK (valid_to IS NULL OR valid_to > valid_from)
);

COMMENT ON TABLE tariff IS 'Тарифы (прайс-лист) проката: стоимость суток, срок и пеня за просрочку';
COMMENT ON COLUMN tariff.daily_rate IS 'Стоимость одних суток проката, руб.';
COMMENT ON COLUMN tariff.max_rental_days IS 'Нормативный срок проката, суток';
COMMENT ON COLUMN tariff.late_fee_per_day IS 'Пеня за каждые сутки просрочки, руб.';
COMMENT ON COLUMN tariff.valid_to IS 'Дата окончания действия тарифа; NULL - действует бессрочно';

-- =============================================================================
-- 3. Каталог фильмов и физические экземпляры
-- =============================================================================

-- 3.1 Фильм (каталожная карточка) -----------------------------------------
CREATE TABLE film (
    film_id        integer       GENERATED ALWAYS AS IDENTITY,
    catalog_number varchar(16)   NOT NULL,
    title          varchar(200)  NOT NULL,
    original_title varchar(200),
    release_year   smallint      NOT NULL,
    duration_min   smallint      NOT NULL,
    age_rating     varchar(8)    NOT NULL,
    media_type     varchar(10)    NOT NULL,
    tariff_id      integer       NOT NULL,
    synopsis       varchar(1000),
    added_on       date          NOT NULL DEFAULT lab.current_date(),
    CONSTRAINT pk_film PRIMARY KEY (film_id),
    CONSTRAINT uq_film_catalog_number UNIQUE (catalog_number),
    CONSTRAINT uq_film_title_year UNIQUE (title, release_year, media_type),
    CONSTRAINT fk_film_tariff FOREIGN KEY (tariff_id) REFERENCES tariff (tariff_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_film_catalog_number CHECK (catalog_number ~ '^FM-[0-9]{4}$'),
    CONSTRAINT ck_film_release_year CHECK (release_year BETWEEN 1895 AND 2100),
    CONSTRAINT ck_film_duration CHECK (duration_min BETWEEN 1 AND 600),
    CONSTRAINT ck_film_age_rating CHECK (age_rating IN ('0+','6+','12+','16+','18+')),
    CONSTRAINT ck_film_media_type CHECK (media_type IN ('VHS','DVD','Blu-ray'))
);

COMMENT ON TABLE film IS 'Каталог фильмов видеопроката (описательная карточка фильма без учета экземпляров)';
COMMENT ON COLUMN film.catalog_number IS 'Каталожный номер фильма (бизнес-ключ)';
COMMENT ON COLUMN film.tariff_id IS 'Действующий тариф проката фильма';
COMMENT ON COLUMN film.media_type IS 'Носитель: VHS, DVD, Blu-ray';

-- 3.2 Связь фильм - жанр (M:N) --------------------------------------------
CREATE TABLE film_genre (
    film_id    integer NOT NULL,
    genre_id   integer NOT NULL,
    is_primary boolean NOT NULL DEFAULT false,
    CONSTRAINT pk_film_genre PRIMARY KEY (film_id, genre_id),
    CONSTRAINT fk_film_genre_film FOREIGN KEY (film_id) REFERENCES film (film_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_film_genre_genre FOREIGN KEY (genre_id) REFERENCES genre (genre_id)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

COMMENT ON TABLE film_genre IS 'Связь "многие ко многим" между фильмами и жанрами';
COMMENT ON COLUMN film_genre.is_primary IS 'Признак основного жанра фильма (не более одного на фильм)';

-- Не более одного основного жанра на фильм
CREATE UNIQUE INDEX ux_film_genre_primary ON film_genre (film_id) WHERE is_primary;
CREATE INDEX ix_film_genre_genre ON film_genre (genre_id);

-- 3.3 Физический экземпляр (носитель) -------------------------------------
CREATE TABLE video_copy (
    copy_id          integer       GENERATED ALWAYS AS IDENTITY,
    film_id          integer       NOT NULL,
    inventory_code   varchar(16)   NOT NULL,
    acquisition_date date          NOT NULL DEFAULT lab.current_date(),
    purchase_price   numeric(10,2) NOT NULL,
    condition        varchar(12)   NOT NULL DEFAULT 'new',
    storage_location varchar(20),
    CONSTRAINT pk_video_copy PRIMARY KEY (copy_id),
    CONSTRAINT uq_video_copy_inventory_code UNIQUE (inventory_code),
    CONSTRAINT fk_video_copy_film FOREIGN KEY (film_id) REFERENCES film (film_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_video_copy_inventory_code CHECK (inventory_code ~ '^VC-[0-9]{5}$'),
    CONSTRAINT ck_video_copy_price CHECK (purchase_price >= 0),
    CONSTRAINT ck_video_copy_condition CHECK (condition IN ('new','good','worn','damaged','written_off'))
);

COMMENT ON TABLE video_copy IS 'Физические экземпляры (носители) фильмов, находящиеся в фонде видеопроката';
COMMENT ON COLUMN video_copy.inventory_code IS 'Инвентарный номер экземпляра (бизнес-ключ)';
COMMENT ON COLUMN video_copy.condition IS 'Состояние экземпляра: new, good, worn, damaged, written_off';
COMMENT ON COLUMN video_copy.storage_location IS 'Место хранения (зал, стеллаж)';

CREATE INDEX ix_video_copy_film ON video_copy (film_id);
CREATE INDEX ix_video_copy_condition ON video_copy (condition);

-- =============================================================================
-- 4. Участники проката
-- =============================================================================

-- 4.1 Клиент --------------------------------------------------------------
CREATE TABLE customer (
    customer_id       integer      GENERATED ALWAYS AS IDENTITY,
    card_number       varchar(12)  NOT NULL,
    last_name         varchar(60)  NOT NULL,
    first_name        varchar(60)  NOT NULL,
    middle_name       varchar(60),
    phone             varchar(20)  NOT NULL,
    email             varchar(120),
    birth_date        date,
    address           varchar(200),
    registration_date date         NOT NULL DEFAULT lab.current_date(),
    status            varchar(10)  NOT NULL DEFAULT 'active',
    CONSTRAINT pk_customer PRIMARY KEY (customer_id),
    CONSTRAINT uq_customer_card_number UNIQUE (card_number),
    CONSTRAINT uq_customer_phone UNIQUE (phone),
    CONSTRAINT uq_customer_email UNIQUE (email),
    CONSTRAINT ck_customer_card_number CHECK (card_number ~ '^CR-[0-9]{5}$'),
    CONSTRAINT ck_customer_phone CHECK (phone ~ '^\+7[0-9]{10}$'),
    CONSTRAINT ck_customer_email CHECK (email IS NULL OR email ~ '^[^@[:space:]]+@[^@[:space:]]+\.[A-Za-z]{2,}$'),
    CONSTRAINT ck_customer_birth_date CHECK (birth_date IS NULL OR birth_date < registration_date),
    CONSTRAINT ck_customer_status CHECK (status IN ('active','blocked','archived'))
);

COMMENT ON TABLE customer IS 'Клиенты (держатели клубных карт) видеопроката';
COMMENT ON COLUMN customer.card_number IS 'Номер клубной карты (бизнес-ключ)';
COMMENT ON COLUMN customer.status IS 'Статус клиента: active, blocked, archived';

CREATE INDEX ix_customer_name ON customer (last_name, first_name);

-- 4.2 Сотрудник -----------------------------------------------------------
CREATE TABLE employee (
    employee_id      integer     GENERATED ALWAYS AS IDENTITY,
    personnel_number varchar(10) NOT NULL,
    last_name        varchar(60) NOT NULL,
    first_name       varchar(60) NOT NULL,
    middle_name      varchar(60),
    position         varchar(40) NOT NULL,
    phone            varchar(20) NOT NULL,
    hire_date        date        NOT NULL,
    dismissal_date   date,
    status           varchar(10) NOT NULL DEFAULT 'active',
    CONSTRAINT pk_employee PRIMARY KEY (employee_id),
    CONSTRAINT uq_employee_personnel_number UNIQUE (personnel_number),
    CONSTRAINT uq_employee_phone UNIQUE (phone),
    CONSTRAINT ck_employee_personnel_number CHECK (personnel_number ~ '^EMP-[0-9]{4}$'),
    CONSTRAINT ck_employee_position CHECK (position IN ('administrator','cashier','storekeeper','manager')),
    CONSTRAINT ck_employee_status CHECK (status IN ('active','dismissed')),
    CONSTRAINT ck_employee_dates CHECK (dismissal_date IS NULL OR dismissal_date >= hire_date),
    CONSTRAINT ck_employee_status_dismissal CHECK ((status = 'dismissed') = (dismissal_date IS NOT NULL))
);

COMMENT ON TABLE employee IS 'Сотрудники видеопроката, оформляющие выдачу и возврат';
COMMENT ON COLUMN employee.personnel_number IS 'Табельный номер (бизнес-ключ)';
COMMENT ON COLUMN employee.position IS 'Должность: administrator, cashier, storekeeper, manager';

-- =============================================================================
-- 5. Операции проката
-- =============================================================================

-- 5.1 Прокат (заголовок операции) -----------------------------------------
CREATE TABLE rental (
    rental_id           integer       GENERATED ALWAYS AS IDENTITY,
    rental_number       varchar(12)   NOT NULL,
    customer_id         integer       NOT NULL,
    employee_id         integer       NOT NULL,
    issue_date          date          NOT NULL DEFAULT lab.current_date(),
    planned_return_date date          NOT NULL,
    actual_return_date  date,
    deposit_amount      numeric(10,2) NOT NULL DEFAULT 0,
    status              varchar(12)   NOT NULL DEFAULT 'issued',
    note                varchar(300),
    CONSTRAINT pk_rental PRIMARY KEY (rental_id),
    CONSTRAINT uq_rental_number UNIQUE (rental_number),
    CONSTRAINT fk_rental_customer FOREIGN KEY (customer_id) REFERENCES customer (customer_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_rental_employee FOREIGN KEY (employee_id) REFERENCES employee (employee_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_rental_number CHECK (rental_number ~ '^RN-[0-9]{6}$'),
    CONSTRAINT ck_rental_issue_planned CHECK (planned_return_date >= issue_date),
    CONSTRAINT ck_rental_actual CHECK (actual_return_date IS NULL OR actual_return_date >= issue_date),
    CONSTRAINT ck_rental_deposit CHECK (deposit_amount >= 0),
    CONSTRAINT ck_rental_status CHECK (status IN ('issued','closed','cancelled')),
    CONSTRAINT ck_rental_closed_actual CHECK (status <> 'closed' OR actual_return_date IS NOT NULL)
);

COMMENT ON TABLE rental IS 'Операции проката (выдача одного или нескольких экземпляров клиенту)';
COMMENT ON COLUMN rental.rental_number IS 'Номер операции проката (бизнес-ключ)';
COMMENT ON COLUMN rental.planned_return_date IS 'Плановая дата возврата всего проката';
COMMENT ON COLUMN rental.actual_return_date IS 'Фактическая дата возврата; заполняется автоматически при возврате всех экземпляров';
COMMENT ON COLUMN rental.status IS 'Статус операции: issued (выдан), closed (закрыт), cancelled (отменен)';

CREATE INDEX ix_rental_customer ON rental (customer_id);
CREATE INDEX ix_rental_employee ON rental (employee_id);
CREATE INDEX ix_rental_planned_return ON rental (planned_return_date);
CREATE INDEX ix_rental_status ON rental (status);

-- 5.2 Позиция проката (конкретный экземпляр в операции) -------------------
CREATE TABLE rental_item (
    rental_item_id      integer     GENERATED ALWAYS AS IDENTITY,
    rental_id           integer     NOT NULL,
    copy_id             integer     NOT NULL,
    daily_rate          numeric(8,2) NOT NULL,
    status              varchar(10) NOT NULL DEFAULT 'issued',
    actual_return_date  date,
    condition_on_return varchar(12),
    CONSTRAINT pk_rental_item PRIMARY KEY (rental_item_id),
    CONSTRAINT uq_rental_item UNIQUE (rental_id, copy_id),
    CONSTRAINT fk_rental_item_rental FOREIGN KEY (rental_id) REFERENCES rental (rental_id)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_rental_item_copy FOREIGN KEY (copy_id) REFERENCES video_copy (copy_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_rental_item_daily_rate CHECK (daily_rate > 0),
    CONSTRAINT ck_rental_item_status CHECK (status IN ('issued','returned')),
    CONSTRAINT ck_rental_item_return CHECK ((status = 'returned') = (actual_return_date IS NOT NULL)),
    CONSTRAINT ck_rental_item_condition CHECK (condition_on_return IS NULL
        OR condition_on_return IN ('new','good','worn','damaged','written_off')),
    CONSTRAINT ck_rental_item_condition_required CHECK (status <> 'returned' OR condition_on_return IS NOT NULL)
);

COMMENT ON TABLE rental_item IS 'Позиции проката: какой именно физический экземпляр выдан в рамках операции';
COMMENT ON COLUMN rental_item.daily_rate IS 'Стоимость суток проката, зафиксированная на момент выдачи (историческая цена)';
COMMENT ON COLUMN rental_item.condition_on_return IS 'Состояние экземпляра при возврате';

CREATE INDEX ix_rental_item_rental ON rental_item (rental_id);
CREATE INDEX ix_rental_item_copy ON rental_item (copy_id);

-- Бизнес-правило: один экземпляр не может находиться в двух активных прокатах.
-- В PostgreSQL это гарантируется частичным уникальным индексом.
CREATE UNIQUE INDEX ux_rental_item_active_copy ON rental_item (copy_id) WHERE status = 'issued';

-- 5.3 Платежи -------------------------------------------------------------
CREATE TABLE payment (
    payment_id     integer       GENERATED ALWAYS AS IDENTITY,
    payment_number varchar(12)   NOT NULL,
    rental_id      integer       NOT NULL,
    payment_date   timestamp     NOT NULL DEFAULT lab.now(),
    amount         numeric(10,2) NOT NULL,
    method         varchar(10)   NOT NULL,
    payment_type   varchar(10)   NOT NULL,
    CONSTRAINT pk_payment PRIMARY KEY (payment_id),
    CONSTRAINT uq_payment_number UNIQUE (payment_number),
    CONSTRAINT fk_payment_rental FOREIGN KEY (rental_id) REFERENCES rental (rental_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT ck_payment_number CHECK (payment_number ~ '^PM-[0-9]{6}$'),
    CONSTRAINT ck_payment_amount CHECK (amount > 0),
    CONSTRAINT ck_payment_method CHECK (method IN ('cash','card','transfer')),
    CONSTRAINT ck_payment_type CHECK (payment_type IN ('deposit','rent','penalty'))
);

COMMENT ON TABLE payment IS 'Платежи клиентов по операциям проката (залог, оплата проката, пеня)';
COMMENT ON COLUMN payment.amount IS 'Сумма платежа, руб. (строго положительная)';
COMMENT ON COLUMN payment.payment_type IS 'Тип платежа: deposit (залог), rent (оплата проката), penalty (пеня)';

CREATE INDEX ix_payment_rental ON payment (rental_id);
CREATE INDEX ix_payment_date ON payment (payment_date);

-- =============================================================================
-- 6. Автоматическое сопровождение статуса проката
-- Правило: прокат закрывается, когда возвращены все его позиции.
-- CHECK-ограничением это выразить нельзя (зависит от других строк),
-- поэтому используется триггер.
-- =============================================================================
CREATE OR REPLACE FUNCTION trg_rental_item_sync() RETURNS trigger
    LANGUAGE plpgsql AS $$
DECLARE
    v_rental_id integer;
    v_open      integer;
    v_returned  integer;
    v_max_date  date;
BEGIN
    v_rental_id := COALESCE(NEW.rental_id, OLD.rental_id);

    SELECT count(*) FILTER (WHERE status = 'issued'),
           count(*) FILTER (WHERE status = 'returned'),
           max(actual_return_date)
      INTO v_open, v_returned, v_max_date
      FROM rental_item
     WHERE rental_id = v_rental_id;

    IF v_open = 0 AND v_returned > 0 THEN
        UPDATE rental
           SET status = 'closed', actual_return_date = v_max_date
         WHERE rental_id = v_rental_id AND status = 'issued';
    ELSIF v_open > 0 THEN
        UPDATE rental
           SET status = 'issued', actual_return_date = NULL
         WHERE rental_id = v_rental_id AND status = 'closed';
    END IF;

    RETURN NULL;
END $$;

COMMENT ON FUNCTION trg_rental_item_sync() IS 'Синхронизация статуса и даты фактического возврата операции проката с состоянием ее позиций';

CREATE TRIGGER trg_rental_item_sync_aiud
    AFTER INSERT OR UPDATE OR DELETE ON rental_item
    FOR EACH ROW EXECUTE FUNCTION trg_rental_item_sync();

-- =============================================================================
-- 7. Представления (вычисляемые показатели не хранятся в таблицах)
-- =============================================================================

-- 7.1 Каталог фильмов с жанрами -------------------------------------------
CREATE VIEW v_film_catalog AS
SELECT f.film_id,
       f.catalog_number,
       f.title,
       f.release_year,
       f.media_type,
       f.age_rating,
       f.duration_min,
       t.code  AS tariff_code,
       t.daily_rate,
       (SELECT string_agg(g.name, ', ' ORDER BY g.name)
          FROM film_genre fg JOIN genre g ON g.genre_id = fg.genre_id
         WHERE fg.film_id = f.film_id) AS genres,
       (SELECT count(*) FROM video_copy vc WHERE vc.film_id = f.film_id) AS copies_total
  FROM film f
  JOIN tariff t ON t.tariff_id = f.tariff_id;

COMMENT ON VIEW v_film_catalog IS 'Каталог фильмов с перечнем жанров и количеством экземпляров';

-- 7.2 Экземпляры с признаком доступности ----------------------------------
CREATE VIEW v_copy_status AS
SELECT vc.copy_id,
       vc.inventory_code,
       f.film_id,
       f.title,
       vc.condition,
       vc.storage_location,
       EXISTS (SELECT 1 FROM rental_item ri
                WHERE ri.copy_id = vc.copy_id AND ri.status = 'issued') AS is_rented,
       (vc.condition <> 'written_off'
        AND NOT EXISTS (SELECT 1 FROM rental_item ri
                         WHERE ri.copy_id = vc.copy_id AND ri.status = 'issued')) AS is_available
  FROM video_copy vc
  JOIN film f ON f.film_id = vc.film_id;

COMMENT ON VIEW v_copy_status IS 'Состояние физических экземпляров и признак доступности к выдаче';

-- 7.3 Активные прокаты ----------------------------------------------------
CREATE VIEW v_active_rental AS
SELECT r.rental_id,
       r.rental_number,
       r.issue_date,
       r.planned_return_date,
       c.card_number,
       c.last_name || ' ' || c.first_name AS customer_name,
       e.personnel_number,
       e.last_name || ' ' || e.first_name AS employee_name,
       (SELECT count(*) FROM rental_item ri WHERE ri.rental_id = r.rental_id) AS items_total,
       (SELECT count(*) FROM rental_item ri WHERE ri.rental_id = r.rental_id AND ri.status = 'issued') AS items_open,
       (r.planned_return_date < lab.current_date()) AS is_overdue,
       (lab.current_date() - r.planned_return_date) AS overdue_days
  FROM rental r
  JOIN customer c ON c.customer_id = r.customer_id
  JOIN employee e ON e.employee_id = r.employee_id
 WHERE r.status = 'issued';

COMMENT ON VIEW v_active_rental IS 'Активные (незакрытые) операции проката с признаком просрочки';

-- 7.4 Стоимость проката по позициям ---------------------------------------
CREATE VIEW v_rental_item_cost AS
SELECT ri.rental_item_id,
       r.rental_id,
       r.rental_number,
       ri.copy_id,
       vc.inventory_code,
       f.title,
       r.issue_date,
       r.planned_return_date,
       ri.actual_return_date,
       ri.daily_rate,
       GREATEST(1, COALESCE(ri.actual_return_date, lab.current_date()) - r.issue_date) AS billed_days,
       ri.daily_rate * GREATEST(1, COALESCE(ri.actual_return_date, lab.current_date()) - r.issue_date) AS item_cost,
       CASE WHEN ri.actual_return_date IS NULL AND r.planned_return_date < lab.current_date()
            THEN lab.current_date() - r.planned_return_date ELSE 0 END AS overdue_days
  FROM rental_item ri
  JOIN rental r ON r.rental_id = ri.rental_id
  JOIN video_copy vc ON vc.copy_id = ri.copy_id
  JOIN film f ON f.film_id = vc.film_id;

COMMENT ON VIEW v_rental_item_cost IS 'Расчет стоимости проката по каждой позиции (минимум одни сутки)';

-- 7.5 Итоги по операции проката -------------------------------------------
CREATE VIEW v_rental_total AS
SELECT r.rental_id,
       r.rental_number,
       r.status,
       r.issue_date,
       r.planned_return_date,
       r.actual_return_date,
       COALESCE((SELECT sum(ic.item_cost) FROM v_rental_item_cost ic WHERE ic.rental_id = r.rental_id), 0) AS rent_cost,
       COALESCE((SELECT sum(p.amount) FROM payment p WHERE p.rental_id = r.rental_id), 0) AS paid_total,
       COALESCE((SELECT sum(p.amount) FROM payment p
                  WHERE p.rental_id = r.rental_id AND p.payment_type = 'penalty'), 0) AS penalty_total
  FROM rental r;

COMMENT ON VIEW v_rental_total IS 'Стоимость проката, сумма платежей и пеня по каждой операции';

-- =============================================================================
-- 8. Контроль выполнения
-- =============================================================================
\echo '--- Схема 3NF создана. Перечень таблиц: ---'
SELECT table_name
  FROM information_schema.tables
 WHERE table_schema = 'video_rental_3nf' AND table_type = 'BASE TABLE'
 ORDER BY table_name;
