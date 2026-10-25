import json

from primitive_db.constants import ID_COLUMN, VALID_TYPES
from primitive_db.decorators import (
    confirm_action,
    create_cacher,
    handle_db_errors,
    log_time,
)
from primitive_db.utils import load_table_data, remove_table_data, table_path

_cache_select = create_cacher()


def validate_fields(schema, fields, allow_id=True):
    """Проверяет столбцы и типы. bool и int считаются разными типами."""
    for column, value in fields.items():
        if column not in schema:
            raise KeyError(column)
        if column == ID_COLUMN and not allow_id:
            raise ValueError("ID формируется автоматически и не изменяется")
        if schema[column] not in VALID_TYPES:
            raise ValueError(f"неизвестный тип {schema[column]!r}")
        if type(value) is not VALID_TYPES[schema[column]]:
            raise ValueError(f"{column}: ожидается тип {schema[column]}")


def matches(row, where_clause):
    """Проверяет, подходит ли запись под условие."""
    return all(
        column in row and type(row[column]) is type(value) and row[column] == value
        for column, value in (where_clause or {}).items()
    )


@handle_db_errors
def create_table(metadata, table_name, columns):
    """Добавляет таблицу с указанными столбцами и полем ID."""
    table_path(table_name)
    if table_name in metadata:
        raise ValueError(f'таблица "{table_name}" уже существует')
    schema = {ID_COLUMN: "int"}
    for definition in columns:
        if definition.count(":") != 1:
            raise ValueError(f"{definition!r}: ожидается столбец:тип")
        column, data_type = definition.split(":")
        if not column.isidentifier() or column.upper() == ID_COLUMN:
            raise ValueError(f"недопустимое имя столбца {column!r}")
        if column in schema:
            raise ValueError(f"столбец {column!r} указан повторно")
        if data_type not in VALID_TYPES:
            raise ValueError(f"неизвестный тип {data_type!r}")
        schema[column] = data_type
    if len(schema) == 1:
        raise ValueError("укажите хотя бы один пользовательский столбец")
    metadata[table_name] = schema
    return metadata


@handle_db_errors
@confirm_action("удаление таблицы")
def drop_table(metadata, table_name):
    """Удаляет таблицу и файл с её записями."""
    if table_name not in metadata:
        raise KeyError(table_name)
    remove_table_data(table_name)
    del metadata[table_name]
    return metadata


@handle_db_errors
@log_time
def insert(metadata, table_name, values):
    """Добавляет запись с ID на единицу больше текущего максимума."""
    schema = metadata[table_name]
    columns = [column for column in schema if column != ID_COLUMN]
    if len(values) != len(columns):
        raise ValueError(f"ожидается {len(columns)} значений без ID")
    fields = dict(zip(columns, values, strict=True))
    validate_fields(schema, fields, allow_id=False)
    rows = load_table_data(table_name)
    new_id = max((row[ID_COLUMN] for row in rows), default=0) + 1
    rows.append({ID_COLUMN: new_id, **fields})
    return rows


@handle_db_errors
@log_time
def select(table_data, where_clause=None, schema=None):
    """Выбирает записи по условию и возвращает их копии."""
    if schema is not None:
        validate_fields(schema, where_clause or {})
    # Данные входят в ключ кэша, чтобы после изменений не получать старый результат.
    key = json.dumps([table_data, where_clause], sort_keys=True, ensure_ascii=False)
    rows = _cache_select(
        key,
        lambda: [row.copy() for row in table_data if matches(row, where_clause)],
    )
    return [row.copy() for row in rows]


@handle_db_errors
def update(table_data, set_clause, where_clause, schema=None):
    """Проверяет новые значения и обновляет записи по условию."""
    if not set_clause or not where_clause:
        raise ValueError("нужны set и where")
    if ID_COLUMN in set_clause:
        raise ValueError("ID формируется автоматически и не изменяется")
    if schema is not None:
        validate_fields(schema, set_clause, allow_id=False)
        validate_fields(schema, where_clause)
    else:
        for row in table_data:
            for column, value in {**where_clause, **set_clause}.items():
                if column not in row:
                    raise KeyError(column)
                if type(row[column]) is not type(value):
                    raise ValueError(f"неверный тип столбца {column}")
    return [
        {**row, **set_clause} if matches(row, where_clause) else row.copy()
        for row in table_data
    ]


@handle_db_errors
@confirm_action("удаление записей")
def delete(table_data, where_clause, schema=None):
    """Удаляет записи, которые подходят под условие."""
    if not where_clause:
        raise ValueError("нужно условие where")
    if schema is not None:
        validate_fields(schema, where_clause)
    return [row.copy() for row in table_data if not matches(row, where_clause)]
