# SbAe9-Kit

The shared base of the Sound Blaster AE-9 apps for Linux:
[SbAe9-SBC](https://github.com/3xHelix/SbAe9-SBC) (Sound Blaster Command, the
control panel) and SbAe9-AudioMon (the listen-only level meters). Both run on
the [SbAe9-Drv](https://github.com/3xHelix/SbAe9-Drv) driver, PipeWire and
Qt 6 (PySide6), and are built, tested, installed and released the same way.

## How the apps use it

The kit is **vendored**: each app carries an identical copy in its own
`sbae9kit/` folder, so each app stays self-contained (one tarball, no extra
install). The copy is only ever changed here:

```sh
python3 tools/sync_kit.py ~/Projects/SbAe9-SBC ~/Projects/SbAe9-AudioMon
```

`sync_kit.py` writes `sbae9kit/MANIFEST` (kit version, this repo's commit, a
sha256 per file). Each app has a test that calls `sbae9kit.vendor.verify()`,
so an edit made in an app's copy fails that app's tests.

## What's in it

| Module | What it does |
|---|---|
| `ae9` | Read-only AE-9 facts: which PipeWire nodes are the card (by name, never PCI address or card number), mic / optical in / What U Hear, driver version and options, what its PCMs are open at, whether ae9-reload is reloading the driver (its notice) |
| `boards` | Which cards are ours (AE-9, AE-7; AE-5 reserved), bound to the AE driver: detection, models, wording-level features, naming. Used through `ae9` |
| `mixer` | ALSA mixer controls via ctypes, read **and write**. Control apps only: SbAe9-AudioMon is listen-only and never imports it |
| `palettes` | The Command, Helix, Albino and Wololo palettes, the shared warning red, level-meter zone colours |
| `glass` | Glass: see-through backgrounds on any palette, KDE's blur behind |
| `desktop` | UI scale, the XWayland choice (scaled UI or Glass), the window's X11 name for docks, relaunching, the app icon |
| `frame` | The frameless window's title bar (drag, double-click) and edge grips |
| `testing` | The fake AE-9 for tests: a fake PipeWire graph from a snapshot of the real machine (states, passive links, What U Hear, silent restart, card drop-out), fake `pw-link` and `pw-record`, temp folders, blocked commands, a fake ae9-reload notice, one `TIME_SCALE`; `testing.mixer`: the fake ALSA mixer (control apps only). Tests only |
| `vendor` | The vendored-copy check |

Nothing in the kit keeps state: apps hold their own settings and pass them in.

Tools: `tools/sync_kit.py` (above) and `tools/make_icons.py` (cuts an app's
icon PNGs, 16–512 px, out of square artwork).

## Shared conventions

- Python 3 + PySide6 (Fusion style), an app package plus a small `sh`
  launcher, `__version__` in the package.
- `install.sh` installs a **copy** into `~/.local` (menu entry, icon,
  command), so the menu app is the last build deliberately installed.
- Settings in `~/.config/<app>/`, logs in `~/.local/state/<app>/`.
- Options both apps take: `--palette`, `--scale`, `--glass`, `--frame`,
  `--version`.
- Tests: `python3 -m unittest discover -s tests`, against a fake AE-9 (no
  card, PipeWire or real settings touched).
- Releases: GitHub pre-release, title = tag, a `git archive` tarball plus
  its `.sha256`, notes from the CHANGELOG section.

## Tests

```sh
python3 -m unittest discover -s tests
```

## License

GPL-2.0-only, like the driver and the apps. See [LICENSE](LICENSE).
