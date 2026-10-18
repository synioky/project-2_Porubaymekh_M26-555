"""Regression tests for parsing, persistence, validation and caching."""

import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from primitive_db import core
from primitive_db.decorators import create_cacher
from primitive_db.engine import execute
from primitive_db.parser import parse_command
from primitive_db.utils import load_metadata, load_table_data


class DatabaseTests(unittest.TestCase):
    """Run each database case in an independent temporary working folder."""

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        self.previous = os.getcwd()
        os.chdir(self.folder.name)
        self.output = io.StringIO()
        self.redirect = contextlib.redirect_stdout(self.output)
        self.redirect.__enter__()

    def tearDown(self):
        self.redirect.__exit__(None, None, None)
        os.chdir(self.previous)
        self.folder.cleanup()

    def create_users(self):
        execute("create_table users name:str age:int active:bool")

    def add_user(self, name="Sergei", age=28):
        execute(f'insert into users values ("{name}", {age}, true)')

    def test_crud_and_table_deletion(self):
        self.create_users()
        self.add_user()
        execute('update users set age=29, active=false where name="Sergei"')
        self.assertEqual(
            load_table_data("users"),
            [
                {"ID": 1, "name": "Sergei", "age": 29, "active": False},
            ],
        )
        execute("select from users where age=29")
        self.assertIn("Sergei", self.output.getvalue())
        with patch("prompt.string", return_value="y"):
            execute("delete from users where ID=1")
            self.assertEqual(load_table_data("users"), [])
            execute("drop_table users")
        self.assertEqual(load_metadata("db_meta.json"), {})
        self.assertFalse(Path("data/users.json").exists())

    def test_confirmation_cancel_preserves_files(self):
        self.create_users()
        self.add_user()
        before = Path("data/users.json").read_bytes()
        with patch("prompt.string", return_value="n"):
            execute("delete from users where ID=1")
            execute("drop_table users")
        self.assertEqual(Path("data/users.json").read_bytes(), before)
        self.assertIn("users", load_metadata("db_meta.json"))

    def test_invalid_schemas_do_not_create_files(self):
        for text in (
            "create_table bad age:float",
            "create_table bad ID:int",
            "create_table bad age:int age:str",
            "create_table ../bad age:int",
            "create_table bad age",
            "create_table bad id:str",
        ):
            with self.subTest(text=text):
                execute(text)
                self.assertEqual(load_metadata("db_meta.json"), {})

    def test_duplicate_table_does_not_erase_data(self):
        self.create_users()
        self.add_user()
        execute("create_table users other:str")
        self.assertEqual(len(load_table_data("users")), 1)

    def test_insert_validates_count_and_types(self):
        self.create_users()
        for values in (
            '("A", true, false)',
            '("A", "28", true)',
            '("A", 28, 1)',
            '("A", 28)',
            '("A", 28, true, 9)',
        ):
            execute(f"insert into users values {values}")
            self.assertEqual(load_table_data("users"), [])

    def test_id_does_not_collide_after_middle_deletion(self):
        self.create_users()
        for name in ("A", "B", "C"):
            self.add_user(name)
        with patch("prompt.string", return_value="y"):
            execute("delete from users where ID=2")
        self.add_user("D")
        self.assertEqual([row["ID"] for row in load_table_data("users")], [1, 3, 4])

    def test_invalid_update_is_atomic_and_id_is_read_only(self):
        self.create_users()
        self.add_user()
        before = load_table_data("users")
        for clause in ('age="wrong"', 'name="Changed", age=true', "ID=4", "missing=1"):
            execute(f"update users set {clause} where ID=1")
            self.assertEqual(load_table_data("users"), before)

    def test_invalid_columns_even_on_empty_table(self):
        self.create_users()
        execute("select from users where missing=1")
        execute("update users set age=2 where missing=1")
        with patch("prompt.string") as confirm:
            execute("delete from users where missing=1")
            confirm.assert_not_called()
        self.assertGreaterEqual(self.output.getvalue().count("не найден"), 3)

    def test_cache_refreshes_and_returns_copies(self):
        rows = [{"ID": 1, "name": "A"}]
        core.select(rows)[0]["name"] = "tampered"
        self.assertEqual(core.select(rows)[0]["name"], "A")
        rows[0]["name"] = "B"
        self.assertEqual(core.select(rows)[0]["name"], "B")
        self.assertEqual(core.select(rows, {"name": "A"}), [])

    def test_cache_computes_once_per_key(self):
        cache = create_cacher()
        calls = []
        self.assertEqual(cache("key", lambda: calls.append(1) or 42), 42)
        self.assertEqual(cache("key", lambda: calls.append(2) or 99), 42)
        self.assertEqual(calls, [1])

    def test_no_bool_int_confusion_in_filter(self):
        self.assertEqual(core.select([{"age": 1}], {"age": True}), [])

    def test_quoted_values_preserve_punctuation_and_keywords(self):
        _, args = parse_command(
            'insert into users values ("Anna, Maria = where", -28, false)'
        )
        self.assertEqual(args[1], ["Anna, Maria = where", -28, False])
        _, args = parse_command('update users set name="where" where ID=1')
        self.assertEqual(args[1], {"name": "where"})
        _, args = parse_command("insert into t values ('28', '', 'O\"Brien')")
        self.assertEqual(args[1], ["28", "", 'O"Brien'])

    def test_malformed_commands_rejected(self):
        for text in (
            'insert into t values ("A",)',
            "insert into t values (A)",
            "select from t where age > 1",
            "update t set age=2",
            "select from t where age=1, ID=2",
            "help extra",
            'insert into t values ("unclosed)',
            "delete from t",
            "update t set age=1, age=2 where ID=1",
        ):
            with self.subTest(text=text), self.assertRaises(ValueError):
                parse_command(text)

    def test_corrupt_json_is_not_overwritten(self):
        Path("db_meta.json").write_text("broken", encoding="utf-8")
        execute("create_table t age:int")
        self.assertEqual(Path("db_meta.json").read_text(), "broken")

    def test_missing_data_is_reported(self):
        self.create_users()
        Path("data/users.json").unlink()
        execute("select from users")
        self.assertIn("файл данных не найден", self.output.getvalue())

    def test_persistence_across_processes_and_all_entry_points(self):
        env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        first = subprocess.run(
            [sys.executable, "-m", "primitive_db.main"],
            input='create_table t name:str\ninsert into t values ("Saved")\nexit\n',
            text=True,
            capture_output=True,
            encoding="utf-8",
            env=env,
            timeout=10,
        )
        self.assertEqual(first.returncode, 0, first.stderr)
        for entry in ("database", "project"):
            script = Path(sys.executable).parent / entry
            if os.name == "nt":
                script = script.with_suffix(".exe")
            result = subprocess.run(
                [str(script)],
                input="select from t\nexit\n",
                text=True,
                capture_output=True,
                encoding="utf-8",
                env=env,
                timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Saved", result.stdout)

    def test_eof_and_unknown_command(self):
        self.assertTrue(execute(""))
        execute("unknown")
        self.assertIn("Функции unknown нет", self.output.getvalue())
        result = subprocess.run(
            [sys.executable, "-m", "primitive_db.main"],
            input="",
            text=True,
            capture_output=True,
            encoding="utf-8",
            env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_json_is_readable_and_keeps_unicode(self):
        execute("create_table люди имя:str")
        execute('insert into люди values ("Анна")')
        self.assertEqual(
            json.loads(
                Path("data/люди.json").read_text(
                    encoding="utf-8",
                )
            )[0]["имя"],
            "Анна",
        )


if __name__ == "__main__":
    unittest.main()
