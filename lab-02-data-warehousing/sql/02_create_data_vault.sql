-- =============================================================================
-- Лабораторная работа №2. Хранилища данных.
-- Вариант 14. Система учета в видеопрокате.
-- Файл 02: создание модели Data Vault (video_rental_dv).
-- СУБД: PostgreSQL 17.
-- Скрипт идемпотентен: повторный запуск пересоздает схему с нуля.
-- =============================================================================

\set ON_ERROR_STOP on

DROP SCHEMA IF EXISTS video_rental_dv CASCADE;
CREATE SCHEMA video_rental_dv;
COMMENT ON SCHEMA video_rental_dv IS 'Хранилище данных видеопроката, построенное по методике Data Vault (Hub / Link / Satellite)';

SET search_path TO video_rental_dv, lab;

-- =============================================================================
-- 1. Служебные функции Data Vault
-- =============================================================================

-- 1.1 Хэш бизнес-ключа (hub key) и хэш-дифферент (hashdiff).
--     Значения приводятся к верхнему регистру, обрезаются по краям и
--     склеиваются через '||'. NULL заменяется символом chr(1), чтобы
--     NULL и пустая строка давали разные хэши.
CREATE OR REPLACE FUNCTION dv_hash(VARIADIC parts text[])
RETURNS char(32)
LANGUAGE sql IMMUTABLE
AS $$
    SELECT md5(coalesce(string_agg(upper(btrim(coalesce(p, chr(1)))), '||' ORDER BY ord), ''))
      FROM unnest(parts) WITH ORDINALITY AS t(p, ord)
$$;

COMMENT ON FUNCTION dv_hash(text[]) IS
'Детерминированный хэш (md5) бизнес-ключа или набора атрибутов. Используется как ключ Хаба/Связи и как hashdiff Спутника.';

CREATE OR REPLACE FUNCTION dv_hashdiff(VARIADIC parts text[])
RETURNS char(32)
LANGUAGE sql IMMUTABLE
AS $$
    SELECT dv_hash(VARIADIC parts)
$$;

COMMENT ON FUNCTION dv_hashdiff(text[]) IS
'Хэш-дифферент: значение, меняющееся при любом изменении описательных атрибутов Спутника.';

-- =============================================================================
-- 2. Hubs (Хабы) - устойчивые бизнес-ключи предметной области
--    Структура каждого Хаба: <entity>_hk, бизнес-ключ, load_dts, record_source.
-- =============================================================================

-- 2.1 HUB_CUSTOMER ---------------------------------------------------------
CREATE TABLE hub_customer (
    customer_hk   char(32)    NOT NULL,
    card_number   varchar(12) NOT NULL,
    load_dts      timestamp   NOT NULL DEFAULT lab.now(),
    record_source varchar(50) NOT NULL,
    CONSTRAINT pk_hub_customer PRIMARY KEY (customer_hk),
    CONSTRAINT uq_hub_customer_bk UNIQUE (card_number),
    CONSTRAINT ck_hub_customer_bk CHECK (card_number ~ '^CR-[0-9]{5}$')
);
COMMENT ON TABLE hub_customer IS 'Хаб клиентов. Бизнес-ключ - номер клубной карты';
COMMENT ON COLUMN hub_customer.customer_hk IS 'Хэш-ключ Хаба (md5 от бизнес-ключа)';
COMMENT ON COLUMN hub_customer.card_number IS 'Бизнес-ключ: номер клубной карты';
COMMENT ON COLUMN hub_customer.load_dts IS 'Дата и время загрузки записи в хранилище';
COMMENT ON COLUMN hub_customer.record_source IS 'Источник записи';

-- 2.2 HUB_EMPLOYEE ---------------------------------------------------------
CREATE TABLE hub_employee (
    employee_hk      char(32)    NOT NULL,
    personnel_number varchar(10) NOT NULL,
    load_dts         timestamp   NOT NULL DEFAULT lab.now(),
    record_source    varchar(50) NOT NULL,
    CONSTRAINT pk_hub_employee PRIMARY KEY (employee_hk),
    CONSTRAINT uq_hub_employee_bk UNIQUE (personnel_number),
    CONSTRAINT ck_hub_employee_bk CHECK (personnel_number ~ '^EMP-[0-9]{4}$')
);
COMMENT ON TABLE hub_employee IS 'Хаб сотрудников. Бизнес-ключ - табельный номер';

-- 2.3 HUB_FILM -------------------------------------------------------------
CREATE TABLE hub_film (
    film_hk        char(32)    NOT NULL,
    catalog_number varchar(16) NOT NULL,
    load_dts       timestamp   NOT NULL DEFAULT lab.now(),
    record_source  varchar(50) NOT NULL,
    CONSTRAINT pk_hub_film PRIMARY KEY (film_hk),
    CONSTRAINT uq_hub_film_bk UNIQUE (catalog_number),
    CONSTRAINT ck_hub_film_bk CHECK (catalog_number ~ '^FM-[0-9]{4}$')
);
COMMENT ON TABLE hub_film IS 'Хаб фильмов. Бизнес-ключ - каталожный номер фильма';

-- 2.4 HUB_VIDEO_COPY -------------------------------------------------------
CREATE TABLE hub_video_copy (
    copy_hk        char(32)    NOT NULL,
    inventory_code varchar(16) NOT NULL,
    load_dts       timestamp   NOT NULL DEFAULT lab.now(),
    record_source  varchar(50) NOT NULL,
    CONSTRAINT pk_hub_video_copy PRIMARY KEY (copy_hk),
    CONSTRAINT uq_hub_video_copy_bk UNIQUE (inventory_code),
    CONSTRAINT ck_hub_video_copy_bk CHECK (inventory_code ~ '^VC-[0-9]{5}$')
);
COMMENT ON TABLE hub_video_copy IS 'Хаб физических экземпляров. Бизнес-ключ - инвентарный номер';

-- 2.5 HUB_RENTAL -----------------------------------------------------------
CREATE TABLE hub_rental (
    rental_hk     char(32)    NOT NULL,
    rental_number varchar(12) NOT NULL,
    load_dts      timestamp   NOT NULL DEFAULT lab.now(),
    record_source varchar(50) NOT NULL,
    CONSTRAINT pk_hub_rental PRIMARY KEY (rental_hk),
    CONSTRAINT uq_hub_rental_bk UNIQUE (rental_number),
    CONSTRAINT ck_hub_rental_bk CHECK (rental_number ~ '^RN-[0-9]{6}$')
);
COMMENT ON TABLE hub_rental IS 'Хаб операций проката. Бизнес-ключ - номер операции проката';

-- 2.6 HUB_PAYMENT ----------------------------------------------------------
CREATE TABLE hub_payment (
    payment_hk     char(32)    NOT NULL,
    payment_number varchar(12) NOT NULL,
    load_dts       timestamp   NOT NULL DEFAULT lab.now(),
    record_source  varchar(50) NOT NULL,
    CONSTRAINT pk_hub_payment PRIMARY KEY (payment_hk),
    CONSTRAINT uq_hub_payment_bk UNIQUE (payment_number),
    CONSTRAINT ck_hub_payment_bk CHECK (payment_number ~ '^PM-[0-9]{6}$')
);
COMMENT ON TABLE hub_payment IS 'Хаб платежей. Бизнес-ключ - номер платежного документа';

