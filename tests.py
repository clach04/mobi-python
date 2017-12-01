import unittest
import tempfile
import imghdr

from os.path import dirname
from os.path import join as pathjoin

from pprint import pprint

from six import BytesIO

from mobi import Mobi


PATH = dirname(__file__)


class BaseTestCase(unittest.TestCase):
    path = None

    def setUp(self):
        path = pathjoin(PATH, self.path)
        self.mobi = Mobi(path)

    def tearDown(self):
        self.mobi.close()


class ReadTest(object):
    def test_read(self):
        content = b''
        for i in range(1, 5):
            content += self.mobi.readRecord(i)
        self.assertLess(0, len(content))


class DarwinTestCase(BaseTestCase, ReadTest):
    path = "test/CharlesDarwin.mobi"

    def test_parse(self):
        self.assertIn('Mobi', self.mobi.config)
        self.assertIn('EXTH', self.mobi.config)
        self.assertIn('Palmdoc', self.mobi.config)

    def test_image(self):
        for record in range(2):
            bytes = self.mobi.readImageRecord(record)
            self.assertEqual('jpeg', imghdr.what('', h=bytes))

    def test_author_title(self):
        self.assertEqual('Charles Darwin', self.mobi.author)
        self.assertEqual(
            self.mobi.title,
            'The Origin of Species by means of Natural Selection, 6th Edition')


class MobiTestCase(BaseTestCase, ReadTest):
    path = "test/test.mobi"

    def test_read(self):
        import pdb; pdb.set_trace()
        super().test_read()


if __name__ == '__main__':
    unittest.main()
