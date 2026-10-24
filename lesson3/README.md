# Этап 3 — разведочный анализ данных

Исходники третьего занятия (`data/`, `data_dictionary_lesson3.csv`, задание, вводная, шаблон отчёта) не изменяются; `analysis_plan.csv` заполняется ноутбуком. Вход — подготовленные таблицы этапа 2 из `lesson2/output/`.

## Навигация по пунктам

| № | Требование задания | Где |
|---|---|---|
| 1 | Ноутбук, команда запуска, версии, конфигурация периода, горизонта и базы | [`eda.ipynb`](eda.ipynb), команда — выше, [`requirements.txt`](../requirements.txt), [`config.json`](output/config.json) |
| 2 | `eda_sample`, словарь полей, таблица доступности сетевых отчётов | [`eda_sample.csv`](output/eda_sample.csv), [`eda_sample_dictionary.csv`](docs/eda_sample_dictionary.csv), [`network_availability.csv`](output/network_availability.csv) |
| 3 | Шесть рисунков и расчётные таблицы | [`output/figures/`](output/figures/), [`output/tables/`](output/tables/) — файлы `fig1_…`–`fig6_…` |
| 4 | Отчёт по шаблону и журнал гипотез | [`eda_report.md`](docs/eda_report.md), [`analysis_plan.csv`](analysis_plan.csv) |
| 5 | Направления признаков, ограничения, проверки | Разделы 6–7 [отчёта](docs/eda_report.md), [`checks.csv`](output/checks.csv) |
| 6 | Вклад участников и версия репозитория | Шапка и раздел 7 [отчёта](docs/eda_report.md) |