-- 2.7 HUB_GENRE ------------------------------------------------------------
CREATE TABLE hub_genre (
    genre_hk      char(32)    NOT NULL,
    genre_code    varchar(12) NOT NULL,
    load_dts      timestamp   NOT NULL DEFAULT lab.now(),
    record_source varchar(50) NOT NULL,
    CONSTRAINT pk_hub_genre PRIMARY KEY (genre_hk),
    CONSTRAINT uq_hub_genre_bk UNIQUE (genre_code)
);
COMMENT ON TABLE hub_genre IS 'Хаб жанров. Бизнес-ключ - код жанра';

-- 2.8 HUB_TARIFF -----------------------------------------------------------
CREATE TABLE hub_tariff (
    tariff_hk     char(32)    NOT NULL,
    tariff_code   varchar(12) NOT NULL,
    load_dts      timestamp   NOT NULL DEFAULT lab.now(),
    record_source varchar(50) NOT NULL,
    CONSTRAINT pk_hub_tariff PRIMARY KEY (tariff_hk),
    CONSTRAINT uq_hub_tariff_bk UNIQUE (tariff_code)
);
COMMENT ON TABLE hub_tariff IS 'Хаб тарифов проката. Бизнес-ключ - код тарифа';

-- =============================================================================
-- 3. Links (Связи) - бизнес-взаимодействия между Хабами
--    Структура: <link>_hk, ссылки на Хабы, load_dts, record_source.
-- =============================================================================

-- 3.1 LINK_FILM_COPY: фильм имеет физические экземпляры -------------------
CREATE TABLE link_film_copy (
    film_copy_hk  char(32)    NOT NULL,
    film_hk       char(32)    NOT NULL,
    copy_hk       char(32)    NOT NULL,
    load_dts      timestamp   NOT NULL DEFAULT lab.now(),
    record_source varchar(50) NOT NULL,
    CONSTRAINT pk_link_film_copy PRIMARY KEY (film_copy_hk),
    CONSTRAINT uq_link_film_copy_bk UNIQUE (film_hk, copy_hk),
    CONSTRAINT fk_link_film_copy_film FOREIGN KEY (film_hk) REFERENCES hub_film (film_hk),
    CONSTRAINT fk_link_film_copy_copy FOREIGN KEY (copy_hk) REFERENCES hub_video_copy (copy_hk)
);
COMMENT ON TABLE link_film_copy IS 'Связь "фильм - физический экземпляр"';

-- 3.2 LINK_FILM_GENRE: фильм относится к жанрам (M:N) ----------------------
CREATE TABLE link_film_genre (
    film_genre_hk char(32)    NOT NULL,
    film_hk       char(32)    NOT NULL,
    genre_hk      char(32)    NOT NULL,
    load_dts      timestamp   NOT NULL DEFAULT lab.now(),
    record_source varchar(50) NOT NULL,
    CONSTRAINT pk_link_film_genre PRIMARY KEY (film_genre_hk),
    CONSTRAINT uq_link_film_genre_bk UNIQUE (film_hk, genre_hk),
    CONSTRAINT fk_link_film_genre_film FOREIGN KEY (film_hk) REFERENCES hub_film (film_hk),
    CONSTRAINT fk_link_film_genre_genre FOREIGN KEY (genre_hk) REFERENCES hub_genre (genre_hk)
);
COMMENT ON TABLE link_film_genre IS 'Связь "фильм - жанр" (многие ко многим)';

-- 3.3 LINK_FILM_TARIFF: фильм прокатывается по тарифу ---------------------
CREATE TABLE link_film_tariff (
    film_tariff_hk char(32)    NOT NULL,
    film_hk        char(32)    NOT NULL,
    tariff_hk      char(32)    NOT NULL,
    load_dts       timestamp   NOT NULL DEFAULT lab.now(),
    record_source  varchar(50) NOT NULL,
    CONSTRAINT pk_link_film_tariff PRIMARY KEY (film_tariff_hk),
    CONSTRAINT uq_link_film_tariff_bk UNIQUE (film_hk, tariff_hk),
    CONSTRAINT fk_link_film_tariff_film FOREIGN KEY (film_hk) REFERENCES hub_film (film_hk),
    CONSTRAINT fk_link_film_tariff_tariff FOREIGN KEY (tariff_hk) REFERENCES hub_tariff (tariff_hk)
);
COMMENT ON TABLE link_film_tariff IS 'Связь "фильм - тариф проката"';

-- 3.4 LINK_RENTAL_CUSTOMER: кто оформил прокат ----------------------------
CREATE TABLE link_rental_customer (
    rental_customer_hk char(32)    NOT NULL,
    rental_hk          char(32)    NOT NULL,
    customer_hk        char(32)    NOT NULL,
    load_dts           timestamp   NOT NULL DEFAULT lab.now(),
    record_source      varchar(50) NOT NULL,
    CONSTRAINT pk_link_rental_customer PRIMARY KEY (rental_customer_hk),
    CONSTRAINT uq_link_rental_customer_bk UNIQUE (rental_hk, customer_hk),
    CONSTRAINT fk_link_rental_customer_rental FOREIGN KEY (rental_hk) REFERENCES hub_rental (rental_hk),
    CONSTRAINT fk_link_rental_customer_customer FOREIGN KEY (customer_hk) REFERENCES hub_customer (customer_hk)
);
COMMENT ON TABLE link_rental_customer IS 'Связь "прокат - клиент"';

-- 3.5 LINK_RENTAL_EMPLOYEE: кто оформил выдачу ----------------------------
CREATE TABLE link_rental_employee (
    rental_employee_hk char(32)    NOT NULL,
    rental_hk          char(32)    NOT NULL,
    employee_hk        char(32)    NOT NULL,
    load_dts           timestamp   NOT NULL DEFAULT lab.now(),
    record_source      varchar(50) NOT NULL,
    CONSTRAINT pk_link_rental_employee PRIMARY KEY (rental_employee_hk),
    CONSTRAINT uq_link_rental_employee_bk UNIQUE (rental_hk, employee_hk),
    CONSTRAINT fk_link_rental_employee_rental FOREIGN KEY (rental_hk) REFERENCES hub_rental (rental_hk),
    CONSTRAINT fk_link_rental_employee_employee FOREIGN KEY (employee_hk) REFERENCES hub_employee (employee_hk)
);
COMMENT ON TABLE link_rental_employee IS 'Связь "прокат - сотрудник, оформивший выдачу"';

-- 3.6 LINK_RENTAL_COPY: позиция проката (какой экземпляр выдан) -----------
CREATE TABLE link_rental_copy (
    rental_copy_hk char(32)    NOT NULL,
    rental_hk      char(32)    NOT NULL,
    copy_hk        char(32)    NOT NULL,
    load_dts       timestamp   NOT NULL DEFAULT lab.now(),
    record_source  varchar(50) NOT NULL,
    CONSTRAINT pk_link_rental_copy PRIMARY KEY (rental_copy_hk),
    CONSTRAINT uq_link_rental_copy_bk UNIQUE (rental_hk, copy_hk),
    CONSTRAINT fk_link_rental_copy_rental FOREIGN KEY (rental_hk) REFERENCES hub_rental (rental_hk),
    CONSTRAINT fk_link_rental_copy_copy FOREIGN KEY (copy_hk) REFERENCES hub_video_copy (copy_hk)
);
COMMENT ON TABLE link_rental_copy IS 'Связь "прокат - физический экземпляр" (позиция проката); допускает несколько экземпляров в одной операции';

