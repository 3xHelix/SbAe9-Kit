# Changelog

SbAe9-Kit: the shared base of SbAe9-SBC and SbAe9-AudioMon.

## 0.3.11 (2026-11-21)

- `MODELS` wording from Creative's Sound Blaster Command support notes
  (via SBC): the AE-9 has no Lighting page (`lighting` False; only the AE-5
  has one). New features `encoder` (AE-9, AE-7; not the plain AE-5),
  `aux_in` (AE-9), `line_in`, `input_select` (AE-7, AE-5), `front_mic`
  (AE-5), `hp_gain_names` (AE-7, AE-5: Low / Normal / High) and
  `dac_filter_names` (AE-7; a DAC Filter control's own items always win).
  The AE-5's `optical_out_max` is 96000.

## 0.3.10 (2026-11-20)

- Multi-card groundwork (AE-9 now, AE-7 later), one detection for both apps.
  New `sbae9kit.boards`, used through `ae9`: `find_cards()`, `find_card(prefer=)`,
  `current()` / `refresh()` (cached), `card_id()` ("AE9" when nothing is found,
  so an AE-9 machine behaves as before). Only cards bound to
  snd-hda-codec-creative-ae9 count, never the in-tree snd_hda_intel. Each card
  is identified by its ALSA id, else its long/short name, else its PCI
  subsystem (0x0071 AE-9, 0x0081 AE-7, 0x0051 / 0x0191 AE-5, reserved). A
  future "Card Model" control can come first (`card_model=`).
- `Card`: index, id, model, longname, subsystem, source; `hw(dev)`, `proc`,
  `has_pcm("4p")`, and short / name / key / features from its `Model`.
  `MODELS`: AE-9, AE-7 (provisional) and AE-5 (reserved, provisional) with name, short, pci_devices,
  key, node_prefix and wording-level features (head_unit, optical_in,
  direct_51, dsd, hp_gain, dsp_51_analog, optical_out_max, dac_filters,
  lighting). The controls and PCMs decide what a card can do; the features
  only word it.
- `ae9.is_our_card(props, card=None)`: a PipeWire node of any of our cards
  (or of `card`). A node from another driver never counts. `is_ae9` is now
  an alias. `input_kind` / `output_kind` know `hw:AE7,N` too, and
  PipeWire's numeric `hw:<index>,N` when the node's driver is ours.
  `has_capture_pcm` / `pcm_open_at` default to the detected card, and read
  under the same root as `Card.proc` (a fake tree in tests).
- `testing.fake_sound_tree(root, cards)` with `AE9_CARD`, `AE7_CARD`,
  `AE7_INTREE`, `AE5_CARD`, `HDMI_CARD` and `USB_CARD`: fake /sys and /proc
  for detection tests.

## 0.3.9 (2026-11-18)

- `ae9.reload_notice_path()` / `ae9.reload_notice_active()`: driver
  0.12.13's ae9-reload notice, shared instead of written twice (SBC's
  `card.py`, AudioMon's `driverstate.py`). `$XDG_RUNTIME_DIR/ae9-reload` (or
  `/run/user/<uid>/ae9-reload`) holds a PID; it counts while that PID is
  alive in /proc. An empty or unreadable notice counts for
  `RELOAD_NOTICE_MAX_S` (120 s) by its mtime, then is ignored. Plain
  functions, no Qt, no state, read-only (fine for listen-only apps).
- `testing.write_reload_notice(path, pid=None, age_s=0)` and
  `testing.dead_pid()`: a fake notice (live, stale, empty or back-dated).

## 0.3.8 (2026-11-08)

- `ae9.output_kind()`: tells the AE-9's separate optical output (driver
  0.12.0, hw:AE9,4: `alsa_output.pci-<addr>.optical_out`, or the old
  drop-in's `alsa_output.ae9_optical`) from the main output, so an app
  never takes the optical sink for its speakers / headphones.
- `Mixer.get_iec958()` / `set_iec958()`: an IEC958 control's 24 channel-status
  bytes (driver 0.12.0's "IEC958 Playback Default" on the optical output:
  AES0 bit 1 = non-audio passthrough). `TYPE_IEC958`; the fake mixer has
  them too, with `add_iec958()`.
- `testing.FakePipeWire(optical_out=True)`: the fake card gets driver
  0.12.0's Optical Out sink (`testing.OPTICAL_OUT`, hw:AE9,4), off by
  default. It comes before the main sink in pw-dump, so a test catches an
  app that takes the first AE-9 sink for its output.

## 0.3.7 (2026-11-08)

- The fake AE-9's "DAC Filter" follows driver 0.11.0: the seven ES9038Q2M
  filters with the Creative app's names, Apodizing Fast Roll Off (Windows'
  startup filter, the default) first. Was Default / Fast / Slow.

## 0.3.6 (2026-11-07)

