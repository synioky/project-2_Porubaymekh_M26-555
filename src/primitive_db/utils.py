"""Read and write database JSON files."""

import json
import os

from primitive_db.constants import DATA_DIR


def load_metadata(filepath):
    """Return metadata or an empty dictionary for a new database."""
    try:
        with open(filepath, encoding="utf-8") as source:
            metadata = json.load(source)
    except FileNotFoundError:
        return {}
    if not isinstance(metadata, dict):
        raise ValueError("метаданные должны содержать объект JSON")
    for schema in metadata.values():
        if not isinstance(schema, dict):
            raise ValueError("повреждена структура метаданных")
    return metadata


def save_metadata(filepath, data):
    """Save metadata as readable UTF-8 JSON."""
    with open(filepath, "w", encoding="utf-8") as target:
        json.dump(data, target, ensure_ascii=False, indent=2)


def table_path(table_name):
    """Validate a table identifier before building a file path."""
    if not table_name.isidentifier():
        raise ValueError(f"недопустимое имя таблицы {table_name!r}")
    return os.path.join(DATA_DIR, f"{table_name}.json")


def load_table_data(table_name):
    """Load rows, reporting a missing or damaged table file."""
    with open(table_path(table_name), encoding="utf-8") as source:
        rows = json.load(source)
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError("данные таблицы должны содержать список объектов JSON")
    return rows


def save_table_data(table_name, data):
    """Create the data directory if necessary and save the rows."""
    path = table_path(table_name)
    os.makedirs(DATA_DIR, exist_ok=True)
    save_metadata(path, data)


def remove_table_data(table_name):
    """Remove a table file along with its metadata."""
    os.remove(table_path(table_name))
