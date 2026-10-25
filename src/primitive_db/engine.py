import prompt
from prettytable import PrettyTable

from primitive_db import core
from primitive_db.constants import HELP, META_FILE
from primitive_db.decorators import handle_db_errors
from primitive_db.parser import parse_command
from primitive_db.utils import (
    load_metadata,
    load_table_data,
    save_metadata,
    save_table_data,
)


def print_help():
    """Выводит список команд."""
    print(HELP)


def show_rows(schema, rows):
    """Выводит записи в виде таблицы."""
    table = PrettyTable(list(schema))
    for row in rows:
        table.add_row([row[column] for column in schema])
    print(table)


def report_changes(before, after, table_name, action):
    """Выводит ID изменённых записей или сообщает, что изменений нет."""
    if action == "удалена":
        remaining = {row["ID"] for row in after}
        changed = [row for row in before if row["ID"] not in remaining]
    else:
        changed = [new for old, new in zip(before, after, strict=True) if old != new]
    if not changed:
        print("Изменено записей: 0.")
    for row in changed:
        print(f'Запись с ID={row["ID"]} в таблице "{table_name}" успешно {action}.')


@handle_db_errors
def execute(text):
    """Выполняет команду и сохраняет изменения в файлы."""
    command, args = parse_command(text)
    if command == "exit":
        return False
    if command == "empty":
        return True
    if command == "help":
        print_help()
        return True
    if command == "unknown":
        print(f"Функции {args[0]} нет. Попробуйте снова.")
        return True

    metadata = load_metadata(META_FILE)
    if command == "list_tables":
        print("\n".join(f"- {name}" for name in metadata) or "Таблиц пока нет.")
        return True
    table_name = args[0]
    if command == "create_table":
        result = core.create_table(metadata, *args)
        if result is not None:
            save_table_data(table_name, [])
            save_metadata(META_FILE, result)
            columns = ", ".join(
                f"{col}:{kind}" for col, kind in result[table_name].items()
            )
            print(f'Таблица "{table_name}" успешно создана со столбцами: {columns}')
        return True

    if table_name not in metadata:
        raise KeyError(table_name)
    schema = metadata[table_name]
    if command == "drop_table":
        result = core.drop_table(metadata, table_name)
        if result is not None:
            save_metadata(META_FILE, result)
            print(f'Таблица "{table_name}" успешно удалена.')
        return True

    if command == "insert":
        result = core.insert(metadata, *args)
        if result is not None:
            save_table_data(table_name, result)
            print(
                f"Запись с ID={result[-1]['ID']} успешно добавлена "
                f'в таблицу "{table_name}".'
            )
        return True

    rows = load_table_data(table_name)
    match command:
        case "info":
            print(f"Таблица: {table_name}")
            print(
                "Столбцы: " + ", ".join(f"{col}:{kind}" for col, kind in schema.items())
            )
            print(f"Количество записей: {len(rows)}")
        case "select":
            result = core.select(rows, args[1], schema)
            if result is not None:
                show_rows(schema, result)
        case "update" | "delete":
            # Проверяем условие до запроса подтверждения.
            core.validate_fields(schema, args[-1])
            if command == "update":
                result = core.update(rows, args[1], args[2], schema)
            else:
                result = core.delete(rows, args[1], schema)
            if result is not None:
                save_table_data(table_name, result)
                action = "обновлена" if command == "update" else "удалена"
                report_changes(rows, result, table_name, action)
    return True


def run():
    """Читает команды до выхода из программы."""
    print_help()
    while True:
        try:
            text = prompt.string("Введите команду: ", empty=True)
            if execute(text) is False:
                break
        except (EOFError, KeyboardInterrupt):
            print("\nВыход.")
            break
