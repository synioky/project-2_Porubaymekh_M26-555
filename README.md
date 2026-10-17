# Примитивная база данных

Консольная база данных на Python 3.12+. Поддерживает создание и удаление таблиц,
CRUD-операции, типы `int`, `str`, `bool` и хранение данных в JSON.

## Установка и запуск

Из папки репозитория:

```sh
uv sync
uv run database
```

Также доступны `uv run project` и `uv run python -m primitive_db.main`.

## Управление таблицами

```text
create_table users name:str age:int is_active:bool
list_tables
info users
```

Столбец `ID:int` добавляется автоматически. Имена таблиц и столбцов должны быть
идентификаторами Python. Данные хранятся в `data/<таблица>.json`, структура таблиц
в `db_meta.json` в рабочей папке.

