"""Error handling, confirmation, timing and a closure cache."""

import time

import prompt

from primitive_db.constants import CACHE_LIMIT


def preserve_metadata(wrapper, func):
    """Keep the wrapped function's public name and documentation."""
    wrapper.__name__ = func.__name__
    wrapper.__doc__ = func.__doc__
    return wrapper


def handle_db_errors(func):
    """Report input and storage errors and let the command loop continue."""

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
    """Ask for explicit confirmation before a destructive operation."""

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
    """Print elapsed time after a successful operation."""

    def wrapper(*args, **kwargs):
        started = time.monotonic()
        result = func(*args, **kwargs)
        elapsed = time.monotonic() - started
        print(f"Функция {func.__name__} выполнилась за {elapsed:.3f} секунд")
        return result

    return preserve_metadata(wrapper, func)


def create_cacher():
    """Return a function that caches computed values in a closure."""
    cache = {}

    def cache_result(key, value_func):
        if key not in cache:
            if len(cache) >= CACHE_LIMIT:
                cache.clear()
            cache[key] = value_func()
        return cache[key]

    return cache_result
