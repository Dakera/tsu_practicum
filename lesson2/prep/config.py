"""Пути и константы подготовки данных второго занятия.

Пути строятся от расположения этого файла, а не от текущей папки,
поэтому запуск работает одинаково локально, в Colab и у другого участника.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]  # lesson2/prep/config.py -> корень репозитория

LESSON1_RAW = ROOT / "lesson1" / "data" / "raw"
LESSON2_RAW = ROOT / "lesson2" / "data"
OUTPUT = ROOT / "lesson2" / "output"

SUBSCRIBERS = LESSON1_RAW / "subscribers.csv"
BILLING = LESSON1_RAW / "billing_monthly.csv"
EVENTS = LESSON1_RAW / "contract_events.csv"
DICTIONARY = LESSON1_RAW / "data_dictionary.csv"
SUPPORT_DB = LESSON2_RAW / "support.sqlite"
SUPPORT_LEGACY = LESSON2_RAW / "support_legacy_sep_oct_2025.csv"
SUPPORT_SCHEMA = ROOT / "lesson2" / "schema_support.csv"
DICTIONARY_V2 = ROOT / "lesson2" / "docs" / "data_dictionary.csv"  # prepared tables, maintained by hand

# CSV-экспорт SQLite намеренно не входит в список: это копия той же таблицы,
# читаем один источник — саму базу.
INPUTS = [SUBSCRIBERS, BILLING, EVENTS, DICTIONARY, SUPPORT_DB, SUPPORT_LEGACY, SUPPORT_SCHEMA]

TZ = "Europe/Moscow"  # все моменты времени приводятся к Москве (UTC+3, без перехода на летнее время)


def check_inputs() -> None:
    """Падает со списком отсутствующих файлов, если чего-то нет."""
    missing = [str(p.relative_to(ROOT)) for p in INPUTS if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Не найдены входные файлы (пути от {ROOT}): {missing}")