-- 3.7 LINK_RENTAL_PAYMENT: платежи по операции проката --------------------
CREATE TABLE link_rental_payment (
    rental_payment_hk char(32)    NOT NULL,
    rental_hk         char(32)    NOT NULL,
    payment_hk        char(32)    NOT NULL,
    load_dts          timestamp   NOT NULL DEFAULT lab.now(),
    record_source     varchar(50) NOT NULL,
    CONSTRAINT pk_link_rental_payment PRIMARY KEY (rental_payment_hk),
    CONSTRAINT uq_link_rental_payment_bk UNIQUE (rental_hk, payment_hk),
    CONSTRAINT fk_link_rental_payment_rental FOREIGN KEY (rental_hk) REFERENCES hub_rental (rental_hk),
    CONSTRAINT fk_link_rental_payment_payment FOREIGN KEY (payment_hk) REFERENCES hub_payment (payment_hk)
);
COMMENT ON TABLE link_rental_payment IS 'Связь "прокат - платеж"';

-- Индексы по внешним ключам Связей (обратные выборки по Хабу)
CREATE INDEX ix_link_film_copy_copy             ON link_film_copy (copy_hk);
CREATE INDEX ix_link_film_genre_genre           ON link_film_genre (genre_hk);
CREATE INDEX ix_link_film_tariff_tariff         ON link_film_tariff (tariff_hk);
CREATE INDEX ix_link_rental_customer_customer   ON link_rental_customer (customer_hk);
CREATE INDEX ix_link_rental_employee_employee   ON link_rental_employee (employee_hk);
CREATE INDEX ix_link_rental_copy_copy           ON link_rental_copy (copy_hk);
CREATE INDEX ix_link_rental_payment_payment     ON link_rental_payment (payment_hk);

-- =============================================================================
-- 4. Satellites (Спутники) - историзируемые описательные атрибуты
--    Структура: <parent>_hk, load_dts, hashdiff, атрибуты, record_source.
--    Первичный ключ - (parent_hk, load_dts): изменение атрибутов создает
--    НОВУЮ строку, исторические версии не перезаписываются.
--    Спутники разделены по темпам изменения данных.
-- =============================================================================

-- 4.1 SAT_CUSTOMER_DETAILS (медленно меняющиеся данные) -------------------
CREATE TABLE sat_customer_details (
    customer_hk    char(32)    NOT NULL,
    load_dts       timestamp   NOT NULL DEFAULT lab.now(),
    hashdiff       char(32)    NOT NULL,
    last_name      varchar(60) NOT NULL,
    first_name     varchar(60) NOT NULL,
    middle_name    varchar(60),
    birth_date     date,
    registration_date date     NOT NULL,
    record_source  varchar(50) NOT NULL,
    CONSTRAINT pk_sat_customer_details PRIMARY KEY (customer_hk, load_dts),
    CONSTRAINT fk_sat_customer_details FOREIGN KEY (customer_hk) REFERENCES hub_customer (customer_hk)
);
COMMENT ON TABLE sat_customer_details IS 'Спутник клиента: ФИО и дата рождения (меняются редко)';
COMMENT ON COLUMN sat_customer_details.hashdiff IS 'Хэш описательных атрибутов; изменение хэша означает появление новой версии';

-- 4.2 SAT_CUSTOMER_CONTACT (часто меняющиеся данные) ----------------------
CREATE TABLE sat_customer_contact (
    customer_hk char(32)    NOT NULL,
    load_dts    timestamp   NOT NULL DEFAULT lab.now(),
    hashdiff    char(32)    NOT NULL,
    phone       varchar(20) NOT NULL,
    email       varchar(120),
    address     varchar(200),
    status      varchar(10) NOT NULL,
    record_source varchar(50) NOT NULL,
    CONSTRAINT pk_sat_customer_contact PRIMARY KEY (customer_hk, load_dts),
    CONSTRAINT fk_sat_customer_contact FOREIGN KEY (customer_hk) REFERENCES hub_customer (customer_hk)
);
COMMENT ON TABLE sat_customer_contact IS 'Спутник клиента: контакты и статус (меняются часто, вынесены отдельно от ФИО)';

-- 4.3 SAT_EMPLOYEE_DETAILS -------------------------------------------------
CREATE TABLE sat_employee_details (
    employee_hk    char(32)    NOT NULL,
    load_dts       timestamp   NOT NULL DEFAULT lab.now(),
    hashdiff       char(32)    NOT NULL,
    last_name      varchar(60) NOT NULL,
    first_name     varchar(60) NOT NULL,
    middle_name    varchar(60),
    position       varchar(40) NOT NULL,
    phone          varchar(20) NOT NULL,
    hire_date      date        NOT NULL,
    dismissal_date date,
    status         varchar(10) NOT NULL,
    record_source  varchar(50) NOT NULL,
    CONSTRAINT pk_sat_employee_details PRIMARY KEY (employee_hk, load_dts),
    CONSTRAINT fk_sat_employee_details FOREIGN KEY (employee_hk) REFERENCES hub_employee (employee_hk)
);
COMMENT ON TABLE sat_employee_details IS 'Спутник сотрудника: ФИО, должность, телефон, даты приема и увольнения, статус';

-- 4.4 SAT_FILM_DETAILS -----------------------------------------------------
CREATE TABLE sat_film_details (
    film_hk        char(32)     NOT NULL,
    load_dts       timestamp    NOT NULL DEFAULT lab.now(),
    hashdiff       char(32)     NOT NULL,
    title          varchar(200) NOT NULL,
    original_title varchar(200),
    release_year   smallint     NOT NULL,
    duration_min   smallint     NOT NULL,
    age_rating     varchar(8)   NOT NULL,
    media_type     varchar(10)  NOT NULL,
    synopsis       varchar(1000),
    added_on       date         NOT NULL,
    record_source  varchar(50)  NOT NULL,
    CONSTRAINT pk_sat_film_details PRIMARY KEY (film_hk, load_dts),
    CONSTRAINT fk_sat_film_details FOREIGN KEY (film_hk) REFERENCES hub_film (film_hk)
);
COMMENT ON TABLE sat_film_details IS 'Спутник фильма: описательная карточка фильма';

-- 4.5 SAT_VIDEO_COPY_ACQUISITION (данные поступления) --------------------
CREATE TABLE sat_video_copy_acquisition (
    copy_hk          char(32)      NOT NULL,
    load_dts         timestamp     NOT NULL DEFAULT lab.now(),
    hashdiff         char(32)      NOT NULL,
    acquisition_date date          NOT NULL,
    purchase_price   numeric(10,2) NOT NULL,
    record_source    varchar(50)   NOT NULL,
    CONSTRAINT pk_sat_video_copy_acquisition PRIMARY KEY (copy_hk, load_dts),
    CONSTRAINT fk_sat_video_copy_acquisition FOREIGN KEY (copy_hk) REFERENCES hub_video_copy (copy_hk)
);
COMMENT ON TABLE sat_video_copy_acquisition IS 'Спутник экземпляра: данные поступления (дата и цена закупки)';

