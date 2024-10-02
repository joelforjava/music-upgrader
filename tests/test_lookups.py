import re
import string
import unittest


class StringReplacementTests(unittest.TestCase):
    def test_string_translate(self):
        track_name = "Hey, That's Right!"
        converted = track_name.translate(str.maketrans("", "", string.punctuation))
        expected = "Hey Thats Right"
        self.assertEqual(expected, converted)

    def test_re(self):
        track_name = "Hey, That's Right!"
        regex = re.compile("[%s]" % re.escape(string.punctuation))
        converted = regex.sub(".?", track_name)
        expected = "Hey.? That.?s Right.?"
        self.assertEqual(expected, converted)


if __name__ == "__main__":
    unittest.main()
