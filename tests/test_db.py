import unittest

import pytest

from music_upgrader.db import regexify

@pytest.mark.parametrize(
    "start_value,expected_result",
    [
        ("Hey, That's Right!", "[Hh]ey.? [Tt]hat.?s [Rr]ight.?"),
        ("Zero [Explicit Version]", "[Zz]ero .?Explicit [Vv]ersion.?"),
        ("Now You've Got Something to Die For [Explicit]", "[Nn]ow [Yy]ou.?ve [Gg]ot [Ss]omething [Tt]o [Dd]ie [Ff]or .?Explicit.?"),
        ("Forgotten (Lost Angels) (Album Version)", "[Ff]orgotten .?Lost [Aa]ngels.? .?Album [Vv]ersion.?"),
        ("Bullet With Butterfly Wings", "[Bb]ullet [Ww]ith [Bb]utterfly [Ww]ings"),
        ("everybody wants to rule the world", "[Ee]verybody [Ww]ants [Tt]o [Rr]ule [Tt]he [Ww]orld"),
    ],
)
def test_regexify_replaces_data_as_expected(start_value, expected_result):
    assert regexify(start_value) == expected_result


class MyRegexifyTests(unittest.TestCase):
    def xtest_something(self):
        self.assertEqual(True, False)  # add assertion here


if __name__ == '__main__':
    unittest.main()
