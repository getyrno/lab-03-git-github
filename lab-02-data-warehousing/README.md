# Лабораторная работа № 2. Хранилища данных

**Тема:** Проектирование базы данных в 3NF и Data Vault
**Вариант 14:** «Система учета в видеопрокате»
**Студент:** Никитин Платон Алексеевич, группа 231-363

Предметная область - учет проката **физических экземпляров** фильмов
(VHS, DVD, Blu-ray) клиентам пункта видеопроката: каталог фильмов и жанров,
фонд экземпляров, клиенты и сотрудники, операции выдачи и возврата, стоимость
проката, платежи и контроль просрочки. Это не стриминговый сервис.

Обе модели реализованы в PostgreSQL и реально выполнены: скрипты создают схемы
с нуля, загружают синтетические данные, выполняют проверочные запросы и
проверяют ограничения целостности.

---

## 1. Что реализовано

| Модель | Схема | Состав |
|---|---|---|
| 3NF (третья нормальная форма) | `video_rental_3nf` | 10 таблиц, 6 представлений, триггер, частичный уникальный индекс |
| Data Vault | `video_rental_dv` | 8 Hub, 7 Link, 12 Satellite, 12 представлений, функция загрузки `dv_load_all` |

Дополнительно создана служебная схема `lab` с функциями `lab.current_date()` и
`lab.now()`: «текущая дата» системы зафиксирована, поэтому проверки
воспроизводимы и не зависят от дня запуска.

---

## 2. Структура файлов

```
Лабораторная работа №2/
├── README.md                        этот файл
├── .gitignore                       служебные файлы Python
├── run_all.sh                       полный прогон: схемы, данные, проверки
├── Отчет/
│   ├── Лабораторная работа №2.docx   итоговый отчет Word
│   └── Лабораторная работа №2.pdf    контрольный PDF-экспорт отчета
├── sql/
│   ├── 01_create_3nf.sql             DDL модели 3NF
│   ├── 02_create_data_vault.sql      DDL модели Data Vault + функция загрузки
│   ├── 03_test_data_3nf.sql          тестовые данные 3NF
│   ├── 04_test_data_data_vault.sql   загрузка Data Vault и примеры историзации
│   └── 05_validation.sql             проверочные запросы и проверка ограничений
├── diagrams/
│   ├── 3nf_model.svg / .png          даталогическая модель 3NF
│   ├── data_vault_model.svg / .png   даталогическая модель Data Vault
│   ├── make_diagrams.py              генератор диаграмм (PNG ~310-340 dpi)
│   └── check_diagrams.py             геометрическая проверка диаграмм
├── report/
│   ├── build_report.py               сборка отчета Word на реальных данных
│   ├── build_and_verify.sh           сборка + рендер + проверки
│   ├── docx_helpers.py               оформление DOCX по требованиям
│   ├── query_db.py                   выполнение SQL к учебной БД
│   ├── check_docx.py                 проверка структуры DOCX
│   ├── check_render.py               проверка отрендеренных страниц
│   ├── check_visual.py               попиксельная проверка верстки страниц
│   ├── page_numbers.py               номера страниц разделов для оглавления
│   └── toc_pages.json                фактические номера страниц (генерируется)
└── evidence/
    ├── postgres_validation.txt       полный журнал прогона (создание + проверки)
    ├── postgres_schema_3nf.txt       структура таблиц 3NF (\d+)
    ├── postgres_schema_dv.txt        структура таблиц Data Vault (\d+)
    ├── data_vault_history.txt        история изменения Спутников
    ├── make_evidence.sh              сбор доказательств из работающей БД
    └── render/                       страницы отчета в PNG и PDF (визуальный контроль)
```

---

## 3. Требования

- Docker (образ `postgres:17`, скачивается автоматически при первом запуске);
- для сборки отчета: Python 3 с `python-docx` и `Pillow`
  (в окружении Codex используется встроенный runtime);
- рендер отчета в PDF/PNG выполняется LibreOffice из состава
  `codex-primary-runtime` (системный LibreOffice не требуется).

Проверено на PostgreSQL 17.11.

---

## 4. Запуск PostgreSQL

Создается изолированный контейнер на свободном порту 55432, чтобы не задеть
уже работающие базы пользователя:

```bash
docker run -d --name video_rental_lab_pg \
  -e POSTGRES_PASSWORD=labpass \
  -e POSTGRES_USER=labuser \
  -e POSTGRES_DB=video_rental_lab \
  -p 55432:5432 postgres:17

# дождаться готовности
docker exec video_rental_lab_pg pg_isready -U labuser -d video_rental_lab
```

Проверка версии:

```bash
docker exec video_rental_lab_pg psql -U labuser -d video_rental_lab -c "select version();"
```

Чистый старт (пересоздать учебную БД с нуля):

```bash
docker exec video_rental_lab_pg psql -U labuser -d postgres \
  -c "DROP DATABASE IF EXISTS video_rental_lab;" \
  -c "CREATE DATABASE video_rental_lab;"
```

---

## 5. Порядок выполнения SQL

Полный прогон одной командой из каталога лабораторной работы:

```bash
./run_all.sh
```

Пошагово (то же самое, но с видимым результатом каждого файла):

