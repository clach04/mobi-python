import unittest

from pprint import pprint

from mobi import Mobi


class MobiTests(unittest.TestCase):
    def setUp(self):
        self.mobitest = Mobi("test/CharlesDarwin.mobi")

    def test_parse(self):
        self.mobitest.parse()
        pprint(self.mobitest.config)

    def test_read(self):
        self.mobitest.parse()
        content = ""
        for i in range(1, 5):
            content += self.mobitest.readRecord(i)

    def test_image(self):
        self.mobitest.parse()
        pprint(self.mobitest.records)
        for record in range(4):
            f = open("imagerecord%d.jpg" % record, 'w')
            f.write(self.mobitest.readImageRecord(record))
            f.close()

    def test_author_title(self):
        self.mobitest.parse()
        self.assertEqual(self.mobitest.author(), 'Charles Darwin')
        self.assertEqual(
            self.mobitest.title(),
            'The Origin of Species by means of Natural Selection, 6th Edition')


if __name__ == '__main__':
    unittest.main()