- `ae9` knows driver 0.10.1's Rear RCA In (the head unit's rear RCA jacks,
  hw:AE9,3, node `alsa_input.ae9_rear_rca` from config/ae9-rear-rca-in.conf):
  `EXTRA_INPUTS["rear_rca"]`, and `input_kind` returns "rear_rca" for it.
  Before, it was taken for the mic.
- The fake AE-9 can add Rear RCA In (`FakePipeWire(rear_rca=True)`, level
  `rear_rca_db`, `testing.REAR_RCA`). It's off by default.

## 0.3.5 (2026-11-06)

- `ae9.is_ae9` skips virtual nodes (`node.virtual`): echo-cancel,
  filter-chain and loopback nodes named after the card (the driver's
  WebRTC voice config makes "ae9_voice" / "ae9_voice_ref") were taken for
  the card's own sink and mic.

## 0.3.4 (2026-11-06)

- `testing.mixer` and the kit's tests use the driver's new jack names: the
  head unit's plug switches are "Head Unit 3.5mm Phones Plugged" and
  "Head Unit 3.5mm Mic Plugged", and the mic's desktop name is
  "AE-9 Head Unit Mic / Aux". (The 0.6.8 control snapshot has no plug
  switches, so it's unchanged.)

## 0.3.3 (2026-11-06)

- `testing`: the fake card names the head unit's input as the driver's
  desktop names do: "AE-9 Head Unit Mic / Aux" (the XLR/TRS and 3.5 mm mic
  jacks share it; it was "Mic / Line In"). Node names are unchanged.
  `testing.MIC_DESC` holds it.

## 0.3.2 (2026-11-06)

- `testing`: What U Hear now plays the output back at the same level (0 dB).
  The earlier -3.1 dB was a misreading: a -20 dBFS-peak sine's RMS is -23 dB.
  The driver confirms What U Hear is level-exact, and AudioMon measured
  within 0.1-0.3 dB of the output on the real card.
- `testing`: the Optical In notes now say what really happens with no light:
  the driver refuses the capture and PipeWire's node carries on with silence.

## 0.3.1 (2026-11-06)

- `palettes`: each palette has its own `METER_ZONES` (normal, high, over).
  Albino's came from its coral meter gradient, so all three were nearly the
  same shade and a normal level already looked like a warning; it now uses
  its green, gold and a deeper red. Command, Helix and Wololo keep the same
  colours as before. Spotted by SbAe9-AudioMon on its meters.

## 0.3.0 (2026-11-06)

- `testing.mixer`: SBC's fake ALSA mixer for control apps' tests, from a
  snapshot of the real card's controls (`testing/fixtures/ae9_controls.json`,
  driver 0.6.8). Writes come back as change events like the real card's, and
  changes "from elsewhere" (the knob, alsamixer) arrive the same way.
  - New: controls can be greyed out (`set_inactive`): they keep their
    value, still write, and send an INFO event, the way the driver greys
    the effects out with SBX off.
  - `add_bool` / `add_enum` for controls newer drivers have (read-only ones
    too), `set_items`, `remove`.
  - It imports `sbae9kit.mixer`, so listen-only apps leave it alone.

## 0.2.0 (2026-11-06)

- `testing`: the fake AE-9 both apps test against, from SbAe9-AudioMon's rig.
  - A fake PipeWire graph built from the real-machine snapshot (now in
    `testing/fixtures/`), with ports and links in pw-dump's format.
  - Running / idle / suspended states that honour `node.passive`.
  - What U Hear following the output (3.1 dB lower until 0.3.2), and a silent-restart
    switch to fake the bug.
  - Optical In sending digital silence when dark, as the real card does.
  - The card dropping off and coming back.
  - A `run()` dispatcher for PipeWire commands (`pw-dump`, `pw-link` built
    in, others via `handle()`), a fake `pw-link` worker and fake `pw-record`
    meters.
  - Harness helpers: `isolate()` (temp XDG folders), `block_subprocesses()`
    and one `TIME_SCALE` for every modelled wait.
  - Room for SBC's fake ALSA mixer as `testing/mixer.py`.

## 0.1.0 (2026-11-06)

First cut, pulled together from the two apps.

- `ae9`: one AE-9 detection for both apps (SBC's card-name check and
  AudioMon's node-name / ALSA path / object path check, merged; the apps'
  own `sbae9-*` nodes never count), input kinds, driver version and options,
  hw_params readers.
- `mixer`: SBC's ctypes ALSA binding.
- `palettes`, `glass`, `desktop`, `frame`: SBC's palettes, Glass, UI scale,
  XWayland choice, WM_CLASS fix, relaunch (now with a hook to run first) and
  frameless window parts, made app-neutral.
- `tools/sync_kit.py` and the vendored-copy check; `tools/make_icons.py`
  for any app id.
