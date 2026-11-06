# SPDX-License-Identifier: GPL-2.0-only
"""The shared fake AE-9 (sbae9kit.testing) on its own, without either app."""

import json
import math
import os
import subprocess
import sys
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sbae9kit import ae9, testing  # noqa: E402
from sbae9kit.testing import MIC, OPTICAL, SINK, WHAT_U_HEAR  # noqa: E402

MAPS = {2: ["FL", "FR"], 4: ["FL", "FR", "RL", "RR"]}


def wait_until(pred, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if pred():
            return True
        time.sleep(0.01)
    return pred()


class Rig(unittest.TestCase):
    def setUp(self):
        self._scale = testing.TIME_SCALE
        testing.TIME_SCALE = 0.04            # 5 s suspend wait -> 0.2 s
        self.pw = testing.FakePipeWire()
        self.Capture = testing.make_fake_capture(self.pw, MAPS, app_name="SbAe9-Test")

    def tearDown(self):
        testing.TIME_SCALE = self._scale

    def meter(self, name="sbae9-test.meter", passive=False, channels=2):
        return self.Capture(name, "Test meter", channels, passive)

    def port(self, node_name, port_name):
        return self.pw._port_id(f"{node_name}:{port_name}")

    def wire(self, src, src_ports, cap):
        for sp, ch in zip(src_ports, ("FL", "FR")):
            self.assertTrue(self.pw.pw_link(self.port(src, sp), self.port(cap.node_name, f"input_{ch}")))

    def peak_db(self, cap):
        time.sleep(0.02)
        peak, _, frames, _ = cap.take()
        if not frames:
            return None
        top = float(max(peak))
        return 20 * math.log10(top) if top > 0 else -math.inf


class Graph(Rig):
    def test_the_snapshot_card_with_its_extra_sources(self):
        names = {o["info"]["props"]["node.name"] for o in self.pw.objects.values() if o["type"].endswith("Node")}
        self.assertEqual(names, {SINK, MIC, WHAT_U_HEAR, OPTICAL})
        for n in (SINK, MIC, WHAT_U_HEAR, OPTICAL):
            self.assertTrue(ae9.is_ae9(self.pw.node(n)["info"]["props"]), n)
            self.assertEqual(self.pw.state(n), "suspended")
        self.assertEqual(ae9.input_kind(self.pw.node(WHAT_U_HEAR)["info"]["props"]), "what_u_hear")
        self.assertEqual(ae9.input_kind(self.pw.node(OPTICAL)["info"]["props"]), "optical_in")
        mic = self.pw.node(MIC)["info"]["props"]
        self.assertEqual(mic["node.description"], testing.MIC_DESC)   # the driver's head-unit name
        self.assertEqual(ae9.input_kind(mic), "mic")
        sink_ports = {p["info"]["props"]["port.name"]: p["info"]["props"]["port.monitor"]
                      for p in self.pw.ports(self.pw.node(SINK)["id"])}
        self.assertEqual(sink_ports, {"playback_FL": False, "playback_FR": False,
                                      "monitor_FL": True, "monitor_FR": True})

    def test_reads_like_pw_dump(self):
        v0 = self.pw.version
        dumped = json.loads(self.pw.run("pw-dump"))
        self.assertEqual({o["id"] for o in dumped}, set(self.pw.objects))
        self.pw.add_stream("Firefox", "YouTube")
        self.assertGreater(self.pw.version, v0)

    def test_card_drop_and_return(self):
        cap = self.meter()
        self.wire(SINK, ("monitor_FL", "monitor_FR"), cap)
        self.pw.card_present(False)
        self.assertIsNone(self.pw.node(SINK))
        self.assertEqual(self.pw.links(), [])          # its links went with it
        self.assertIsNotNone(self.pw.node(cap.node_name))
        self.pw.card_present(True)
        self.assertEqual(self.pw.state(SINK), "suspended")

    def test_the_apps_meters_are_not_the_card(self):
        cap = self.meter()
        self.assertFalse(ae9.is_ae9(self.pw.node(cap.node_name)["info"]["props"]))


class States(Rig):
    def test_playback_runs_the_sink_then_idle_then_suspended(self):
        sid = self.pw.add_stream("Firefox", "YouTube")
        self.assertEqual(self.pw.state(SINK), "running")
        self.assertEqual(len(self.pw.links_from("firefox")), 2)   # WirePlumber linked it
        self.pw.stop_stream(sid)
        self.assertEqual(self.pw.state(SINK), "idle")
        self.assertTrue(wait_until(lambda: self.pw.state(SINK) == "suspended"))

    def test_a_passive_meter_never_wakes_the_card(self):
        cap = self.meter(passive=True)
        self.wire(SINK, ("monitor_FL", "monitor_FR"), cap)
        self.assertEqual(self.pw.state(SINK), "suspended")
        self.assertIsNone(self.peak_db(cap))                       # no data while it sleeps

    def test_an_active_meter_keeps_it_running(self):
        cap = self.meter()
        self.wire(SINK, ("monitor_FL", "monitor_FR"), cap)
        self.assertEqual(self.pw.state(SINK), "running")
        self.assertEqual(self.peak_db(cap), -math.inf)             # running, but silent
        cap.stop()
        self.assertIsNone(self.pw.node(cap.node_name))
        self.assertEqual(self.pw.state(SINK), "idle")

    def test_capturing_a_source_runs_only_that_source(self):
        cap = self.meter()
        self.wire(WHAT_U_HEAR, ("capture_FL", "capture_FR"), cap)
        self.assertEqual(self.pw.state(WHAT_U_HEAR), "running")
        self.assertEqual(self.pw.state(SINK), "suspended")


class Levels(Rig):
    def test_what_u_hear_matches_the_output(self):
        out, wuh = self.meter("sbae9-test.out", passive=True), self.meter("sbae9-test.wuh")
        self.wire(SINK, ("monitor_FL", "monitor_FR"), out)
        self.wire(WHAT_U_HEAR, ("capture_FL", "capture_FR"), wuh)
        self.pw.add_stream("mpv", "tone", -20)
        self.assertAlmostEqual(self.peak_db(out), -20, places=3)
        self.assertAlmostEqual(self.peak_db(wuh), -20, places=3)       # level-exact, 0 dB

    def test_silent_restart(self):
        wuh = self.meter()
        self.wire(WHAT_U_HEAR, ("capture_FL", "capture_FR"), wuh)
        self.pw.silent_restart = True
        self.pw.add_stream("mpv", "tone", -20)
        self.assertEqual(self.peak_db(wuh), -math.inf)             # running, delivering silence

    def test_optical_sends_silence_when_dark(self):
        opt = self.meter()
        self.wire(OPTICAL, ("capture_FL", "capture_FR"), opt)
        self.assertEqual(self.peak_db(opt), -math.inf)
        self.pw.optical_db = -24
        self.assertAlmostEqual(self.peak_db(opt), -24, places=3)

    def test_mic_and_channel_mapping(self):
        mic = self.meter(channels=4)
        self.wire(MIC, ("capture_FL", "capture_FR"), mic)
        self.pw.mic_db = -35
        time.sleep(0.02)
        peak, sumsq, frames, _ = mic.take()
        self.assertGreater(frames, 0)
        self.assertEqual(len(peak), 4)
        self.assertAlmostEqual(20 * math.log10(peak[0]), -35, places=3)
        self.assertEqual(peak[2], 0.0)                             # RL / RR: nothing wired
        self.assertAlmostEqual(sumsq[0] / frames, peak[0] ** 2 / 2)   # a sine's mean power


class Commands(Rig):
    def test_pw_link_by_id_and_by_name(self):
        cap = self.meter()
        out = self.port(SINK, "monitor_FL")
        inp = self.port(cap.node_name, "input_FL")
        self.pw.run("pw-link", "--wait", str(out), str(inp))
        self.assertEqual(len(self.pw.links_from(SINK)), 1)
        self.pw.run("pw-link", "-d", f"{SINK}:monitor_FL", f"{cap.node_name}:input_FL")
        self.assertEqual(self.pw.links_from(SINK), [])
        self.pw.run("pw-link", f"{SINK}:monitor_FR", f"{cap.node_name}:input_FR")
        lid = self.pw.links_from(SINK)[0]["id"]
        self.pw.run("pw-link", "--disconnect", str(lid))
        self.assertEqual(self.pw.links_from(SINK), [])
        self.assertEqual([c[0] for c in self.pw.calls], ["link", "unlink", "link", "unlink"])

    def test_other_commands_are_recorded_or_handled(self):
        self.assertEqual(self.pw.run("wpctl", "get-volume", "@DEFAULT_SINK@"), "")
        self.assertIn(("wpctl", "get-volume", "@DEFAULT_SINK@"), self.pw.calls)
        self.pw.handle("wpctl", lambda *a: "Volume: 1.00\n")
        self.assertEqual(self.pw.run("wpctl", "get-volume", "@DEFAULT_SINK@"), "Volume: 1.00\n")

    def test_fake_linker(self):
        linker = testing.FakeLinker(lambda: self.pw)
        cap = self.meter()
        linker.link(self.port(SINK, "monitor_FL"), self.port(cap.node_name, "input_FL"))
        self.assertEqual(len(self.pw.links_from(SINK)), 1)
        linker.link(999999, 1)
        self.assertIn("no such port", linker.failures.get_nowait())
        linker.unlink(self.pw.links_from(SINK)[0]["id"])
        self.assertEqual(self.pw.links_from(SINK), [])


class Harness(unittest.TestCase):
    def test_isolate_and_block(self):
        saved = {k: os.environ.get(k) for k in ("XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_CACHE_HOME",
                                                  "XDG_DATA_HOME")}
        popen, run = subprocess.Popen, subprocess.run
        try:
            tmp = testing.isolate("sbae9-test")
            self.assertTrue(os.environ["XDG_STATE_HOME"].startswith(tmp))
            testing.block_subprocesses()
            with self.assertRaises(AssertionError):
                subprocess.run(["true"])
        finally:
            subprocess.Popen, subprocess.run = popen, run
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_time_scale(self):
        old = testing.TIME_SCALE
        try:
            testing.TIME_SCALE = 0.1
            self.assertAlmostEqual(testing.scaled(5), 0.5)
            self.assertAlmostEqual(testing.FakePipeWire(card=False).suspend_after, 0.5)
        finally:
            testing.TIME_SCALE = old


if __name__ == "__main__":
    unittest.main()
