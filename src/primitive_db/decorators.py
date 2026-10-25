import time

import prompt

from primitive_db.constants import CACHE_LIMIT


def preserve_metadata(wrapper, func):
    """Сохраняет имя и описание исходной функции."""
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def handle_db_errors(func):
    """Выводит ошибку и позволяет продолжить ввод команд."""

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except FileNotFoundError:
            print("Ошибка: файл данных не найден.")
        except KeyError as error:
            print(f"Ошибка: таблица или столбец {error} не найден.")
        except (ValueError, TypeError) as error:
            print(f"Некорректное значение: {error}. Попробуйте снова.")
        except OSError as error:
            print(f"Ошибка работы с файлом: {error}")
        return None

    return preserve_metadata(wrapper, func)


def confirm_action(action_name):
    """Запрашивает подтверждение перед выполнением функции."""

    def decorate(func):
        def wrapper(*args, **kwargs):
            answer = prompt.string(
                f'Вы уверены, что хотите выполнить "{action_name}"? [y/n]: ',
                empty=True,
            )
            if answer.strip().lower() != "y":
                print("Операция отменена.")
                return None
            return func(*args, **kwargs)

        return preserve_metadata(wrapper, func)

    return decorate


def log_time(func):
    """Выводит время выполнения функции."""

    def wrapper(*args, **kwargs):
        started = time.monotonic()
        result = func(*args, **kwargs)
        elapsed = time.monotonic() - started
        print(f"Функция {func.__name__} выполнилась за {elapsed:.3f} секунд")
        return result

    return preserve_metadata(wrapper, func)


def create_cacher():
    """Создаёт функцию с кэшем в замыкании."""
    cache = {}

    def cache_result(key, value_func):
        if key not in cache:
            if len(cache) >= CACHE_LIMIT:
                cache.clear()
            cache[key] = value_func()
        return cache[key]

    return cache_result