-- 4.6 SAT_VIDEO_COPY_DETAILS (состояние экземпляра) ----------------------
CREATE TABLE sat_video_copy_details (
    copy_hk          char(32)   NOT NULL,
    load_dts         timestamp  NOT NULL DEFAULT lab.now(),
    hashdiff         char(32)   NOT NULL,
    condition        varchar(12) NOT NULL,
    storage_location varchar(20),
    record_source    varchar(50) NOT NULL,
    CONSTRAINT pk_sat_video_copy_details PRIMARY KEY (copy_hk, load_dts),
    CONSTRAINT fk_sat_video_copy_details FOREIGN KEY (copy_hk) REFERENCES hub_video_copy (copy_hk),
    CONSTRAINT ck_sat_video_copy_condition CHECK (condition IN ('new','good','worn','damaged','written_off'))
);
COMMENT ON TABLE sat_video_copy_details IS 'Спутник экземпляра: физическое состояние и место хранения (историзируется)';

-- 4.7 SAT_GENRE_DETAILS ----------------------------------------------------
CREATE TABLE sat_genre_details (
    genre_hk      char(32)    NOT NULL,
    load_dts      timestamp   NOT NULL DEFAULT lab.now(),
    hashdiff      char(32)    NOT NULL,
    name          varchar(60) NOT NULL,
    description   varchar(300),
    record_source varchar(50) NOT NULL,
    CONSTRAINT pk_sat_genre_details PRIMARY KEY (genre_hk, load_dts),
    CONSTRAINT fk_sat_genre_details FOREIGN KEY (genre_hk) REFERENCES hub_genre (genre_hk)
);
COMMENT ON TABLE sat_genre_details IS 'Спутник жанра: название и описание';

-- 4.8 SAT_TARIFF_DETAILS ---------------------------------------------------
CREATE TABLE sat_tariff_details (
    tariff_hk        char(32)      NOT NULL,
    load_dts         timestamp     NOT NULL DEFAULT lab.now(),
    hashdiff         char(32)      NOT NULL,
    name             varchar(80)   NOT NULL,
    daily_rate       numeric(8,2)  NOT NULL,
    max_rental_days  smallint      NOT NULL,
    late_fee_per_day numeric(8,2)  NOT NULL,
    valid_from       date          NOT NULL,
    valid_to         date,
    record_source    varchar(50)   NOT NULL,
    CONSTRAINT pk_sat_tariff_details PRIMARY KEY (tariff_hk, load_dts),
    CONSTRAINT fk_sat_tariff_details FOREIGN KEY (tariff_hk) REFERENCES hub_tariff (tariff_hk),
    CONSTRAINT ck_sat_tariff_daily_rate CHECK (daily_rate > 0),
    CONSTRAINT ck_sat_tariff_late_fee CHECK (late_fee_per_day >= 0)
);
COMMENT ON TABLE sat_tariff_details IS 'Спутник тарифа: условия проката (стоимость суток, срок, пеня, период действия)';

-- 4.9 SAT_RENTAL_DETAILS ---------------------------------------------------
CREATE TABLE sat_rental_details (
    rental_hk           char(32)      NOT NULL,
    load_dts            timestamp     NOT NULL DEFAULT lab.now(),
    hashdiff            char(32)      NOT NULL,
    issue_date          date          NOT NULL,
    planned_return_date date          NOT NULL,
    actual_return_date  date,
    deposit_amount      numeric(10,2) NOT NULL,
    status              varchar(12)   NOT NULL,
    note                varchar(300),
    record_source       varchar(50)   NOT NULL,
    CONSTRAINT pk_sat_rental_details PRIMARY KEY (rental_hk, load_dts),
    CONSTRAINT fk_sat_rental_details FOREIGN KEY (rental_hk) REFERENCES hub_rental (rental_hk),
    CONSTRAINT ck_sat_rental_status CHECK (status IN ('issued','closed','cancelled'))
);
COMMENT ON TABLE sat_rental_details IS 'Спутник проката: сроки, залог, статус операции (историзируется при каждом изменении)';

-- 4.10 SAT_RENTAL_ITEM_DETAILS (спутник Связи "прокат - экземпляр") -------
CREATE TABLE sat_rental_item_details (
    rental_copy_hk      char(32)     NOT NULL,
    load_dts            timestamp    NOT NULL DEFAULT lab.now(),
    hashdiff            char(32)     NOT NULL,
    daily_rate          numeric(8,2) NOT NULL,
    status              varchar(10)  NOT NULL,
    actual_return_date  date,
    condition_on_return varchar(12),
    record_source       varchar(50)  NOT NULL,
    CONSTRAINT pk_sat_rental_item_details PRIMARY KEY (rental_copy_hk, load_dts),
    CONSTRAINT fk_sat_rental_item_details FOREIGN KEY (rental_copy_hk) REFERENCES link_rental_copy (rental_copy_hk),
    CONSTRAINT ck_sat_rental_item_status CHECK (status IN ('issued','returned')),
    CONSTRAINT ck_sat_rental_item_return CHECK ((status = 'returned') = (actual_return_date IS NOT NULL))
);
COMMENT ON TABLE sat_rental_item_details IS 'Спутник позиции проката: цена суток, статус, дата возврата и состояние экземпляра при возврате';

-- 4.11 SAT_PAYMENT_DETAILS ------------------------------------------------
CREATE TABLE sat_payment_details (
    payment_hk     char(32)      NOT NULL,
    load_dts       timestamp     NOT NULL DEFAULT lab.now(),
    hashdiff       char(32)      NOT NULL,
    payment_date   timestamp     NOT NULL,
    amount         numeric(10,2) NOT NULL,
    method         varchar(10)   NOT NULL,
    payment_type   varchar(10)   NOT NULL,
    record_source  varchar(50)   NOT NULL,
    CONSTRAINT pk_sat_payment_details PRIMARY KEY (payment_hk, load_dts),
    CONSTRAINT fk_sat_payment_details FOREIGN KEY (payment_hk) REFERENCES hub_payment (payment_hk),
    CONSTRAINT ck_sat_payment_amount CHECK (amount > 0)
);
COMMENT ON TABLE sat_payment_details IS 'Спутник платежа: сумма, способ и тип платежа';

-- 4.12 SAT_FILM_GENRE_DETAILS (спутник Связи "фильм - жанр") --------------
CREATE TABLE sat_film_genre_details (
    film_genre_hk char(32)    NOT NULL,
    load_dts      timestamp   NOT NULL DEFAULT lab.now(),
    hashdiff      char(32)    NOT NULL,
    is_primary    boolean     NOT NULL,
    record_source varchar(50) NOT NULL,
    CONSTRAINT pk_sat_film_genre_details PRIMARY KEY (film_genre_hk, load_dts),
    CONSTRAINT fk_sat_film_genre_details FOREIGN KEY (film_genre_hk) REFERENCES link_film_genre (film_genre_hk)
);
COMMENT ON TABLE sat_film_genre_details IS 'Спутник связи "фильм - жанр": признак основного жанра';

