import unittest
import tempfile
import imghdr

from pprint import pprint

from six import BytesIO

from mobi import Mobi


class MobiTests(unittest.TestCase):
    def setUp(self):
        self.mobi = Mobi("test/CharlesDarwin.mobi")

    def tearDown(self):
        self.mobi.close()

    def test_parse(self):
        self.assertIn('Mobi', self.mobi.config)
        self.assertIn('EXTH', self.mobi.config)
        self.assertIn('Palmdoc', self.mobi.config)

    def test_read(self):
        content = b''
        for i in range(1, 5):
            content += self.mobi.readRecord(i)
        self.assertLess(0, len(content))

    def test_image(self):
        for record in range(2):
            bytes = self.mobi.readImageRecord(record)
            self.assertEqual('jpeg', imghdr.what('', h=bytes))

    def test_author_title(self):
        self.assertEqual('Charles Darwin', self.mobi.author)
        self.assertEqual(
            self.mobi.title,
            'The Origin of Species by means of Natural Selection, 6th Edition')


if __name__ == '__main__':
    unittest.main()
