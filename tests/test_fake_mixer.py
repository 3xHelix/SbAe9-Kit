# SPDX-License-Identifier: GPL-2.0-only
"""sbae9kit.testing.mixer: the fake AE-9 ALSA mixer."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sbae9kit import mixer as alsa  # noqa: E402
from sbae9kit.testing.mixer import FakeMixer, load_controls  # noqa: E402


class FakeMixerTest(unittest.TestCase):
    def setUp(self):
        self.m = FakeMixer(0)

    def tearDown(self):
        self.m.close()

    def test_starts_from_the_real_snapshot(self):
        self.assertEqual(len(self.m.controls), len(load_controls()))
        self.assertTrue(self.m.has("Direct Mode Switch"))
        self.assertIs(FakeMixer.last, self.m)

    def test_writes_are_logged_and_come_back_as_events(self):
        self.m.set("Head Unit Output", "Headphones")
        self.assertEqual(self.m.get("Head Unit Output"), 1)
        self.assertEqual(self.m.writes, [("Head Unit Output", 1)])
        ev = self.m.read_events()
        self.assertEqual(ev, [(self.m.controls["Head Unit Output"].numid, alsa.EVENT_MASK_VALUE)])
        self.assertEqual(self.m.read_events(), [])

    def test_outside_changes_are_events_but_not_writes(self):
        self.m.external("Master Playback Volume", 120)
        self.assertEqual(self.m.writes, [])
        self.assertEqual(len(self.m.read_events()), 1)

    def test_inactive_controls_keep_their_value_and_send_info(self):
        self.m.set_inactive("SBX Switch")
        c = self.m.refresh_info(self.m.controls["SBX Switch"].numid)
        self.assertTrue(c.inactive)
        self.m.set("SBX Switch", True)                 # still writable, like the real card
        self.assertTrue(self.m.get("SBX Switch"))
        masks = [mask for _, mask in self.m.read_events()]
        self.assertEqual(masks, [alsa.EVENT_MASK_INFO, alsa.EVENT_MASK_VALUE])

    def test_controls_newer_drivers_add(self):
        self.m.add_bool("Optical Out Playback Switch", True)
        self.m.add_bool("Head Unit Phones Plugged", False, writable=False)
        self.m.add_enum("Capture Bit Depth", ["24-bit", "32-bit"])
        self.assertFalse(self.m.controls["Head Unit Phones Plugged"].writable)
        self.m.set("Capture Bit Depth", "32-bit")
        self.assertEqual(self.m.get("Capture Bit Depth"), 1)
        self.m.remove("Optical Out Playback Switch")
        self.assertFalse(self.m.has("Optical Out Playback Switch"))


if __name__ == "__main__":
    unittest.main()