-- Индексы по load_dts для выборки последних версий
CREATE INDEX ix_sat_customer_details_ld  ON sat_customer_details (load_dts);
CREATE INDEX ix_sat_customer_contact_ld  ON sat_customer_contact (load_dts);
CREATE INDEX ix_sat_employee_details_ld  ON sat_employee_details (load_dts);
CREATE INDEX ix_sat_film_details_ld      ON sat_film_details (load_dts);
CREATE INDEX ix_sat_copy_details_ld      ON sat_video_copy_details (load_dts);
CREATE INDEX ix_sat_copy_acquisition_ld  ON sat_video_copy_acquisition (load_dts);
CREATE INDEX ix_sat_genre_details_ld     ON sat_genre_details (load_dts);
CREATE INDEX ix_sat_tariff_details_ld    ON sat_tariff_details (load_dts);
CREATE INDEX ix_sat_rental_details_ld    ON sat_rental_details (load_dts);
CREATE INDEX ix_sat_rental_item_ld       ON sat_rental_item_details (load_dts);
CREATE INDEX ix_sat_payment_details_ld   ON sat_payment_details (load_dts);
CREATE INDEX ix_sat_film_genre_ld        ON sat_film_genre_details (load_dts);

-- =============================================================================
-- 5. Представления: последние версии Спутников
--    Стандартный прием Data Vault - DISTINCT ON (parent_key) ... ORDER BY load_dts DESC
-- =============================================================================

CREATE VIEW v_customer_details_current AS
SELECT DISTINCT ON (customer_hk) customer_hk, load_dts, hashdiff,
       last_name, first_name, middle_name, birth_date, registration_date
  FROM sat_customer_details
 ORDER BY customer_hk, load_dts DESC;

CREATE VIEW v_customer_contact_current AS
SELECT DISTINCT ON (customer_hk) customer_hk, load_dts, hashdiff,
       phone, email, address, status
  FROM sat_customer_contact
 ORDER BY customer_hk, load_dts DESC;

CREATE VIEW v_customer_current AS
SELECT hc.customer_hk, hc.card_number,
       d.last_name, d.first_name, d.middle_name, d.birth_date,
       c.phone, c.email, c.address, c.status,
       d.load_dts AS details_load_dts, c.load_dts AS contact_load_dts
  FROM hub_customer hc
  JOIN v_customer_details_current d ON d.customer_hk = hc.customer_hk
  JOIN v_customer_contact_current c ON c.customer_hk = hc.customer_hk;

COMMENT ON VIEW v_customer_current IS 'Актуальное состояние клиента, собранное из Хаба и последних версий Спутников';

CREATE VIEW v_employee_current AS
SELECT he.employee_hk, he.personnel_number, sd.load_dts, sd.hashdiff,
       sd.last_name, sd.first_name, sd.middle_name, sd.position, sd.phone,
       sd.hire_date, sd.dismissal_date, sd.status
  FROM hub_employee he
  JOIN (SELECT DISTINCT ON (employee_hk) * FROM sat_employee_details
         ORDER BY employee_hk, load_dts DESC) sd ON sd.employee_hk = he.employee_hk;

CREATE VIEW v_film_current AS
SELECT hf.film_hk, hf.catalog_number, sd.title, sd.release_year, sd.media_type, sd.age_rating,
       sd.duration_min, sd.synopsis, sd.added_on
  FROM hub_film hf
  JOIN (SELECT DISTINCT ON (film_hk) * FROM sat_film_details
         ORDER BY film_hk, load_dts DESC) sd ON sd.film_hk = hf.film_hk;

CREATE VIEW v_video_copy_current AS
SELECT hvc.copy_hk, hvc.inventory_code, sd.condition, sd.storage_location,
       sa.acquisition_date, sa.purchase_price, sd.load_dts AS condition_load_dts
  FROM hub_video_copy hvc
  JOIN (SELECT DISTINCT ON (copy_hk) * FROM sat_video_copy_details
         ORDER BY copy_hk, load_dts DESC) sd ON sd.copy_hk = hvc.copy_hk
  JOIN (SELECT DISTINCT ON (copy_hk) * FROM sat_video_copy_acquisition
         ORDER BY copy_hk, load_dts DESC) sa ON sa.copy_hk = hvc.copy_hk;

CREATE VIEW v_rental_current AS
SELECT hr.rental_hk, hr.rental_number, sd.issue_date, sd.planned_return_date,
       sd.actual_return_date, sd.deposit_amount, sd.status, sd.note
  FROM hub_rental hr
  JOIN (SELECT DISTINCT ON (rental_hk) * FROM sat_rental_details
         ORDER BY rental_hk, load_dts DESC) sd ON sd.rental_hk = hr.rental_hk;

CREATE VIEW v_payment_current AS
SELECT hp.payment_hk, hp.payment_number, sd.payment_date, sd.amount, sd.method, sd.payment_type
  FROM hub_payment hp
  JOIN (SELECT DISTINCT ON (payment_hk) * FROM sat_payment_details
         ORDER BY payment_hk, load_dts DESC) sd ON sd.payment_hk = hp.payment_hk;

CREATE VIEW v_genre_current AS
SELECT hg.genre_hk, hg.genre_code, sd.name, sd.description
  FROM hub_genre hg
  JOIN (SELECT DISTINCT ON (genre_hk) * FROM sat_genre_details
         ORDER BY genre_hk, load_dts DESC) sd ON sd.genre_hk = hg.genre_hk;

CREATE VIEW v_tariff_current AS
SELECT ht.tariff_hk, ht.tariff_code, sd.name, sd.daily_rate, sd.max_rental_days,
       sd.late_fee_per_day, sd.valid_from, sd.valid_to
  FROM hub_tariff ht
  JOIN (SELECT DISTINCT ON (tariff_hk) * FROM sat_tariff_details
         ORDER BY tariff_hk, load_dts DESC) sd ON sd.tariff_hk = ht.tariff_hk;

CREATE VIEW v_rental_item_current AS
SELECT lrc.rental_copy_hk, lrc.rental_hk, lrc.copy_hk, sd.daily_rate, sd.status,
       sd.actual_return_date, sd.condition_on_return
  FROM link_rental_copy lrc
  JOIN (SELECT DISTINCT ON (rental_copy_hk) * FROM sat_rental_item_details
         ORDER BY rental_copy_hk, load_dts DESC) sd ON sd.rental_copy_hk = lrc.rental_copy_hk;

