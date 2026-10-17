"""Command loop for table management."""

import shlex

import prompt

from primitive_db import core
from primitive_db.constants import HELP, META_FILE
from primitive_db.utils import (
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
)


def execute(text):
    """Process a table command and persist the schema."""
    args = shlex.split(text)
    if not args:
        return True
    command = args[0]
    if command == "exit":
        return False
    if command == "help":
        print(HELP)
        return True
    metadata = load_metadata(META_FILE)
    if command == "list_tables" and len(args) == 1:
        print("\n".join(metadata) or "Таблиц пока нет.")
    elif command == "create_table" and len(args) >= 3:
        core.create_table(metadata, args[1], args[2:])
        save_table_data(args[1], [])
        save_metadata(META_FILE, metadata)
        print(f'Таблица "{args[1]}" успешно создана.')
    elif command == "drop_table" and len(args) == 2:
        core.drop_table(metadata, args[1])
        save_metadata(META_FILE, metadata)
        print(f'Таблица "{args[1]}" успешно удалена.')
    elif command == "info" and len(args) == 2:
        print(metadata[args[1]])
        print(f"Количество записей: {len(load_table_data(args[1]))}")
    else:
        raise ValueError("неверная команда, см. help")
    return True


def run():
    """Read commands until exit or EOF."""
    print(HELP)
    while True:
        try:
            if execute(prompt.string("Введите команду: ", empty=True)) is False:
                break
        except (KeyError, ValueError, OSError) as error:
            print(f"Ошибка: {error}")
        except (EOFError, KeyboardInterrupt):
            break
