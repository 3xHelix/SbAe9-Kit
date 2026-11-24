# SbAe9-Kit

The shared base of the Linux apps for the **Creative Sound Blaster AE-9**:
[Sound Blaster Command for Linux](https://github.com/3xHelix/SbAe9-SBC) (the
control panel) and [SbAe9-AudioMon](https://github.com/3xHelix/SbAe9-AudioMon)
(the listen-only level meters). Both run on the AE-9 driver,
[SbAe9-Drv](https://github.com/3xHelix/SbAe9-Drv), with PipeWire and Qt 6
(PySide6).

**You don't need to install this.** Each app already carries its own copy of
the kit. This repo is where that copy is made and tested. To use the card,
install [SbAe9-Drv](https://github.com/3xHelix/SbAe9-Drv) and then one of the
apps. Please report app problems in that app's repo.

---

## Highlights

- **One look for both apps**: the Command, Helix, Albino and Wololo palettes,
  **Glass** (see-through backgrounds with KDE's blur behind), UI scaling, and
  the frameless window's title bar.
- **Card detection**: finds the cards bound to the AE driver, the AE-9 today
  and the AE-7 later, and names them the same way in both apps. It never
  confuses them with the same boards on the kernel's own driver.
- **AE-9 facts, read-only**: which PipeWire nodes belong to the card (by name,
  never by PCI address or card number), what its PCMs are open at, the driver
  version, and whether `ae9-reload` is reloading the driver.
- **The mixer**: the driver's ALSA controls, read and write. Only Sound
  Blaster Command uses it. AudioMon is listen-only and never loads it.
- **A fake AE-9 for tests**: a fake PipeWire graph and a fake ALSA mixer
  built from snapshots of a real card. Both apps test against it, so tests
  never touch your card, PipeWire or settings.

---

## How the apps use it

The kit is **vendored**: each app has an identical copy in its own
`sbae9kit/` folder. That keeps each app self-contained: one tarball, nothing
extra to install. The copy is only ever changed here, then written into the
apps:

```sh
python3 tools/sync_kit.py ~/Projects/SbAe9-SBC ~/Projects/SbAe9-AudioMon
```

`sync_kit.py` also writes `sbae9kit/MANIFEST`: the kit version, this repo's
commit, and a sha256 for each file. Each app has a test that checks its copy
against it (`sbae9kit.vendor.verify()`). An edit made in an app's copy fails
that app's tests, so changes to the kit always start here.

---

## What's in it

| Module | What it does |
|---|---|
| `ae9` | Read-only card facts: which PipeWire nodes are the card, the mic, optical in and What U Hear, driver version and options, what its PCMs are open at, and whether `ae9-reload` is reloading the driver |
| `boards` | Which cards are ours, bound to the AE driver (AE-9, AE-7; AE-5 reserved): detection, models, naming and wording-level features. Apps use it through `ae9` |
| `mixer` | ALSA mixer controls via ctypes, read **and write**. Control apps only |
| `palettes` | The four palettes, the shared warning red, the level-meter colours |
| `glass` | See-through backgrounds on any palette, with KDE's blur behind |
| `desktop` | UI scale, the XWayland choice (scaled UI or Glass), the window's X11 name for docks, relaunching, the app icon |
| `frame` | The frameless window's title bar (drag, double-click) and edge grips |
| `testing` | The fake AE-9: a fake PipeWire graph from a snapshot of the real card (states, links, What U Hear, silent restarts, the card dropping out), fake `pw-link` and `pw-record`, fake sysfs and `/proc/asound` trees for card detection, and a fake `ae9-reload` notice. `testing.mixer` is the fake ALSA mixer. Tests only |
| `vendor` | The check that an app's copy matches its MANIFEST |

Nothing in the kit keeps state. The apps keep their own settings and pass
them in.

### Card detection, in short

Only cards bound to `snd-hda-codec-creative-ae9` count. The first match wins:

1. the driver's "Card Model" control (once the driver has one)
2. the ALSA card id: `AE9`, `AE7`
3. the card's name: "Sound Blaster AE-9", "... AE-7"
4. the PCI subsystem id: `0x0071` AE-9, `0x0081` AE-7

What a card can do is decided by the driver's controls and PCMs. A model's
features only cover what the controls can't say, such as which pages to
show and how to word them.

---

## Tools

- `tools/sync_kit.py` copies the kit into the apps (see above).
- `tools/make_icons.py` cuts an app's icon PNGs, 16 to 512 px, from square
  artwork.

---

## Shared conventions

Both apps are built, tested, installed and released the same way:

- Python 3 and PySide6 (Fusion style): an app package plus a small `sh`
  launcher, with `__version__` in the package.
- `install.sh` installs a **copy** into `~/.local` (menu entry, icon,
  command), so the menu app is always the last build you chose to install.
- Settings go in `~/.config/<app>/` and logs in `~/.local/state/<app>/`.
- Both take `--palette`, `--scale`, `--glass`, `--frame` and `--version`.
- Releases are GitHub pre-releases: the title is the tag, with a
  `git archive` tarball, its `.sha256`, and notes from the CHANGELOG.

---

## For developers

### Tests

```sh
python3 -m unittest discover -s tests
```

The tests use the fake AE-9 and need no card. Before a kit release, also run
both apps' tests with the new copy synced in.

### Making a change

1. Change the kit here, add tests, bump `KIT_VERSION` in
   `sbae9kit/__init__.py`, and add a [CHANGELOG](CHANGELOG.md) entry.
2. Commit it.
3. Sync it into both apps with `tools/sync_kit.py`, and run their tests.

---

## License

GPL-2.0-only, same as the driver and both apps. See [LICENSE](LICENSE).

## Disclaimer

Not affiliated with Creative. "Sound Blaster" and related names are Creative
Technology's trademarks.
