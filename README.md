# JGR Cursor Installer

A sleek, dark-themed Windows cursor installer with smart auto-detection. Drop in any cursor pack and it figures out which cursor goes where — no manual setup needed.

![Version](https://img.shields.io/badge/version-2.1.0-white?style=flat-square) ![Platform](https://img.shields.io/badge/platform-Windows-blue?style=flat-square) ![Python](https://img.shields.io/badge/python-3.8%2B-yellow?style=flat-square)

---

## Features

- **Smart Auto-Detection** — Automatically assigns cursor roles (Arrow, Hand, IBeam, Wait, etc.) using a 4-tier detection system: scheme files, filename patterns, image shape analysis, and hotspot position
- **150+ Filename Patterns** — Recognizes cursors from CursorFX, DeviantArt, cursors-4u.com, RealWorld, and more
- **Archive Support** — Drag and drop `.zip`, `.rar`, `.7z`, `.tar.gz` files directly
- **Scheme File Parsing** — Reads `.inf`, `.ini`, `.crs`, and `.theme` files for perfect role mapping
- **Database ID Detection** — Handles packs from cursors-4u.com where files have meaningless names like `nat884.ani`
- **Image Analysis** — When filenames give no clues, pixel-level shape analysis identifies arrows, hands, crosshairs, resize cursors, and more
- **One-Click Install** — Writes directly to the Windows Registry and applies changes instantly
- **One-Click Revert** — Restore Windows default cursors anytime
- **Dark Theme** — Clean black and white UI with smooth animations
- **Auto-Update** — Checks GitHub for new versions and notifies you when an update is available

## Supported Formats

| Type | Extensions |
|------|-----------|
| Cursors | `.cur` `.ani` `.ico` |
| Archives | `.zip` `.rar` `.7z` `.tar` `.gz` `.bz2` `.xz` |
| Schemes | `.inf` `.ini` `.crs` `.theme` |

## How to Use

1. **Download** the latest `.exe` from [Releases](https://github.com/infamousjuu-debug/jgr-cursor-installer/releases)
2. **Run it** — no installation needed
3. **Drop cursor files** or a `.zip` pack onto the window
4. Click **Install Cursors** — the app auto-detects roles and applies them
5. To go back to normal, click **Restore Windows Default Cursors**

## Cursor Roles

The app detects and assigns all 17 Windows cursor roles:

| Role | What it does |
|------|-------------|
| Arrow | Normal pointer on desktop |
| Hand | Hover over clickable links |
| IBeam | Text typing cursor |
| Wait | Loading / busy spinner |
| AppStarting | Loading in background |
| Cross | Precise pixel selection |
| SizeAll | Drag to move in any direction |
| SizeNWSE | Stretch diagonally \\ |
| SizeNESW | Stretch diagonally / |
| SizeWE | Stretch left and right |
| SizeNS | Stretch up and down |
| No | Action not allowed |
| Help | Click for help info |
| UpArrow | Alternate selection pointer |
| NWPen | Handwriting / pen input |
| Pin | Pick a location on map |
| Person | Select a person / contact |

## Building from Source

Requirements: Python 3.8+, PyQt5, Pillow

```bash
pip install PyQt5 Pillow py7zr rarfile pyinstaller
```

Build the `.exe`:

```bash
pyinstaller --onefile --noconsole --name "JGR Cursor Installer" --icon=icon.ico jgr_cursor_installer.py
```

The output will be in the `dist/` folder.

## How Auto-Detection Works

The app uses a 4-tier priority system to figure out which cursor is which:

1. **Scheme files** — If the pack includes an `.inf`, `.ini`, or `.theme` file, it reads the role mappings directly. This is the most accurate method.
2. **Filename patterns** — Matches against 150+ known patterns like `arrow.cur`, `linkselect.ani`, `leftptr.cur`, `diagonal1.cur`, etc. Handles camelCase, underscores, dashes, and common prefixes.
3. **Image analysis** — Opens the cursor image and analyzes the pixel shape: narrow vertical bar = IBeam, circle with slash = No, pointed tip at top-left = Arrow, etc.
4. **Hotspot + animation** — Uses the cursor's hotspot coordinates and frame count as final tiebreakers.

For packs from sites like cursors-4u.com where files have database IDs (e.g. `nat884.ani` through `nat899.ani`), the app detects the consecutive numbering pattern and maps them by standard Windows cursor order.

## Credits

Made by JGR

## License

Free to use.
