"""Paths, supported types and command help."""

META_FILE = "db_meta.json"
DATA_DIR = "data"
VALID_TYPES = {"int": int, "str": str, "bool": bool}
ID_COLUMN = "ID"
HELP = """***База данных***
create_table <таблица> <столбец:тип> ...
list_tables
info <таблица>
drop_table <таблица>
help
exit
"""
