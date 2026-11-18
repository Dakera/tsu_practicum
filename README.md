# tsu_practicum — прогноз оттока «СвязьРегион»

Учебный проект: каждый месяц выбирать не более 10% активной базы абонентов с наибольшим риском расторгнуть договор в следующем месяце.

**Итог:** на отложенном сентябре 2026 модель и сортировка по долгу нашли поровну — по 30 уходов из 65 при K = 191 (Recall@K 46,2%). Протокол, запуск, разбор и рекомендация — в [lesson6/README.md](lesson6/README.md).

| Этап | Отчёт | Код и результаты |
|---|---|---|
| 1. Устав проекта | [project_charter.md](lesson1/docs/project_charter.md) | |
| 2. Сбор и подготовка данных | [quality_report.md](lesson2/docs/quality_report.md) | [lesson2/](lesson2/README.md) |
| 3. Разведочный анализ | [eda_report.md](lesson3/docs/eda_report.md) | [lesson3/](lesson3/README.md) |
| 4. Признаки и выбор метода | [modeling_plan.md](lesson4/docs/modeling_plan.md) | [lesson4/](lesson4/README.md) |
| 5. Построение и обучение модели | [training_report.md](lesson5/docs/training_report.md) | [lesson5/](lesson5/README.md) |
| 6. Итоговая проверка и защита | [README итоговой проверки](lesson6/README.md) | [evaluate.ipynb](lesson6/evaluate.ipynb), [presentation.pptx](lesson6/presentation.pptx) |

Ответы заказчика на вопросы по уставу: [client_answers.md](client_answers.md).

Исходные выгрузки каждого этапа не изменяются. Формат CSV: UTF-8 с BOM, разделитель `;`.