-- =============================================================================
-- 6. Представление, восстанавливающее картину уровня 3NF из Data Vault
-- =============================================================================
CREATE VIEW v_rental_full AS
SELECT hr.rental_number,
       rc.card_number,
       rc.last_name || ' ' || rc.first_name AS customer_name,
       he.personnel_number,
       he.last_name || ' ' || he.first_name AS employee_name,
       rs.issue_date,
       rs.planned_return_date,
       rs.actual_return_date,
       rs.status,
       vc.inventory_code,
       fc.title,
       ris.status        AS item_status,
       ris.daily_rate    AS item_daily_rate,
       ris.actual_return_date AS item_return_date
  FROM hub_rental hr
  JOIN v_rental_current rs               ON rs.rental_hk = hr.rental_hk
  JOIN link_rental_customer lrc          ON lrc.rental_hk = hr.rental_hk
  JOIN v_customer_current rc             ON rc.customer_hk = lrc.customer_hk
  JOIN link_rental_employee lre          ON lre.rental_hk = hr.rental_hk
  JOIN v_employee_current he             ON he.employee_hk = lre.employee_hk
  LEFT JOIN v_rental_item_current ris    ON ris.rental_hk = hr.rental_hk
  LEFT JOIN v_video_copy_current vc      ON vc.copy_hk = ris.copy_hk
  LEFT JOIN link_film_copy lfc           ON lfc.copy_hk = ris.copy_hk
  LEFT JOIN v_film_current fc            ON fc.film_hk = lfc.film_hk;

COMMENT ON VIEW v_rental_full IS 'Денормализованная выборка из Data Vault: Hub + Link + Satellite, эквивалент представления 3NF';

-- =============================================================================
-- 7. Механизм загрузки Data Vault (insert-only ETL)
--    Правила:
--      * Хабы и Связи - только вставка новых ключей (ON CONFLICT DO NOTHING);
--      * Спутники - вставка новой версии только тогда, когда hashdiff
--        описательных атрибутов отличается от hashdiff последней версии;
--      * исторические строки Спутников никогда не обновляются и не удаляются.
-- =============================================================================
CREATE OR REPLACE FUNCTION dv_load_all(
    p_load_dts      timestamp,
    p_record_source varchar DEFAULT 'video_rental_3nf'
) RETURNS TABLE (vault_object text, rows_inserted bigint)
LANGUAGE plpgsql AS $fn$
DECLARE
    n bigint;
