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

    def test_output_kinds(self):
        self.assertEqual(ae9.output_kind({"node.name": "alsa_output.pci-0000_06_00.0.analog-stereo"}), "main")
        self.assertEqual(ae9.output_kind({"node.name": "alsa_output.pci-0000_06_00.0.analog-surround-51"}), "main")
        self.assertEqual(ae9.output_kind({"node.name": "alsa_output.pci-0000_06_00.0.optical_out"}), "optical_out")
        self.assertEqual(ae9.output_kind({"node.name": "alsa_output.ae9_optical"}), "optical_out")
        self.assertEqual(ae9.output_kind({"node.name": "x", "api.alsa.path": "hw:AE9,4"}), "optical_out")
        self.assertEqual(ae9.output_kind({"node.name": "x", "node.description": "AE-9 Optical Out"}), "optical_out")

    def test_versions_and_hw_params(self):
        self.assertTrue(ae9.driver_at_least(0, 9, 1, version="0.9.2"))
        self.assertFalse(ae9.driver_at_least(0, 9, 1, version="0.8.0"))
        self.assertFalse(ae9.driver_at_least(0, 1, version="junk"))
        self.assertEqual(ae9.parse_hw_params("access: RW\nformat: S32_LE\nchannels: 6\nrate: 48000 (48000/1)\n"),
                         (48000, 6))
        self.assertIsNone(ae9.parse_hw_params("closed\n"))

    def test_reload_notice(self):
        from sbae9kit import testing
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        path = os.path.join(tmp, "ae9-reload")
        self.assertFalse(ae9.reload_notice_active(path))                 # no notice
        testing.write_reload_notice(path)                                 # this PID: alive
        self.assertTrue(ae9.reload_notice_active(path))
        testing.write_reload_notice(path, pid=testing.dead_pid())         # stale
        self.assertFalse(ae9.reload_notice_active(path))
        testing.write_reload_notice(path, pid="")                         # empty: counts by mtime
        self.assertTrue(ae9.reload_notice_active(path))
        mtime = os.stat(path).st_mtime
        self.assertFalse(ae9.reload_notice_active(path, now=mtime + ae9.RELOAD_NOTICE_MAX_S))
        testing.write_reload_notice(path, pid="", age_s=ae9.RELOAD_NOTICE_MAX_S + 1)
        self.assertFalse(ae9.reload_notice_active(path))
        with open(path, "w") as f:
            f.write("junk\n")                                             # unreadable: like empty
        self.assertTrue(ae9.reload_notice_active(path))
        os.remove(path)
        self.assertFalse(ae9.reload_notice_active(path))

        old = os.environ.get("XDG_RUNTIME_DIR")
        self.addCleanup(lambda: os.environ.__setitem__("XDG_RUNTIME_DIR", old) if old is not None
                        else os.environ.pop("XDG_RUNTIME_DIR", None))
        os.environ["XDG_RUNTIME_DIR"] = tmp
        self.assertEqual(ae9.reload_notice_path(), path)
        os.environ.pop("XDG_RUNTIME_DIR")
        self.assertEqual(ae9.reload_notice_path(), f"/run/user/{os.getuid()}/ae9-reload")


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


