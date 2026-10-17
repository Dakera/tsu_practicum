# tsu_practicum — прогноз оттока «СвязьРегион»

Учебный проект: каждый месяц выбирать не более 10% активной базы абонентов с наибольшим риском расторгнуть договор в следующем месяце.

- Устав проекта: [lesson1/docs/project_charter.md](lesson1/docs/project_charter.md)
- ~~Jupyter Notebook: [lesson1/notebooks/01_charter_checks.ipynb](notebooks/01_charter_checks.ipynb) - _(Google collab)_~~

## Данные

Исходные выгрузки (`subscribers.csv`, `billing_monthly.csv`, `contract_events.csv`, `data_dictionary.csv`, `billing_preview.csv`) не изменяются. Формат: UTF-8 с BOM, разделитель `;`.

## Этап 2 — сбор и подготовка данных

Исходники второго занятия лежат в `lesson2/data/` и `lesson2/schema_support.csv` и не изменяются. Текущие обращения читаются из SQLite, CSV-экспорт базы не используется.

| Результат (`lesson2/output/`) | Содержание |
|---|---|
| `subscribers_clean.csv`, `billing_clean.csv`, `contract_events_clean.csv`, `support_clean.csv` | Нормализованные таблицы |
| `customer_month.csv` | Одна строка на `customer_id` и `billing_month`, агрегаты поддержки на момент снимка |
| `quarantine.csv` | Записи поддержки, исключённые из расчётов, с причиной |
| `decisions.csv` | Журнал решений: проблема, действие, обоснование, число записей |
| `audit_before.csv`, `audit_after.csv` | Проверки качества до и после очистки |
| `checks.csv` | Проверки доступности информации и объединения |
| `inventory_sources.csv`, `inventory_columns.csv` | Инвентаризация источников |
| `summary.json` | Машинно-читаемая сводка количеств |

Документы: [отчёт о качестве](lesson2/docs/quality_report.md), [словарь данных](lesson2/docs/data_dictionary.csv). Код: `lesson2/prepare.py` (точка входа) и модули `lesson2/prep/`: `load` → `inventory` → `audit` → `clean` → `merge` → `checks`.

### Комплект сдачи

| № | Требование задания | Где |
|---|---|---|
| 1 | Код, SQL-запросы, команда запуска | [`lesson2/prep/`](lesson2/prep/), [`support_current.sql`](lesson2/prep/sql/support_current.sql), команда — выше |
| 2 | Подготовленные таблицы | [`subscribers_clean.csv`](lesson2/output/subscribers_clean.csv), [`billing_clean.csv`](lesson2/output/billing_clean.csv), [`contract_events_clean.csv`](lesson2/output/contract_events_clean.csv), [`support_clean.csv`](lesson2/output/support_clean.csv), [`customer_month.csv`](lesson2/output/customer_month.csv) |
| 3 | Карантин с причинами | [`quarantine.csv`](lesson2/output/quarantine.csv) |
| 4 | Обновлённый словарь данных | [`data_dictionary.csv`](lesson2/docs/data_dictionary.csv) |
| 5 | Отчёт о качестве и машинная сводка | [`quality_report.md`](lesson2/docs/quality_report.md), [`summary.json`](lesson2/output/summary.json) |
| 6 | Журнал решений | [`decisions.csv`](lesson2/output/decisions.csv) |
| 7 | Результаты проверок и вклад участников | [`checks.csv`](lesson2/output/checks.csv), раздел «Вклад участников» в [отчёте](lesson2/docs/quality_report.md) |
