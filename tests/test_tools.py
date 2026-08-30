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


if __name__ == "__main__":
    unittest.main()
