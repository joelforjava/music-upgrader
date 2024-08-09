import unittest

from music_upgrader import tracks


class TracksTests(unittest.TestCase):
    def test_mp3_is_upgradable_to_alac(self):
        _o = "/Users/joel/Music/Music/Media.localized/Music/Meat Puppets/No Strings Attached/13 Bucket Head.mp3"
        _n = "/Users/joel/Music/ForFutureUse/No Strings Attached/13 - Bucket Head.m4a"
        self.assertTrue(tracks.is_upgradable(_o, _n))

    def test_alac_is_not_upgradable_to_mp3(self):
        _o = "/Users/joel/Music/ForFutureUse/No Strings Attached/13 - Bucket Head.m4a"
        _n = "/Users/joel/Music/Music/Media.localized/Music/Meat Puppets/No Strings Attached/13 Bucket Head.mp3"
        self.assertFalse(tracks.is_upgradable(_o, _n))

    def test_get_field_from_apple_music(self):
        persistent_id = "61A578F3A06A1801"
        track_year = tracks.get_year(persistent_id)
        self.assertEqual(track_year, 1990)

    def test_get_field_using_track_fields(self):
        n = "Lake of Fire"
        artist = "Meat Puppets"
        alb = "No Strings Attached"
        track_year = tracks._get_year_alt(n, artist, alb)
        self.assertEqual(track_year, 1990)

    def test_mp3_and_alac_of_same_track_are_considered_same_track(self):
        _o = "/Users/joel/Music/Music/Media.localized/Music/Meat Puppets/No Strings Attached/13 Bucket Head.mp3"
        _n = "/Users/joel/Music/ForFutureUse/No Strings Attached/13 - Bucket Head.m4a"
        self.assertTrue(tracks.is_same_track(_o, _n))


if __name__ == '__main__':
    unittest.main()
