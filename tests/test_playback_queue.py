import unittest
from commercial.playback_queue import (
    QueueState, create_queue, play, pause, next_track, previous_track,
    set_repeat, remove_track, reconcile_eligible,
)


class PlaybackQueueTests(unittest.TestCase):
    def test_empty_queue(self):
        state = play(create_queue([]))
        self.assertFalse(state.playing)
        self.assertIsNone(state.current)

    def test_play_pause_next(self):
        state = play(create_queue(["a", "b"]))
        self.assertEqual(state.current, "a")
        self.assertTrue(state.playing)
        state = next_track(state)
        self.assertEqual(state.current, "b")
        self.assertFalse(pause(state).playing)

    def test_end_stops(self):
        state = play(create_queue(["a"]))
        self.assertFalse(next_track(state).playing)

    def test_repeat_all(self):
        state = play(set_repeat(create_queue(["a", "b"]), "all"))
        self.assertEqual(next_track(next_track(state)).current, "a")
        self.assertEqual(previous_track(state).current, "b")

    def test_repeat_one(self):
        state = play(set_repeat(create_queue(["a", "b"]), "one"))
        self.assertEqual(next_track(state).current, "a")

    def test_duplicate_removed(self):
        self.assertEqual(create_queue(["a", "a", "b"]).track_ids, ("a", "b"))

    def test_remove_current(self):
        state = play(create_queue(["a", "b", "c"]))
        state = remove_track(state, "a")
        self.assertEqual(state.current, "b")

    def test_revocation_stops_playback(self):
        state = play(create_queue(["a", "b"]))
        state = reconcile_eligible(state, {"b"})
        self.assertEqual(state.current, "b")
        self.assertFalse(state.playing)

    def test_revocation_of_other_keeps_playing(self):
        state = play(create_queue(["a", "b"]))
        state = reconcile_eligible(state, {"a"})
        self.assertEqual(state.current, "a")
        self.assertTrue(state.playing)

    def test_invalid_input(self):
        with self.assertRaises(ValueError):
            create_queue([""])
        with self.assertRaises(ValueError):
            set_repeat(QueueState(), "random")

if __name__ == "__main__":
    unittest.main()
