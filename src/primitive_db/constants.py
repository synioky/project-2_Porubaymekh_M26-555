"""Paths, supported types and command help."""

META_FILE = "db_meta.json"
DATA_DIR = "data"
VALID_TYPES = {"int": int, "str": str, "bool": bool}
ID_COLUMN = "ID"
CACHE_LIMIT = 128
HELP = """***База данных***
create_table <таблица> <столбец:тип> ...
list_tables
drop_table <таблица>
insert into <таблица> values (<значение>, ...)
select from <таблица> [where <столбец> = <значение>]
update <таблица> set <столбец> = <значение> [, ...] where <столбец> = <значение>
delete from <таблица> where <столбец> = <значение>
info <таблица>
help
exit
Типы: int, str, bool. Строки заключаются в кавычки, bool: true или false.
"""
