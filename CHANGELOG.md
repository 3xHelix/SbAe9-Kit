# Changelog

SbAe9-Kit: the shared base of SbAe9-SBC and SbAe9-AudioMon.

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
  - What U Hear following the output 3.1 dB lower, and a silent-restart
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
