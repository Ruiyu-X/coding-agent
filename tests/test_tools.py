import tempfile
import unittest
from pathlib import Path

from agent.tools import LocalToolbox


class LocalToolboxTests(unittest.TestCase):
    def test_read_write_and_list_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            toolbox = LocalToolbox(Path(tmp))
            write_result = toolbox.write_file("src/example.txt", "hello")
            self.assertTrue(write_result.ok)

            read_result = toolbox.read_file("src/example.txt")
            self.assertTrue(read_result.ok)
            self.assertEqual(read_result.output, "hello")

            list_result = toolbox.list_files()
            self.assertTrue(list_result.ok)
            self.assertIn("src/example.txt", list_result.output)

    def test_prevents_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            toolbox = LocalToolbox(Path(tmp))
            result = toolbox.run("read_file", {"path": "../secret.txt"})
            self.assertFalse(result.ok)
            self.assertIn("escapes workspace", result.output)

    def test_replace_in_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            toolbox = LocalToolbox(Path(tmp))
            toolbox.write_file("app.py", "value = 1\n")

            result = toolbox.replace_in_file("app.py", "value = 1", "value = 2")

            self.assertTrue(result.ok)
            self.assertEqual(toolbox.read_file("app.py").output, "value = 2\n")

    def test_replace_in_file_rejects_unexpected_count(self):
        with tempfile.TemporaryDirectory() as tmp:
            toolbox = LocalToolbox(Path(tmp))
            toolbox.write_file("app.py", "value = 1\nvalue = 1\n")

            result = toolbox.replace_in_file("app.py", "value = 1", "value = 2")

            self.assertFalse(result.ok)
            self.assertEqual(toolbox.read_file("app.py").output, "value = 1\nvalue = 1\n")

    def test_diff_workspace(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app.py").write_text("value = 1\n", encoding="utf-8")
            toolbox = LocalToolbox(root)

            toolbox.write_file("app.py", "value = 2\n")
            result = toolbox.diff_workspace()

            self.assertTrue(result.ok)
            self.assertIn("-value = 1", result.output)
            self.assertIn("+value = 2", result.output)

    def test_discover_python_tests_reports_missing_expected_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "test_sample.py").write_text(
                (
                    "import unittest\n\n"
                    "class SampleTests(unittest.TestCase):\n"
                    "    def test_existing(self):\n"
                    "        self.assertTrue(True)\n\n"
                    "if __name__ == '__main__':\n"
                    "    unittest.main()\n\n"
                    "    def test_power(self):\n"
                    "        self.assertTrue(True)\n"
                ),
                encoding="utf-8",
            )
            toolbox = LocalToolbox(root)

            result = toolbox.discover_python_tests(expected_tests=["test_power"])

            self.assertFalse(result.ok)
            self.assertIn("discovered_count=1", result.output)
            self.assertIn("missing_expected_tests=['test_power']", result.output)

    def test_discover_python_tests_accepts_expected_test(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "test_sample.py").write_text(
                (
                    "import unittest\n\n"
                    "class SampleTests(unittest.TestCase):\n"
                    "    def test_power(self):\n"
                    "        self.assertTrue(True)\n"
                ),
                encoding="utf-8",
            )
            toolbox = LocalToolbox(root)

            result = toolbox.discover_python_tests(expected_tests=["test_power"])

            self.assertTrue(result.ok)
            self.assertIn("discovered_count=1", result.output)
            self.assertIn("test_sample.SampleTests.test_power", result.output)

    def test_check_python_syntax_reports_indentation_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "broken.py").write_text(
                "    def test_power(self):\n        return True\n",
                encoding="utf-8",
            )
            toolbox = LocalToolbox(root)

            result = toolbox.check_python_syntax("broken.py")

            self.assertFalse(result.ok)
            self.assertIn("IndentationError", result.output)


if __name__ == "__main__":
    unittest.main()
