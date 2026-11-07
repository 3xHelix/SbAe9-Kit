# SPDX-License-Identifier: GPL-2.0-only
"""The kit on its own: AE-9 detection, desktop plumbing, Glass, palettes,
and the vendoring check. Run: python3 -m unittest discover -s tests"""

import os
import shutil
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from sbae9kit import ae9, desktop, glass, palettes, vendor  # noqa: E402

SINK = {"node.name": "alsa_output.pci-0000_06_00.0.analog-stereo", "media.class": "Audio/Sink",
        "alsa.card_name": "Sound Blaster AE-9", "api.alsa.path": "hw:3,0"}
MIC = {"node.name": "alsa_input.pci-0000_06_00.0.analog-stereo", "alsa.card_name": "Sound Blaster AE-9",
       "node.description": "AE-9 Head Unit Mic / Aux", "api.alsa.path": "hw:3,0"}
OPTICAL = {"node.name": "alsa_input.ae9_optical", "api.alsa.path": "hw:AE9,1",
           "node.description": "AE-9 Optical In"}
WUH = {"node.name": "alsa_input.ae9_what_u_hear", "api.alsa.path": "hw:AE9,2",
       "node.description": "AE-9 What U Hear"}
OTHER = {"node.name": "alsa_output.usb-Burr-Brown_from_TI_USB_Audio_CODEC-00.analog-stereo",
         "alsa.card_name": "USB Audio CODEC", "api.alsa.path": "hw:1"}
METER = {"node.name": "sbae9-audiomon.ae9.monitor", "media.class": "Stream/Input/Audio"}


class Ae9Test(unittest.TestCase):
    def test_finds_the_card_by_name_never_by_pci(self):
        for props in (SINK, MIC, OPTICAL, WUH, {"alsa.driver_name": "snd_hda_codec_creative_ae9"},
                      {"object.path": "alsa:pcm:AE9:0:playback"}, {"alsa.id": "AE9"}):
            self.assertTrue(ae9.is_ae9(props), props)
        self.assertFalse(ae9.is_ae9(OTHER))
        self.assertFalse(ae9.is_ae9({"api.alsa.path": "hw:3,0", "node.name": "alsa_output.pci-0000_06_00.0"}))

    def test_the_apps_own_nodes_are_not_the_card(self):
        self.assertFalse(ae9.is_ae9(METER))

    def test_virtual_nodes_named_after_the_card_are_not_the_card(self):
        # the driver's WebRTC voice config: an echo-cancel pair named "AE-9 Voice ..."
        voice = {"node.name": "ae9_voice", "node.description": "AE-9 Voice (WebRTC)",
                 "media.class": "Audio/Source", "node.virtual": True}
        ref = {"node.name": "ae9_voice_ref", "media.class": "Audio/Sink", "node.virtual": "true"}
        self.assertFalse(ae9.is_ae9(voice))
        self.assertFalse(ae9.is_ae9(ref))
        self.assertTrue(ae9.is_ae9(dict(SINK, **{"node.virtual": False})))

    def test_input_kinds(self):
        self.assertEqual(ae9.input_kind(MIC), "mic")
        self.assertEqual(ae9.input_kind(OPTICAL), "optical_in")
        self.assertEqual(ae9.input_kind(WUH), "what_u_hear")
        self.assertEqual(ae9.input_kind({"node.name": "x", "api.alsa.path": "hw:AE9,2"}), "what_u_hear")
        self.assertEqual(ae9.input_kind({"node.name": "alsa_input.ae9_rear_rca"}), "rear_rca")
        self.assertEqual(ae9.input_kind({"node.name": "x", "api.alsa.path": "hw:AE9,3"}), "rear_rca")
        self.assertEqual(ae9.input_kind({"node.name": "x", "node.description": "AE-9 Rear RCA In"}), "rear_rca")
        self.assertEqual(ae9.input_kind({"node.name": "alsa_input.foo.iec958-stereo"}), "optical_in")

    def test_versions_and_hw_params(self):
        self.assertTrue(ae9.driver_at_least(0, 9, 1, version="0.9.2"))
        self.assertFalse(ae9.driver_at_least(0, 9, 1, version="0.8.0"))
        self.assertFalse(ae9.driver_at_least(0, 1, version="junk"))
        self.assertEqual(ae9.parse_hw_params("access: RW\nformat: S32_LE\nchannels: 6\nrate: 48000 (48000/1)\n"),
                         (48000, 6))
        self.assertIsNone(ae9.parse_hw_params("closed\n"))


