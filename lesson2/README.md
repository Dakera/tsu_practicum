# Этап 2 — сбор и подготовка данных

Исходники второго занятия лежат в `data/` и `schema_support.csv` и не изменяются. Текущие обращения читаются из SQLite, CSV-экспорт базы не используется.

Запуск из корня репозитория: `python lesson2/prepare.py`. Код: `prepare.py` (точка входа) и модули `prep/`: `load` → `inventory` → `audit` → `clean` → `merge` → `checks`.

| Результат (`output/`) | Содержание |
|---|---|
| `subscribers_clean.csv`, `billing_clean.csv`, `contract_events_clean.csv`, `support_clean.csv` | Нормализованные таблицы |
| `customer_month.csv` | Одна строка на `customer_id` и `billing_month`, агрегаты поддержки на момент снимка |
| `quarantine.csv` | Записи поддержки, исключённые из расчётов, с причиной |
| `decisions.csv` | Журнал решений: проблема, действие, обоснование, число записей |
| `audit_before.csv`, `audit_after.csv` | Проверки качества до и после очистки |
| `checks.csv` | Проверки доступности информации и объединения |
| `inventory_sources.csv`, `inventory_columns.csv` | Инвентаризация источников |
| `summary.json` | Машинно-читаемая сводка количеств |

Документы: [отчёт о качестве](docs/quality_report.md), [словарь данных](docs/data_dictionary.csv).

## Навигация по пунктам

| № | Требование задания | Где |
|---|---|---|
| 1 | Код, SQL-запросы, команда запуска | [`prep/`](prep/), [`support_current.sql`](prep/sql/support_current.sql), команда — выше |
| 2 | Подготовленные таблицы | [`subscribers_clean.csv`](output/subscribers_clean.csv), [`billing_clean.csv`](output/billing_clean.csv), [`contract_events_clean.csv`](output/contract_events_clean.csv), [`support_clean.csv`](output/support_clean.csv), [`customer_month.csv`](output/customer_month.csv) |
| 3 | Карантин с причинами | [`quarantine.csv`](output/quarantine.csv) |
| 4 | Обновлённый словарь данных | [`data_dictionary.csv`](docs/data_dictionary.csv) |
| 5 | Отчёт о качестве и машинная сводка | [`quality_report.md`](docs/quality_report.md), [`summary.json`](output/summary.json) |
| 6 | Журнал решений | [`decisions.csv`](output/decisions.csv) |
| 7 | Результаты проверок и вклад участников | [`checks.csv`](output/checks.csv), раздел «Вклад участников» в [отчёте](docs/quality_report.md) |