```bash
# 1. Схема 3NF
docker exec -i video_rental_lab_pg psql -U labuser -d video_rental_lab \
  -v ON_ERROR_STOP=1 -f - < sql/01_create_3nf.sql

# 2. Схема Data Vault (DDL + функция загрузки dv_load_all)
docker exec -i video_rental_lab_pg psql -U labuser -d video_rental_lab \
  -v ON_ERROR_STOP=1 -f - < sql/02_create_data_vault.sql

# 3. Тестовые данные 3NF
docker exec -i video_rental_lab_pg psql -U labuser -d video_rental_lab \
  -v ON_ERROR_STOP=1 -f - < sql/03_test_data_3nf.sql

# 4. Загрузка Data Vault и историзация Спутников
docker exec -i video_rental_lab_pg psql -U labuser -d video_rental_lab \
  -v ON_ERROR_STOP=1 -f - < sql/04_test_data_data_vault.sql

# 5. Проверочные запросы и проверка ограничений
docker exec -i video_rental_lab_pg psql -U labuser -d video_rental_lab \
  -v ON_ERROR_STOP=1 -f - < sql/05_validation.sql
```

Все скрипты идемпотентны: повторный запуск пересоздает схемы и данные с нуля и
дает тот же результат.

---

## 6. Команды проверки

Список таблиц 3NF и Data Vault:

```bash
docker exec video_rental_lab_pg psql -U labuser -d video_rental_lab -c "\dt video_rental_3nf.*"
docker exec video_rental_lab_pg psql -U labuser -d video_rental_lab -c "\dt video_rental_dv.*"
```

Структура таблиц с ограничениями и комментариями:

```bash
docker exec video_rental_lab_pg psql -U labuser -d video_rental_lab -c "\d+ video_rental_3nf.*"
docker exec video_rental_lab_pg psql -U labuser -d video_rental_lab -c "\d+ video_rental_dv.*"
```

Ключевые проверочные запросы вручную:

```bash
# активные прокаты
docker exec video_rental_lab_pg psql -U labuser -d video_rental_lab \
  -c "SELECT * FROM video_rental_3nf.v_active_rental;"

# доступные экземпляры
docker exec video_rental_lab_pg psql -U labuser -d video_rental_lab \
  -c "SELECT inventory_code, title FROM video_rental_3nf.v_copy_status WHERE is_available;"

# история изменения клиента CR-00001 в Data Vault
docker exec video_rental_lab_pg psql -U labuser -d video_rental_lab -c "
SELECT hc.card_number, sc.load_dts, sc.phone, sc.address, sc.hashdiff
  FROM video_rental_dv.hub_customer hc
  JOIN video_rental_dv.sat_customer_contact sc ON sc.customer_hk = hc.customer_hk
 WHERE hc.card_number = 'CR-00001' ORDER BY sc.load_dts;"

# восстановление картины 3NF из Hub + Link + Satellite
docker exec video_rental_lab_pg psql -U labuser -d video_rental_lab \
  -c "SELECT * FROM video_rental_dv.v_rental_full ORDER BY rental_number;"
```

Сбор доказательств в каталог `evidence/`:

```bash
./evidence/make_evidence.sh
```

Сборка и полная проверка отчета:

```bash
./report/build_and_verify.sh
```

Отдельные проверки:

```bash
python3 diagrams/check_diagrams.py        # геометрия диаграмм
python3 report/check_docx.py              # структура DOCX
python3 report/check_render.py evidence/render/report.txt evidence/render  # страницы
python3 report/check_visual.py evidence/render   # попиксельная проверка верстки
```

`report/build_and_verify.sh` собирает отчет дважды: первый проход определяет
фактические номера страниц разделов по отрендеренному PDF, второй проставляет
их в оглавление. Поэтому оглавление всегда совпадает с версткой.

---

## 7. Проверенные сценарии

Проверочные запросы (`sql/05_validation.sql`) реально выполнены:

1. список активных прокатов;
2. список просроченных экземпляров с начисленной пеней;
3. история прокатов конкретного клиента (CR-00002);
4. экземпляры, доступные к выдаче сейчас, и сводка по фонду;
5. фильмы и их жанры;
6. суммы платежей по операциям проката и итоги по способам оплаты;
7. восстановление информации из Hub + Link + Satellite (`v_rental_full`);
8. получение последней версии записи Спутника;
9. получение истории изменения объекта (клиент, экземпляр, прокат);
10. аудит загрузок по `record_source`.

Проверка ограничений: десять негативных тестов (ссылка на несуществующую
сущность, отрицательная сумма, некорректная дата, нарушение UNIQUE, повторная
выдача занятого экземпляра, неверный формат бизнес-ключа, повтор бизнес-ключа
Хаба, повтор версии Спутника, Спутник без родительского Хаба, отрицательная
сумма в Спутнике). Все отклонены PostgreSQL с ожидаемыми кодами SQLSTATE
(23503, 23505, 23514), данные основной модели не изменились.

---

## 8. Итоговые файлы для загрузки в LMS

1. `Отчет/Лабораторная работа №2.docx` - отчет.
2. `Отчет/Лабораторная работа №2.pdf` - контрольный экспорт отчета.
3. `sql/01_create_3nf.sql` ... `sql/05_validation.sql` - SQL-скрипты (5 файлов).
4. `diagrams/3nf_model.png` и `diagrams/3nf_model.svg` - модель 3NF.
5. `diagrams/data_vault_model.png` и `diagrams/data_vault_model.svg` - модель Data Vault.
6. `evidence/postgres_validation.txt` - журнал реального выполнения SQL.
