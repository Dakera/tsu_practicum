# Этап 5 — построение и обучение модели

Исходники пятого занятия (`starter/`, `config_example.json`, задание, вводная, шаблоны журнала и отчёта) не изменяются. Новых данных нет: вход — таблицы этапа 4 из `lesson4/output/` (`features.csv`, `labels.csv`, `split.csv`).

Запуск из корня репозитория:

```
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --inplace lesson5/train.ipynb
```

Проверка сохранённого кандидата в новом процессе, без обучения:

```
python lesson5/starter/check_saved_model.py --model lesson5/output/model/candidate.joblib --prepared lesson4/output --out lesson5/output/reload_validation_predictions.csv --expected lesson5/output/validation_predictions.csv
```

Списки признаков, шесть конфигураций, временные фолды и правило выбора — [`config.json`](config.json). Загрузка и метрики — `starter/training_utils.py`, подготовка для регрессии — `starter/preprocessing_template.py`; ноутбук импортирует их из `starter/`.

Результат: выбран `hgb_leaf4_nodig` (бустинг, 4 листа, без цифрового источника). На validation 01.08.2026 он нашёл 18 уходов из 63 против 14 у сортировки по долгу; на проверочных датах внутри train — 92 против 97 из 236. Преимущество над baseline не доказано. Test не оценивался.

## Навигация по пунктам сдачи

| № | Требование задания | Где |
|---|---|---|
| 1 | Код, конфигурация, версия признаков, зависимости, команды | [`train.ipynb`](train.ipynb), [`config.json`](config.json), [`requirements.txt`](../requirements.txt), [`versions.json`](output/versions.json); версия признаков — суммы в [`input_schema.json`](output/model/input_schema.json); команды — выше |
| 2 | Журнал конфигураций, два метода и baseline на train/validation | [`docs/experiment_journal.md`](docs/experiment_journal.md), [`experiment_log.csv`](output/experiment_log.csv) |
| 3 | Таблицы по T: N, K, ушедшие, найденные, Recall@K, Precision@K, AP | [`metrics_by_date.csv`](output/metrics_by_date.csv), фолды — [`fold_metrics_by_date.csv`](output/fold_metrics_by_date.csv) |
| 4 | Validation-прогнозы кандидата: ключи, score, rank, top-K | [`validation_predictions.csv`](output/validation_predictions.csv); метка — в `lesson4/output/labels.csv` |
| 5 | Сохранённый Pipeline, схема входов, проверка загрузки без fit | [`candidate.joblib`](output/model/candidate.joblib), [`input_schema.json`](output/model/input_schema.json), [`reload_validation_predictions.csv`](output/reload_validation_predictions.csv), шаг 7 ноутбука |
| 6 | Отчёт | [`docs/training_report.md`](docs/training_report.md) |
| 7 | Вклад участников, версия репозитория, проверки | Шапка и конец [отчёта](docs/training_report.md), [`checks.csv`](output/checks.csv), [`selection.json`](output/selection.json) |

## Шаги ноутбука и шаги задания

| Шаг ноутбука | Шаг задания |
|---|---|
| 0. Конфигурация | — |
| 1. Проверка входа | 1 |
| 2. Baseline на тех же данных | 2 |
| 3. Два обучаемых метода | 3 |
| 4. План экспериментов и запуск | 4 |
| 5. Оценки риска и метрики кампании | 5 |
| 6. Выбор и фиксация кандидата | 6 |
| 7. Сохранение и воспроизводимость | 7 |
