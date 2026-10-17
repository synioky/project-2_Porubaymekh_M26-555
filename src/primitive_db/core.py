"""Table schema management."""

from primitive_db.constants import ID_COLUMN, VALID_TYPES
from primitive_db.utils import remove_table_data, table_path


def create_table(metadata, table_name, columns):
    """Add a validated schema with an automatic integer ID column."""
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


def drop_table(metadata, table_name):
    """Remove both the table schema and its data file."""
    if table_name not in metadata:
        raise KeyError(table_name)
    remove_table_data(table_name)
    del metadata[table_name]
    return metadata