BEGIN
    ---------------------------------------------------------------------------
    -- 7.1 Хабы
    ---------------------------------------------------------------------------
    INSERT INTO hub_customer (customer_hk, card_number, load_dts, record_source)
    SELECT dv_hash(c.card_number), c.card_number, p_load_dts, p_record_source
      FROM video_rental_3nf.customer c
    ON CONFLICT (customer_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'hub_customer'; rows_inserted := n; RETURN NEXT;

    INSERT INTO hub_employee (employee_hk, personnel_number, load_dts, record_source)
    SELECT dv_hash(e.personnel_number), e.personnel_number, p_load_dts, p_record_source
      FROM video_rental_3nf.employee e
    ON CONFLICT (employee_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'hub_employee'; rows_inserted := n; RETURN NEXT;

    INSERT INTO hub_film (film_hk, catalog_number, load_dts, record_source)
    SELECT dv_hash(f.catalog_number), f.catalog_number, p_load_dts, p_record_source
      FROM video_rental_3nf.film f
    ON CONFLICT (film_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'hub_film'; rows_inserted := n; RETURN NEXT;

    INSERT INTO hub_video_copy (copy_hk, inventory_code, load_dts, record_source)
    SELECT dv_hash(vc.inventory_code), vc.inventory_code, p_load_dts, p_record_source
      FROM video_rental_3nf.video_copy vc
    ON CONFLICT (copy_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'hub_video_copy'; rows_inserted := n; RETURN NEXT;

    INSERT INTO hub_rental (rental_hk, rental_number, load_dts, record_source)
    SELECT dv_hash(r.rental_number), r.rental_number, p_load_dts, p_record_source
      FROM video_rental_3nf.rental r
    ON CONFLICT (rental_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'hub_rental'; rows_inserted := n; RETURN NEXT;

    INSERT INTO hub_payment (payment_hk, payment_number, load_dts, record_source)
    SELECT dv_hash(p.payment_number), p.payment_number, p_load_dts, p_record_source
      FROM video_rental_3nf.payment p
    ON CONFLICT (payment_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'hub_payment'; rows_inserted := n; RETURN NEXT;

    INSERT INTO hub_genre (genre_hk, genre_code, load_dts, record_source)
    SELECT dv_hash(g.code), g.code, p_load_dts, p_record_source
      FROM video_rental_3nf.genre g
    ON CONFLICT (genre_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'hub_genre'; rows_inserted := n; RETURN NEXT;

    INSERT INTO hub_tariff (tariff_hk, tariff_code, load_dts, record_source)
    SELECT dv_hash(t.code), t.code, p_load_dts, p_record_source
      FROM video_rental_3nf.tariff t
    ON CONFLICT (tariff_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'hub_tariff'; rows_inserted := n; RETURN NEXT;

    ---------------------------------------------------------------------------
    -- 7.2 Связи
    ---------------------------------------------------------------------------
    INSERT INTO link_film_copy (film_copy_hk, film_hk, copy_hk, load_dts, record_source)
    SELECT dv_hash(f.catalog_number, vc.inventory_code),
           dv_hash(f.catalog_number), dv_hash(vc.inventory_code),
           p_load_dts, p_record_source
      FROM video_rental_3nf.video_copy vc
      JOIN video_rental_3nf.film f ON f.film_id = vc.film_id
    ON CONFLICT (film_copy_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'link_film_copy'; rows_inserted := n; RETURN NEXT;

    INSERT INTO link_film_genre (film_genre_hk, film_hk, genre_hk, load_dts, record_source)
    SELECT dv_hash(f.catalog_number, g.code),
           dv_hash(f.catalog_number), dv_hash(g.code),
           p_load_dts, p_record_source
      FROM video_rental_3nf.film_genre fg
      JOIN video_rental_3nf.film f  ON f.film_id = fg.film_id
      JOIN video_rental_3nf.genre g ON g.genre_id = fg.genre_id
    ON CONFLICT (film_genre_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'link_film_genre'; rows_inserted := n; RETURN NEXT;

    INSERT INTO link_film_tariff (film_tariff_hk, film_hk, tariff_hk, load_dts, record_source)
    SELECT dv_hash(f.catalog_number, t.code),
           dv_hash(f.catalog_number), dv_hash(t.code),
           p_load_dts, p_record_source
      FROM video_rental_3nf.film f
      JOIN video_rental_3nf.tariff t ON t.tariff_id = f.tariff_id
    ON CONFLICT (film_tariff_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'link_film_tariff'; rows_inserted := n; RETURN NEXT;

    INSERT INTO link_rental_customer (rental_customer_hk, rental_hk, customer_hk, load_dts, record_source)
    SELECT dv_hash(r.rental_number, c.card_number),
           dv_hash(r.rental_number), dv_hash(c.card_number),
           p_load_dts, p_record_source
      FROM video_rental_3nf.rental r
      JOIN video_rental_3nf.customer c ON c.customer_id = r.customer_id
    ON CONFLICT (rental_customer_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'link_rental_customer'; rows_inserted := n; RETURN NEXT;

    INSERT INTO link_rental_employee (rental_employee_hk, rental_hk, employee_hk, load_dts, record_source)
    SELECT dv_hash(r.rental_number, e.personnel_number),
           dv_hash(r.rental_number), dv_hash(e.personnel_number),
           p_load_dts, p_record_source
      FROM video_rental_3nf.rental r
      JOIN video_rental_3nf.employee e ON e.employee_id = r.employee_id
    ON CONFLICT (rental_employee_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'link_rental_employee'; rows_inserted := n; RETURN NEXT;

    INSERT INTO link_rental_copy (rental_copy_hk, rental_hk, copy_hk, load_dts, record_source)
    SELECT dv_hash(r.rental_number, vc.inventory_code),
           dv_hash(r.rental_number), dv_hash(vc.inventory_code),
           p_load_dts, p_record_source
      FROM video_rental_3nf.rental_item ri
      JOIN video_rental_3nf.rental r      ON r.rental_id = ri.rental_id
      JOIN video_rental_3nf.video_copy vc ON vc.copy_id = ri.copy_id
    ON CONFLICT (rental_copy_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'link_rental_copy'; rows_inserted := n; RETURN NEXT;

    INSERT INTO link_rental_payment (rental_payment_hk, rental_hk, payment_hk, load_dts, record_source)
    SELECT dv_hash(r.rental_number, p.payment_number),
           dv_hash(r.rental_number), dv_hash(p.payment_number),
           p_load_dts, p_record_source
      FROM video_rental_3nf.payment p
      JOIN video_rental_3nf.rental r ON r.rental_id = p.rental_id
    ON CONFLICT (rental_payment_hk) DO NOTHING;
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'link_rental_payment'; rows_inserted := n; RETURN NEXT;

    ---------------------------------------------------------------------------
    -- 7.3 Спутники (загрузка только изменившихся версий по hashdiff)
    ---------------------------------------------------------------------------
    INSERT INTO sat_customer_details
        (customer_hk, load_dts, hashdiff, last_name, first_name, middle_name,
         birth_date, registration_date, record_source)
    SELECT dv_hash(c.card_number), p_load_dts,
           dv_hashdiff(c.last_name, c.first_name, c.middle_name,
                       c.birth_date::text, c.registration_date::text),
           c.last_name, c.first_name, c.middle_name, c.birth_date, c.registration_date,
           p_record_source
      FROM video_rental_3nf.customer c
     WHERE NOT EXISTS (
           SELECT 1 FROM (
               SELECT DISTINCT ON (customer_hk) customer_hk, hashdiff
                 FROM sat_customer_details
                ORDER BY customer_hk, load_dts DESC) cur
            WHERE cur.customer_hk = dv_hash(c.card_number)
              AND cur.hashdiff = dv_hashdiff(c.last_name, c.first_name, c.middle_name,
                                             c.birth_date::text, c.registration_date::text));
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'sat_customer_details'; rows_inserted := n; RETURN NEXT;

    INSERT INTO sat_customer_contact
        (customer_hk, load_dts, hashdiff, phone, email, address, status, record_source)
    SELECT dv_hash(c.card_number), p_load_dts,
           dv_hashdiff(c.phone, c.email, c.address, c.status),
           c.phone, c.email, c.address, c.status, p_record_source
      FROM video_rental_3nf.customer c
     WHERE NOT EXISTS (
           SELECT 1 FROM (
               SELECT DISTINCT ON (customer_hk) customer_hk, hashdiff
                 FROM sat_customer_contact
                ORDER BY customer_hk, load_dts DESC) cur
            WHERE cur.customer_hk = dv_hash(c.card_number)
              AND cur.hashdiff = dv_hashdiff(c.phone, c.email, c.address, c.status));
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'sat_customer_contact'; rows_inserted := n; RETURN NEXT;

    INSERT INTO sat_employee_details
        (employee_hk, load_dts, hashdiff, last_name, first_name, middle_name, position,
         phone, hire_date, dismissal_date, status, record_source)
    SELECT dv_hash(e.personnel_number), p_load_dts,
           dv_hashdiff(e.last_name, e.first_name, e.middle_name, e.position, e.phone,
                       e.hire_date::text, e.dismissal_date::text, e.status),
           e.last_name, e.first_name, e.middle_name, e.position, e.phone,
           e.hire_date, e.dismissal_date, e.status, p_record_source
      FROM video_rental_3nf.employee e
     WHERE NOT EXISTS (
           SELECT 1 FROM (
               SELECT DISTINCT ON (employee_hk) employee_hk, hashdiff
                 FROM sat_employee_details
                ORDER BY employee_hk, load_dts DESC) cur
            WHERE cur.employee_hk = dv_hash(e.personnel_number)
              AND cur.hashdiff = dv_hashdiff(e.last_name, e.first_name, e.middle_name, e.position,
                                             e.phone, e.hire_date::text, e.dismissal_date::text, e.status));
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'sat_employee_details'; rows_inserted := n; RETURN NEXT;

    INSERT INTO sat_film_details
        (film_hk, load_dts, hashdiff, title, original_title, release_year, duration_min,
         age_rating, media_type, synopsis, added_on, record_source)
    SELECT dv_hash(f.catalog_number), p_load_dts,
           dv_hashdiff(f.title, f.original_title, f.release_year::text, f.duration_min::text,
                       f.age_rating, f.media_type, f.synopsis, f.added_on::text),
           f.title, f.original_title, f.release_year, f.duration_min, f.age_rating,
           f.media_type, f.synopsis, f.added_on, p_record_source
      FROM video_rental_3nf.film f
     WHERE NOT EXISTS (
           SELECT 1 FROM (
               SELECT DISTINCT ON (film_hk) film_hk, hashdiff
                 FROM sat_film_details
                ORDER BY film_hk, load_dts DESC) cur
            WHERE cur.film_hk = dv_hash(f.catalog_number)
              AND cur.hashdiff = dv_hashdiff(f.title, f.original_title, f.release_year::text,
                                             f.duration_min::text, f.age_rating, f.media_type,
                                             f.synopsis, f.added_on::text));
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'sat_film_details'; rows_inserted := n; RETURN NEXT;

    INSERT INTO sat_video_copy_acquisition
        (copy_hk, load_dts, hashdiff, acquisition_date, purchase_price, record_source)
    SELECT dv_hash(vc.inventory_code), p_load_dts,
           dv_hashdiff(vc.acquisition_date::text, vc.purchase_price::text),
           vc.acquisition_date, vc.purchase_price, p_record_source
      FROM video_rental_3nf.video_copy vc
     WHERE NOT EXISTS (
           SELECT 1 FROM (
               SELECT DISTINCT ON (copy_hk) copy_hk, hashdiff
                 FROM sat_video_copy_acquisition
                ORDER BY copy_hk, load_dts DESC) cur
            WHERE cur.copy_hk = dv_hash(vc.inventory_code)
              AND cur.hashdiff = dv_hashdiff(vc.acquisition_date::text, vc.purchase_price::text));
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'sat_video_copy_acquisition'; rows_inserted := n; RETURN NEXT;

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
              AND cur.hashdiff = dv_hashdiff(vc.condition, vc.storage_location));
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'sat_video_copy_details'; rows_inserted := n; RETURN NEXT;

    INSERT INTO sat_genre_details (genre_hk, load_dts, hashdiff, name, description, record_source)
    SELECT dv_hash(g.code), p_load_dts,
           dv_hashdiff(g.name, g.description), g.name, g.description, p_record_source
      FROM video_rental_3nf.genre g
     WHERE NOT EXISTS (
           SELECT 1 FROM (
               SELECT DISTINCT ON (genre_hk) genre_hk, hashdiff
                 FROM sat_genre_details
                ORDER BY genre_hk, load_dts DESC) cur
            WHERE cur.genre_hk = dv_hash(g.code)
              AND cur.hashdiff = dv_hashdiff(g.name, g.description));
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'sat_genre_details'; rows_inserted := n; RETURN NEXT;

    INSERT INTO sat_tariff_details
        (tariff_hk, load_dts, hashdiff, name, daily_rate, max_rental_days, late_fee_per_day,
         valid_from, valid_to, record_source)
    SELECT dv_hash(t.code), p_load_dts,
           dv_hashdiff(t.name, t.daily_rate::text, t.max_rental_days::text,
                       t.late_fee_per_day::text, t.valid_from::text, t.valid_to::text),
           t.name, t.daily_rate, t.max_rental_days, t.late_fee_per_day,
           t.valid_from, t.valid_to, p_record_source
      FROM video_rental_3nf.tariff t
     WHERE NOT EXISTS (
           SELECT 1 FROM (
               SELECT DISTINCT ON (tariff_hk) tariff_hk, hashdiff
                 FROM sat_tariff_details
                ORDER BY tariff_hk, load_dts DESC) cur
            WHERE cur.tariff_hk = dv_hash(t.code)
              AND cur.hashdiff = dv_hashdiff(t.name, t.daily_rate::text, t.max_rental_days::text,
                                             t.late_fee_per_day::text, t.valid_from::text, t.valid_to::text));
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'sat_tariff_details'; rows_inserted := n; RETURN NEXT;

    INSERT INTO sat_rental_details
        (rental_hk, load_dts, hashdiff, issue_date, planned_return_date, actual_return_date,
         deposit_amount, status, note, record_source)
    SELECT dv_hash(r.rental_number), p_load_dts,
           dv_hashdiff(r.issue_date::text, r.planned_return_date::text, r.actual_return_date::text,
                       r.deposit_amount::text, r.status, r.note),
           r.issue_date, r.planned_return_date, r.actual_return_date,
           r.deposit_amount, r.status, r.note, p_record_source
      FROM video_rental_3nf.rental r
     WHERE NOT EXISTS (
           SELECT 1 FROM (
               SELECT DISTINCT ON (rental_hk) rental_hk, hashdiff
                 FROM sat_rental_details
                ORDER BY rental_hk, load_dts DESC) cur
            WHERE cur.rental_hk = dv_hash(r.rental_number)
              AND cur.hashdiff = dv_hashdiff(r.issue_date::text, r.planned_return_date::text,
                                             r.actual_return_date::text, r.deposit_amount::text,
                                             r.status, r.note));
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'sat_rental_details'; rows_inserted := n; RETURN NEXT;

    INSERT INTO sat_rental_item_details
        (rental_copy_hk, load_dts, hashdiff, daily_rate, status, actual_return_date,
         condition_on_return, record_source)
    SELECT dv_hash(r.rental_number, vc.inventory_code), p_load_dts,
           dv_hashdiff(ri.daily_rate::text, ri.status, ri.actual_return_date::text, ri.condition_on_return),
           ri.daily_rate, ri.status, ri.actual_return_date, ri.condition_on_return, p_record_source
      FROM video_rental_3nf.rental_item ri
      JOIN video_rental_3nf.rental r      ON r.rental_id = ri.rental_id
      JOIN video_rental_3nf.video_copy vc ON vc.copy_id = ri.copy_id
     WHERE NOT EXISTS (
           SELECT 1 FROM (
               SELECT DISTINCT ON (rental_copy_hk) rental_copy_hk, hashdiff
                 FROM sat_rental_item_details
                ORDER BY rental_copy_hk, load_dts DESC) cur
            WHERE cur.rental_copy_hk = dv_hash(r.rental_number, vc.inventory_code)
              AND cur.hashdiff = dv_hashdiff(ri.daily_rate::text, ri.status,
                                             ri.actual_return_date::text, ri.condition_on_return));
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'sat_rental_item_details'; rows_inserted := n; RETURN NEXT;

    INSERT INTO sat_payment_details
        (payment_hk, load_dts, hashdiff, payment_date, amount, method, payment_type, record_source)
    SELECT dv_hash(p.payment_number), p_load_dts,
           dv_hashdiff(p.payment_date::text, p.amount::text, p.method, p.payment_type),
           p.payment_date, p.amount, p.method, p.payment_type, p_record_source
      FROM video_rental_3nf.payment p
     WHERE NOT EXISTS (
           SELECT 1 FROM (
               SELECT DISTINCT ON (payment_hk) payment_hk, hashdiff
                 FROM sat_payment_details
                ORDER BY payment_hk, load_dts DESC) cur
            WHERE cur.payment_hk = dv_hash(p.payment_number)
              AND cur.hashdiff = dv_hashdiff(p.payment_date::text, p.amount::text,
                                             p.method, p.payment_type));
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'sat_payment_details'; rows_inserted := n; RETURN NEXT;

    INSERT INTO sat_film_genre_details
        (film_genre_hk, load_dts, hashdiff, is_primary, record_source)
    SELECT dv_hash(f.catalog_number, g.code), p_load_dts,
           dv_hashdiff(fg.is_primary::text), fg.is_primary, p_record_source
      FROM video_rental_3nf.film_genre fg
      JOIN video_rental_3nf.film f  ON f.film_id = fg.film_id
      JOIN video_rental_3nf.genre g ON g.genre_id = fg.genre_id
     WHERE NOT EXISTS (
           SELECT 1 FROM (
               SELECT DISTINCT ON (film_genre_hk) film_genre_hk, hashdiff
                 FROM sat_film_genre_details
                ORDER BY film_genre_hk, load_dts DESC) cur
            WHERE cur.film_genre_hk = dv_hash(f.catalog_number, g.code)
              AND cur.hashdiff = dv_hashdiff(fg.is_primary::text));
    GET DIAGNOSTICS n = ROW_COUNT;
    vault_object := 'sat_film_genre_details'; rows_inserted := n; RETURN NEXT;

    RETURN;
END $fn$;

COMMENT ON FUNCTION dv_load_all(timestamp, varchar) IS
'Пакетная загрузка Data Vault из операционной схемы video_rental_3nf. Хабы и Связи пополняются только новыми ключами, Спутники - только изменившимися версиями (сравнение hashdiff).';

-- =============================================================================
-- 8. Контроль выполнения
-- =============================================================================
\echo '--- Схема Data Vault создана. Состав объектов: ---'
SELECT CASE
         WHEN table_name LIKE 'hub\_%' THEN 'HUB'
         WHEN table_name LIKE 'link\_%' THEN 'LINK'
         WHEN table_name LIKE 'sat\_%' THEN 'SATELLITE'
       END AS vault_object_type,
       count(*) AS objects,
       string_agg(table_name, ', ' ORDER BY table_name) AS object_list
  FROM information_schema.tables
 WHERE table_schema = 'video_rental_dv'
   AND table_type = 'BASE TABLE'
 GROUP BY 1
 ORDER BY 1;