class BoardsTest(unittest.TestCase):
    """Card detection (sbae9kit.boards, used through ae9) on fake sound trees."""

    def setUp(self):
        from sbae9kit import boards, testing
        self.boards, self.t = boards, testing
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        old = boards.ROOT
        self.addCleanup(lambda: (setattr(boards, "ROOT", old), boards.refresh()))

    def tree(self, *cards):
        return self.t.fake_sound_tree(self.tmp, cards)

    def test_the_ae9_as_on_the_real_machine(self):
        t = self.t
        self.tree(t.HDMI_CARD, t.USB_CARD, t.AE9_CARD)
        (c,) = ae9.find_cards()
        self.assertEqual((c.index, c.id, c.short, c.name, c.key, c.subsystem, c.source),
                         (2, "AE9", "AE-9", "Sound Blaster AE-9", "ae9", 0x0071, "card_id"))
        self.assertIn("Sound Blaster AE-9", c.longname)
        self.assertEqual(c.hw(4), "hw:AE9,4")
        self.assertTrue(c.proc.endswith("/proc/asound/AE9"))
        self.assertTrue(c.has_pcm("4p") and c.has_pcm("1c"))
        self.assertFalse(c.has_pcm("5p"))
        self.assertTrue(ae9.has_capture_pcm(1) and ae9.has_capture_pcm(3))   # the fake tree, not the host
        self.assertFalse(ae9.has_capture_pcm(1, card_id="AE7"))
        hw = os.path.join(c.proc, "pcm0p", "sub0")
        os.makedirs(hw)
        with open(os.path.join(hw, "hw_params"), "w") as f:
            f.write("channels: 2\nrate: 96000 (96000/1)\n")
        self.assertEqual(ae9.pcm_open_at("pcm0p"), (96000, 2))
        self.assertTrue(c.has("head_unit"))
        self.assertEqual(str(c.model), "AE-9")
        self.assertIs(ae9.current(), ae9.current())          # cached
        self.assertEqual(ae9.card_id(), "AE9")

    def test_the_ae7(self):
        self.tree(self.t.AE7_CARD)
        c = ae9.current()
        self.assertEqual((c.id, c.short, c.index), ("AE7", "AE-7", 0))
        self.assertTrue(c.model.provisional)
        self.assertFalse(c.has("head_unit") or c.has("optical_in") or c.has("direct_51"))
        self.assertEqual(c.features["hp_gain"], "software")
        self.assertEqual(c.features["optical_out_max"], 96000)
        self.assertFalse(c.has_pcm("1c"))                     # no optical in
        self.assertEqual(ae9.card_id(), "AE7")

    def test_never_a_card_on_another_driver(self):
        t = self.t
        self.tree(t.HDMI_CARD, t.AE7_INTREE, t.USB_CARD)
        self.assertEqual(ae9.find_cards(), [])
        self.assertIsNone(ae9.current())
        self.assertEqual(ae9.card_id(), "AE9")                # as before detection
        intree = {"node.name": "alsa_output.pci-0000_07_00.0.analog-stereo",
                  "alsa.driver_name": "snd_hda_intel", "alsa.card_name": "Sound Blaster AE-7",
                  "api.alsa.path": "hw:AE7,0"}
        self.assertFalse(ae9.is_our_card(intree))

    def test_no_cards_at_all(self):
        self.tree()
        self.assertEqual(ae9.find_cards(), [])
        self.assertEqual(ae9.card_id(), "AE9")

    def test_two_cards_first_by_index_or_the_pick(self):
        t = self.t
        self.tree(t.AE7_CARD, t.HDMI_CARD, t.AE9_CARD)
        self.assertEqual([c.id for c in ae9.find_cards()], ["AE7", "AE9"])
        self.assertEqual(ae9.find_card().id, "AE7")
        self.assertEqual(ae9.find_card(prefer="ae9").id, "AE9")
        self.assertEqual(ae9.find_card(prefer="AE9").index, 2)
        self.assertEqual(ae9.find_card(prefer="gone").id, "AE7")

    def test_detection_order(self):
        t = self.t
        renamed = ("MyCard",) + t.AE7_CARD[1:]                # id doesn't say: the name does
        self.tree(renamed)
        self.assertEqual((ae9.current().short, ae9.current().source), ("AE-7", "longname"))
        bare = ("X",) + ("HD-Audio", "HD-Audio at 0x0") + t.AE9_CARD[3:]   # only subsys says
        self.tree(bare)
        self.assertEqual((ae9.current().short, ae9.current().source), ("AE-9", "subsys"))
        self.assertEqual(ae9.current().id, "X")
        # a future "Card Model" control comes first
        self.assertEqual(ae9.find_cards(card_model={0: "Sound Blaster AE-7"})[0].source, "card_model")
        self.assertEqual(ae9.identify("AE9", "Sound Blaster AE-7", 0x0081), (ae9.MODELS["ae9"], "card_id"))

    def test_the_ae5_is_reserved(self):
        self.tree(self.t.AE5_CARD)
        self.assertEqual(ae9.find_cards(), [])
        (c,) = ae9.find_cards(supported_only=False)
        self.assertEqual((c.short, c.model.supported), ("AE-5", False))
        self.assertTrue(c.model.provisional and c.has("lighting"))
        self.assertFalse(c.has("dsd"))
        self.assertEqual(c.model.pci_devices, (0x0012,))
        self.assertEqual(ae9.MODELS["ae9"].pci_devices, (0x0010, 0x0012))

    def test_model_wording(self):
        ae9_, ae7, ae5 = (ae9.MODELS[k] for k in ("ae9", "ae7", "ae5"))
        self.assertEqual([m.has("lighting") for m in (ae9_, ae7, ae5)], [False, False, True])
        self.assertEqual([m.has("encoder") for m in (ae9_, ae7, ae5)], [True, True, False])
        self.assertEqual([m.has("input_select") for m in (ae9_, ae7, ae5)], [False, True, True])
        self.assertTrue(ae9_.has("aux_in") and ae5.has("front_mic") and not ae7.has("front_mic"))
        self.assertEqual(len(ae7.features["dac_filter_names"]), ae7.features["dac_filters"])
        self.assertEqual(ae7.features["hp_gain_names"][1], "Normal (32 - 149 ohm)")
        self.assertEqual(ae5.features["optical_out_max"], 96000)
        for m in ae9.MODELS.values():    # every model words every feature
            self.assertTrue({"lighting", "encoder", "aux_in", "line_in", "input_select",
                             "front_mic", "optical_out_max", "dac_filters"} <= set(m.features))

    def test_pipewire_nodes_of_our_cards(self):
        ae7 = {"node.name": "alsa_output.pci-0000_07_00.0.analog-stereo", "alsa.id": "AE7",
               "alsa.driver_name": "snd_hda_codec_creative_ae9", "api.alsa.path": "hw:AE7,0", "alsa.card": 0}
        self.assertTrue(ae9.is_our_card(ae7) and ae9.is_ae9(ae7))
        self.tree(self.t.AE7_CARD, self.t.AE9_CARD)
        ae7c, ae9c = ae9.find_cards()
        self.assertTrue(ae9.is_our_card(ae7, ae7c))
        self.assertFalse(ae9.is_our_card(ae7, ae9c))
        self.assertTrue(ae9.is_our_card(SINK | {"alsa.id": "AE9"}, ae9c))
        dropin = {"node.name": "alsa_input.ae7_optical", "api.alsa.path": "hw:AE7,1"}
        self.assertTrue(ae9.is_our_card(dropin, ae7c))
        self.assertEqual(ae9.input_kind({"node.name": "x", "api.alsa.path": "hw:AE7,2"}), "what_u_hear")
        self.assertEqual(ae9.output_kind({"node.name": "x", "api.alsa.path": "hw:AE7,4"}), "optical_out")
        self.assertEqual(ae9.output_kind({"node.name": "x", "api.alsa.path": "hw:HDMI,4"}), "main")
        # PipeWire's paths are numeric (hw:2,4): they count only with our driver
        ours = {"node.name": "x", "api.alsa.path": "hw:2,4", "alsa.driver_name": "snd_hda_codec_creative_ae9"}
        self.assertEqual(ae9.output_kind(ours), "optical_out")
        self.assertEqual(ae9.output_kind(ours | {"alsa.driver_name": "snd_hda_intel"}), "main")
        self.assertEqual(ae9.input_kind(ours | {"api.alsa.path": "hw:2,1"}), "optical_in")
        self.assertEqual((ae7c.index, ae9c.index), (0, 1))
        self.assertTrue(ae9.is_our_card(ours | {"api.alsa.path": "hw:1,4"}, ae9c))
        self.assertFalse(ae9.is_our_card(ours | {"api.alsa.path": "hw:1,4"}, ae7c))
        self.assertFalse(ae9.is_our_card(ours, ae9c))          # hw:2: neither card


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
