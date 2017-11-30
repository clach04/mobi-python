import unittest
import tempfile

from pprint import pprint

from mobi import Mobi


class MobiTests(unittest.TestCase):
    def setUp(self):
        self.mobitest = Mobi("test/CharlesDarwin.mobi")

    def test_parse(self):
        pprint(self.mobitest.config)

    def test_read(self):
        content = b''
        for i in range(1, 5):
            content += self.mobitest.readRecord(i)

    def test_image(self):
        pprint(self.mobitest.records)
        for record in range(4):
            with tempfile.TemporaryFile() as f:
                f.write(self.mobitest.readImageRecord(record))

    def test_author_title(self):
        self.assertEqual('Charles Darwin', self.mobitest.author)
        self.assertEqual(
            self.mobitest.title,
            'The Origin of Species by means of Natural Selection, 6th Edition')


if __name__ == '__main__':
    unittest.main()
