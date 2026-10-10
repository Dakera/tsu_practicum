"""Единый запуск подготовки данных второго занятия.

Запуск из корня репозитория:
    python lesson2/prepare.py
"""
from prep import config


def main() -> None:
    config.check_inputs()
    print("Входные файлы найдены:")
    for path in config.INPUTS:
        print(f"  {path.relative_to(config.ROOT)}  ({path.stat().st_size:,} байт)")


if __name__ == "__main__":
    main()
