# Этап 4 — признаки и выбор метода

Исходники четвёртого занятия (`data/`, `data_dictionary_lesson4.csv`, `feature_catalog_template.csv`, `config_example.json`, `starter/`, задание, вводная, шаблон плана) не изменяются. Вход — очищенные таблицы этапа 2 из `lesson2/output/` и новый `data/digital_usage_monthly.csv`.

Запуск из корня репозитория:

```
pip install -r requirements.txt
jupyter nbconvert --to notebook --execute --inplace lesson4/features.ipynb
```

Конфигурация дат, окна, горизонта и доли кампании — [`config.json`](config.json) (совпадает с примером из комплекта). Преобразователь — `make_preprocessor` из [`starter/preprocessing_template.py`](starter/preprocessing_template.py), ноутбук передаёт ему свои списки столбцов.

## Навигация по пунктам сдачи

| № | Требование задания | Где |
|---|---|---|
| 1 | Код, команда запуска, конфигурация, версии | [`features.ipynb`](features.ipynb), команда — выше, [`config.json`](config.json), [`requirements.txt`](../requirements.txt) |
| 2 | Четыре слоя таблиц | [`features.csv`](output/features.csv), [`labels.csv`](output/labels.csv), [`split.csv`](output/split.csv), [`feature_audit.csv`](output/feature_audit.csv) |
| 3 | Паспорт признаков: 20 содержательных + 4 индикатора полноты | [`docs/feature_catalog.csv`](docs/feature_catalog.csv), доля пропусков — [`feature_missing_share.csv`](output/feature_missing_share.csv) |
| 4 | Преобразование с fit только на train, список X, размеры, порядок строк | Шаг 7 ноутбука, [`x_columns.csv`](output/x_columns.csv), [`matrix_shapes.csv`](output/matrix_shapes.csv) |
| 5 | Train-метрики базового правила по датам | [`baseline_train_metrics.csv`](output/baseline_train_metrics.csv) |
| 6 | План моделирования | [`docs/modeling_plan.md`](docs/modeling_plan.md) |
| 7 | Проверки и вклад участников | [`checks.csv`](output/checks.csv), [`check_active_base.csv`](output/check_active_base.csv), раздел «Проверки» плана |

## Шаги ноутбука и шаги задания

| Шаг ноутбука | Шаг задания |
|---|---|
| 0. Конфигурация, загрузка, проверки цифрового источника | 3 (проверка источника) |
| 1. Активная база и метка | 2 |
| 2–4. Признаки биллинга, поддержки, цифрового источника | 1, 2, 3 |
| 5. Сборка слоёв и паспорт | 1, 4 |
| 6. Проверки времени и полноты | «Минимальные проверки» |
| 7. Преобразование для кандидата 1 | 4 |
| 8. Базовое правило на train | 5 |
| 9. Воспроизводимость | «Минимальные проверки», последний пункт |