class DesktopTest(unittest.TestCase):
    def test_scale_does_not_stack_over_relaunches(self):
        env = {}
        self.assertEqual(desktop.set_scale("sbae9-sbc", 80, env), 80)
        desktop.set_scale("sbae9-sbc", 80, env)
        self.assertEqual(env["QT_SCALE_FACTOR"], "0.8")
        self.assertIn("SBAE9_SBC_BASE_SCALE_FACTOR", env)
        desktop.set_scale("sbae9-sbc", 100, env)
        self.assertNotIn("QT_SCALE_FACTOR", env)
        env = {"QT_SCALE_FACTOR": "2"}
        desktop.set_scale("sbae9-audiomon", 50, env)
        desktop.set_scale("sbae9-audiomon", 100, env)
        self.assertEqual(env["QT_SCALE_FACTOR"], "2")

    def test_xwayland_choice(self):
        env = {"WAYLAND_DISPLAY": "wayland-1", "DISPLAY": ":0"}
        self.assertTrue(desktop.use_xwayland("sbae9-sbc", True, env, xcb_ok=True))
        self.assertEqual(env["QT_QPA_PLATFORM"], "xcb")
        desktop.use_xwayland("sbae9-sbc", False, env, xcb_ok=True)
        self.assertNotIn("QT_QPA_PLATFORM", env)
        env = {"WAYLAND_DISPLAY": "w", "DISPLAY": ":0", "QT_QPA_PLATFORM": "wayland"}
        desktop.use_xwayland("sbae9-sbc", True, env, xcb_ok=True)
        self.assertEqual(env["QT_QPA_PLATFORM"], "wayland")
        self.assertFalse(desktop.use_xwayland("x", True, {"WAYLAND_DISPLAY": "w"}, xcb_ok=True))
        self.assertFalse(desktop.use_xwayland("x", True, {"DISPLAY": ":0"}, xcb_ok=True))

    def test_qt_argv_and_relaunch_args(self):
        self.assertEqual(desktop.qt_argv("sbae9-audiomon", ["-style", "x"]), ["sbae9-audiomon", "-style", "x"])
        argv = ["-c", "code", "/here", "--scale", "80", "--palette", "helix", "--scale=90", "--glass", "--ae9"]
        self.assertEqual(desktop.relaunch_args(argv, drop=("--scale", "--glass")),
                         ["-c", "code", "/here", "--palette", "helix", "--ae9"])

    def test_app_icon(self):
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])
        d = tempfile.mkdtemp()
        try:
            from PySide6.QtGui import QImage
            for s in (16, 32):
                QImage(s, s, QImage.Format_ARGB32).save(os.path.join(d, f"myapp-{s}.png"))
            self.assertEqual(sorted(x.width() for x in desktop.app_icon(d, "myapp").availableSizes()), [16, 32])
            self.assertTrue(desktop.app_icon("/nonexistent", "myapp").isNull())
        finally:
            shutil.rmtree(d)


class GlassPaletteTest(unittest.TestCase):
    def test_glass(self):
        self.assertEqual(glass.clamp(5), 30)
        self.assertEqual(glass.clamp(97), 95)
        self.assertEqual(glass.clamp("x"), 70)
        self.assertEqual(glass.surface("#102030", False, 0.7), "#102030")
        self.assertEqual(glass.surface("#102030", True, 0.7), "rgba(16,32,48,0.7)")
        self.assertEqual(glass.surface("#102030", True, 0.7, 0.85), "rgba(16,32,48,0.595)")

    def test_palettes(self):
        self.assertEqual(list(palettes.PALETTES), ["command", "helix", "albino", "wololo"])
        keys = set(palettes.PALETTES["command"])
        for name, p in palettes.PALETTES.items():
            self.assertEqual(set(p), keys, name)          # every palette has every colour
            zones = palettes.meter_zones(name)
            self.assertEqual(len(set(zones)), 3, name)
            hues = [__import__("colorsys").rgb_to_hsv(*(int(z[i:i + 2], 16) / 255 for i in (1, 3, 5)))[0]
                    for z in zones]
            # normal, high and over are different colours, not shades of one
            for a, b in ((0, 1), (1, 2), (0, 2)):
                d = abs(hues[a] - hues[b])
                self.assertGreater(min(d, 1 - d), 0.05, f"{name} zones {a},{b}")
        self.assertIs(palettes.get("nope"), palettes.PALETTES["command"])


class VendorTest(unittest.TestCase):
    def test_sync_and_verify(self):
        import subprocess
        app = tempfile.mkdtemp()
        try:
            r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "sync_kit.py"), app],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            kit = os.path.join(app, "sbae9kit")
            self.assertEqual(vendor.verify(kit), [])
            with open(os.path.join(kit, "glass.py"), "a") as f:
                f.write("# local tweak\n")
            self.assertTrue(any("glass.py" in p for p in vendor.verify(kit)))
        finally:
            shutil.rmtree(app)

    def test_sub_folders_and_data_files_come_along(self):
        import subprocess
        sub = os.path.join(ROOT, "sbae9kit", "_probe")
        app = tempfile.mkdtemp()
        os.makedirs(os.path.join(sub, "fixtures"))
        try:
            for rel, text in (("__init__.py", ""), ("fixtures/x.json", "{}")):
                with open(os.path.join(sub, rel), "w") as f:
                    f.write(text)
            r = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "sync_kit.py"), app],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            kit = os.path.join(app, "sbae9kit")
            self.assertTrue(os.path.exists(os.path.join(kit, "_probe", "fixtures", "x.json")))
            self.assertIn("_probe/fixtures/x.json", vendor.read_manifest(kit))
            self.assertEqual(vendor.verify(kit), [])
            os.remove(os.path.join(kit, "_probe", "fixtures", "x.json"))
            self.assertTrue(any("missing" in p for p in vendor.verify(kit)))
        finally:
            shutil.rmtree(sub)
            shutil.rmtree(app)


if __name__ == "__main__":
    unittest.main()
