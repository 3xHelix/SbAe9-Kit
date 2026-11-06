# Changelog

SbAe9-Kit: the shared base of SbAe9-SBC and SbAe9-AudioMon.

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
