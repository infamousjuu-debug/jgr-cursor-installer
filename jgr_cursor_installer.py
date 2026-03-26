#!/usr/bin/env python3
"""
JGR Cursor Installer  v2.2.1
Dark-themed cursor installer for Windows with smart auto-detection.
Supports: .cur  .ani  .ico  .zip  .rar  .7z  .tar  .gz  .bz2  .xz
"""

import sys
import os
import re
import shutil
import ctypes
import math
import struct
import zipfile
import tarfile
import tempfile
import webbrowser
import json
import subprocess
from pathlib import Path

# ── Version & Auto-Update Config ─────────────────────────────────────────────
APP_VERSION   = '2.2.1'
APP_NAME      = 'JGR Cursor Installer'

# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  AUTO-UPDATE CONFIG  —  Change these when you set up hosting            ║
# ╠═══════════════════════════════════════════════════════════════════════════╣
# ║  Option A: GitHub Releases                                              ║
# ║    UPDATE_CHECK_URL = 'https://api.github.com/repos/YOU/REPO/releases/latest'
# ║    The JSON must have: "tag_name" (version), "body" (changelog),        ║
# ║    and "assets" array with a .exe "browser_download_url".               ║
# ║                                                                         ║
# ║  Option B: Custom JSON endpoint                                         ║
# ║    UPDATE_CHECK_URL = 'https://yoursite.com/jgr-update.json'            ║
# ║    Return JSON: {"version":"2.2.0","download_url":"...","changelog":""} ║
# ║                                                                         ║
# ║  Set to '' to disable update checking entirely.                         ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
UPDATE_CHECK_URL  = 'https://api.github.com/repos/infamousjuu-debug/jgr-cursor-installer/releases/latest'
UPDATE_CHECK_SECS = 3600    # How often to re-check (seconds); default 1 hour

# ╔═══════════════════════════════════════════════════════════════════════════╗
# ║  AI CURSOR CREATOR  —  Uses Stable Horde (free, no key needed)          ║
# ╚═══════════════════════════════════════════════════════════════════════════╝
HORDE_API_URL  = 'https://stablehorde.net/api/v2'
HORDE_API_KEY  = '0000000000'   # anonymous key – free, no signup needed

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QGraphicsDropShadowEffect,
    QSizePolicy, QScrollArea, QFileDialog, QDialog, QComboBox,
    QGraphicsOpacityEffect, QLineEdit, QTextEdit, QProgressBar
)
from PyQt5.QtCore import (
    Qt, QPoint, pyqtSignal, QThread, QTimer, QRect,
    QPropertyAnimation, QEasingCurve
)
from PyQt5.QtGui import QColor, QFont, QPainter, QPen, QBrush

try:
    import py7zr;  HAS_7Z  = True
except ImportError:
    HAS_7Z = False

try:
    import rarfile; HAS_RAR = True
except ImportError:
    HAS_RAR = False

try:
    from PIL import Image; HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Windows API ───────────────────────────────────────────────────────────────
SPI_SETCURSORS     = 0x0057
SPIF_UPDATEINIFILE = 0x01
SPIF_SENDCHANGE    = 0x02

CURSOR_EXTS  = {'.cur', '.ani', '.ico'}
ARCHIVE_EXTS = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz', '.tgz', '.tbz2'}
SCHEME_EXTS  = {'.inf', '.ini', '.txt', '.theme', '.crs'}

# ── Cursor roles with PLAIN-ENGLISH descriptions ─────────────────────────────
CURSOR_ROLES = [
    ('Arrow',       'Normal pointer on desktop'),
    ('Hand',        'Hover over clickable links'),
    ('IBeam',       'Text typing cursor'),
    ('Wait',        'Loading / busy spinner'),
    ('AppStarting', 'Loading in background'),
    ('Cross',       'Precise pixel selection'),
    ('SizeAll',     'Drag to move in any direction'),
    ('SizeNWSE',    'Stretch diagonally  \\ '),
    ('SizeNESW',    'Stretch diagonally  / '),
    ('SizeWE',      'Stretch left and right'),
    ('SizeNS',      'Stretch up and down'),
    ('No',          'Action not allowed'),
    ('Help',        'Click for help info'),
    ('UpArrow',     'Alternate selection pointer'),
    ('NWPen',       'Handwriting / pen input'),
    ('Pin',         'Pick a location on map'),
    ('Person',      'Select a person / contact'),
]

# The canonical roles Windows registry uses
REGISTRY_ROLES = [
    'Arrow', 'Hand', 'IBeam', 'Wait', 'AppStarting', 'Cross',
    'SizeAll', 'SizeNWSE', 'SizeNESW', 'SizeWE', 'SizeNS', 'No', 'Help',
    'UpArrow', 'NWPen', 'Pin', 'Person',
]

# All known registry value names under Control Panel\Cursors (for cleanup)
_KNOWN_CURSOR_KEYS = {
    '', 'Arrow', 'Hand', 'IBeam', 'Wait', 'AppStarting', 'Cross',
    'SizeAll', 'SizeNWSE', 'SizeNESW', 'SizeWE', 'SizeNS', 'No', 'Help',
    'UpArrow', 'Pin', 'Person', 'NWPen', 'Scheme Source', 'ContactVisualization',
    'CursorBaseSize', 'GestureVisualization',
}

# ── TRUE SYSTEM DEFAULTS ─────────────────────────────────────────────────────
_SYSTEM_DEFAULTS = {
    '':            '',
    'Arrow':       '',
    'Hand':        '',
    'IBeam':       '',
    'Wait':        '',
    'AppStarting': '',
    'Cross':       '',
    'SizeAll':     '',
    'SizeNWSE':    '',
    'SizeNESW':    '',
    'SizeWE':      '',
    'SizeNS':      '',
    'No':          '',
    'Help':        '',
    'UpArrow':     '',
    'Pin':         '',
    'Person':      '',
}

CURSOR_SITES = [
    ('cursor.cc',         'https://www.cursor.cc/',
     'Design your own cursors online'),
    ('cursors-4u.com',    'https://cursors-4u.com/',
     'Huge free cursor library'),
    ('RW Designer',       'https://www.rw-designer.com/cursor-library',
     'Community-made cursor packs'),
    ('DeviantArt',        'https://www.deviantart.com/customization/skins/windows/cursors/',
     'Artist-made cursor themes'),
    ('Pling / KDE Store', 'https://www.pling.com/browse?cat=107',
     'Open-source cursor collections'),
    ('cursor.in',         'https://cursor.in/',
     'Animated cursor packs'),
]

INSTALL_DIR = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))) / 'JGR' / 'Cursors'
REG_PATH    = r'Control Panel\Cursors'

# ── Dark theme combo style ───────────────────────────────────────────────────
COMBO_STYLE = (
    'QComboBox{color:#ffffff;background:rgba(255,255,255,12);'
    'border:1px solid rgba(255,255,255,40);border-radius:5px;'
    'padding:1px 5px;font-size:8pt;font-weight:bold;}'
    'QComboBox:hover{border-color:rgba(255,255,255,90);background:rgba(255,255,255,22);}'
    'QComboBox[unassigned="true"]{color:rgba(255,180,60,210);'
    'border-color:rgba(255,180,60,60);background:rgba(255,150,0,12);}'
    'QComboBox::drop-down{border:none;width:16px;}'
    'QComboBox::down-arrow{border-left:4px solid transparent;'
    'border-right:4px solid transparent;border-top:5px solid rgba(255,255,255,140);'
    'margin-right:4px;}'
    'QComboBox QAbstractItemView{background:rgb(18,18,22);color:#e0e0e0;'
    'selection-background-color:rgba(255,255,255,18);selection-color:#ffffff;'
    'border:1px solid rgba(255,255,255,40);outline:none;}'
)


# =============================================================================
#  Registry helpers
# =============================================================================

def _read_current_cursors():
    """Read current cursor registry values."""
    try:
        import winreg
        result = {}
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ) as reg:
            try:
                result[''] = winreg.QueryValueEx(reg, '')[0]
            except Exception:
                result[''] = ''
            for key, _ in CURSOR_ROLES:
                try:
                    result[key] = winreg.QueryValueEx(reg, key)[0]
                except Exception:
                    result[key] = ''
        return result
    except Exception:
        return dict(_SYSTEM_DEFAULTS)


# =============================================================================
#  INF / SCHEME FILE PARSER  (highest-priority detection)
# =============================================================================

_INF_KEY_MAP = {}
_inf_aliases = {
    'Arrow':       ['arrow', 'pointer', 'normal', 'normal select', 'default',
                    'idc_arrow', '0', 'normalselect', 'standard', 'main', 'regular',
                    'select', 'cursor', 'left_ptr', 'top_left_arrow',
                    'base_arrow', 'mainarrow', 'basecursor', 'arrowcursor'],
    'Help':        ['help', 'help select', 'idc_help', 'question', 'helpselect',
                    'whatsthis', 'question_arrow', 'dnd_ask', 'helpcur',
                    'helpcursor', 'questionmark'],
    'AppStarting': ['appstarting', 'app starting', 'working in background',
                    'working', 'background', 'idc_appstarting', 'busy_l',
                    'workinginbackground', 'backgroundbusy', 'busyarrow', 'progress',
                    'left_ptr_watch', 'half_busy', 'halfbusy', 'bgworking',
                    'startingapp', 'arrowbusy', 'waitarrow', 'progressarrow'],
    'Wait':        ['wait', 'busy', 'idc_wait', 'hourglass', 'loading',
                    'spinning', 'busy_r', 'spin', 'spinner', 'clock', 'timer',
                    'watch', 'fullbusy', 'processing', 'waitcur', 'waitcursor',
                    'busycursor', 'thinking'],
    'Cross':       ['cross', 'crosshair', 'precision', 'precision select',
                    'idc_cross', 'precisionselect', 'target', 'tcross',
                    'crosshaircur', 'exactselect', 'pinpoint'],
    'IBeam':       ['ibeam', 'text', 'text select', 'i-beam', 'idc_ibeam',
                    'beam', 'textselect', 'caret', 'edit', 'type', 'xterm',
                    'textcur', 'textcursor', 'typecursor', 'editcursor',
                    'typetext', 'inserttext'],
    'SizeNWSE':    ['sizenwse', 'nwse', 'diagonal resize 1', 'idc_sizenwse',
                    'dgn1', 'nw-se', 'diag1', 'diagonalresize1', 'nwseresize',
                    'sizenw', 'sizese', 'bd_double_arrow', 'top_left_corner',
                    'bottom_right_corner', 'size_fdiag', 'diagonal1',
                    'nwse_resize', 'diag_left', 'diagleft'],
    'SizeNESW':    ['sizenesw', 'nesw', 'diagonal resize 2', 'idc_sizenesw',
                    'dgn2', 'ne-sw', 'diag2', 'diagonalresize2', 'neswresize',
                    'sizene', 'sizesw', 'fd_double_arrow', 'top_right_corner',
                    'bottom_left_corner', 'size_bdiag', 'diagonal2',
                    'nesw_resize', 'diag_right', 'diagright'],
    'SizeWE':      ['sizewe', 'we', 'horizontal resize', 'idc_sizewe',
                    'horz', 'ew', 'w-e', 'hresize', 'horizontalresize',
                    'leftright', 'col', 'sb_h_double_arrow', 'left_side',
                    'right_side', 'split_h', 'h_double_arrow', 'col_resize',
                    'ewresize', 'ew_resize', 'horzresize', 'sizeh',
                    'resizehoriz', 'resizehorizontal'],
    'SizeNS':      ['sizens', 'ns', 'vertical resize', 'idc_sizens',
                    'vert', 'n-s', 'vresize', 'verticalresize', 'updown', 'row',
                    'sb_v_double_arrow', 'top_side', 'bottom_side', 'split_v',
                    'v_double_arrow', 'row_resize', 'nsresize', 'ns_resize',
                    'vertresize', 'sizev', 'resizevert', 'resizevertical'],
    'SizeAll':     ['sizeall', 'move', 'idc_sizeall', 'all', 'allmove',
                    'fourway', '4way', 'fleur', 'size_all', 'grabbing',
                    'closedhand', 'dnd_move', 'movecursor', 'dragmove',
                    'allscroll', 'moveall'],
    'No':          ['no', 'unavailable', 'idc_no', 'forbidden', 'not allowed',
                    'blocked', 'stop', 'denied', 'unavail', 'block', 'deny',
                    'notallowed', 'cant', 'circle', 'dnd_no_drop', 'no_drop',
                    'crossed_circle', 'not_allowed', 'restricted', 'banned',
                    'prohibited', 'nodrop', 'cannotdrop', 'stopcur', 'disable',
                    'disabled'],
    'Hand':        ['hand', 'link', 'link select', 'idc_hand', 'finger',
                    'pointing', 'linkselect', 'grab', 'point',
                    'pointing_hand', 'hand2', 'openhand',
                    'handpointer', 'clickhand', 'weblink', 'urlhand'],
    'UpArrow':     ['uparrow', 'up arrow', 'alternate', 'alternate select',
                    'idc_uparrow', 'alternateselect', 'up', 'alt',
                    'up_arrow', 'center_ptr', 'altselect', 'alt_select',
                    'altuparrow'],
    'NWPen':       ['nwpen', 'handwriting', 'idc_nwpen', 'pen', 'write',
                    'pencil', 'scribble', 'stylus', 'freeform', 'inkpen',
                    'writecur'],
    'Pin':         ['pin', 'location', 'location select', 'idc_pin',
                    'marker', 'mappin', 'locator', 'geopin'],
    'Person':      ['person', 'person select', 'idc_person', 'contact',
                    'people', 'user', 'personselect', 'selectperson'],
}
for _role, _aliases in _inf_aliases.items():
    for _a in _aliases:
        _INF_KEY_MAP[_a.lower()] = _role
    _INF_KEY_MAP[_role.lower()] = _role


def _resolve_cursor_path(val, cursor_dir):
    """Resolve a cursor filename/path to an actual file on disk."""
    val = val.strip().strip('"').strip("'")
    if not val:
        return ''
    p = Path(val)
    if p.is_absolute() and p.exists():
        return str(p)
    check = Path(cursor_dir) / val
    if check.exists():
        return str(check)
    check = Path(cursor_dir) / p.name
    if check.exists():
        return str(check)
    target = p.name.lower()
    try:
        for f in Path(cursor_dir).iterdir():
            if f.name.lower() == target:
                return str(f)
    except Exception:
        pass
    return ''


def _parse_inf_file(inf_path, cursor_dir):
    """
    Parse cursor scheme files for role -> filename mappings.
    Supports: .crs, .inf, .ini, .theme formats.
    """
    mapping = {}
    try:
        raw = Path(inf_path).read_bytes()
        for enc in ('utf-16', 'utf-8-sig', 'utf-8', 'latin-1'):
            try:
                text = raw.decode(enc)
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        else:
            return mapping

        lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
        current_section = ''

        for line in lines:
            line = line.strip()
            if not line or line.startswith(';') or line.startswith('#'):
                continue
            sec_match = re.match(r'^\[(.+)\]$', line)
            if sec_match:
                current_section = sec_match.group(1).strip()
                continue
            if '=' not in line:
                continue
            key, _, val = line.partition('=')
            key = key.strip().strip('"').strip("'").lower()
            val = val.strip().strip('"').strip("'")

            # .crs format: [Arrow] section with Path=filename
            if key == 'path' and current_section:
                role = _INF_KEY_MAP.get(current_section.lower(), '')
                if role and val:
                    fp = _resolve_cursor_path(val, cursor_dir)
                    if fp:
                        mapping[fp] = role
                continue

            # .inf format: HKCU registry lines
            if val.startswith('HKCU,') or val.startswith('HKLM,'):
                parts = [p.strip().strip('"') for p in val.split(',')]
                if len(parts) >= 5 and 'cursors' in parts[1].lower():
                    role_candidate = parts[2].strip()
                    cursor_file = parts[-1].strip().strip('"')
                    role = _INF_KEY_MAP.get(role_candidate.lower(), '')
                    if role and cursor_file:
                        fp = _resolve_cursor_path(cursor_file, cursor_dir)
                        if fp:
                            mapping[fp] = role
                continue

            # .theme format: [Control Panel\Cursors]
            if current_section.lower().replace(' ', '') in (
                    'controlpanel\\cursors', 'controlpanel\\\\cursors',
                    r'control panel\cursors'):
                role = _INF_KEY_MAP.get(key, '')
                if role and val:
                    fname = Path(val).name if val else ''
                    if fname:
                        fp = _resolve_cursor_path(fname, cursor_dir)
                        if fp:
                            mapping[fp] = role
                continue

            # .ini format: direct key=value
            role = _INF_KEY_MAP.get(key, '')
            if role and val:
                fp = _resolve_cursor_path(val, cursor_dir)
                if fp:
                    mapping[fp] = role

        # Fallback scan
        if not mapping:
            for line in lines:
                for ext in ('.cur', '.ani', '.ico'):
                    if ext in line.lower():
                        m = re.match(r'^\s*([^=]+?)\s*=\s*(.+?' + re.escape(ext) + r')\s*$',
                                     line, re.IGNORECASE)
                        if m:
                            key = m.group(1).strip().strip('"').lower()
                            val = m.group(2).strip().strip('"')
                            role = _INF_KEY_MAP.get(key, '')
                            if role:
                                fp = _resolve_cursor_path(val, cursor_dir)
                                if fp:
                                    mapping[fp] = role

    except Exception:
        pass
    return mapping


# =============================================================================
#  BINARY CURSOR PARSING
# =============================================================================

def _parse_cur_header(data):
    """Return ((hx,hy),(w,h)) from raw .cur bytes, or (None,None)."""
    try:
        _, typ, count = struct.unpack_from('<HHH', data, 0)
        if typ not in (1, 2) or count < 1:
            return None, None
        e = struct.unpack_from('<BBBBHHII', data, 6)
        w, h = (e[0] or 256), (e[1] or 256)
        return (e[4], e[5]), (w, h)
    except Exception:
        return None, None


def _parse_ani_header(data):
    """Return (nFrames, (hx,hy), (w,h)) from .ani RIFF data.
    Searches both top-level chunks and icons inside LIST/fram."""
    frames, hotspot, img_size = 1, None, None
    try:
        if data[:4] != b'RIFF':
            return frames, hotspot, img_size

        def _walk(buf, start, end):
            nonlocal frames, hotspot, img_size
            j = start
            while j < end - 8:
                cid = buf[j:j+4]
                sz = struct.unpack_from('<I', buf, j + 4)[0]
                if cid == b'anih' and sz >= 24:
                    fc = struct.unpack_from('<I', buf, j + 12)[0]
                    if fc > 0:
                        frames = fc
                elif cid == b'LIST':
                    list_type = buf[j+8:j+12] if j + 12 <= end else b''
                    if list_type == b'fram':
                        _walk(buf, j + 12, j + 8 + sz)
                elif cid == b'icon':
                    hs, ims = _parse_cur_header(buf[j+8 : j+8+sz])
                    if hs and hotspot is None:
                        hotspot = hs
                    if ims and img_size is None:
                        img_size = ims
                j += 8 + sz + (sz % 2)

        _walk(data, 12, len(data))
    except Exception:
        pass
    return frames, hotspot, img_size


def _extract_first_frame_from_ani(data):
    """Extract the first .cur/.ico frame from a RIFF .ani file as PIL Image.
    Handles both top-level icon chunks AND icons nested inside LIST/fram."""
    try:
        import io
        if len(data) < 12 or data[:4] != b'RIFF':
            return None

        def _find_first_icon(buf, start, end):
            """Walk chunk list and return first valid icon Image."""
            j = start
            while j < end - 8:
                cid = buf[j:j+4]
                csz = struct.unpack_from('<I', buf, j + 4)[0]
                if cid == b'LIST':
                    list_type = buf[j+8:j+12] if j + 12 <= end else b''
                    if list_type == b'fram':
                        result = _find_first_icon(buf, j + 12, j + 8 + csz)
                        if result is not None:
                            return result
                    j += 8 + csz + (csz % 2)
                elif cid == b'icon' and csz > 6:
                    icon_data = buf[j+8 : j+8+csz]
                    if len(icon_data) >= 6:
                        _, typ, _ = struct.unpack_from('<HHH', icon_data, 0)
                        if typ in (1, 2):
                            return Image.open(io.BytesIO(icon_data))
                    j += 8 + csz + (csz % 2)
                else:
                    j += 8 + csz + (csz % 2)
            return None

        return _find_first_icon(data, 12, len(data))
    except Exception:
        pass
    return None


# =============================================================================
#  IMAGE SHAPE ANALYSIS
# =============================================================================

def _image_shape_hint(filepath):
    """Analyse cursor image pixels and return best-guess role, or ''.
    Uses multi-feature analysis: aspect ratio, tip detection, symmetry,
    cross-band density, ring/circle detection, diagonal concentration,
    and profile analysis for IBeam/Arrow/Hand shapes.
    """
    if not HAS_PIL:
        return ''
    try:
        ext = Path(filepath).suffix.lower()
        if ext == '.ani':
            with open(filepath, 'rb') as fh:
                raw = fh.read()
            img = _extract_first_frame_from_ani(raw)
            if not img:
                return ''
        else:
            img = Image.open(filepath)

        img = img.convert('RGBA')
        W, H = img.size
        if W < 4 or H < 4:
            return ''
        pix = img.load()

        vis = []
        for y in range(H):
            for x in range(W):
                if pix[x, y][3] > 30:
                    vis.append((y, x))
        total = len(vis)
        if total < 8:
            return ''

        rows_l = [r for r, c in vis]
        cols_l = [c for r, c in vis]
        r0, r1 = min(rows_l), max(rows_l)
        c0, c1 = min(cols_l), max(cols_l)
        ch = r1 - r0 + 1
        cw = c1 - c0 + 1
        if ch == 0 or cw == 0:
            return ''

        aspect   = cw / ch
        cm_r     = sum(rows_l) / total
        cm_c     = sum(cols_l) / total
        ncm_r    = (cm_r - r0) / ch
        ncm_c    = (cm_c - c0) / cw
        fill     = total / (ch * cw) if (ch * cw) > 0 else 0

        rw_dict = {}
        cw_dict = {}
        for r, c in vis:
            rw_dict[r] = rw_dict.get(r, 0) + 1
            cw_dict[c] = cw_dict.get(c, 0) + 1

        rw = [rw_dict.get(r, 0) for r in range(r0, r1 + 1)]
        cw_arr = [cw_dict.get(c, 0) for c in range(c0, c1 + 1)]
        max_rw  = max(rw)  if rw  else 1
        max_cww = max(cw_arr) if cw_arr else 1

        # ── Helper: tip strength (how sharply a profile narrows) ──────────
        def tip_strength(widths, from_start):
            n = len(widths)
            if n < 5:
                return 0.0
            w = list(reversed(widths)) if not from_start else widths
            tip_n   = max(1, n // 8)
            mid_s   = n // 3
            mid_e   = 2 * n // 3
            tip_avg = sum(w[:tip_n])         / tip_n
            mid_avg = sum(w[mid_s : mid_e])  / max(1, mid_e - mid_s)
            if mid_avg == 0:
                return 0.0
            ratio = tip_avg / mid_avg
            return max(0.0, min(1.0, 1.0 - ratio / 0.45))

        n_str = tip_strength(rw,     from_start=True)
        s_str = tip_strength(rw,     from_start=False)
        w_str = tip_strength(cw_arr, from_start=True)
        e_str = tip_strength(cw_arr, from_start=False)

        T = 0.45
        n_tip = n_str > T
        s_tip = s_str > T
        w_tip = w_str > T
        e_tip = e_str > T

        # ── Helper: symmetry ─────────────────────────────────────────────
        vis_set = set(vis)
        mid_r = (r0 + r1) / 2.0
        mid_c = (c0 + c1) / 2.0
        sym_lr_m = sum(1 for r, c in vis if (r, int(2*mid_c - c + 0.5)) in vis_set)
        sym_ud_m = sum(1 for r, c in vis if (int(2*mid_r - r + 0.5), c) in vis_set)
        sym_lr = sym_lr_m / total if total > 0 else 0
        sym_ud = sym_ud_m / total if total > 0 else 0

        # ── IBeam: narrow vertical bar, possibly with serifs ─────────────
        if cw <= max(W * 0.65, 20):
            norm_rw = [w / max_rw for w in rw] if max_rw > 0 else []
            if len(norm_rw) >= 10:
                top_serifs = max(norm_rw[:max(1, ch//6)])
                bot_serifs = max(norm_rw[ch - max(1, ch//6):])
                mid_s_idx = ch // 4
                mid_e_idx = 3 * ch // 4
                mid_widths = norm_rw[mid_s_idx:mid_e_idx]
                if mid_widths:
                    mid_avg_n = sum(mid_widths) / len(mid_widths)
                    mid_max_n = max(mid_widths)
                    # IBeam: wide at top & bottom, narrow middle, OR uniformly narrow
                    if mid_max_n < 0.60 and aspect < 0.55:
                        return 'IBeam'
                    if top_serifs > mid_avg_n * 1.5 and bot_serifs > mid_avg_n * 1.5:
                        if mid_avg_n < 0.50:
                            return 'IBeam'
            # Very narrow aspect and small width
            if aspect < 0.35 and cw <= max(W * 0.32, 11):
                return 'IBeam'

        # ── Double-arrow shapes (check before single-arrow) ──────────────

        # SizeWE: wide aspect, tips on left+right
        if aspect > 2.0 and (w_tip or e_tip):
            return 'SizeWE'
        if w_tip and e_tip and not n_tip and not s_tip:
            return 'SizeWE'

        # SizeNS: tall aspect, tips on top+bottom
        if aspect < 0.55 and n_tip and s_tip:
            return 'SizeNS'
        if n_tip and s_tip and not w_tip and not e_tip:
            return 'SizeNS'

        # ── Cross-band analysis (Cross vs SizeAll) ───────────────────────
        band_r = max(H * 0.14, 2)
        band_c = max(W * 0.14, 2)
        h_band = sum(1 for r, c in vis if abs(r - cm_r) < band_r)
        v_band = sum(1 for r, c in vis if abs(c - cm_c) < band_c)
        h_ratio = h_band / total
        v_ratio = v_band / total
        if h_ratio > 0.42 and v_ratio > 0.42:
            corner_pix = sum(1 for r, c in vis
                             if abs(r - cm_r) > band_r and abs(c - cm_c) > band_c)
            corner_ratio = corner_pix / total
            # SizeAll: has arrowheads extending into corners
            if corner_ratio > 0.06:
                # Verify it has tips in all 4 cardinal directions
                if n_tip and s_tip and w_tip and e_tip:
                    return 'SizeAll'
                return 'SizeAll'
            # Cross: clean crosshair, almost nothing in corners
            if corner_ratio < 0.08:
                return 'Cross'

        # ── No / Forbidden: circle with diagonal slash ───────────────────
        if cw >= 10 and ch >= 10:
            rad = min(cw, ch) / 2.0
            dists = [math.sqrt((r-cm_r)**2+(c-cm_c)**2) for r, c in vis]
            ring = sum(1 for d in dists if 0.28 * rad <= d <= 0.98 * rad)
            inner = sum(1 for d in dists if d < 0.28 * rad)
            # Check for NESW diagonal slash (top-right to bottom-left)
            slash_nesw = sum(1 for r, c in vis
                             if abs((r - cm_r) + (c - cm_c)) < rad * 0.35)
            # Check for NWSE diagonal slash (top-left to bottom-right)
            slash_nwse = sum(1 for r, c in vis
                             if abs((r - cm_r) - (c - cm_c)) < rad * 0.35)
            slash = max(slash_nesw, slash_nwse)
            ring_r = ring / total
            inner_r = inner / total
            slash_r = slash / total
            if ring_r > 0.30 and inner_r < 0.25 and slash_r > 0.06:
                return 'No'
            # Also detect filled circle with slash (some themes use solid No cursor)
            if 0.75 < aspect < 1.35 and sym_lr > 0.4 and sym_ud > 0.4:
                if fill > 0.25 and slash_r > 0.15:
                    return 'No'

        # ── Arrow: tip at top, widens downward ───────────────────────────
        if n_tip and not s_tip:
            third = max(1, ch // 3)
            top_avg = sum(rw[:third])        / third
            bot_avg = sum(rw[ch - third :])  / third
            widens  = bot_avg > top_avg * 1.20

            if widens and ncm_r > 0.40:
                # Check for Hand shape: narrow tip then sudden wide section
                norm = [w / max_rw for w in rw]
                first_wide = next((i for i, w in enumerate(norm) if w > 0.30), ch)
                if first_wide > ch * 0.25 and norm[0] < 0.20:
                    if first_wide < ch and norm[first_wide] > 0.50:
                        return 'Hand'
                return 'Arrow'

        # ── Hand: narrow tip/finger at top, wider palm below ─────────────
        if ch > 10 and n_tip:
            norm = [w / max_rw for w in rw]
            first_wide = next((i for i, w in enumerate(norm) if w > 0.30), ch)
            if first_wide > ch * 0.18 and norm[0] < 0.25:
                if first_wide < ch * 0.65 and max(norm[first_wide:]) > 0.50:
                    return 'Hand'

        # ── Wait / spinner: roughly circular, symmetric ──────────────────
        if cw >= 10 and ch >= 10 and 0.60 < aspect < 1.65:
            rad = min(cw, ch) / 2.0
            dists = [math.sqrt((r-cm_r)**2+(c-cm_c)**2) for r, c in vis]
            ring = sum(1 for d in dists if 0.25 * rad <= d <= 0.98 * rad)
            inner = sum(1 for d in dists if d < 0.25 * rad)
            ring_r = ring / total
            inner_r = inner / total
            # Hollow ring (hourglass outline, spinner)
            if ring_r > 0.38 and inner_r < 0.20 and sym_lr > 0.45:
                return 'Wait'
            # Filled circular shape (solid hourglass)
            if fill > 0.30 and sym_lr > 0.55 and 0.70 < aspect < 1.35:
                mid_idx = ch // 2
                mid_w = rw[mid_idx] if mid_idx < len(rw) else max_rw
                edge_avg = (rw[0] + rw[-1]) / 2.0 if len(rw) > 1 else max_rw
                if mid_w < edge_avg * 0.75:
                    return 'Wait'

        # ── Diagonal double-arrows ───────────────────────────────────────
        dscale = max(cw, ch)
        dband  = dscale * 0.22
        d_nwse = sum(1 for r, c in vis if abs((r-cm_r) - (c-cm_c)) < dband)
        d_nesw = sum(1 for r, c in vis if abs((r-cm_r) + (c-cm_c)) < dband)
        d_nwse_r = d_nwse / total
        d_nesw_r = d_nesw / total
        if d_nwse_r > 0.50 and d_nwse_r > d_nesw_r + 0.10:
            return 'SizeNWSE'
        if d_nesw_r > 0.50 and d_nesw_r > d_nwse_r + 0.10:
            return 'SizeNESW'

        # ── Fallback Arrow: any top-tip shape ────────────────────────────
        if n_tip and not s_tip and ncm_r > 0.35:
            return 'Arrow'

        # ── Fallback wide → SizeWE ───────────────────────────────────────
        if aspect > 1.8:
            return 'SizeWE'

        # ── Fallback tall → SizeNS ───────────────────────────────────────
        if aspect < 0.55 and sym_lr > 0.4:
            return 'SizeNS'

        return ''

    except Exception:
        return ''


# =============================================================================
#  FILENAME-BASED DETECTION  (massive pattern database)
# =============================================================================

_TOKEN_MAP = {
    # Arrow / Normal
    'arrow': 'Arrow', 'normal': 'Arrow', 'default': 'Arrow',
    'standard': 'Arrow', 'regular': 'Arrow',
    'main': 'Arrow',
    # Hand / Link  (NOT 'pointer' — too ambiguous, many packs use it for Arrow)
    'hand': 'Hand', 'link': 'Hand', 'finger': 'Hand', 'grab': 'Hand',
    'pointing': 'Hand',
    # IBeam / Text
    'ibeam': 'IBeam', 'beam': 'IBeam', 'caret': 'IBeam', 'text': 'IBeam',
    'xterm': 'IBeam',
    # Wait / Busy
    'wait': 'Wait', 'busy': 'Wait', 'loading': 'Wait', 'hourglass': 'Wait',
    'spinner': 'Wait', 'clock': 'Wait', 'watch': 'Wait', 'thinking': 'Wait',
    'processing': 'Wait',
    # Cross
    'cross': 'Cross', 'crosshair': 'Cross', 'precision': 'Cross',
    'pinpoint': 'Cross', 'target': 'Cross',
    # No / Unavailable
    'unavailable': 'No', 'unavail': 'No', 'forbidden': 'No', 'blocked': 'No',
    'no': 'No', 'stop': 'No', 'denied': 'No', 'prohibited': 'No',
    'banned': 'No', 'restricted': 'No', 'disabled': 'No',
    # SizeAll / Move
    'move': 'SizeAll', 'sizeall': 'SizeAll', 'fleur': 'SizeAll',
    'grabbing': 'SizeAll',
    # SizeNWSE
    'nwse': 'SizeNWSE', 'sizenwse': 'SizeNWSE',
    # SizeNESW
    'nesw': 'SizeNESW', 'sizenesw': 'SizeNESW',
    # SizeWE
    'sizewe': 'SizeWE', 'horizontal': 'SizeWE',
    # SizeNS
    'sizens': 'SizeNS', 'vertical': 'SizeNS',
    # Help
    'help': 'Help', 'question': 'Help',
    # AppStarting
    'working': 'AppStarting', 'progress': 'AppStarting',
    # UpArrow
    'alternate': 'UpArrow', 'up': 'UpArrow', 'alt': 'UpArrow',
    # NWPen / Handwriting
    'handwriting': 'NWPen', 'nwpen': 'NWPen', 'pen': 'NWPen',
    'pencil': 'NWPen', 'stylus': 'NWPen',
    # Pin / Location
    'location': 'Pin', 'pin': 'Pin', 'marker': 'Pin',
    # Person
    'person': 'Person', 'contact': 'Person', 'people': 'Person',
}

_COMPOUND_MAP = {
    # Arrow
    'normalselect': 'Arrow', 'leftptr': 'Arrow', 'basearrow': 'Arrow',
    'arrowcursor': 'Arrow', 'mainarrow': 'Arrow', 'topleftarrow': 'Arrow',
    # NWPen / Handwriting — BEFORE Hand so it matches first
    'handwriting': 'NWPen', 'inkpen': 'NWPen', 'freeform': 'NWPen',
    # Hand
    'linkselect': 'Hand', 'pointinghand': 'Hand', 'handpointer': 'Hand',
    'openhand': 'Hand', 'clickhand': 'Hand', 'weblink': 'Hand',
    # IBeam
    'textselect': 'IBeam', 'textcursor': 'IBeam', 'editcursor': 'IBeam',
    'typecursor': 'IBeam', 'inserttext': 'IBeam', 'typetext': 'IBeam',
    # Wait
    'hourglass': 'Wait', 'fullbusy': 'Wait', 'busycursor': 'Wait',
    'waitcursor': 'Wait',
    # Cross
    'precisionselect': 'Cross', 'exactselect': 'Cross',
    'crosshaircur': 'Cross',
    # No
    'notallowed': 'No', 'unavailable': 'No', 'unavail': 'No',
    'forbidden': 'No', 'crossedcircle': 'No', 'nodrop': 'No',
    'cannotdrop': 'No', 'restricted': 'No', 'prohibited': 'No',
    # SizeNWSE
    'sizenw': 'SizeNWSE', 'sizese': 'SizeNWSE', 'diag1': 'SizeNWSE',
    'dgn1': 'SizeNWSE', 'diagonalresize1': 'SizeNWSE', 'diagonal1': 'SizeNWSE',
    'sizefdiag': 'SizeNWSE', 'nwseresize': 'SizeNWSE', 'diagleft': 'SizeNWSE',
    'bddoublearrow': 'SizeNWSE', 'topleftcorner': 'SizeNWSE',
    'bottomrightcorner': 'SizeNWSE',
    # SizeNESW
    'sizene': 'SizeNESW', 'sizesw': 'SizeNESW', 'diag2': 'SizeNESW',
    'dgn2': 'SizeNESW', 'diagonalresize2': 'SizeNESW', 'diagonal2': 'SizeNESW',
    'sizebdiag': 'SizeNESW', 'neswresize': 'SizeNESW', 'diagright': 'SizeNESW',
    'fddoublearrow': 'SizeNESW', 'toprightcorner': 'SizeNESW',
    'bottomleftcorner': 'SizeNESW',
    # SizeWE
    'horizontalresize': 'SizeWE', 'hresize': 'SizeWE', 'leftright': 'SizeWE',
    'colresize': 'SizeWE', 'ewresize': 'SizeWE', 'sbhdoublearrow': 'SizeWE',
    'hdoublearrow': 'SizeWE', 'horzresize': 'SizeWE', 'resizehoriz': 'SizeWE',
    'resizehorizontal': 'SizeWE', 'splith': 'SizeWE',
    # SizeNS
    'verticalresize': 'SizeNS', 'vresize': 'SizeNS', 'updown': 'SizeNS',
    'rowresize': 'SizeNS', 'nsresize': 'SizeNS', 'sbvdoublearrow': 'SizeNS',
    'vdoublearrow': 'SizeNS', 'vertresize': 'SizeNS', 'resizevert': 'SizeNS',
    'resizevertical': 'SizeNS', 'splitv': 'SizeNS',
    # SizeAll
    'allmove': 'SizeAll', 'fourway': 'SizeAll', '4way': 'SizeAll',
    'movecursor': 'SizeAll', 'dragmove': 'SizeAll', 'allscroll': 'SizeAll',
    'closedhand': 'SizeAll', 'moveall': 'SizeAll', 'dndmove': 'SizeAll',
    # AppStarting
    'appstarting': 'AppStarting', 'appstart': 'AppStarting',
    'workinginbackground': 'AppStarting', 'backgroundbusy': 'AppStarting',
    'busyarrow': 'AppStarting', 'halfbusy': 'AppStarting',
    'leftptrwatch': 'AppStarting', 'arrowbusy': 'AppStarting',
    'waitarrow': 'AppStarting', 'progressarrow': 'AppStarting',
    'bgworking': 'AppStarting',
    # Help
    'helpselect': 'Help', 'whatsthis': 'Help', 'questionarrow': 'Help',
    'questionmark': 'Help', 'helpcursor': 'Help', 'dndask': 'Help',
    # UpArrow
    'uparrow': 'UpArrow', 'alternateselect': 'UpArrow', 'centerptr': 'UpArrow',
    'altselect': 'UpArrow', 'altuparrow': 'UpArrow',
    # Pin
    'mappin': 'Pin', 'locationselect': 'Pin', 'geopin': 'Pin',
    # Person
    'personselect': 'Person', 'selectperson': 'Person',
}

_TOKEN_PAIR_MAP = {
    ('text', 'select'): 'IBeam',
    ('text', 'cursor'): 'IBeam',
    ('text', 'edit'):    'IBeam',
    ('normal', 'select'): 'Arrow',
    ('link', 'select'): 'Hand',
    ('help', 'select'): 'Help',
    ('precision', 'select'): 'Cross',
    ('alternate', 'select'): 'UpArrow',
    ('not', 'allowed'): 'No',
    ('size', 'all'): 'SizeAll',
    ('move', 'all'): 'SizeAll',
    ('no', 'drop'): 'No',
    ('left', 'right'): 'SizeWE',
    ('up', 'down'): 'SizeNS',
    ('up', 'arrow'): 'UpArrow',
    ('app', 'starting'): 'AppStarting',
    ('location', 'select'): 'Pin',
    ('person', 'select'): 'Person',
    ('hand', 'writing'): 'NWPen',
}

_NUMBERED_ORDER = [
    'Arrow', 'Help', 'AppStarting', 'Wait', 'Cross', 'IBeam',
    'SizeNWSE', 'SizeNESW', 'SizeWE', 'SizeNS', 'SizeAll', 'No', 'Hand',
    'UpArrow', 'NWPen', 'Pin', 'Person',
]


def _filename_hint(filepath):
    """
    Filename-based cursor type detection.
    Strategy:
      1. Strip common prefixes (aero_, win_, cursor_, etc.)
      2. Split into tokens (camelCase, underscore, dash, space, numbers)
      3. Check token PAIRS first (highest confidence)
      4. Check compound substring patterns (long, safe patterns)
      5. Check individual tokens last (exact whole-word matches)
    """
    stem = Path(filepath).stem.lower()

    # Strip common prefixes that don't convey cursor type info
    for prefix in ('aero_', 'win_', 'cursor_', 'cur_', 'theme_', 'set_'):
        if stem.startswith(prefix):
            rest = stem[len(prefix):]
            if rest:
                stem = rest

    # Split into tokens with camelCase and number boundary splitting
    tokens = [t for t in re.split(r'[-_\s.]+', stem) if t]
    expanded = []
    for t in tokens:
        parts = re.sub(r'([a-z])([A-Z])', r'\1_\2', t).split('_')
        for p in parts:
            sub = re.split(r'(\d+)', p)
            expanded.extend(s.lower() for s in sub if s and not s.isdigit())
    tokens = expanded
    tokens = [t for t in tokens if len(t) >= 2]
    token_set = set(tokens)

    # 1. Token pair matches (highest confidence)
    for (t1, t2), role in _TOKEN_PAIR_MAP.items():
        if t1 in token_set and t2 in token_set:
            return role

    # 2. Compound substring matches
    clean = re.sub(r'[-_\s.]+', '', stem)
    for hint in sorted(_COMPOUND_MAP, key=len, reverse=True):
        if hint in clean:
            return _COMPOUND_MAP[hint]

    # 3. Exact whole-token matches
    for t in tokens:
        if t in _TOKEN_MAP:
            return _TOKEN_MAP[t]

    return ''


def _detect_numbered_scheme(filepaths):
    """
    If files are CLEARLY numbered as cursor indices (01.cur..17.cur),
    map by standard Windows order.

    STRICT rules to avoid false positives on database IDs (e.g. nat884.cur):
      - Only triggers on purely numeric filenames (like "01.cur", "13.cur")
        OR short prefix + low number (like "cursor01.cur")
      - Starting number must be 0 or 1 (cursor index, not database ID)
      - Numbers must be tightly sequential (no big gaps)
    """
    numbered = []
    for fp in filepaths:
        stem = Path(fp).stem
        # Only match PURELY numeric filenames like "01", "1", "13"
        m = re.match(r'^(\d{1,3})$', stem)
        if not m:
            # Or very short prefix + number: "cur01", "c1", but NOT "nat884"
            m = re.match(r'^[a-zA-Z]{0,3}(\d{1,2})$', stem)
        if m:
            numbered.append((int(m.group(1)), fp))

    # Need most files to be numbered, and at least 3
    if len(numbered) < len(filepaths) * 0.7 or len(numbered) < 3:
        return {}

    numbered.sort(key=lambda x: x[0])
    first_num = numbered[0][0]
    last_num  = numbered[-1][0]

    # Starting number must be low (0 or 1) — high numbers are database IDs
    if first_num > 1:
        return {}

    # Numbers must be tightly packed (no more than a few gaps)
    span = last_num - first_num + 1
    if span > len(numbered) * 1.5:
        return {}

    result = {}
    for num, fp in numbered:
        idx = num - first_num
        if 0 <= idx < len(_NUMBERED_ORDER):
            result[fp] = _NUMBERED_ORDER[idx]
    return result


def _detect_consecutive_id_scheme(filepaths):
    """
    Detect cursor packs from sites like cursors-4u.com where files have
    database IDs as names (e.g. nat884.ani through nat899.ani).

    These are converted CursorFX packs where:
      - All files share the same alphabetic prefix
      - Numbers are perfectly consecutive
      - Total count is 12-17 (standard cursor set sizes)

    Returns dict { filepath: role } or empty dict.
    """
    if len(filepaths) < 12 or len(filepaths) > 17:
        return {}

    parsed = []
    for fp in filepaths:
        stem = Path(fp).stem
        m = re.match(r'^([a-zA-Z]+)(\d+)$', stem)
        if not m:
            return {}  # ALL files must match prefix+number pattern
        parsed.append((m.group(1).lower(), int(m.group(2)), fp))

    # All must share the SAME prefix
    prefixes = set(p for p, n, f in parsed)
    if len(prefixes) != 1:
        return {}

    # Sort by number
    parsed.sort(key=lambda x: x[1])
    nums = [n for _, n, _ in parsed]

    # Must be perfectly consecutive (no gaps)
    for i in range(1, len(nums)):
        if nums[i] != nums[i-1] + 1:
            return {}

    # Starting number must be > 1 (these are database IDs, not indices)
    # If starting from 0 or 1, _detect_numbered_scheme handles it
    if nums[0] <= 1:
        return {}

    # Map by standard Windows cursor order
    result = {}
    for i, (prefix, num, fp) in enumerate(parsed):
        if i < len(_NUMBERED_ORDER):
            result[fp] = _NUMBERED_ORDER[i]
    return result


# =============================================================================
#  COMBINED SMART DETECTION
# =============================================================================

_inf_mappings_cache = {}


def smart_detect_cursor_type(filepath, with_source=False):
    """
    Cursor type detection -- filename is PRIMARY, image is fallback.
    Priority: INF cache > filename > image > hotspot > animation.
    """
    def _ret(role, src=''):
        return (role, src) if with_source else role

    if filepath in _inf_mappings_cache:
        return _ret(_inf_mappings_cache[filepath], 'scheme file')

    ext        = Path(filepath).suffix.lower()
    is_ani     = ext == '.ani'
    frames     = 1
    hotspot    = None
    img_size   = None

    try:
        with open(filepath, 'rb') as fh:
            raw = fh.read()
        if is_ani:
            frames, hotspot, img_size = _parse_ani_header(raw)
        elif ext in ('.cur', '.ico'):
            hotspot, img_size = _parse_cur_header(raw)
    except Exception:
        pass

    fn = _filename_hint(filepath)
    img = _image_shape_hint(filepath)

    hs_zone = ''
    if hotspot and img_size:
        hx, hy = hotspot
        w, h   = img_size
        if w > 0 and h > 0:
            nhx, nhy = hx / w, hy / h
            if nhx < 0.07 and nhy < 0.07:
                hs_zone = 'arrow'
            elif 0.07 <= nhx <= 0.50 and nhy < 0.22:
                hs_zone = 'hand'
            elif 0.25 < nhx < 0.75 and 0.25 < nhy < 0.75:
                hs_zone = 'center'
            elif nhy < 0.22 and 0.22 <= nhx <= 0.78:
                hs_zone = 'top_ctr'
            elif nhx < 0.22 and 0.25 < nhy < 0.75:
                hs_zone = 'left_ctr'
            elif nhx > 0.78 and 0.25 < nhy < 0.75:
                hs_zone = 'right_ctr'

    # ── Decision: filename FIRST, then image, then hotspot ───────────────────
    if fn:
        if fn == 'Wait' and img == 'Arrow':
            return _ret('AppStarting', 'filename + image refine')
        if fn == 'Arrow' and hs_zone == 'hand':
            return _ret('Hand', 'hotspot override')
        return _ret(fn, 'filename')

    if img:
        if img == 'Arrow' and hs_zone == 'hand':
            return _ret('Hand', 'image + hotspot')
        if img in ('Arrow', 'Hand') and hs_zone == 'center':
            if is_ani and frames > 2:
                return _ret('Wait', 'animated + centered')
        # Image + hotspot cross-validation: prefer image analysis
        # but adjust when hotspot strongly contradicts
        if img == 'SizeAll' and hs_zone == 'arrow':
            return _ret('Arrow', 'hotspot override on SizeAll')
        if img == 'No' and hs_zone == 'arrow':
            return _ret('Arrow', 'hotspot override on No')
        return _ret(img, 'image analysis')

    # ── Hotspot-only fallback ────────────────────────────────────────────
    if hs_zone == 'arrow':
        if is_ani and frames > 2:
            return _ret('Arrow', 'hotspot + animated')
        return _ret('Arrow', 'hotspot')
    if hs_zone == 'hand':
        return _ret('Hand', 'hotspot')
    if hs_zone == 'center':
        if is_ani and frames > 2:
            return _ret('Wait', 'animated + centered')
        return _ret('Cross', 'hotspot center')
    if hs_zone == 'top_ctr':
        return _ret('SizeNS', 'hotspot')
    if hs_zone in ('left_ctr', 'right_ctr'):
        return _ret('SizeWE', 'hotspot')

    # ── Animation-based fallback (weakest signal) ────────────────────────
    if is_ani and frames > 4:
        return _ret('Wait', 'animated fallback')

    return _ret('', '')


def smart_detect_batch(filepaths, inf_mapping=None):
    """Detect cursor types for a batch. Returns dict { filepath: (role, source) }"""
    global _inf_mappings_cache
    result = {}

    if inf_mapping:
        for fp, role in inf_mapping.items():
            if role in REGISTRY_ROLES:
                result[fp] = (role, 'scheme file')
                _inf_mappings_cache[fp] = role

    remaining = [fp for fp in filepaths if fp not in result]

    # Try standard numbered scheme (01.cur, 02.cur, ...)
    numbered = _detect_numbered_scheme(remaining)
    if numbered and len(numbered) >= len(remaining) * 0.6:
        for fp, role in numbered.items():
            if fp not in result:
                result[fp] = (role, 'numbered order')
        remaining = [fp for fp in remaining if fp not in result]

    # Try consecutive-ID scheme (nat884.ani, nat885.cur, ... from cursors-4u.com)
    if remaining:
        consec = _detect_consecutive_id_scheme(remaining)
        if consec and len(consec) >= len(remaining) * 0.6:
            for fp, role in consec.items():
                if fp not in result:
                    result[fp] = (role, 'consecutive ID order')
            remaining = [fp for fp in remaining if fp not in result]

    for fp in remaining:
        ct, src = smart_detect_cursor_type(fp, with_source=True)
        if ct:
            result[fp] = (ct, src)

    role_files = {}
    for fp, (role, src) in result.items():
        role_files.setdefault(role, []).append(fp)

    animated_roles = {'Wait', 'AppStarting'}
    for role, fps in role_files.items():
        if len(fps) > 1:
            if role in animated_roles:
                ani_files = [f for f in fps if Path(f).suffix.lower() == '.ani']
                best = ani_files[0] if ani_files else fps[0]
            else:
                cur_files = [f for f in fps if Path(f).suffix.lower() == '.cur']
                best = cur_files[0] if cur_files else fps[0]
            for f in fps:
                if f != best:
                    result.pop(f, None)

    return result


# =============================================================================
#  Archive extraction
# =============================================================================

def extract_cursors_from_archive(archive_path, extract_dir):
    ext  = Path(archive_path).suffix.lower()
    name = Path(archive_path).name
    extracted = []
    scheme_files = []
    err = ''
    inf_mapping = {}
    all_exts = CURSOR_EXTS | SCHEME_EXTS
    scheme_names = {'install.inf', 'scheme.ini', 'cursor.inf'}

    try:
        if ext == '.zip':
            with zipfile.ZipFile(archive_path, 'r') as zf:
                for member in zf.namelist():
                    mext = Path(member).suffix.lower()
                    mname = Path(member).name.lower()
                    if mext in all_exts or mname in scheme_names:
                        zf.extract(member, extract_dir)
                        src = Path(extract_dir) / member
                        dst = Path(extract_dir) / src.name
                        if src != dst and src.exists():
                            if dst.exists():
                                dst = Path(extract_dir) / (src.stem + '_' + src.parent.name + src.suffix)
                            shutil.move(str(src), str(dst))
                        if mext in CURSOR_EXTS:
                            extracted.append(str(dst))
                        else:
                            scheme_files.append(str(dst))

        elif ext in {'.tar','.gz','.bz2','.xz','.tgz','.tbz2'} or \
             name.endswith(('.tar.gz','.tar.bz2','.tar.xz')):
            with tarfile.open(archive_path, 'r:*') as tf:
                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    mext = Path(member.name).suffix.lower()
                    mname = Path(member.name).name.lower()
                    if mext in all_exts or mname in scheme_names:
                        member.name = Path(member.name).name
                        tf.extract(member, extract_dir)
                        fp = str(Path(extract_dir) / member.name)
                        if mext in CURSOR_EXTS:
                            extracted.append(fp)
                        else:
                            scheme_files.append(fp)

        elif ext == '.7z':
            if not HAS_7Z:
                err = 'py7zr not installed'
            else:
                with py7zr.SevenZipFile(archive_path, mode='r') as zf:
                    targets = [f for f in zf.getnames()
                               if Path(f).suffix.lower() in all_exts or
                               Path(f).name.lower() in scheme_names]
                    if targets:
                        zf.extract(path=extract_dir, targets=targets)
                        for t in targets:
                            src = Path(extract_dir) / t
                            dst = Path(extract_dir) / src.name
                            if src != dst and src.exists():
                                shutil.move(str(src), str(dst))
                            text = Path(t).suffix.lower()
                            if text in CURSOR_EXTS:
                                extracted.append(str(dst))
                            else:
                                scheme_files.append(str(dst))

        elif ext == '.rar':
            if not HAS_RAR:
                err = 'rarfile not installed'
            else:
                try:
                    with rarfile.RarFile(archive_path) as rf:
                        for info in rf.infolist():
                            if info.is_dir():
                                continue
                            mext = Path(info.filename).suffix.lower()
                            mname = Path(info.filename).name.lower()
                            if mext in all_exts or mname in scheme_names:
                                rf.extract(info, extract_dir)
                                src = Path(extract_dir) / info.filename
                                dst = Path(extract_dir) / src.name
                                if src != dst and src.exists():
                                    shutil.move(str(src), str(dst))
                                if mext in CURSOR_EXTS:
                                    extracted.append(str(dst))
                                else:
                                    scheme_files.append(str(dst))
                except Exception as re_err:
                    err = 'RAR error: ' + str(re_err)
        else:
            err = 'Unsupported format: ' + ext

    except Exception as exc:
        err = str(exc)

    for sf in scheme_files:
        try:
            m = _parse_inf_file(sf, extract_dir)
            inf_mapping.update(m)
        except Exception:
            pass

    return extracted, inf_mapping, err


# =============================================================================
#  Cursor thumbnail helper
# =============================================================================

def _parse_cur_image(raw):
    """Extract the first image from a .cur/.ico file as a PIL Image."""
    import io
    if len(raw) < 22:
        return None
    reserved, img_type, count = struct.unpack_from('<HHH', raw, 0)
    if img_type not in (1, 2) or count < 1:
        return None
    # ICONDIRENTRY is 16 bytes: BBBB HH II  starting at offset 6
    # Bytes 6-9: width, height, colorCount, reserved
    # Bytes 10-11: hotspotX (or planes), 12-13: hotspotY (or bitCount)
    # Bytes 14-17: bytesInRes (DWORD), 18-21: imageOffset (DWORD)
    w = raw[6] or 256
    h = raw[7] or 256
    data_size = struct.unpack_from('<I', raw, 14)[0]
    data_off  = struct.unpack_from('<I', raw, 18)[0]
    if data_off + data_size > len(raw):
        return None
    icon_data = raw[data_off:data_off + data_size]
    # Check if it's a PNG inside
    if icon_data[:8] == b'\x89PNG\r\n\x1a\n':
        return Image.open(io.BytesIO(icon_data))
    # Otherwise it's a BMP DIB
    if len(icon_data) < 40:
        return None
    bi_size = struct.unpack_from('<I', icon_data, 0)[0]
    if bi_size < 40:
        return None
    bw = struct.unpack_from('<i', icon_data, 4)[0]
    bh = struct.unpack_from('<i', icon_data, 8)[0]
    bpp = struct.unpack_from('<H', icon_data, 14)[0]
    real_h = abs(bh) // 2  # height includes XOR + AND
    if bw <= 0 or real_h <= 0:
        return None
    if bpp == 32:
        xor_start = bi_size
        xor_size = bw * real_h * 4
        if xor_start + xor_size > len(icon_data):
            return None
        img = Image.new('RGBA', (bw, real_h))
        pix = img.load()
        for y in range(real_h):
            for x in range(bw):
                off = xor_start + ((real_h - 1 - y) * bw + x) * 4
                if off + 4 <= len(icon_data):
                    b, g, r, a = icon_data[off], icon_data[off+1], icon_data[off+2], icon_data[off+3]
                    pix[x, y] = (r, g, b, a)
        return img
    return None


def _cursor_to_pixmap(filepath, size=32):
    """Try to load a cursor file (.cur/.ani/.ico) as a QPixmap for preview.
    Returns a QPixmap of the given size, or an empty QPixmap on failure."""
    from PyQt5.QtGui import QImage, QPixmap
    try:
        if not os.path.isfile(filepath):
            return QPixmap()
        ext = Path(filepath).suffix.lower()
        img = None

        # Check for PNG sidecar (created by AI generator)
        png_path = os.path.splitext(filepath)[0] + '.png'
        if os.path.isfile(png_path):
            try:
                img = Image.open(png_path)
                img.load()
            except Exception:
                img = None

        if img is None:
            try:
                with open(filepath, 'rb') as fh:
                    raw = fh.read()
            except Exception:
                return QPixmap()

            # Try ANI first-frame extraction
            if ext == '.ani':
                try:
                    img = _extract_first_frame_from_ani(raw)
                except Exception:
                    img = None

            # Try parsing as .cur/.ico raw bitmap (works for .cur, .ico,
            # and misnamed .ani files that are actually .cur)
            if img is None:
                try:
                    img = _parse_cur_image(raw)
                except Exception:
                    img = None

            # Fallback: try PIL on raw bytes, then on filepath
            if img is None:
                try:
                    import io
                    img = Image.open(io.BytesIO(raw))
                    img.load()
                except Exception:
                    try:
                        img = Image.open(filepath)
                        img.load()
                    except Exception:
                        img = None

        if img is None:
            return QPixmap()

        img = img.convert('RGBA').resize((size, size),
            Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)

        # CRITICAL: QImage does NOT copy the buffer — it just references it.
        # We must keep 'data' alive and use qimg.copy() to force a deep copy
        # before 'data' can be garbage collected, otherwise → crash.
        data = img.tobytes('raw', 'BGRA')
        qimg = QImage(data, size, size, size * 4, QImage.Format_ARGB32)
        result = QPixmap.fromImage(qimg.copy())  # .copy() = deep copy, safe
        return result
    except Exception:
        pass
    return QPixmap()


# =============================================================================
#  Threads
# =============================================================================

class InstallerThread(QThread):
    progress = pyqtSignal(int, int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self, cursor_map):
        super().__init__()
        self.cursor_map = cursor_map

    def run(self):
        try:
            import winreg
            INSTALL_DIR.mkdir(parents=True, exist_ok=True)
            installed = {}
            items = list(self.cursor_map.items())
            for i, (key, src) in enumerate(items):
                self.progress.emit(i, len(items), 'Copying  ' + Path(src).name)
                dest = INSTALL_DIR / Path(src).name
                if dest.exists() and str(dest) != src:
                    dest = INSTALL_DIR / (Path(src).stem + '_' + key + Path(src).suffix)
                shutil.copy2(src, dest)
                installed[key] = str(dest)
            self.progress.emit(len(items), len(items), 'Updating registry...')
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                                winreg.KEY_SET_VALUE) as reg:
                winreg.SetValueEx(reg, '', 0, winreg.REG_SZ, 'JGR')
                for key, dest in installed.items():
                    winreg.SetValueEx(reg, key, 0, winreg.REG_EXPAND_SZ, dest)
            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETCURSORS, 0, None, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
            self.finished.emit(True, 'Installed ' + str(len(installed)) + ' cursor(s)!')
        except Exception as exc:
            self.finished.emit(False, str(exc))


class RevertThread(QThread):
    finished = pyqtSignal(bool, str)

    def __init__(self, restore_map):
        super().__init__()
        self.restore_map = restore_map

    def run(self):
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                                winreg.KEY_ALL_ACCESS) as reg:
                winreg.SetValueEx(reg, '', 0, winreg.REG_SZ, '')
                all_roles = {k for k, _ in CURSOR_ROLES}
                for key in all_roles:
                    try:
                        winreg.SetValueEx(reg, key, 0, winreg.REG_EXPAND_SZ, '')
                    except Exception:
                        pass
                try:
                    idx = 0
                    to_delete = []
                    while True:
                        try:
                            vname, vdata, vtype = winreg.EnumValue(reg, idx)
                            if vname not in _KNOWN_CURSOR_KEYS and vname not in all_roles:
                                to_delete.append(vname)
                            idx += 1
                        except OSError:
                            break
                    for vname in to_delete:
                        try:
                            winreg.DeleteValue(reg, vname)
                        except Exception:
                            pass
                except Exception:
                    pass

            ctypes.windll.user32.SystemParametersInfoW(
                SPI_SETCURSORS, 0, None, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)
            self.finished.emit(True, 'Default cursors restored!')
        except Exception as exc:
            self.finished.emit(False, str(exc))


class AutoAssignThread(QThread):
    result = pyqtSignal(str, str, str)
    done   = pyqtSignal(int)

    def __init__(self, file_items, inf_mapping=None):
        super().__init__()
        self.file_items  = file_items
        self.inf_mapping = inf_mapping or {}

    def run(self):
        filepaths = list(self.file_items.keys())
        batch_result = smart_detect_batch(filepaths, self.inf_mapping)
        count = 0
        for fp in filepaths:
            entry = batch_result.get(fp)
            if entry:
                ct, src = entry
                if ct:
                    count += 1
                self.result.emit(fp, ct, src)
            else:
                self.result.emit(fp, '', '')
        self.done.emit(count)


# =============================================================================
#  AUTO-UPDATE SYSTEM
# =============================================================================

def _compare_versions(a, b):
    """Compare version strings like '2.1.0' > '2.0.0'. Returns 1, 0, or -1."""
    def _parts(v):
        return [int(x) for x in re.sub(r'[^0-9.]', '', v).split('.') if x]
    pa, pb = _parts(a), _parts(b)
    for x, y in zip(pa, pb):
        if x > y: return 1
        if x < y: return -1
    return len(pa) - len(pb)


class UpdateChecker(QThread):
    """Background thread that checks for a newer version of the app."""
    update_available = pyqtSignal(str, str, str)  # new_version, download_url, changelog

    def run(self):
        if not UPDATE_CHECK_URL:
            return
        try:
            import urllib.request, ssl
            ctx = ssl.create_default_context()
            req = urllib.request.Request(UPDATE_CHECK_URL, headers={
                'User-Agent': f'{APP_NAME}/{APP_VERSION}',
                'Accept': 'application/json',
            })
            with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                data = json.loads(resp.read().decode())

            # Support both GitHub Releases API and custom JSON formats
            if 'tag_name' in data:
                # GitHub Releases format
                new_ver = data['tag_name'].lstrip('vV')
                changelog = data.get('body', '')
                dl_url = ''
                for asset in data.get('assets', []):
                    name = asset.get('name', '').lower()
                    if name.endswith('.exe'):
                        dl_url = asset['browser_download_url']
                        break
                if not dl_url:
                    dl_url = data.get('html_url', '')
            else:
                # Custom JSON: {"version":"X.Y.Z","download_url":"...","changelog":"..."}
                new_ver = data.get('version', '0.0.0')
                dl_url = data.get('download_url', '')
                changelog = data.get('changelog', '')

            if _compare_versions(new_ver, APP_VERSION) > 0:
                self.update_available.emit(new_ver, dl_url, changelog)
        except Exception:
            pass  # Silently fail — update check should never break the app


class UpdateDownloader(QThread):
    """Downloads the new .exe in the background."""
    progress = pyqtSignal(int)       # percent 0-100
    finished = pyqtSignal(str)       # path to downloaded file ('' on failure)
    error    = pyqtSignal(str)       # error message

    def __init__(self, download_url):
        super().__init__()
        self.download_url = download_url

    def run(self):
        try:
            import urllib.request, ssl
            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.download_url, headers={
                'User-Agent': f'{APP_NAME}/{APP_VERSION}'})

            tmp_path = os.path.join(tempfile.gettempdir(),
                                    f'jgr_update_{os.getpid()}.exe')

            with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
                total = int(resp.headers.get('Content-Length', 0))
                downloaded = 0
                with open(tmp_path, 'wb') as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total > 0:
                            self.progress.emit(int(downloaded / total * 100))

            self.finished.emit(tmp_path)
        except Exception as exc:
            self.error.emit(str(exc))
            self.finished.emit('')


def _apply_update_and_restart(new_exe_path):
    """Launch a batch script that waits for us to exit, swaps the exe, and relaunches."""
    current_exe = sys.executable
    # If running as a script (not frozen exe), can't self-update
    if not getattr(sys, 'frozen', False):
        webbrowser.open(os.path.dirname(new_exe_path))
        return

    bat_path = os.path.join(tempfile.gettempdir(), f'jgr_update_{os.getpid()}.bat')
    bat_content = f'''@echo off
:: Wait for the app to fully close
timeout /t 2 /nobreak >nul

:: Try to replace the exe (retry a few times in case file is still locked)
set RETRIES=10
:retry
copy /y "{new_exe_path}" "{current_exe}" >nul 2>&1
if errorlevel 1 (
    set /a RETRIES-=1
    if %RETRIES% gtr 0 (
        timeout /t 1 /nobreak >nul
        goto retry
    )
    echo Update failed - file may be locked.
    pause
    goto cleanup
)

:: Relaunch the updated app
start "" "{current_exe}"

:cleanup
:: Clean up temp files
del /q "{new_exe_path}" >nul 2>&1
del /q "%~f0" >nul 2>&1
'''
    with open(bat_path, 'w') as f:
        f.write(bat_content)

    # Launch the batch script hidden (no visible cmd window)
    subprocess.Popen(
        ['cmd', '/c', bat_path],
        creationflags=0x08000000,  # CREATE_NO_WINDOW
        close_fds=True
    )


class UpdateBanner(QWidget):
    """A sleek notification banner that auto-downloads and installs updates."""

    def __init__(self, parent, new_version, download_url, changelog=''):
        super().__init__(parent)
        self.download_url = download_url
        self.new_version  = new_version
        self._downloaded  = ''
        self.setFixedHeight(0)
        self._target_h = 54
        self.setStyleSheet('background:transparent;')

        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 6, 14, 6)
        lay.setSpacing(10)

        # "NEW" badge
        self._badge = QLabel('NEW')
        self._badge.setFont(QFont('Segoe UI', 7, QFont.Bold))
        self._badge.setFixedSize(36, 18)
        self._badge.setAlignment(Qt.AlignCenter)
        self._badge.setStyleSheet(
            'color:#000;background:#00e070;border-radius:4px;letter-spacing:1px;')

        # Message
        self._msg = QLabel(f'Version {new_version} is available!')
        self._msg.setFont(QFont('Segoe UI', 9))
        self._msg.setStyleSheet('color:rgba(255,255,255,180);background:transparent;')

        # Progress bar (hidden until downloading)
        self._prog = QProgressBar()
        self._prog.setFixedSize(80, 10)
        self._prog.setRange(0, 100); self._prog.setValue(0)
        self._prog.setTextVisible(False)
        self._prog.setStyleSheet(
            'QProgressBar{background:rgba(255,255,255,12);border:none;border-radius:4px;}'
            'QProgressBar::chunk{background:#00e070;border-radius:4px;}')
        self._prog.hide()

        # Update button
        self._upd_btn = QPushButton('Update')
        self._upd_btn.setFont(QFont('Segoe UI', 8, QFont.Bold))
        self._upd_btn.setFixedSize(70, 26)
        self._upd_btn.setStyleSheet(
            'QPushButton{color:#000;background:#fff;border:none;border-radius:6px;}'
            'QPushButton:hover{background:#e0e0e0;}'
            'QPushButton:disabled{color:rgba(80,80,80,120);background:rgba(255,255,255,20);}')
        self._upd_btn.clicked.connect(self._on_update)

        # Dismiss
        dismiss = QPushButton('x')
        dismiss.setFont(QFont('Segoe UI', 9))
        dismiss.setFixedSize(22, 22)
        dismiss.setStyleSheet(
            'QPushButton{color:rgba(255,255,255,60);background:transparent;border:none;}'
            'QPushButton:hover{color:rgba(255,255,255,180);}')
        dismiss.clicked.connect(self._dismiss)

        lay.addWidget(self._badge)
        lay.addWidget(self._msg)
        lay.addStretch()
        lay.addWidget(self._prog)
        lay.addWidget(self._upd_btn)
        lay.addWidget(dismiss)

        # Slide-in animation
        self._anim = QPropertyAnimation(self, b'maximumHeight')
        self._anim.setDuration(350)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        QTimer.singleShot(200, self._slide_in)

    def _slide_in(self):
        self._anim.setStartValue(0)
        self._anim.setEndValue(self._target_h)
        self._anim.start()

    def _dismiss(self):
        self._anim.setStartValue(self.height())
        self._anim.setEndValue(0)
        self._anim.finished.connect(lambda: self.deleteLater())
        self._anim.start()

    def _on_update(self):
        if not self.download_url:
            return

        if self._downloaded:
            # Already downloaded — apply and restart
            self._msg.setText('Restarting...')
            self._upd_btn.setEnabled(False)
            QApplication.processEvents()
            _apply_update_and_restart(self._downloaded)
            QApplication.quit()
            return

        # Start downloading
        self._upd_btn.setEnabled(False)
        self._upd_btn.setText('...')
        self._msg.setText(f'Downloading v{self.new_version}...')
        self._prog.show()
        self._prog.setValue(0)

        self._dl_thread = UpdateDownloader(self.download_url)
        self._dl_thread.progress.connect(self._on_dl_progress)
        self._dl_thread.error.connect(self._on_dl_error)
        self._dl_thread.finished.connect(self._on_dl_finished)
        self._dl_thread.start()

    def _on_dl_progress(self, pct):
        self._prog.setValue(pct)

    def _on_dl_error(self, err_msg):
        self._msg.setText('Download failed — click to retry')
        self._msg.setStyleSheet('color:rgba(255,100,100,200);background:transparent;')
        self._upd_btn.setEnabled(True)
        self._upd_btn.setText('Retry')
        self._prog.hide()

    def _on_dl_finished(self, path):
        if not path:
            return  # error handler already ran
        self._downloaded = path
        self._prog.setValue(100)
        self._prog.hide()
        self._badge.setText('OK')
        self._badge.setStyleSheet(
            'color:#000;background:#00e070;border-radius:4px;letter-spacing:1px;')
        self._msg.setText(f'v{self.new_version} ready — click to install & restart')
        self._msg.setStyleSheet('color:rgba(80,230,130,220);background:transparent;')
        self._upd_btn.setEnabled(True)
        self._upd_btn.setText('Install')
        self._upd_btn.setStyleSheet(
            'QPushButton{color:#000;background:#00e070;border:none;border-radius:6px;}'
            'QPushButton:hover{background:#00cc60;}')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(255, 255, 255, 15)))
        p.setBrush(QBrush(QColor(30, 200, 100, 18)))
        p.drawRoundedRect(4, 2, self.width() - 8, self.height() - 4, 10, 10)
        p.end()


# =============================================================================
#  AI CURSOR CREATOR  —  Generate full cursor packs from a text description
# =============================================================================

# Hotspot positions for each role (x, y on a 32x32 grid)
_ROLE_HOTSPOTS = {
    'Arrow':       (0, 0),    'Help':        (0, 0),
    'AppStarting': (0, 0),    'Wait':        (16, 16),
    'Cross':       (16, 16),  'IBeam':       (16, 16),
    'SizeNWSE':    (16, 16),  'SizeNESW':    (16, 16),
    'SizeWE':      (16, 16),  'SizeNS':      (16, 16),
    'SizeAll':     (16, 16),  'No':          (16, 16),
    'Hand':        (8, 0),    'UpArrow':     (16, 0),
    'NWPen':       (0, 30),   'Pin':         (8, 30),
    'Person':      (0, 0),
}

# How to describe each cursor for the AI prompt
_ROLE_PROMPTS = {
    'Arrow':       'a standard mouse pointer arrow, pointing upper-left',
    'Help':        'a mouse pointer arrow with a small question mark next to it',
    'AppStarting': 'a mouse pointer arrow with a small spinning loading icon',
    'Wait':        'a spinning loading/busy indicator (hourglass or spinner circle)',
    'Cross':       'a precise crosshair/plus-sign target reticle',
    'IBeam':       'a text cursor I-beam (thin vertical line with serifs top and bottom)',
    'SizeNWSE':    'a double-headed diagonal arrow going from top-left to bottom-right',
    'SizeNESW':    'a double-headed diagonal arrow going from top-right to bottom-left',
    'SizeWE':      'a double-headed horizontal arrow pointing left and right',
    'SizeNS':      'a double-headed vertical arrow pointing up and down',
    'SizeAll':     'a four-way arrow cross pointing in all 4 directions (move cursor)',
    'No':          'a circle with a diagonal line through it (forbidden/not-allowed symbol)',
    'Hand':        'a pointing hand cursor with index finger pointing up (link select)',
    'UpArrow':     'an arrow pointing straight up',
    'NWPen':       'a pen or pencil cursor tilted for handwriting',
    'Pin':         'a map pin/location marker icon',
    'Person':      'a small person/user silhouette icon',
}

# Roles to generate (the main 13 most packs use, plus extras)
_GEN_ROLES_MAIN   = ['Arrow', 'Help', 'AppStarting', 'Wait', 'Cross', 'IBeam',
                      'SizeNWSE', 'SizeNESW', 'SizeWE', 'SizeNS', 'SizeAll',
                      'No', 'Hand']
_GEN_ROLES_EXTRA  = ['UpArrow', 'NWPen', 'Pin', 'Person']


def _build_cursor_prompt(theme_desc, role):
    """Build an image prompt for generating a single cursor image."""
    shape_desc = _ROLE_PROMPTS.get(role, 'a mouse cursor icon')
    return (
        f"{theme_desc} style {shape_desc}, "
        f"32x32 pixel cursor icon, transparent background, "
        f"clean sharp edges, small icon suitable for mouse cursor, "
        f"no text, centered"
    )


def _write_cur_file(img, hotspot, out_path):
    """Write a PIL Image as a Windows .cur file."""
    import io
    img = img.convert('RGBA').resize((32, 32), Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)
    W, H = img.size
    hx, hy = hotspot

    # Build DIB (device-independent bitmap) for the cursor
    pix = img.load()
    xor_data = bytearray()
    for y in range(H - 1, -1, -1):  # bottom-up
        for x in range(W):
            r, g, b, a = pix[x, y]
            xor_data.extend([b, g, r, a])

    # AND mask (1-bit, bottom-up, padded to 4-byte boundary)
    and_row_bytes = ((W + 31) // 32) * 4
    and_data = bytearray()
    for y in range(H - 1, -1, -1):
        row = bytearray(and_row_bytes)
        for x in range(W):
            a = pix[x, y][3]
            if a < 128:
                row[x // 8] |= (0x80 >> (x % 8))
        and_data.extend(row)

    # BITMAPINFOHEADER (40 bytes)
    bih = struct.pack('<IiiHHIIiiII',
        40,         # biSize
        W,          # biWidth
        H * 2,      # biHeight (XOR + AND)
        1,          # biPlanes
        32,         # biBitCount
        0,          # biCompression
        len(xor_data) + len(and_data),
        0, 0, 0, 0)

    dib = bih + bytes(xor_data) + bytes(and_data)

    # .cur file structure: ICONDIR (6 bytes) + ICONDIRENTRY (16 bytes) + DIB data
    icon_dir_entry = struct.pack('<BBBBHHII',
        W if W < 256 else 0,
        H if H < 256 else 0,
        0,          # color count
        0,          # reserved
        hx,         # hotspot X
        hy,         # hotspot Y
        len(dib),   # data size  (DWORD)
        6 + 16)     # data offset (DWORD) = header(6) + one entry(16)

    header = struct.pack('<HHH', 0, 2, 1)  # reserved, type=CUR, count=1
    with open(out_path, 'wb') as f:
        f.write(header + icon_dir_entry + dib)


def _horde_generate_image(prompt):
    """Call Stable Horde to generate an image. Returns PIL Image or raises.
    Free, no API key needed – uses anonymous access."""
    import urllib.request, ssl, io, time as _time

    ctx = ssl.create_default_context()

    # 1. Submit async generation request
    payload = json.dumps({
        'prompt': prompt,
        'params': {
            'width': 128, 'height': 128,
            'steps': 25, 'n': 1,
            'post_processing': ['GFPGAN'],
        },
        'nsfw': False,
    }).encode()

    req = urllib.request.Request(
        f'{HORDE_API_URL}/generate/async',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'apikey': HORDE_API_KEY,
        })

    try:
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            result = json.loads(resp.read())
        job_id = result.get('id')
        if not job_id:
            raise RuntimeError(f'Stable Horde did not return a job ID: {result}')
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')[:200] if hasattr(e, 'read') else ''
        raise RuntimeError(f'Stable Horde submit error (HTTP {e.code}): {body}')

    # 2. Poll for completion (up to ~3 minutes)
    for attempt in range(60):
        _time.sleep(3)
        try:
            with urllib.request.urlopen(
                    f'{HORDE_API_URL}/generate/check/{job_id}',
                    timeout=15, context=ctx) as r:
                status = json.loads(r.read())
            if status.get('done'):
                break
            if status.get('faulted'):
                raise RuntimeError('Generation faulted – try again')
        except urllib.error.HTTPError:
            continue
    else:
        raise RuntimeError('Generation timed out – the queue may be busy, try again')

    # 3. Get the finished image URL
    try:
        with urllib.request.urlopen(
                f'{HORDE_API_URL}/generate/status/{job_id}',
                timeout=30, context=ctx) as r:
            final = json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Failed to fetch result: HTTP {e.code}')

    gens = final.get('generations', [])
    if not gens:
        raise RuntimeError('No image was generated – try a different prompt')

    img_url = gens[0].get('img', '')
    if not img_url:
        raise RuntimeError('Generation completed but no image URL returned')

    # 4. Download the image
    req2 = urllib.request.Request(img_url, headers={
        'User-Agent': 'JGR-Cursor-Installer/2.2',
    })
    try:
        with urllib.request.urlopen(req2, timeout=60, context=ctx) as r2:
            img_data = r2.read()
        if len(img_data) < 100:
            raise RuntimeError('Downloaded image is too small / empty')
        return Image.open(io.BytesIO(img_data))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'Failed to download generated image: HTTP {e.code}')


class CursorGeneratorThread(QThread):
    """Background thread that generates all cursor images via Stable Horde."""
    progress    = pyqtSignal(str, int, int)   # role, current, total
    role_done   = pyqtSignal(str, str)        # role, filepath
    error       = pyqtSignal(str, str)        # role, error message
    all_done    = pyqtSignal(str, int, int)   # output_dir, success_count, total

    def __init__(self, theme_desc, output_dir, include_extra=False):
        super().__init__()
        self.theme_desc  = theme_desc
        self.output_dir  = output_dir
        self.roles       = list(_GEN_ROLES_MAIN)
        if include_extra:
            self.roles += _GEN_ROLES_EXTRA

    def run(self):
        os.makedirs(self.output_dir, exist_ok=True)
        total = len(self.roles)
        ok = 0

        for i, role in enumerate(self.roles):
            self.progress.emit(role, i + 1, total)
            prompt = _build_cursor_prompt(self.theme_desc, role)
            try:
                img = _horde_generate_image(prompt)
                img = img.convert('RGBA').resize((32, 32),
                    Image.LANCZOS if hasattr(Image, 'LANCZOS') else Image.ANTIALIAS)

                fname = f'{role}.cur'
                fpath = os.path.join(self.output_dir, fname)
                hotspot = _ROLE_HOTSPOTS.get(role, (0, 0))
                _write_cur_file(img, hotspot, fpath)
                # Save PNG sidecar for preview thumbnails
                try:
                    img.save(os.path.join(self.output_dir, f'{role}.png'), 'PNG')
                except Exception:
                    pass

                ok += 1
                self.role_done.emit(role, fpath)
            except Exception as exc:
                self.error.emit(role, str(exc))

        self.all_done.emit(self.output_dir, ok, total)


class CursorCreatorDialog(QDialog):
    """Dialog for generating AI cursor packs from a text description."""
    cursors_created = pyqtSignal(list)  # list of generated .cur file paths

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(500, 520)
        self._drag_origin = None
        self._generated   = []
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)

        panel = QWidget(); panel.setObjectName('CreatorPanel')
        panel.setStyleSheet(
            'QWidget#CreatorPanel{background:rgba(12,12,16,248);'
            'border-radius:16px;border:1px solid rgba(255,255,255,22);}')
        glow = QGraphicsDropShadowEffect()
        glow.setColor(QColor(255, 255, 255, 25))
        glow.setBlurRadius(40); glow.setOffset(0, 0)
        panel.setGraphicsEffect(glow)

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(22, 16, 22, 18); lay.setSpacing(10)

        # Title
        title_row = QHBoxLayout()
        title = QLabel('AI CURSOR CREATOR')
        title.setFont(QFont('Segoe UI', 14, QFont.Bold))
        title.setStyleSheet('color:#fff;background:transparent;letter-spacing:3px;')
        close_btn = QPushButton('X')
        close_btn.setFixedSize(26, 26); close_btn.setFont(QFont('Segoe UI', 9))
        close_btn.setStyleSheet(
            'QPushButton{color:rgba(180,180,180,140);background:rgba(255,255,255,8);'
            'border:1px solid rgba(255,255,255,18);border-radius:7px;}'
            'QPushButton:hover{color:#ff4060;border-color:#ff4060;}')
        close_btn.clicked.connect(self.close)
        title_row.addWidget(title); title_row.addStretch(); title_row.addWidget(close_btn)
        lay.addLayout(title_row)

        lay.addStretch()

        # ── Under Development overlay ──
        dev_icon = QLabel()
        dev_icon.setAlignment(Qt.AlignCenter)
        dev_icon.setFont(QFont('Segoe UI', 36))
        dev_icon.setText('\u2692')   # hammer-and-pick unicode
        dev_icon.setStyleSheet('color:rgba(100,160,255,120);background:transparent;')
        lay.addWidget(dev_icon)

        dev_title = QLabel('UNDER DEVELOPMENT')
        dev_title.setFont(QFont('Segoe UI', 16, QFont.Bold))
        dev_title.setAlignment(Qt.AlignCenter)
        dev_title.setStyleSheet('color:rgba(255,255,255,180);background:transparent;letter-spacing:4px;')
        lay.addWidget(dev_title)

        dev_sub = QLabel(
            'AI Cursor Creator is being rebuilt with a new engine.\n'
            'This feature will be available in a future update.')
        dev_sub.setFont(QFont('Segoe UI', 9))
        dev_sub.setAlignment(Qt.AlignCenter)
        dev_sub.setWordWrap(True)
        dev_sub.setStyleSheet('color:rgba(255,255,255,60);background:transparent;')
        lay.addWidget(dev_sub)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet('color:rgba(255,255,255,10);')
        sep.setFixedWidth(200)
        sep_row = QHBoxLayout(); sep_row.addStretch(); sep_row.addWidget(sep); sep_row.addStretch()
        lay.addLayout(sep_row)

        dev_hint = QLabel('In the meantime, use Browse Cursors to find\nthousands of free cursor packs to install.')
        dev_hint.setFont(QFont('Segoe UI', 8))
        dev_hint.setAlignment(Qt.AlignCenter)
        dev_hint.setStyleSheet('color:rgba(140,180,255,100);background:transparent;')
        lay.addWidget(dev_hint)

        lay.addStretch()

        # Keep these hidden but existing so the rest of the code doesn't crash
        self._theme_input = QTextEdit(); self._theme_input.hide()
        self._progress_bar = QProgressBar(); self._progress_bar.hide()
        self._progress_lbl = QLabel(''); self._progress_lbl.hide()
        self._preview_frame = QWidget()
        self._preview_grid = QGridLayout(self._preview_frame)
        self._preview_frame.hide()
        self._preview_col = 0; self._preview_row = 0
        self._gen_btn = QPushButton(); self._gen_btn.hide()
        self._install_btn = QPushButton(); self._install_btn.hide()

        root.addWidget(panel)

    def _start_generation(self):
        theme = self._theme_input.toPlainText().strip()

        if not theme:
            self._progress_lbl.setText('Please describe a cursor theme')
            self._progress_lbl.setStyleSheet('color:rgba(255,100,100,200);background:transparent;')
            return

        self._gen_btn.setEnabled(False)
        self._gen_btn.setText('Generating...')
        self._install_btn.hide()
        self._progress_bar.show()
        self._progress_bar.setValue(0)
        self._preview_frame.show()
        # Clear old previews
        while self._preview_grid.count():
            w = self._preview_grid.takeAt(0).widget()
            if w: w.deleteLater()
        self._preview_col = 0
        self._preview_row = 0
        self._generated = []

        out_dir = os.path.join(tempfile.gettempdir(), 'jgr_ai_cursors',
                               re.sub(r'[^\w\s-]', '', theme)[:30].strip())

        self._gen_thread = CursorGeneratorThread(
            theme, out_dir, include_extra=True)
        self._gen_thread.progress.connect(self._on_progress)
        self._gen_thread.role_done.connect(self._on_role_done)
        self._gen_thread.error.connect(self._on_role_error)
        self._gen_thread.all_done.connect(self._on_all_done)
        self._gen_thread.start()

    def _on_progress(self, role, current, total):
        pct = int(current / total * 100)
        self._progress_bar.setValue(pct)
        self._progress_lbl.setText(f'Generating {role}...  ({current}/{total})')
        self._progress_lbl.setStyleSheet('color:rgba(255,255,255,120);background:transparent;')

    def _on_role_done(self, role, filepath):
        self._generated.append(filepath)
        # Add preview icon to the grid
        try:
            cell = QWidget()
            cell_lay = QVBoxLayout(cell)
            cell_lay.setContentsMargins(2, 2, 2, 2)
            cell_lay.setSpacing(1)
            thumb = QLabel()
            thumb.setFixedSize(28, 28)
            thumb.setAlignment(Qt.AlignCenter)
            thumb.setStyleSheet('background:transparent;border:none;')
            try:
                pix = _cursor_to_pixmap(filepath, 28)
                if not pix.isNull():
                    thumb.setPixmap(pix)
                else:
                    thumb.setText('+')
                    thumb.setStyleSheet('color:rgba(80,230,130,120);background:transparent;')
            except Exception:
                thumb.setText('+')
                thumb.setStyleSheet('color:rgba(80,230,130,120);background:transparent;')
            lbl = QLabel(role)
            lbl.setFont(QFont('Segoe UI', 6))
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet('color:rgba(255,255,255,50);background:transparent;')
            cell_lay.addWidget(thumb, 0, Qt.AlignCenter)
            cell_lay.addWidget(lbl, 0, Qt.AlignCenter)
            self._preview_grid.addWidget(cell, self._preview_row, self._preview_col)
            self._preview_col += 1
            if self._preview_col >= 9:
                self._preview_col = 0
                self._preview_row += 1
        except Exception:
            pass

    def _on_role_error(self, role, error_msg):
        # Show an X for failed roles
        cell = QWidget()
        cell_lay = QVBoxLayout(cell)
        cell_lay.setContentsMargins(2, 2, 2, 2)
        cell_lay.setSpacing(1)
        x_lbl = QLabel('X')
        x_lbl.setFixedSize(28, 28)
        x_lbl.setAlignment(Qt.AlignCenter)
        x_lbl.setFont(QFont('Segoe UI', 10, QFont.Bold))
        x_lbl.setStyleSheet('color:rgba(255,80,80,150);background:transparent;')
        x_lbl.setToolTip(f'{role}: {error_msg}')
        lbl = QLabel(role)
        lbl.setFont(QFont('Segoe UI', 6))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet('color:rgba(255,80,80,80);background:transparent;')
        cell_lay.addWidget(x_lbl, 0, Qt.AlignCenter)
        cell_lay.addWidget(lbl, 0, Qt.AlignCenter)
        self._preview_grid.addWidget(cell, self._preview_row, self._preview_col)
        self._preview_col += 1
        if self._preview_col >= 9:
            self._preview_col = 0
            self._preview_row += 1

    def _on_all_done(self, output_dir, ok_count, total):
        self._gen_btn.setEnabled(True)
        self._gen_btn.setText('GENERATE CURSOR PACK')
        self._progress_bar.setValue(100)
        self._output_dir = output_dir

        if ok_count == 0:
            self._progress_lbl.setText('Generation failed — check your API key and try again')
            self._progress_lbl.setStyleSheet('color:rgba(255,100,100,200);background:transparent;')
        else:
            # Auto-save to user's Documents/JGR Cursors folder
            save_dir = self._save_to_documents(output_dir)
            save_note = f'  (saved to {save_dir})' if save_dir else ''
            self._progress_lbl.setText(
                f'Generated {ok_count}/{total} cursors!{save_note}')
            self._progress_lbl.setStyleSheet('color:rgba(80,230,130,200);background:transparent;')
            self._install_btn.show()
            self._install_btn.setText('INSTALL NOW')

    def _save_to_documents(self, src_dir):
        """Copy generated cursors to Documents/JGR Cursors/<theme> for the user."""
        try:
            docs = Path(os.path.expanduser('~/Documents'))
            if not docs.exists():
                docs = Path(os.path.expanduser('~'))
            theme_name = Path(src_dir).name or 'AI Cursors'
            save_dir = docs / 'JGR Cursors' / theme_name
            save_dir.mkdir(parents=True, exist_ok=True)
            for fp in self._generated:
                dest = save_dir / Path(fp).name
                shutil.copy2(fp, dest)
            return str(save_dir)
        except Exception:
            return ''

    def _install_generated(self):
        """Directly install cursors to Windows (registry + SystemParametersInfo)."""
        if not self._generated:
            return
        self._install_btn.setEnabled(False)
        self._install_btn.setText('Installing...')
        self._progress_lbl.setText('Applying cursors to Windows...')
        self._progress_lbl.setStyleSheet('color:rgba(255,255,255,120);background:transparent;')
        QApplication.processEvents()

        try:
            import winreg
            INSTALL_DIR.mkdir(parents=True, exist_ok=True)
            installed = {}
            for fp in self._generated:
                role = Path(fp).stem  # e.g. 'Arrow', 'Hand', etc.
                # Verify this is a valid cursor role
                valid_roles = {k for k, _ in CURSOR_ROLES}
                if role not in valid_roles:
                    continue
                dest = INSTALL_DIR / Path(fp).name
                shutil.copy2(fp, dest)
                installed[role] = str(dest)

            if installed:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0,
                                    winreg.KEY_SET_VALUE) as reg:
                    winreg.SetValueEx(reg, '', 0, winreg.REG_SZ, 'JGR AI')
                    for key, dest in installed.items():
                        winreg.SetValueEx(reg, key, 0, winreg.REG_EXPAND_SZ, dest)
                ctypes.windll.user32.SystemParametersInfoW(
                    SPI_SETCURSORS, 0, None, SPIF_UPDATEINIFILE | SPIF_SENDCHANGE)

                self._install_btn.setText('INSTALLED!')
                self._install_btn.setStyleSheet(
                    'QPushButton{color:#000;background:#00e888;border:none;'
                    'border-radius:9px;letter-spacing:1px;}')
                self._progress_lbl.setText(
                    f'Installed {len(installed)} cursors! Your new cursors are now active.')
                self._progress_lbl.setStyleSheet('color:rgba(80,230,130,200);background:transparent;')
                # Also send to main window so file list updates
                self.cursors_created.emit(list(self._generated))
            else:
                self._install_btn.setEnabled(True)
                self._install_btn.setText('INSTALL NOW')
                self._progress_lbl.setText('No valid cursor roles found in generated files')
                self._progress_lbl.setStyleSheet('color:rgba(255,100,100,200);background:transparent;')
        except Exception as exc:
            self._install_btn.setEnabled(True)
            self._install_btn.setText('INSTALL NOW')
            self._progress_lbl.setText(f'Install error: {exc}')
            self._progress_lbl.setStyleSheet('color:rgba(255,100,100,200);background:transparent;')

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_origin = e.globalPos() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_origin:
            self.move(e.globalPos() - self._drag_origin)
    def mouseReleaseEvent(self, e):
        self._drag_origin = None
    def paintEvent(self, _):
        pass


# =============================================================================
#  Cursor Sites dialog  (dark theme)
# =============================================================================
class SitesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedWidth(420)
        self._drag_origin = None
        self._build()

    def _build(self):
        outer = QVBoxLayout(self); outer.setContentsMargins(14,14,14,14)
        panel = QWidget(); panel.setObjectName('SPanel')
        panel.setStyleSheet(
            'QWidget#SPanel{background:rgba(14,14,18,248);'
            'border-radius:16px;border:1px solid rgba(255,255,255,30);}')
        glow = QGraphicsDropShadowEffect()
        glow.setColor(QColor(255,255,255,40)); glow.setBlurRadius(36); glow.setOffset(0,0)
        panel.setGraphicsEffect(glow)
        play = QVBoxLayout(panel); play.setContentsMargins(20,18,20,20); play.setSpacing(10)
        tr = QHBoxLayout()
        title = QLabel('Find Cursors Online')
        title.setFont(QFont('Segoe UI',13,QFont.Bold))
        title.setStyleSheet('color:#ffffff;background:transparent;')
        close = QPushButton('X'); close.setFixedSize(26,26)
        close.setFont(QFont('Segoe UI',9,QFont.Bold))
        close.setStyleSheet(
            'QPushButton{color:rgba(200,80,80,180);background:transparent;'
            'border:1px solid rgba(200,80,80,50);border-radius:6px;}'
            'QPushButton:hover{color:#ff5555;border-color:#ff5555;background:rgba(255,60,60,20);}')
        close.clicked.connect(self.close)
        tr.addWidget(title); tr.addStretch(); tr.addWidget(close)
        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet('color:rgba(255,255,255,18);')
        play.addLayout(tr); play.addWidget(sep)
        for name, url, desc in CURSOR_SITES:
            play.addWidget(self._row(name, url, desc))
        outer.addWidget(panel)

    def _row(self, name, url, desc):
        w = QWidget()
        w.setStyleSheet(
            'QWidget{background:rgba(255,255,255,5);border:1px solid rgba(255,255,255,15);border-radius:8px;}'
            'QWidget:hover{background:rgba(255,255,255,10);border-color:rgba(255,255,255,35);}')
        lay = QHBoxLayout(w); lay.setContentsMargins(12,8,12,8); lay.setSpacing(10)
        info = QVBoxLayout(); info.setSpacing(2)
        nl = QLabel(name); nl.setFont(QFont('Segoe UI',10,QFont.Bold))
        nl.setStyleSheet('color:#ffffff;background:transparent;border:none;')
        dl = QLabel(desc); dl.setFont(QFont('Segoe UI',8))
        dl.setStyleSheet('color:rgba(180,180,180,170);background:transparent;border:none;')
        info.addWidget(nl); info.addWidget(dl)
        btn = QPushButton('Open'); btn.setFixedSize(60,28)
        btn.setFont(QFont('Segoe UI',8,QFont.Bold))
        btn.setStyleSheet(
            'QPushButton{color:#000000;background:#ffffff;border:none;border-radius:6px;}'
            'QPushButton:hover{background:#e0e0e0;}')
        btn.clicked.connect(lambda checked, u=url: webbrowser.open(u))
        lay.addLayout(info); lay.addStretch(); lay.addWidget(btn)
        return w

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_origin = e.globalPos() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_origin:
            self.move(e.globalPos() - self._drag_origin)
    def mouseReleaseEvent(self, e): self._drag_origin = None
    def paintEvent(self, _): pass


# =============================================================================
#  Cursor Browse Gallery  –  scrape thumbnails from cursor sites
# =============================================================================
_GALLERY_SOURCES = [
    {
        'name': 'RW-Designer.com',
        'base': 'https://www.rw-designer.com',
        'per_page': 40,
        'download_pattern': 'https://www.rw-designer.com/cursor-downloadset/{slug}.zip',
        'categories': [
            ('All Cursor Sets',  '/cursor-library'),
            ('Single Cursors',   '/icon-library/cursors'),
            ('Animated Cursors', '/icon-library/animated-cursors'),
        ],
    },
    {
        'name': 'Cursors-4u.com',
        'base': 'https://www.cursors-4u.com',
        'per_page': 37,
        'download_pattern': None,
        'categories': [
            ('All',        '/cursor'),
            ('Sets',       '/sets'),
            ('Animated',   '/animated'),
            ('Anime',      '/anime'),
            ('Games',      '/games'),
            ('Cute',       '/cute'),
            ('Comics',     '/comic'),
            ('Pointers',   '/cursors'),
            ('Movies/TV',  '/movie_tv'),
            ('Nature',     '/nature'),
            ('Food',       '/food'),
            ('Sports',     '/sports'),
            ('Celebrity',  '/celebrity'),
            ('Holidays',   '/holidays'),
            ('Tech',       '/mechanics'),
            ('Smiley',     '/smiley'),
            ('Symbols',    '/symbols'),
        ],
    },
    {
        'name': 'VSThemes.org',
        'base': 'https://vsthemes.org',
        'per_page': 24,
        'download_pattern': None,
        'categories': [
            ('All',       '/en/cursors/'),
            ('Animated',  '/en/cursors/animated/'),
            ('Anime',     '/en/cursors/anime/'),
            ('Black',     '/en/cursors/black/'),
            ('Neon',      '/en/cursors/neon/'),
            ('Cartoons',  '/en/cursors/cartoons/'),
            ('Games',     '/en/cursors/games/'),
            ('White',     '/en/cursors/white/'),
            ('Colored',   '/en/cursors/colored/'),
            ('Static',    '/en/cursors/static/'),
            ('Mac OS',    '/en/cursors/mac_os/'),
            ('Linux',     '/en/cursors/linux/'),
        ],
    },
]


class _GalleryScraperThread(QThread):
    """Background thread that scrapes cursor thumbnails from websites."""
    items_ready  = pyqtSignal(str, list)   # (source_name, [{'title','thumb_url','link','download_url'}])
    page_info    = pyqtSignal(int)          # total_pages discovered
    error        = pyqtSignal(str, str)     # (source_name, error_msg)

    def __init__(self, source, page=0, category_path=''):
        super().__init__()
        self.source        = source
        self.page          = page
        self.category_path = category_path

    # Class-level caches keyed by category_path
    _max_offset_cache = {}   # RW-Designer: {cat_path: max_offset}
    _max_page_cache   = {}   # Cursors-4u / VSThemes: {cat_path: max_page}

    def run(self):
        import urllib.request, ssl, html as html_mod
        name = self.source['name']
        cat  = self.category_path
        _UA  = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
                '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        try:
            ctx = ssl.create_default_context()
            base = self.source['base']

            if 'RW-Designer' in name:
                per = self.source['per_page']  # 40
                if self.page == 0:
                    url = base + cat  # main page (newest ~20)
                else:
                    # Discover max offset for this category once
                    cache_key = cat
                    if cache_key not in _GalleryScraperThread._max_offset_cache:
                        req0 = urllib.request.Request(
                            base + cat, headers={'User-Agent': _UA})
                        with urllib.request.urlopen(req0, timeout=25, context=ctx) as r0:
                            mhtml = r0.read().decode('utf-8', errors='replace')
                        page_slug = cat.rstrip('/')
                        offs = [int(m) for m in re.findall(
                            r'href="' + re.escape(page_slug) + r'/set-(\d+)"', mhtml)]
                        _GalleryScraperThread._max_offset_cache[cache_key] = max(offs) if offs else 0
                    max_off = _GalleryScraperThread._max_offset_cache[cache_key]
                    # KEY FIX: page 1 → set-{max_off - 40}, page 2 → set-{max_off - 80}, etc.
                    # set-{max_off} is a partial page (often just 1-2 items), so we skip it
                    off = max_off - self.page * per
                    if off < 0:
                        self.items_ready.emit(name, [])
                        return
                    url = f'{base}{cat}/set-{off}'
                    total = (max_off // per) + 1  # page 0 = main, pages 1..N = offsets
                    self.page_info.emit(total)
            elif 'Cursors-4u' in name:
                # Cursors-4u: /cursor, /animated/p2, /sets/p3, etc.
                if self.page == 0:
                    url = base + cat
                else:
                    url = f'{base}{cat}/p{self.page + 1}'
            else:
                # VSThemes: /en/cursors/, /en/cursors/page/2/, etc.
                if self.page == 0:
                    url = base + cat
                else:
                    cat_clean = cat.rstrip('/')
                    url = f'{base}{cat_clean}/page/{self.page + 1}/'

            req = urllib.request.Request(url, headers={
                'User-Agent': _UA,
                'Accept': 'text/html,application/xhtml+xml',
                'Accept-Language': 'en-US,en;q=0.9',
            })
            # VSThemes rate-limits aggressively — retry once on 429
            import time as _time
            raw_html = None
            for _attempt in range(3):
                try:
                    with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
                        raw_html = resp.read().decode('utf-8', errors='replace')
                    break
                except urllib.request.HTTPError as he:
                    if he.code == 429 and _attempt < 2:
                        _time.sleep(4 * (_attempt + 1))  # 4s, 8s
                        continue
                    raise
            if raw_html is None:
                self.error.emit(name, 'Could not load page (rate limited)')
                return

            # Discover max page from pagination links
            if 'Cursors-4u' in name:
                cache_key = cat
                pnums = [int(m) for m in re.findall(r'href="[^"]*?/p(\d+)"', raw_html)]
                if pnums:
                    discovered = max(pnums)
                    prev = _GalleryScraperThread._max_page_cache.get(cache_key, 1)
                    _GalleryScraperThread._max_page_cache[cache_key] = max(prev, discovered)
                    self.page_info.emit(_GalleryScraperThread._max_page_cache[cache_key])
                elif cache_key not in _GalleryScraperThread._max_page_cache:
                    _GalleryScraperThread._max_page_cache[cache_key] = 50
            elif 'VSThemes' in name:
                cache_key = cat
                # VSThemes uses /page/N/ pattern in pagination links
                pnums = [int(m) for m in re.findall(r'/page/(\d+)/?', raw_html)]
                if pnums:
                    discovered = max(pnums)
                    prev = _GalleryScraperThread._max_page_cache.get(cache_key, 1)
                    _GalleryScraperThread._max_page_cache[cache_key] = max(prev, discovered)
                    self.page_info.emit(_GalleryScraperThread._max_page_cache[cache_key])
                elif cache_key not in _GalleryScraperThread._max_page_cache:
                    _GalleryScraperThread._max_page_cache[cache_key] = 40

            items = []
            if 'RW-Designer' in name:
                items = self._parse_rw_designer(raw_html, self.source)
            elif 'Cursors-4u' in name:
                items = self._parse_cursors4u(raw_html, self.source)
            else:
                items = self._parse_vsthemes(raw_html, self.source)

            self.items_ready.emit(name, items)
        except Exception as exc:
            self.error.emit(name, str(exc))

    @staticmethod
    def _parse_rw_designer(raw_html, source):
        """Parse RW-Designer cursor library page.

        HTML structure per entry:
          <a class="item" href="/cursor-set/{slug}">
            <img src="/cursor-teaser/{slug}.png" alt="...">
            <span class="setname">{Title} Cursors</span>
          </a>
        """
        import html as html_mod
        base = source['base']
        items = []
        pattern = re.compile(
            r'<a\s+class="item"\s+href="(/cursor-set/([^"]+))"[^>]*>\s*'
            r'<img\s+src="(/cursor-teaser/[^"]+)"[^>]*>\s*'
            r'<span\s+class="setname">([^<]+)</span>',
            re.IGNORECASE | re.DOTALL)
        for m in pattern.finditer(raw_html):
            slug = m.group(2)
            link = base + m.group(1)
            thumb = base + m.group(3)
            title = html_mod.unescape(m.group(4)).strip()
            title = re.sub(r'\s*Cursors\s*$', '', title).strip()
            dl = source['download_pattern'].format(slug=slug)
            if title:
                items.append({
                    'title': title, 'thumb_url': thumb,
                    'link': link, 'download_url': dl,
                })
        return items

    @staticmethod
    def _parse_cursors4u(raw_html, source):
        """Parse Cursors-4u.com cursor listing page."""
        import html as html_mod
        items = []
        card_iter = re.finditer(
            r'<article\s+class="cursor-card[^"]*">(.*?)</article>',
            raw_html, re.DOTALL | re.IGNORECASE)
        for card_m in card_iter:
            card_html = card_m.group(1)
            # Link can be /cursor/slug, /animated/slug, /games/slug, etc.
            link_m = re.search(
                r'<a\s+href="(https?://www\.cursors-4u\.com/[^"]+)"'
                r'[^>]*\s+title="([^"]*)"', card_html, re.IGNORECASE)
            if not link_m:
                # Try reversed order: title before href
                link_m = re.search(
                    r'<a\s+[^>]*title="([^"]*)"[^>]*href="(https?://www\.cursors-4u\.com/[^"]+)"',
                    card_html, re.IGNORECASE)
                if link_m:
                    link = link_m.group(2)
                    title = html_mod.unescape(link_m.group(1)).strip()
                else:
                    continue
            else:
                link  = link_m.group(1)
                title = html_mod.unescape(link_m.group(2)).strip()
            title = re.sub(r'\s*(Cursor|Set)\s*$', '', title).strip()
            img_m = re.search(r'<img\s+[^>]*src="([^"]+)"', card_html, re.IGNORECASE)
            thumb = img_m.group(1) if img_m else ''
            if title and thumb:
                items.append({
                    'title': title, 'thumb_url': thumb,
                    'link': link, 'download_url': None,
                })
        return items

    @staticmethod
    def _parse_vsthemes(raw_html, source):
        """Parse VSThemes.org cursor listing page.

        Actual card structure (full URL, not relative):
          <a href="https://vsthemes.org/en/cursors/{cat}/{id}-{slug}.html"
             class="shorty-img truncate r5x relative flex picture wmax"
             title="Cursors «Title» on Windows">
            <img src="https://play.vsthemes.org/nova/640480/..." alt="..." loading="lazy">
            <figcaption>Title</figcaption>
          </a>
        """
        import html as html_mod
        base = source['base']
        items = []
        # Match <a> tags with class "shorty-img" — href can be full or relative
        card_pattern = re.compile(
            r'<a\s+href="((?:https?://vsthemes\.org)?/en/cursors/[^"]+\.html)"'
            r'[^>]*class="shorty-img[^"]*"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE)
        for m in card_pattern.finditer(raw_html):
            href = m.group(1)
            link = href if href.startswith('http') else base + href
            card_html = m.group(2)
            # Title from <figcaption>
            fig_m = re.search(r'<figcaption[^>]*>(.*?)</figcaption>', card_html, re.DOTALL | re.I)
            title = ''
            if fig_m:
                title = re.sub(r'<[^>]+>', '', fig_m.group(1)).strip()
                title = html_mod.unescape(title)
            # Thumbnail from <img src>
            img_m = re.search(r'<img\s+[^>]*src="([^"]+)"', card_html, re.I)
            thumb = ''
            if img_m:
                thumb = img_m.group(1)
                if thumb.startswith('/'):
                    thumb = base + thumb
            if title and thumb:
                items.append({
                    'title': title, 'thumb_url': thumb,
                    'link': link, 'download_url': None,
                })
        return items


class _ImageLoaderThread(QThread):
    """Downloads a single thumbnail image in the background."""
    image_ready = pyqtSignal(str, bytes)  # (thumb_url, image_data)

    def __init__(self, url):
        super().__init__()
        self.url = url

    def run(self):
        import urllib.request, ssl
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                              'AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
                'Referer': self.url.split('/')[0] + '//' + self.url.split('/')[2] + '/',
            })
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                data = resp.read()
                if len(data) > 50:
                    self.image_ready.emit(self.url, data)
        except Exception:
            pass


class _CursorDownloadThread(QThread):
    """Downloads a cursor ZIP from RW-Designer and saves to temp dir."""
    finished_ok  = pyqtSignal(str)   # path to downloaded zip
    finished_err = pyqtSignal(str)   # error message

    def __init__(self, url, title):
        super().__init__()
        self.url   = url
        self.title = title

    def run(self):
        import urllib.request, ssl
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.url, headers={
                'User-Agent': 'JGR-Cursor-Installer/2.2',
            })
            with urllib.request.urlopen(req, timeout=60, context=ctx) as resp:
                data = resp.read()
            if len(data) < 100:
                self.finished_err.emit('Downloaded file too small — may not be a valid archive')
                return
            safe = re.sub(r'[^\w\s-]', '', self.title)[:40].strip() or 'cursors'
            tmp = os.path.join(tempfile.gettempdir(), 'jgr_browse_dl')
            os.makedirs(tmp, exist_ok=True)
            path = os.path.join(tmp, safe + '.zip')
            with open(path, 'wb') as fh:
                fh.write(data)
            self.finished_ok.emit(path)
        except Exception as exc:
            self.finished_err.emit(str(exc))


class _CursorDetailThread(QThread):
    """Scrape a cursor-set page to get individual cursor details."""
    detail_ready = pyqtSignal(dict)  # {'title','author','desc','cursors':[{'name','preview_url','dl_url'}],'zip_url'}
    error        = pyqtSignal(str)

    def __init__(self, set_url, source_name):
        super().__init__()
        self.set_url     = set_url
        self.source_name = source_name

    def run(self):
        import urllib.request, ssl, html as html_mod
        try:
            ctx = ssl.create_default_context()
            req = urllib.request.Request(self.set_url, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                              'AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
            })
            with urllib.request.urlopen(req, timeout=25, context=ctx) as resp:
                raw = resp.read().decode('utf-8', errors='replace')

            result = {'title': '', 'author': '', 'desc': '', 'cursors': [], 'zip_url': ''}

            if 'RW-Designer' in self.source_name or 'rw-designer' in self.set_url:
                base = 'https://www.rw-designer.com'
                # Title
                tm = re.search(r'<h1[^>]*>([^<]+)</h1>', raw)
                result['title'] = html_mod.unescape(tm.group(1)).strip() if tm else 'Cursor Set'
                # Author
                am = re.search(r'rel="author"[^>]*>.*?<span>([^<]+)</span>', raw, re.DOTALL)
                result['author'] = html_mod.unescape(am.group(1)).strip() if am else ''
                # ZIP download
                zm = re.search(r'href="(/cursor-downloadset/[^"]+\.zip)"', raw)
                result['zip_url'] = base + zm.group(1) if zm else ''
                # Individual cursors: /cursor-download/ID/NAME  with preview at /cursor-view/ID.png
                dl_pattern = re.compile(
                    r'href="(/cursor-download/(\d+)/([^"]+))"', re.I)
                for m in dl_pattern.finditer(raw):
                    cid   = m.group(2)
                    cname = urllib.parse.unquote(m.group(3))
                    cname = re.sub(r'\.\w+$', '', cname)  # strip extension
                    result['cursors'].append({
                        'name': cname,
                        'preview_url': f'{base}/cursor-view/{cid}.png',
                        'dl_url': base + m.group(1),
                    })
            elif 'Cursors-4u' in self.source_name or 'cursors-4u' in self.set_url:
                # Cursors-4u detail page
                tm = re.search(r'<h1[^>]*>([^<]+)</h1>', raw)
                result['title'] = html_mod.unescape(tm.group(1)).strip() if tm else 'Cursor'
                am = re.search(r'class="creator-name"[^>]*>([^<]+)<', raw)
                if not am:
                    am = re.search(r'CREATOR.*?<a[^>]*>([^<]+)</a>', raw, re.DOTALL | re.I)
                result['author'] = html_mod.unescape(am.group(1)).strip() if am else ''
                # Preview images from CDN
                img_pattern = re.compile(
                    r'<img[^>]+src="(https://cdn\.cursors-4u\.net/[^"]+)"[^>]*'
                    r'(?:alt="([^"]*)")?', re.I)
                for m in img_pattern.finditer(raw):
                    name = html_mod.unescape(m.group(2)).strip() if m.group(2) else 'Cursor'
                    result['cursors'].append({
                        'name': name,
                        'preview_url': m.group(1),
                        'dl_url': '',
                    })
            else:
                # VSThemes detail page
                tm = re.search(r'<h1[^>]*>(.*?)</h1>', raw, re.DOTALL)
                if tm:
                    result['title'] = re.sub(r'<[^>]+>', '', html_mod.unescape(tm.group(1))).strip()
                else:
                    result['title'] = 'Cursor Pack'
                am = re.search(r'class="[^"]*author[^"]*"[^>]*>([^<]+)<', raw, re.I)
                result['author'] = html_mod.unescape(am.group(1)).strip() if am else ''
                # Preview images - find large screenshots
                img_pattern = re.compile(
                    r'<img[^>]+src="(https?://[^"]*(?:uploads|screens|preview)[^"]*)"[^>]*'
                    r'(?:alt="([^"]*)")?', re.I)
                for m in img_pattern.finditer(raw):
                    name = html_mod.unescape(m.group(2)).strip() if m.group(2) else 'Preview'
                    result['cursors'].append({
                        'name': name,
                        'preview_url': m.group(1),
                        'dl_url': '',
                    })
                # Download link
                dl_m = re.search(r'href="(/engine/download[^"]+)"', raw, re.I)
                if dl_m:
                    result['zip_url'] = 'https://vsthemes.org' + dl_m.group(1)

            self.detail_ready.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class CursorDetailDialog(QDialog):
    """Shows all individual cursors in a pack with previews and download buttons."""
    archive_downloaded = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(520, 620)
        self._drag_origin = None
        self._img_loaders = []
        self._dl_threads  = []
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self); outer.setContentsMargins(14, 14, 14, 14)
        panel = QWidget(); panel.setObjectName('DetailPanel')
        panel.setStyleSheet(
            'QWidget#DetailPanel{background:rgba(12,12,16,250);'
            'border-radius:18px;border:1px solid rgba(255,255,255,25);}')
        glow = QGraphicsDropShadowEffect()
        glow.setColor(QColor(255, 255, 255, 35)); glow.setBlurRadius(36); glow.setOffset(0, 0)
        panel.setGraphicsEffect(glow)
        lay = QVBoxLayout(panel); lay.setContentsMargins(20, 14, 20, 16); lay.setSpacing(8)

        # Title row
        tr = QHBoxLayout()
        self._title_lbl = QLabel('Loading...')
        self._title_lbl.setFont(QFont('Segoe UI', 13, QFont.Bold))
        self._title_lbl.setStyleSheet('color:#fff;background:transparent;')
        close_btn = QPushButton('X'); close_btn.setFixedSize(28, 28)
        close_btn.setFont(QFont('Segoe UI', 9, QFont.Bold))
        close_btn.setStyleSheet(
            'QPushButton{color:rgba(200,80,80,180);background:transparent;'
            'border:1px solid rgba(200,80,80,50);border-radius:7px;}'
            'QPushButton:hover{color:#ff5555;border-color:#ff5555;}')
        close_btn.clicked.connect(self.close)
        tr.addWidget(self._title_lbl); tr.addStretch(); tr.addWidget(close_btn)
        lay.addLayout(tr)

        # Author / info
        self._author_lbl = QLabel('')
        self._author_lbl.setFont(QFont('Segoe UI', 9))
        self._author_lbl.setStyleSheet('color:rgba(180,200,255,180);background:transparent;')
        lay.addWidget(self._author_lbl)

        # Download all button
        self._dl_all_btn = QPushButton('DOWNLOAD FULL PACK')
        self._dl_all_btn.setFont(QFont('Segoe UI', 10, QFont.Bold))
        self._dl_all_btn.setFixedHeight(38)
        self._dl_all_btn.setStyleSheet(
            'QPushButton{color:#000;background:#fff;border:none;border-radius:10px;letter-spacing:1px;}'
            'QPushButton:hover{background:#d0d0d0;}'
            'QPushButton:disabled{color:#888;background:rgba(255,255,255,40);}')
        self._dl_all_btn.hide()
        lay.addWidget(self._dl_all_btn)

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet('color:rgba(255,255,255,12);')
        lay.addWidget(sep)

        # Cursor count
        self._count_lbl = QLabel('')
        self._count_lbl.setFont(QFont('Segoe UI', 8))
        self._count_lbl.setStyleSheet('color:rgba(255,255,255,40);background:transparent;letter-spacing:1px;')
        lay.addWidget(self._count_lbl)

        # Scrollable grid of individual cursors
        gw = QWidget(); gw.setStyleSheet('background:transparent;')
        self._grid = QGridLayout(gw)
        self._grid.setContentsMargins(4, 4, 4, 4); self._grid.setSpacing(8)
        scroll = QScrollArea(); scroll.setWidget(gw); scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            'QScrollArea{background:rgba(255,255,255,3);border:1px solid rgba(255,255,255,10);border-radius:10px;}'
            'QScrollBar:vertical{background:rgba(255,255,255,5);width:6px;border-radius:3px;}'
            'QScrollBar::handle:vertical{background:rgba(255,255,255,50);border-radius:3px;min-height:30px;}'
            'QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}')
        lay.addWidget(scroll, 1)

        # Loading
        self._loading_lbl = QLabel('Loading cursor details...')
        self._loading_lbl.setFont(QFont('Segoe UI', 9))
        self._loading_lbl.setAlignment(Qt.AlignCenter)
        self._loading_lbl.setStyleSheet('color:rgba(255,255,255,60);background:transparent;')
        lay.addWidget(self._loading_lbl)

        outer.addWidget(panel)

    def load_from_url(self, url, source_name, title=''):
        """Start loading cursor details from a URL."""
        self._title_lbl.setText(title or 'Loading...')
        self._detail_thread = _CursorDetailThread(url, source_name)
        self._detail_thread.detail_ready.connect(self._on_detail)
        self._detail_thread.error.connect(self._on_error)
        self._detail_thread.start()

    def _on_error(self, msg):
        self._loading_lbl.setText(f'Error: {msg}')
        self._loading_lbl.setStyleSheet('color:rgba(255,100,100,180);background:transparent;')

    def _on_detail(self, data):
        self._loading_lbl.hide()
        self._title_lbl.setText(data.get('title', 'Cursor Set'))
        author = data.get('author', '')
        if author:
            self._author_lbl.setText(f'by {author}')
        cursors = data.get('cursors', [])
        self._count_lbl.setText(f'{len(cursors)} CURSOR{"S" if len(cursors) != 1 else ""} IN THIS PACK')

        zip_url = data.get('zip_url', '')
        if zip_url:
            self._dl_all_btn.show()
            self._dl_all_btn.clicked.connect(
                lambda: self._download_zip(zip_url, data.get('title', 'cursors')))

        cols = 4
        for i, c in enumerate(cursors):
            card = self._make_cursor_card(c)
            self._grid.addWidget(card, i // cols, i % cols)
            # Load preview
            url = c.get('preview_url', '')
            if url:
                loader = _ImageLoaderThread(url)
                loader.image_ready.connect(self._on_thumb_loaded)
                loader.finished.connect(lambda ldr=loader: self._cleanup_loader(ldr))
                self._img_loaders.append(loader)
                loader.start()

    def _make_cursor_card(self, cursor_info):
        from PyQt5.QtGui import QPixmap
        card = QWidget(); card.setFixedSize(108, 110)
        card.setProperty('preview_url', cursor_info.get('preview_url', ''))
        card.setStyleSheet(
            'QWidget{background:rgba(255,255,255,5);border:1px solid rgba(255,255,255,12);border-radius:8px;}'
            'QWidget:hover{background:rgba(255,255,255,10);border-color:rgba(255,255,255,30);}')
        vl = QVBoxLayout(card); vl.setContentsMargins(6, 6, 6, 4); vl.setSpacing(3)
        # Preview
        thumb = QLabel(); thumb.setFixedSize(64, 64); thumb.setAlignment(Qt.AlignCenter)
        thumb.setStyleSheet('background:rgba(255,255,255,5);border:1px solid rgba(255,255,255,8);'
                           'border-radius:6px;color:rgba(255,255,255,25);')
        thumb.setText('...')
        thumb.setFont(QFont('Segoe UI', 7))
        card.setProperty('thumb_label', thumb)
        vl.addWidget(thumb, 0, Qt.AlignCenter)
        # Name
        name = QLabel(cursor_info.get('name', ''))
        name.setFont(QFont('Segoe UI', 7))
        name.setStyleSheet('color:rgba(255,255,255,160);background:transparent;border:none;')
        name.setAlignment(Qt.AlignCenter); name.setWordWrap(True); name.setMaximumHeight(22)
        vl.addWidget(name)
        return card

    def _on_thumb_loaded(self, url, data):
        from PyQt5.QtGui import QPixmap
        pixmap = QPixmap(); pixmap.loadFromData(data)
        if pixmap.isNull():
            return
        pixmap = pixmap.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        for i in range(self._grid.count()):
            item = self._grid.itemAt(i)
            if item and item.widget():
                card = item.widget()
                if card.property('preview_url') == url:
                    lbl = card.property('thumb_label')
                    if lbl:
                        lbl.setPixmap(pixmap); lbl.setText('')

    def _cleanup_loader(self, t):
        try: self._img_loaders.remove(t)
        except ValueError: pass
        t.deleteLater()

    def _download_zip(self, url, title):
        self._dl_all_btn.setEnabled(False)
        self._dl_all_btn.setText('Downloading...')
        thread = _CursorDownloadThread(url, title)
        thread.finished_ok.connect(self._on_dl_ok)
        thread.finished_err.connect(self._on_dl_err)
        thread.finished.connect(lambda thr=thread: self._cleanup_dl(thr))
        self._dl_threads.append(thread)
        thread.start()

    def _on_dl_ok(self, path):
        self._dl_all_btn.setText('Added to queue!')
        self._dl_all_btn.setStyleSheet(
            'QPushButton{color:#fff;background:rgba(0,200,100,180);border:none;'
            'border-radius:10px;letter-spacing:1px;}')
        self.archive_downloaded.emit([path])

    def _on_dl_err(self, err):
        self._dl_all_btn.setEnabled(True)
        self._dl_all_btn.setText('RETRY DOWNLOAD')

    def _cleanup_dl(self, t):
        try: self._dl_threads.remove(t)
        except ValueError: pass
        t.deleteLater()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_origin = e.globalPos() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_origin:
            self.move(e.globalPos() - self._drag_origin)
    def mouseReleaseEvent(self, e): self._drag_origin = None
    def paintEvent(self, _): pass
    def closeEvent(self, e):
        for t in self._img_loaders[:]: t.quit()
        for t in self._dl_threads[:]: t.quit()
        super().closeEvent(e)


class CursorBrowseDialog(QDialog):
    """Full-screen gallery showing cursor images scraped from cursor sites."""
    archive_downloaded = pyqtSignal(list)   # [path_to_zip] – fed to MainWindow

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(620, 760)
        self._drag_origin = None
        self._current_source_idx = 0
        self._current_page = 0
        self._current_cat_idx = 0     # category within current source
        self._total_pages = 100       # updated dynamically from scraper
        self._scrapers = []
        self._img_loaders = []
        self._dl_threads = []
        self._thumb_cache = {}
        self._gallery_items = []
        self._build_ui()
        self._load_page()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(14, 14, 14, 14)

        panel = QWidget()
        panel.setObjectName('BrowsePanel')
        panel.setStyleSheet(
            'QWidget#BrowsePanel{background:rgba(12,12,16,250);'
            'border-radius:18px;border:1px solid rgba(255,255,255,25);}')
        glow = QGraphicsDropShadowEffect()
        glow.setColor(QColor(255, 255, 255, 40))
        glow.setBlurRadius(40); glow.setOffset(0, 0)
        panel.setGraphicsEffect(glow)

        lay = QVBoxLayout(panel)
        lay.setContentsMargins(20, 16, 20, 18); lay.setSpacing(10)

        # ── Title bar ──
        title_row = QHBoxLayout()
        title = QLabel('Browse Cursors')
        title.setFont(QFont('Segoe UI', 14, QFont.Bold))
        title.setStyleSheet('color:#ffffff;background:transparent;')
        close_btn = QPushButton('X'); close_btn.setFixedSize(28, 28)
        close_btn.setFont(QFont('Segoe UI', 9, QFont.Bold))
        close_btn.setStyleSheet(
            'QPushButton{color:rgba(200,80,80,180);background:transparent;'
            'border:1px solid rgba(200,80,80,50);border-radius:7px;}'
            'QPushButton:hover{color:#ff5555;border-color:#ff5555;background:rgba(255,60,60,20);}')
        close_btn.clicked.connect(self.close)
        title_row.addWidget(title); title_row.addStretch(); title_row.addWidget(close_btn)
        lay.addLayout(title_row)

        # ── Site credit banner ──
        self._credit_lbl = QLabel()
        self._credit_lbl.setFont(QFont('Segoe UI', 9))
        self._credit_lbl.setAlignment(Qt.AlignCenter)
        self._credit_lbl.setStyleSheet(
            'color:rgba(180,220,255,200);background:rgba(60,120,220,25);'
            'border:1px solid rgba(80,140,255,40);border-radius:8px;'
            'padding:6px 10px;')
        self._credit_lbl.setOpenExternalLinks(True)
        self._credit_lbl.setTextFormat(Qt.RichText)
        lay.addWidget(self._credit_lbl)

        # ── Source tabs ──
        tab_row = QHBoxLayout(); tab_row.setSpacing(6)
        self._source_btns = []
        for i, src in enumerate(_GALLERY_SOURCES):
            btn = QPushButton(src['name'])
            btn.setFont(QFont('Segoe UI', 9, QFont.Bold))
            btn.setFixedHeight(30); btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._switch_source(idx))
            self._source_btns.append(btn)
            tab_row.addWidget(btn)
        lay.addLayout(tab_row)
        self._update_tab_styles()

        # ── Category filter row (scrollable for many categories) ──
        cat_row = QHBoxLayout(); cat_row.setSpacing(5)
        cat_label = QLabel('Filter:')
        cat_label.setFont(QFont('Segoe UI', 8))
        cat_label.setStyleSheet('color:rgba(255,255,255,80);background:transparent;')
        cat_row.addWidget(cat_label)
        self._cat_btns = []
        self._cat_container = QWidget()
        self._cat_container.setStyleSheet('background:transparent;')
        self._cat_layout = QHBoxLayout(self._cat_container)
        self._cat_layout.setContentsMargins(0, 0, 0, 0); self._cat_layout.setSpacing(4)
        cat_scroll = QScrollArea()
        cat_scroll.setWidget(self._cat_container)
        cat_scroll.setWidgetResizable(True)
        cat_scroll.setFixedHeight(34)
        cat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        cat_scroll.setStyleSheet(
            'QScrollArea{background:transparent;border:none;}'
            'QScrollBar{height:0;width:0;}')
        cat_row.addWidget(cat_scroll, 1)
        lay.addLayout(cat_row)
        self._rebuild_category_buttons()

        sep = QFrame(); sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet('color:rgba(255,255,255,15);')
        lay.addWidget(sep)

        # ── Search bar ──
        search_row = QHBoxLayout(); search_row.setSpacing(6)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText('Search cursors on RW-Designer...')
        self._search_input.setFont(QFont('Segoe UI', 9))
        self._search_input.setFixedHeight(30)
        self._search_input.setStyleSheet(
            'QLineEdit{color:#fff;background:rgba(255,255,255,6);'
            'border:1px solid rgba(255,255,255,20);border-radius:8px;padding:0 10px;}'
            'QLineEdit:focus{border-color:rgba(255,255,255,50);}')
        self._search_input.returnPressed.connect(self._do_search)
        search_btn = QPushButton('Search')
        search_btn.setFont(QFont('Segoe UI', 8, QFont.Bold))
        search_btn.setFixedSize(60, 30)
        search_btn.setStyleSheet(
            'QPushButton{color:#000;background:#fff;border:none;border-radius:8px;}'
            'QPushButton:hover{background:#d0d0d0;}')
        search_btn.clicked.connect(self._do_search)
        search_row.addWidget(self._search_input, 1)
        search_row.addWidget(search_btn)
        lay.addLayout(search_row)

        # ── Loading / status indicator ──
        self._loading_lbl = QLabel('Loading cursors...')
        self._loading_lbl.setFont(QFont('Segoe UI', 10))
        self._loading_lbl.setAlignment(Qt.AlignCenter)
        self._loading_lbl.setStyleSheet('color:rgba(255,255,255,80);background:transparent;')
        lay.addWidget(self._loading_lbl)

        # ── Scrollable gallery grid ──
        self._gallery_widget = QWidget()
        self._gallery_widget.setStyleSheet('background:transparent;')
        self._gallery_grid = QGridLayout(self._gallery_widget)
        self._gallery_grid.setContentsMargins(4, 4, 4, 4)
        self._gallery_grid.setSpacing(10)

        self._scroll = QScrollArea()
        self._scroll.setWidget(self._gallery_widget)
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet(
            'QScrollArea{background:rgba(255,255,255,3);border:1px solid rgba(255,255,255,10);border-radius:10px;}'
            'QScrollBar:vertical{background:rgba(255,255,255,5);width:6px;border-radius:3px;}'
            'QScrollBar::handle:vertical{background:rgba(255,255,255,50);border-radius:3px;min-height:30px;}'
            'QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}')
        lay.addWidget(self._scroll, 1)

        # ── Pagination ──
        page_row = QHBoxLayout(); page_row.setSpacing(10)
        self._prev_btn = QPushButton('< Prev')
        self._prev_btn.setFont(QFont('Segoe UI', 9, QFont.Bold))
        self._prev_btn.setFixedHeight(30); self._prev_btn.setEnabled(False)
        self._prev_btn.setStyleSheet(self._page_btn_style())
        self._prev_btn.clicked.connect(self._prev_page)

        self._page_lbl = QLabel('Page 1')
        self._page_lbl.setFont(QFont('Segoe UI', 9))
        self._page_lbl.setAlignment(Qt.AlignCenter)
        self._page_lbl.setStyleSheet('color:rgba(255,255,255,120);background:transparent;')

        self._next_btn = QPushButton('Next >')
        self._next_btn.setFont(QFont('Segoe UI', 9, QFont.Bold))
        self._next_btn.setFixedHeight(30)
        self._next_btn.setStyleSheet(self._page_btn_style())
        self._next_btn.clicked.connect(self._next_page)

        # Page jump input
        self._page_input = QLineEdit()
        self._page_input.setPlaceholderText('#')
        self._page_input.setFont(QFont('Segoe UI', 8))
        self._page_input.setFixedSize(42, 26)
        self._page_input.setAlignment(Qt.AlignCenter)
        self._page_input.setStyleSheet(
            'QLineEdit{color:#fff;background:rgba(255,255,255,8);'
            'border:1px solid rgba(255,255,255,20);border-radius:6px;padding:0 4px;}'
            'QLineEdit:focus{border-color:rgba(255,255,255,50);}')
        self._page_input.returnPressed.connect(self._jump_to_page)
        go_btn = QPushButton('Go')
        go_btn.setFont(QFont('Segoe UI', 7, QFont.Bold))
        go_btn.setFixedSize(30, 26)
        go_btn.setStyleSheet(
            'QPushButton{color:#000;background:#fff;border:none;border-radius:6px;}'
            'QPushButton:hover{background:#d0d0d0;}')
        go_btn.clicked.connect(self._jump_to_page)

        self._total_lbl = QLabel('')
        self._total_lbl.setFont(QFont('Segoe UI', 8))
        self._total_lbl.setStyleSheet('color:rgba(255,255,255,60);background:transparent;')

        page_row.addWidget(self._prev_btn)
        page_row.addStretch()
        page_row.addWidget(self._page_lbl)
        page_row.addWidget(self._page_input)
        page_row.addWidget(go_btn)
        page_row.addWidget(self._total_lbl)
        page_row.addStretch()
        page_row.addWidget(self._next_btn)
        lay.addLayout(page_row)

        outer.addWidget(panel)

    @staticmethod
    def _page_btn_style():
        return (
            'QPushButton{color:rgba(200,200,200,180);background:rgba(255,255,255,8);'
            'border:1px solid rgba(255,255,255,25);border-radius:8px;padding:0 14px;}'
            'QPushButton:hover{color:#ffffff;background:rgba(255,255,255,15);'
            'border-color:rgba(255,255,255,50);}'
            'QPushButton:disabled{color:rgba(100,100,100,60);'
            'border-color:rgba(255,255,255,10);background:rgba(255,255,255,3);}')

    def _update_tab_styles(self):
        for i, btn in enumerate(self._source_btns):
            if i == self._current_source_idx:
                btn.setStyleSheet(
                    'QPushButton{color:#ffffff;background:rgba(255,255,255,15);'
                    'border:1px solid rgba(255,255,255,50);border-radius:8px;padding:0 14px;}'
                    'QPushButton:hover{background:rgba(255,255,255,20);}')
            else:
                btn.setStyleSheet(
                    'QPushButton{color:rgba(180,180,180,150);background:rgba(255,255,255,5);'
                    'border:1px solid rgba(255,255,255,15);border-radius:8px;padding:0 14px;}'
                    'QPushButton:hover{color:#ffffff;background:rgba(255,255,255,10);}')

    def _rebuild_category_buttons(self):
        """Rebuild the category filter buttons for the current source."""
        # Clear old buttons
        for b in self._cat_btns:
            b.deleteLater()
        self._cat_btns.clear()
        src = _GALLERY_SOURCES[self._current_source_idx]
        cats = src.get('categories', [])
        for i, (label, _path) in enumerate(cats):
            btn = QPushButton(label)
            btn.setFont(QFont('Segoe UI', 7, QFont.Bold))
            btn.setFixedHeight(24); btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, idx=i: self._switch_category(idx))
            self._cat_btns.append(btn)
            self._cat_layout.addWidget(btn)
        self._update_cat_styles()

    def _update_cat_styles(self):
        active_ss = ('QPushButton{color:#fff;background:rgba(100,160,255,60);'
                     'border:1px solid rgba(100,160,255,100);border-radius:6px;padding:0 10px;}'
                     'QPushButton:hover{background:rgba(100,160,255,80);}')
        normal_ss = ('QPushButton{color:rgba(180,180,180,140);background:rgba(255,255,255,5);'
                     'border:1px solid rgba(255,255,255,12);border-radius:6px;padding:0 10px;}'
                     'QPushButton:hover{color:#fff;background:rgba(255,255,255,10);}')
        for i, btn in enumerate(self._cat_btns):
            btn.setStyleSheet(active_ss if i == self._current_cat_idx else normal_ss)

    def _switch_category(self, idx):
        if idx == self._current_cat_idx:
            return
        self._current_cat_idx = idx
        self._current_page = 0
        self._total_pages = 100  # reset until discovered
        self._update_cat_styles()
        self._load_page()

    def _current_category_path(self):
        """Return the URL path for the currently selected category."""
        src = _GALLERY_SOURCES[self._current_source_idx]
        cats = src.get('categories', [])
        if cats and self._current_cat_idx < len(cats):
            return cats[self._current_cat_idx][1]
        return cats[0][1] if cats else ''

    def _update_credit(self):
        src = _GALLERY_SOURCES[self._current_source_idx]
        site_url = src['base']
        self._credit_lbl.setText(
            f'All cursors by <b><a href="{site_url}" '
            f'style="color:#7db8ff;text-decoration:none;">{src["name"]}</a></b>'
            f'  —  credit to the original creators')

    def _switch_source(self, idx):
        if idx == self._current_source_idx:
            return
        self._current_source_idx = idx
        self._current_page = 0
        self._current_cat_idx = 0
        self._total_pages = 100
        self._update_tab_styles()
        self._rebuild_category_buttons()
        self._load_page()

    def _prev_page(self):
        if self._current_page > 0:
            self._current_page -= 1
            self._load_page()

    def _next_page(self):
        if self._current_page + 1 < self._total_pages:
            self._current_page += 1
            self._load_page()

    def _jump_to_page(self):
        """Jump to the page number entered by the user."""
        try:
            pg = int(self._page_input.text().strip()) - 1  # 0-indexed internally
            if pg < 0:
                pg = 0
            if pg >= self._total_pages:
                pg = self._total_pages - 1
            self._current_page = pg
            self._load_page()
            self._page_input.clear()
        except ValueError:
            pass

    def _do_search(self):
        """Filter currently loaded cursors by search term, or re-load with filter."""
        query = self._search_input.text().strip().lower()
        if not query:
            self._load_page()
            return

        if not self._gallery_items:
            self._loading_lbl.setText('Load a page first, then search')
            self._loading_lbl.setStyleSheet('color:rgba(255,200,80,150);background:transparent;')
            self._loading_lbl.show()
            return

        filtered = [it for it in self._gallery_items if query in it['title'].lower()]
        self._clear_grid()
        if not filtered:
            self._loading_lbl.setText(f'No results for "{query}" on this page — try other pages')
            self._loading_lbl.setStyleSheet('color:rgba(255,200,80,150);background:transparent;')
            self._loading_lbl.show()
            return

        self._loading_lbl.setText(f'{len(filtered)} matches for "{query}"')
        self._loading_lbl.setStyleSheet('color:rgba(140,200,255,180);background:transparent;')
        self._loading_lbl.show()

        cols = 3
        for i, item in enumerate(filtered):
            card = self._make_card(item)
            self._gallery_grid.addWidget(card, i // cols, i % cols)
        for item in filtered:
            url = item['thumb_url']
            if url in self._thumb_cache:
                self._set_thumb(url, self._thumb_cache[url])
            else:
                loader = _ImageLoaderThread(url)
                loader.image_ready.connect(self._on_thumb_loaded)
                loader.finished.connect(lambda ldr=loader: self._cleanup_img_loader(ldr))
                self._img_loaders.append(loader)
                loader.start()

    def _on_page_info(self, total):
        """Called when the scraper discovers total page count."""
        self._total_pages = total
        self._total_lbl.setText(f'of ~{total}')
        self._next_btn.setEnabled(self._current_page + 1 < total)

    def _update_page_ui(self):
        """Refresh all pagination display elements."""
        page_text  = f'Page {self._current_page + 1}'
        total_text = f'of ~{self._total_pages}'
        self._page_lbl.setText(page_text)
        self._total_lbl.setText(total_text)
        self._prev_btn.setEnabled(self._current_page > 0)
        self._next_btn.setEnabled(self._current_page + 1 < self._total_pages)
        # Force immediate repaint — schedule via timer so the event loop processes it
        QTimer.singleShot(0, lambda: (
            self._page_lbl.setText(page_text),
            self._page_lbl.update(),
            self._total_lbl.update(),
            self._prev_btn.update(),
            self._next_btn.update(),
        ))

    def _load_page(self):
        self._update_credit()
        self._loading_lbl.setText('Loading cursors...')
        self._loading_lbl.setStyleSheet('color:rgba(255,255,255,80);background:transparent;')
        self._loading_lbl.show()
        self._update_page_ui()
        # Update search placeholder based on source
        src = _GALLERY_SOURCES[self._current_source_idx]
        self._search_input.setPlaceholderText(f'Search cursors on {src["name"]}...')
        self._clear_grid()
        self._gallery_items.clear()
        # Scroll back to top
        self._scroll.verticalScrollBar().setValue(0)

        cat_path = self._current_category_path()
        scraper = _GalleryScraperThread(src, self._current_page, cat_path)
        scraper.items_ready.connect(self._on_items_ready)
        scraper.page_info.connect(self._on_page_info)
        scraper.error.connect(self._on_scrape_error)
        scraper.finished.connect(lambda: self._cleanup_thread(scraper))
        self._scrapers.append(scraper)
        scraper.start()

    def _clear_grid(self):
        while self._gallery_grid.count():
            item = self._gallery_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _cleanup_thread(self, t):
        try:
            self._scrapers.remove(t)
        except ValueError:
            pass
        t.deleteLater()

    def _on_scrape_error(self, name, msg):
        self._loading_lbl.setText(f'Could not load from {name}: {msg}')
        self._loading_lbl.setStyleSheet('color:rgba(255,100,100,180);background:transparent;')
        self._next_btn.setEnabled(False)

    def _on_items_ready(self, name, items):
        self._loading_lbl.hide()
        if not items:
            self._loading_lbl.setText('No cursors found on this page')
            self._loading_lbl.setStyleSheet('color:rgba(255,200,80,150);background:transparent;')
            self._loading_lbl.show()
            self._next_btn.setEnabled(False)
            return

        # If we got very few items, we're likely at the last page
        if len(items) < 3:
            self._next_btn.setEnabled(False)
        else:
            self._next_btn.setEnabled(self._current_page + 1 < self._total_pages)
        self._gallery_items = items
        cols = 3
        for i, item in enumerate(items):
            card = self._make_card(item)
            self._gallery_grid.addWidget(card, i // cols, i % cols)

        # "Visit site for more" prompt below the grid
        src = _GALLERY_SOURCES[self._current_source_idx]
        row_after = (len(items) // cols) + 1
        visit_lbl = QLabel(
            f'Want to see more?  Visit <a href="{src["base"]}" '
            f'style="color:#7db8ff;text-decoration:none;font-weight:bold;">'
            f'{src["name"]}</a> for the full collection')
        visit_lbl.setFont(QFont('Segoe UI', 8))
        visit_lbl.setAlignment(Qt.AlignCenter)
        visit_lbl.setStyleSheet(
            'color:rgba(180,200,255,140);background:rgba(60,120,220,12);'
            'border:1px solid rgba(80,140,255,20);border-radius:8px;'
            'padding:8px 12px;')
        visit_lbl.setOpenExternalLinks(True)
        visit_lbl.setTextFormat(Qt.RichText)
        self._gallery_grid.addWidget(visit_lbl, row_after, 0, 1, cols)

        # Start loading thumbnails
        for item in items:
            url = item['thumb_url']
            if url in self._thumb_cache:
                self._set_thumb(url, self._thumb_cache[url])
            else:
                loader = _ImageLoaderThread(url)
                loader.image_ready.connect(self._on_thumb_loaded)
                loader.finished.connect(lambda ldr=loader: self._cleanup_img_loader(ldr))
                self._img_loaders.append(loader)
                loader.start()

    def _cleanup_img_loader(self, t):
        try:
            self._img_loaders.remove(t)
        except ValueError:
            pass
        t.deleteLater()

    def _make_card(self, item):
        """Create a single cursor gallery card with thumbnail and download button."""
        from PyQt5.QtGui import QPixmap
        card = QWidget()
        card.setFixedSize(176, 190)
        card.setProperty('thumb_url', item['thumb_url'])
        card.setProperty('link', item['link'])
        card.setStyleSheet(
            'QWidget{background:rgba(255,255,255,5);'
            'border:1px solid rgba(255,255,255,15);border-radius:10px;}'
            'QWidget:hover{background:rgba(255,255,255,10);'
            'border-color:rgba(255,255,255,35);}')

        vlay = QVBoxLayout(card)
        vlay.setContentsMargins(8, 8, 8, 6)
        vlay.setSpacing(4)

        # Thumbnail placeholder
        thumb_lbl = QLabel()
        thumb_lbl.setFixedSize(160, 100)
        thumb_lbl.setAlignment(Qt.AlignCenter)
        thumb_lbl.setStyleSheet(
            'background:rgba(255,255,255,5);border:1px solid rgba(255,255,255,8);'
            'border-radius:6px;color:rgba(255,255,255,30);')
        thumb_lbl.setText('Loading...')
        thumb_lbl.setFont(QFont('Segoe UI', 8))
        card.setProperty('thumb_label', thumb_lbl)
        vlay.addWidget(thumb_lbl, 0, Qt.AlignCenter)

        # Title
        title_lbl = QLabel(item['title'])
        title_lbl.setFont(QFont('Segoe UI', 8, QFont.Bold))
        title_lbl.setStyleSheet('color:rgba(255,255,255,200);background:transparent;border:none;')
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setWordWrap(True)
        title_lbl.setMaximumHeight(26)
        vlay.addWidget(title_lbl)

        # Button row: Download + Open
        btn_row = QHBoxLayout(); btn_row.setSpacing(4)

        dl_url = item.get('download_url')
        if dl_url:
            dl_btn = QPushButton('Download')
            dl_btn.setFont(QFont('Segoe UI', 7, QFont.Bold))
            dl_btn.setFixedHeight(24); dl_btn.setCursor(Qt.PointingHandCursor)
            dl_btn.setStyleSheet(
                'QPushButton{color:#000;background:#ffffff;border:none;'
                'border-radius:6px;padding:0 8px;}'
                'QPushButton:hover{background:#d0d0d0;}'
                'QPushButton:disabled{color:#888;background:rgba(255,255,255,40);}')
            dl_btn.clicked.connect(
                lambda checked, u=dl_url, t=item['title'], b=dl_btn:
                    self._download_cursor(u, t, b))
            btn_row.addWidget(dl_btn)
        else:
            # For sites without direct download, show "Open Site" button
            open_btn = QPushButton('Open Site')
            open_btn.setFont(QFont('Segoe UI', 7, QFont.Bold))
            open_btn.setFixedHeight(24); open_btn.setCursor(Qt.PointingHandCursor)
            open_btn.setStyleSheet(
                'QPushButton{color:#000;background:#ffffff;border:none;'
                'border-radius:6px;padding:0 8px;}'
                'QPushButton:hover{background:#d0d0d0;}')
            open_btn.clicked.connect(
                lambda checked, url=item['link']: webbrowser.open(url))
            btn_row.addWidget(open_btn)

        view_btn = QPushButton('View')
        view_btn.setFont(QFont('Segoe UI', 7))
        view_btn.setFixedHeight(24); view_btn.setCursor(Qt.PointingHandCursor)
        view_btn.setStyleSheet(
            'QPushButton{color:rgba(200,200,200,180);background:rgba(255,255,255,8);'
            'border:1px solid rgba(255,255,255,20);border-radius:6px;padding:0 8px;}'
            'QPushButton:hover{color:#fff;border-color:rgba(255,255,255,40);}')
        view_btn.clicked.connect(
            lambda checked, url=item['link'], t=item['title']:
                self._open_detail(url, t))
        btn_row.addWidget(view_btn)

        vlay.addLayout(btn_row)
        return card

    def _open_detail(self, url, title):
        """Open the cursor detail viewer for a cursor set."""
        src = _GALLERY_SOURCES[self._current_source_idx]
        dlg = CursorDetailDialog(self)
        dlg.archive_downloaded.connect(self.archive_downloaded.emit)
        dlg.load_from_url(url, src['name'], title)
        dlg.move(self.x() + (self.width() - dlg.width()) // 2, self.y() + 60)
        dlg.exec_()

    def _download_cursor(self, url, title, btn):
        """Download a cursor zip pack and feed it to the main window."""
        btn.setEnabled(False)
        btn.setText('Downloading...')
        self._loading_lbl.setText(f'Downloading {title}...')
        self._loading_lbl.setStyleSheet('color:rgba(140,200,255,180);background:transparent;')
        self._loading_lbl.show()

        thread = _CursorDownloadThread(url, title)
        thread.finished_ok.connect(lambda path, b=btn, t=title: self._on_dl_ok(path, b, t))
        thread.finished_err.connect(lambda err, b=btn, t=title: self._on_dl_err(err, b, t))
        thread.finished.connect(lambda thr=thread: self._cleanup_dl_thread(thr))
        self._dl_threads.append(thread)
        thread.start()

    def _cleanup_dl_thread(self, t):
        try:
            self._dl_threads.remove(t)
        except ValueError:
            pass
        t.deleteLater()

    def _on_dl_ok(self, path, btn, title):
        btn.setText('Added!')
        btn.setStyleSheet(
            'QPushButton{color:#fff;background:rgba(0,200,100,180);border:none;'
            'border-radius:6px;padding:0 8px;}'
            'QPushButton:disabled{color:#fff;background:rgba(0,200,100,120);}')
        self._loading_lbl.setText(f'Downloaded {title} — added to install queue')
        self._loading_lbl.setStyleSheet('color:rgba(80,230,130,200);background:transparent;')
        self.archive_downloaded.emit([path])

    def _on_dl_err(self, err, btn, title):
        btn.setEnabled(True)
        btn.setText('Retry')
        self._loading_lbl.setText(f'Download failed: {err}')
        self._loading_lbl.setStyleSheet('color:rgba(255,100,100,180);background:transparent;')

    def _on_thumb_loaded(self, url, data):
        self._thumb_cache[url] = data
        self._set_thumb(url, data)

    def _set_thumb(self, url, data):
        from PyQt5.QtGui import QPixmap
        try:
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if pixmap.isNull():
                return
            pixmap = pixmap.scaled(160, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            for i in range(self._gallery_grid.count()):
                item = self._gallery_grid.itemAt(i)
                if item and item.widget():
                    card = item.widget()
                    if card.property('thumb_url') == url:
                        thumb_lbl = card.property('thumb_label')
                        if thumb_lbl and not thumb_lbl.isHidden():
                            thumb_lbl.setPixmap(pixmap)
                            thumb_lbl.setText('')
        except Exception:
            pass

    # ── Drag support ──
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_origin = e.globalPos() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_origin:
            self.move(e.globalPos() - self._drag_origin)
    def mouseReleaseEvent(self, e):
        self._drag_origin = None
    def paintEvent(self, _):
        pass

    def closeEvent(self, e):
        for t in self._scrapers[:]:
            t.quit()
        for t in self._img_loaders[:]:
            t.quit()
        for t in self._dl_threads[:]:
            t.quit()
        super().closeEvent(e)


# =============================================================================
#  Drop Zone  (dark theme)
# =============================================================================
class DropZone(QWidget):
    files_dropped    = pyqtSignal(list)
    archives_dropped = pyqtSignal(list)
    clicked          = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumHeight(115)
        self.setMaximumHeight(115)
        self._hovered = self._drag_over = False
        self._phase   = 0.0
        t = QTimer(self); t.timeout.connect(self._tick); t.start(30)

    def _tick(self):
        self._phase = (self._phase + 0.04) % (2 * math.pi)
        self.update()

    def _classify(self, urls):
        cursors, archives = [], []
        for u in urls:
            fp = u.toLocalFile(); ext = Path(fp).suffix.lower()
            if ext in CURSOR_EXTS: cursors.append(fp)
            elif ext in ARCHIVE_EXTS or any(fp.lower().endswith(s)
                    for s in ('.tar.gz','.tar.bz2','.tar.xz')):
                archives.append(fp)
        return cursors, archives

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            c, a = self._classify(e.mimeData().urls())
            if c or a:
                self._drag_over = True; self.update(); e.acceptProposedAction()
    def dragLeaveEvent(self, e): self._drag_over = False; self.update()
    def dropEvent(self, e):
        self._drag_over = False; self.update()
        c, a = self._classify(e.mimeData().urls())
        if c: self.files_dropped.emit(c)
        if a: self.archives_dropped.emit(a)
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton: self.clicked.emit()
    def enterEvent(self, e):  self._hovered = True;  self.update()
    def leaveEvent(self, e):  self._hovered = False; self.update()

    def paintEvent(self, _):
        p = QPainter(self); p.setRenderHint(QPainter.Antialiasing)
        r = self.rect().adjusted(3,3,-3,-3)
        pulse  = 0.5 + 0.5 * math.sin(self._phase)
        bg_a = 20 if self._drag_over else (12 if self._hovered else int(4+pulse*6))
        p.setBrush(QBrush(QColor(255,255,255, bg_a)))
        p.setPen(Qt.NoPen); p.drawRoundedRect(r,14,14)
        b_a = 140 if self._drag_over else (90 if self._hovered else int(35+pulse*40))
        pen = QPen(QColor(255,255,255,b_a),1.8,Qt.DashLine); pen.setDashPattern([7,4])
        p.setPen(pen); p.setBrush(Qt.NoBrush); p.drawRoundedRect(r,14,14)
        cx = r.center().x(); cy = r.center().y()
        active = self._drag_over or self._hovered
        p.setPen(QPen(QColor(255,255,255,180 if active else int(90+pulse*60))))
        p.setFont(QFont('Segoe UI Symbol',16)); p.drawText(QRect(cx-26,cy-40,52,28),Qt.AlignCenter,'+')
        p.setPen(QPen(QColor(210,210,210,200 if active else 140)))
        p.setFont(QFont('Segoe UI',10))
        p.drawText(QRect(r.left(),cy-6,r.width(),24),Qt.AlignCenter,'Drop files or archives here')
        p.setPen(QPen(QColor(140,140,140,130)))
        p.setFont(QFont('Segoe UI',8))
        p.drawText(QRect(r.left(),cy+18,r.width(),20),Qt.AlignCenter,'or click to browse')
        p.setPen(QPen(QColor(100,100,100,100)))
        p.setFont(QFont('Segoe UI',7,QFont.Bold))
        p.drawText(QRect(r.left(),r.bottom()-18,r.width(),16),Qt.AlignCenter,
                   '.cur  .ani  .ico  .zip  .rar  .7z  .tar')


# =============================================================================
#  File row  (dark theme)
# =============================================================================
class FileItem(QWidget):
    removed      = pyqtSignal(str)
    type_changed = pyqtSignal(str, str)

    def __init__(self, filepath, cursor_type, from_archive='', parent=None):
        super().__init__(parent)
        self.filepath     = filepath
        self.from_archive = from_archive
        self.setFixedHeight(48)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self._apply_style(False)

        lay = QHBoxLayout(self); lay.setContentsMargins(8,0,8,0); lay.setSpacing(7)

        # Preview thumbnail
        self._thumb = QLabel()
        self._thumb.setFixedSize(32, 32)
        self._thumb.setAlignment(Qt.AlignCenter)
        self._thumb.setStyleSheet(
            'color:rgba(255,255,255,40);background:rgba(255,255,255,5);'
            'border:1px solid rgba(255,255,255,15);border-radius:4px;')
        try:
            pix = _cursor_to_pixmap(filepath, 32)
            if pix and not pix.isNull():
                self._thumb.setPixmap(pix)
                self._thumb.setStyleSheet('background:transparent;border:none;')
            else:
                self._thumb.setText('?')
        except Exception:
            self._thumb.setText('?')
        lay.addWidget(self._thumb)

        self._combo = QComboBox()
        self._combo.setFixedWidth(200); self._combo.setFixedHeight(27)
        self._combo.setStyleSheet(COMBO_STYLE)
        self._combo.addItem('-- assign type --', '')
        for key, display in CURSOR_ROLES:
            self._combo.addItem(key + '  -  ' + display, key)

        if cursor_type:
            idx = self._combo.findData(cursor_type)
            if idx >= 0: self._combo.setCurrentIndex(idx)
        self._combo.setProperty('unassigned', 'false' if cursor_type else 'true')
        self._combo.currentIndexChanged.connect(self._on_type_changed)

        fname = QLabel(Path(filepath).name)
        fname.setFont(QFont('Segoe UI',9))
        fname.setStyleSheet('color:rgba(200,200,200,180);background:transparent;')
        fname.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        fname.setToolTip(filepath)
        lay.addWidget(self._combo); lay.addWidget(fname)

        if from_archive:
            badge = QLabel('[A]'); badge.setFixedWidth(24)
            badge.setFont(QFont('Segoe UI',7,QFont.Bold))
            badge.setStyleSheet('color:rgba(255,195,50,170);background:transparent;border:none;')
            badge.setToolTip('Extracted from: ' + Path(from_archive).name)
            lay.addWidget(badge)

        rm = QPushButton('X'); rm.setFixedSize(24,24)
        rm.setFont(QFont('Segoe UI',8,QFont.Bold))
        rm.setStyleSheet(
            'QPushButton{color:rgba(200,80,80,165);background:transparent;'
            'border:1px solid rgba(200,80,80,40);border-radius:5px;}'
            'QPushButton:hover{color:#ff5555;border-color:#ff5555;background:rgba(255,60,60,15);}')
        rm.clicked.connect(lambda: self.removed.emit(self.filepath))
        lay.addWidget(rm)

    def set_type(self, cursor_key):
        idx = self._combo.findData(cursor_key)
        if idx >= 0:
            self._combo.blockSignals(True)
            self._combo.setCurrentIndex(idx)
            self._combo.blockSignals(False)
            self._combo.setProperty('unassigned', 'false')
            self._combo.setStyleSheet(COMBO_STYLE)

    def _on_type_changed(self, _):
        key = self._combo.currentData() or ''
        self._combo.setProperty('unassigned', 'false' if key else 'true')
        self._combo.setStyleSheet(COMBO_STYLE)
        self.type_changed.emit(self.filepath, key)

    def current_type(self):
        return self._combo.currentData() or ''

    def _apply_style(self, hovered):
        self.setStyleSheet(
            'FileItem{background:rgba(255,255,255,10);border:1px solid rgba(255,255,255,25);border-radius:7px;}' if hovered else
            'FileItem{background:rgba(255,255,255,5);border:1px solid rgba(255,255,255,12);border-radius:7px;}')
    def enterEvent(self, e): self._apply_style(True)
    def leaveEvent(self, e): self._apply_style(False)


# =============================================================================
#  Welcome Intro Overlay
# =============================================================================
class WelcomeOverlay(QWidget):
    finished = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.setStyleSheet('background:transparent;')
        self._opacity = 1.0
        self._text_opacity = 0.0
        self._sub_opacity = 0.0
        self._elapsed = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(16)

    def _animate(self):
        self._elapsed += 16
        if self._elapsed <= 600:
            self._text_opacity = min(1.0, self._elapsed / 500.0)
        if 400 <= self._elapsed <= 900:
            self._sub_opacity = min(1.0, (self._elapsed - 400) / 400.0)
        if self._elapsed >= 2200:
            fade = min(1.0, (self._elapsed - 2200) / 500.0)
            self._opacity = 1.0 - fade
        if self._elapsed >= 2700:
            self._timer.stop()
            self.hide()
            self.finished.emit()
            return
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setOpacity(self._opacity)
        p.fillRect(self.rect(), QColor(10, 10, 14, 250))
        cx = self.width() // 2
        cy = self.height() // 2

        # Main title
        p.setOpacity(self._opacity * self._text_opacity)
        f = QFont('Segoe UI', 48, QFont.Black)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 18)
        p.setFont(f)
        p.setPen(QPen(QColor(255, 255, 255, 255)))
        p.drawText(QRect(0, cy - 60, self.width(), 70), Qt.AlignCenter, 'JGR')

        # Subtitle
        p.setOpacity(self._opacity * self._sub_opacity)
        f2 = QFont('Segoe UI', 11, QFont.Bold)
        f2.setLetterSpacing(QFont.AbsoluteSpacing, 6)
        p.setFont(f2)
        p.setPen(QPen(QColor(160, 160, 160, 200)))
        p.drawText(QRect(0, cy + 20, self.width(), 30), Qt.AlignCenter, 'CURSOR INSTALLER')

        # Version
        p.setOpacity(self._opacity * self._sub_opacity * 0.5)
        f3 = QFont('Segoe UI', 8)
        p.setFont(f3)
        p.setPen(QPen(QColor(120, 120, 120, 150)))
        p.drawText(QRect(0, cy + 55, self.width(), 20), Qt.AlignCenter, 'v' + APP_VERSION)
        p.end()


# =============================================================================
#  Main window  (dark theme)
# =============================================================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._cursor_files        = {}
        self._file_items          = {}
        self._inf_mappings        = {}
        self._drag_origin         = None
        self._phase               = 0.0
        self._tmpdir              = tempfile.mkdtemp(prefix='jgr_cursors_')
        self._auto_install_pending = False

        self.setWindowTitle(f'{APP_NAME} v{APP_VERSION}')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(560, 800)
        self._build_ui()
        self._center()
        t = QTimer(self); t.timeout.connect(self._pulse_tick); t.start(40)

        # Welcome overlay
        self._welcome = WelcomeOverlay(self)
        self._welcome.setGeometry(0, 0, self.width(), self.height())
        self._welcome.finished.connect(self._on_welcome_done)
        self._welcome.show()
        self._welcome.raise_()

        # Auto-update checker (starts after welcome finishes)
        self._update_banner = None
        self._update_timer  = None

    def _on_welcome_done(self):
        self._welcome.deleteLater()
        self._welcome = None
        # Start checking for updates once the welcome animation finishes
        self._start_update_check()

    def closeEvent(self, e):
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        super().closeEvent(e)

    # ── Auto-update ──────────────────────────────────────────────────────
    def _start_update_check(self):
        if not UPDATE_CHECK_URL:
            return
        self._run_update_check()
        # Set up periodic re-check
        self._update_timer = QTimer(self)
        self._update_timer.timeout.connect(self._run_update_check)
        self._update_timer.start(UPDATE_CHECK_SECS * 1000)

    def _run_update_check(self):
        checker = UpdateChecker(self)
        checker.update_available.connect(self._show_update_banner)
        checker.finished.connect(checker.deleteLater)
        checker.start()

    def _show_update_banner(self, new_version, download_url, changelog):
        if self._update_banner is not None:
            return  # Already showing
        self._update_banner = UpdateBanner(self.panel, new_version, download_url, changelog)
        # Insert the banner at the top of the panel layout, right after the title bar separator
        panel_layout = self.panel.layout()
        if panel_layout and panel_layout.count() >= 2:
            panel_layout.insertWidget(2, self._update_banner)
        self._set_status(f'Update v{new_version} available!', 'info')

    def _build_ui(self):
        root = QWidget(self); self.setCentralWidget(root)
        outer = QVBoxLayout(root); outer.setContentsMargins(16,16,16,16)

        self.panel = QWidget(); self.panel.setObjectName('MainPanel')
        self.panel.setStyleSheet(
            'QWidget#MainPanel{background:rgba(12,12,16,245);'
            'border-radius:18px;border:1px solid rgba(255,255,255,22);}')
        self.panel_glow = QGraphicsDropShadowEffect()
        self.panel_glow.setColor(QColor(255,255,255,30))
        self.panel_glow.setBlurRadius(44); self.panel_glow.setOffset(0,0)
        self.panel.setGraphicsEffect(self.panel_glow)

        play = QVBoxLayout(self.panel)
        play.setContentsMargins(22,18,22,20); play.setSpacing(9)

        # Title bar
        tb = QWidget(); tb.setFixedHeight(50); tb.setStyleSheet('background:transparent;')
        tblay = QHBoxLayout(tb); tblay.setContentsMargins(0,0,0,0)
        logo = QLabel('JGR'); logo.setFont(QFont('Segoe UI',22,QFont.Black))
        logo.setStyleSheet('color:#ffffff;background:transparent;letter-spacing:7px;')
        lg = QGraphicsDropShadowEffect()
        lg.setColor(QColor(255,255,255,80)); lg.setBlurRadius(22); lg.setOffset(0,0)
        logo.setGraphicsEffect(lg)
        sub = QLabel('CURSOR INSTALLER'); sub.setFont(QFont('Segoe UI',7,QFont.Bold))
        sub.setStyleSheet('color:rgba(255,255,255,50);background:transparent;letter-spacing:4px;')
        lc = QVBoxLayout(); lc.setSpacing(1); lc.addWidget(logo); lc.addWidget(sub)

        def ctrl(ch, hc):
            b = QPushButton(ch); b.setFixedSize(28,28); b.setFont(QFont('Segoe UI',10))
            b.setStyleSheet(
                'QPushButton{color:rgba(180,180,180,140);background:rgba(255,255,255,8);'
                'border:1px solid rgba(255,255,255,18);border-radius:7px;}'
                'QPushButton:hover{color:' + hc + ';border-color:' + hc + ';background:rgba(255,255,255,15);}')
            return b

        min_b = ctrl('-','#ffffff'); cls_b = ctrl('X','#ff4060')
        min_b.clicked.connect(self.showMinimized); cls_b.clicked.connect(self.close)
        tblay.addLayout(lc); tblay.addStretch()
        tblay.addWidget(min_b); tblay.addSpacing(5); tblay.addWidget(cls_b)

        sep0 = QFrame(); sep0.setFrameShape(QFrame.HLine)
        sep0.setStyleSheet('color:rgba(255,255,255,14);')

        # Drop zone
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_cursor_files)
        self.drop_zone.archives_dropped.connect(self._on_archives)
        self.drop_zone.clicked.connect(self._browse)

        # Action buttons
        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        def abtn(t, c, hc, bc):
            b = QPushButton(t); b.setFont(QFont('Segoe UI',9)); b.setFixedHeight(31)
            b.setStyleSheet(
                'QPushButton{color:'+c+';background:rgba(255,255,255,6);'
                'border:1px solid '+bc+';border-radius:9px;}'
                'QPushButton:hover{color:'+hc+';background:rgba(255,255,255,12);border-color:'+hc+';}')
            return b
        br_btn  = abtn('  Select Files...','rgba(255,255,255,160)','#ffffff','rgba(255,255,255,30)')
        gal_btn = abtn('Browse Cursors','rgba(160,200,255,200)','#6db8ff','rgba(80,140,255,40)')
        sit_btn = abtn('Sites','rgba(180,180,180,180)','#ffffff','rgba(255,255,255,22)')
        ai_btn  = abtn('AI Create','rgba(180,230,180,200)','#00e888','rgba(100,230,130,40)')
        br_btn.clicked.connect(self._browse)
        gal_btn.clicked.connect(self._open_gallery)
        sit_btn.clicked.connect(self._open_sites)
        ai_btn.clicked.connect(self._open_creator)
        btn_row.addWidget(br_btn); btn_row.addWidget(gal_btn)
        btn_row.addWidget(sit_btn); btn_row.addWidget(ai_btn)

        # List header
        hdr_row = QHBoxLayout(); hdr_row.setContentsMargins(0,0,0,0); hdr_row.setSpacing(6)
        hdr_lbl = QLabel('QUEUED FILES')
        hdr_lbl.setFont(QFont('Segoe UI',7,QFont.Bold))
        hdr_lbl.setStyleSheet('color:rgba(255,255,255,40);background:transparent;letter-spacing:3px;')

        self._auto_btn = QPushButton('Auto-Assign')
        self._auto_btn.setFont(QFont('Segoe UI',8,QFont.Bold))
        self._auto_btn.setFixedHeight(21); self._auto_btn.setEnabled(False)
        self._auto_btn.setStyleSheet(
            'QPushButton{color:rgba(255,255,255,130);background:rgba(255,255,255,8);'
            'border:1px solid rgba(255,255,255,25);border-radius:5px;padding:0 8px;}'
            'QPushButton:hover{color:#ffffff;border-color:rgba(255,255,255,70);background:rgba(255,255,255,15);}'
            'QPushButton:disabled{color:rgba(255,255,255,30);border-color:rgba(255,255,255,10);}')
        self._auto_btn.clicked.connect(self._auto_assign_all)

        self._clear_btn = QPushButton('Clear All')
        self._clear_btn.setFont(QFont('Segoe UI',8))
        self._clear_btn.setFixedHeight(21); self._clear_btn.setEnabled(False)
        self._clear_btn.setStyleSheet(
            'QPushButton{color:rgba(200,80,80,148);background:transparent;'
            'border:1px solid rgba(200,80,80,35);border-radius:5px;padding:0 7px;}'
            'QPushButton:hover{color:#ff6060;border-color:rgba(255,80,80,100);background:rgba(255,50,50,10);}'
            'QPushButton:disabled{color:rgba(100,80,80,40);border-color:rgba(120,80,80,16);}')
        self._clear_btn.clicked.connect(self._clear_all)

        hdr_row.addWidget(hdr_lbl); hdr_row.addStretch()
        hdr_row.addWidget(self._auto_btn); hdr_row.addWidget(self._clear_btn)

        # Scroll area
        self._files_widget = QWidget()
        self._files_widget.setStyleSheet('background:transparent;')
        self._files_lay = QVBoxLayout(self._files_widget)
        self._files_lay.setContentsMargins(0,0,0,0); self._files_lay.setSpacing(5)
        self._empty_lbl = QLabel('No files added yet')
        self._empty_lbl.setAlignment(Qt.AlignCenter)
        self._empty_lbl.setFont(QFont('Segoe UI',9))
        self._empty_lbl.setStyleSheet('color:rgba(255,255,255,30);background:transparent;')
        self._empty_lbl.setFixedHeight(40)
        self._files_lay.addWidget(self._empty_lbl)
        self._files_lay.addStretch()

        scroll = QScrollArea(); scroll.setWidget(self._files_widget)
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(110); scroll.setMaximumHeight(190)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            'QScrollArea{background:rgba(255,255,255,3);border:1px solid rgba(255,255,255,10);border-radius:10px;}'
            'QScrollBar:vertical{background:rgba(255,255,255,5);width:5px;border-radius:3px;}'
            'QScrollBar::handle:vertical{background:rgba(255,255,255,40);border-radius:3px;}'
            'QScrollBar::add-line:vertical,QScrollBar::sub-line:vertical{height:0;}')

        self._hint = QLabel('Use the dropdowns to assign roles, or click Auto-Assign')
        self._hint.setFont(QFont('Segoe UI',8))
        self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setStyleSheet('color:rgba(255,180,60,130);background:transparent;')
        self._hint.hide()

        self._status = QLabel('Ready  -  drop files or archives to begin')
        self._status.setFont(QFont('Segoe UI',9))
        self._status.setAlignment(Qt.AlignCenter); self._status.setWordWrap(True)
        self._status.setMaximumHeight(42)
        self._status.setStyleSheet('color:rgba(160,160,160,120);background:transparent;')

        # Install button
        self._install_btn = QPushButton('INSTALL CURSORS')
        self._install_btn.setFont(QFont('Segoe UI',11,QFont.Bold))
        self._install_btn.setFixedHeight(48); self._install_btn.setEnabled(False)
        self._install_btn.clicked.connect(self._install)
        self._set_style('disabled')
        self._install_glow = QGraphicsDropShadowEffect()
        self._install_glow.setColor(QColor(255,255,255,20))
        self._install_glow.setBlurRadius(18); self._install_glow.setOffset(0,0)
        self._install_btn.setGraphicsEffect(self._install_glow)

        # Revert
        sep_rv = QFrame(); sep_rv.setFrameShape(QFrame.HLine)
        sep_rv.setStyleSheet('color:rgba(255,255,255,8);')

        self._revert_btn = QPushButton('Restore Windows Default Cursors')
        self._revert_btn.setFont(QFont('Segoe UI',9,QFont.Bold))
        self._revert_btn.setFixedHeight(38)
        self._revert_btn.setStyleSheet(
            'QPushButton{color:rgba(200,200,200,160);background:rgba(255,255,255,5);'
            'border:1px solid rgba(255,255,255,18);border-radius:10px;letter-spacing:1px;}'
            'QPushButton:hover{color:#ffffff;background:rgba(255,255,255,10);'
            'border-color:rgba(255,255,255,40);}'
            'QPushButton:disabled{color:rgba(120,120,120,60);border-color:rgba(255,255,255,8);}')
        rv_glow = QGraphicsDropShadowEffect()
        rv_glow.setColor(QColor(255,255,255,15)); rv_glow.setBlurRadius(16); rv_glow.setOffset(0,0)
        self._revert_btn.setGraphicsEffect(rv_glow)
        self._revert_btn.clicked.connect(self._revert)

        # Assemble
        play.addWidget(tb)
        play.addWidget(sep0)
        play.addWidget(self.drop_zone)
        play.addLayout(btn_row)
        play.addLayout(hdr_row)
        play.addWidget(scroll)
        play.addWidget(self._hint)
        play.addWidget(self._status)
        play.addWidget(self._install_btn)
        play.addWidget(sep_rv)
        play.addWidget(self._revert_btn)
        outer.addWidget(self.panel)

    def _center(self):
        s = QApplication.primaryScreen().geometry()
        self.move((s.width()-self.width())//2, (s.height()-self.height())//2)

    def _set_style(self, mode):
        styles = {
            'disabled':
                'QPushButton{color:rgba(120,120,120,80);background:rgba(255,255,255,5);'
                'border:1px solid rgba(255,255,255,12);border-radius:12px;letter-spacing:2px;}',
            'ready':
                'QPushButton{color:#000000;background:#ffffff;border:none;border-radius:12px;letter-spacing:2px;}'
                'QPushButton:hover{background:#e0e0e0;}',
            'success':
                'QPushButton{color:#000000;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,'
                'stop:0 #00e888,stop:1 #00cc66);border:none;border-radius:12px;letter-spacing:2px;}',
            'error':
                'QPushButton{color:#fff;background:qlineargradient(x1:0,y1:0,x2:1,y2:0,'
                'stop:0 #cc2233,stop:1 #ff3355);border:none;border-radius:12px;letter-spacing:2px;}',
        }
        self._install_btn.setStyleSheet(styles.get(mode, styles['disabled']))

    def _pulse_tick(self):
        self._phase = (self._phase + 0.05) % (2*math.pi)
        pulse = 0.5 + 0.5*math.sin(self._phase)
        self.panel_glow.setBlurRadius(42 + pulse*10)
        self.panel_glow.setColor(QColor(255,255,255,int(18+pulse*18)))

    def _set_status(self, msg, mode='normal'):
        c = {'normal':'rgba(160,160,160,120)','info':'rgba(255,255,255,160)',
             'warn':'rgba(255,200,80,180)','ok':'rgba(80,230,130,200)',
             'error':'rgba(255,78,88,200)'}
        self._status.setText(msg)
        self._status.setStyleSheet('color:'+c.get(mode,c['normal'])+';background:transparent;')

    def _open_gallery(self):
        dlg = CursorBrowseDialog(self)
        dlg.archive_downloaded.connect(self._on_archives)
        dlg.move(self.x() + (self.width() - dlg.width()) // 2, self.y() + 30)
        dlg.exec_()

    def _open_sites(self):
        dlg = SitesDialog(self)
        dlg.move(self.x()+(self.width()-dlg.sizeHint().width())//2, self.y()+110)
        dlg.exec_()

    def _open_creator(self):
        dlg = CursorCreatorDialog(self)
        dlg.cursors_created.connect(self._on_cursor_files)
        dlg.move(self.x()+(self.width()-dlg.width())//2, self.y()+60)
        dlg.exec_()

    def _browse(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, 'Select Cursor Files or Archives', '',
            'All Supported (*.cur *.ani *.ico *.zip *.rar *.7z *.tar *.gz *.bz2 *.xz)'
            ';;Cursor Files (*.cur *.ani *.ico)'
            ';;Archives (*.zip *.rar *.7z *.tar *.gz *.bz2 *.xz)'
            ';;All Files (*.*)')
        cursors  = [f for f in files if Path(f).suffix.lower() in CURSOR_EXTS]
        archives = [f for f in files if f not in cursors]
        if cursors:  self._on_cursor_files(cursors)
        if archives: self._on_archives(archives)

    def _on_cursor_files(self, files, archive_source=''):
        new_files = []
        for fp in files:
            if fp not in self._cursor_files:
                ct = self._inf_mappings.get(fp, '') or smart_detect_cursor_type(fp)
                self._cursor_files[fp] = (ct, archive_source)
                self._add_item(fp, ct, archive_source)
                new_files.append(fp)
        self._refresh_state()
        if new_files and any(fp in self._inf_mappings for fp in new_files):
            inf_count = sum(1 for fp in new_files if fp in self._inf_mappings)
            self._set_status(
                'Loaded ' + str(len(new_files)) + ' files  (' +
                str(inf_count) + ' mapped from scheme)', 'ok')

    def _on_archives(self, archives):
        for archive in archives:
            self._set_status('Extracting  ' + Path(archive).name + '...', 'info')
            QApplication.processEvents()
            subdir = Path(self._tmpdir) / Path(archive).stem
            subdir.mkdir(parents=True, exist_ok=True)
            extracted, inf_mapping, err = extract_cursors_from_archive(archive, str(subdir))
            if inf_mapping:
                self._inf_mappings.update(inf_mapping)
            if err:
                self._set_status('Warning: ' + err, 'warn')
            elif not extracted:
                self._set_status('No cursor files in  ' + Path(archive).name, 'warn')
            else:
                self._on_cursor_files(extracted, archive_source=archive)

    def _add_item(self, fp, ct, archive_source=''):
        self._empty_lbl.hide()
        item = FileItem(fp, ct, archive_source)
        item.removed.connect(self._remove_item)
        item.type_changed.connect(self._on_type_changed)
        self._file_items[fp] = item
        self._files_lay.insertWidget(self._files_lay.count()-1, item)

    def _on_type_changed(self, fp, new_type):
        if fp in self._cursor_files:
            _, src = self._cursor_files[fp]
            self._cursor_files[fp] = (new_type, src)
        self._refresh_state()

    def _remove_item(self, fp):
        self._cursor_files.pop(fp, None)
        self._file_items.pop(fp, None)
        self._inf_mappings.pop(fp, None)
        for i in range(self._files_lay.count()):
            w = self._files_lay.itemAt(i).widget()
            if isinstance(w, FileItem) and w.filepath == fp:
                w.deleteLater(); break
        if not self._cursor_files: self._empty_lbl.show()
        self._refresh_state()

    def _clear_all(self):
        for i in reversed(range(self._files_lay.count())):
            w = self._files_lay.itemAt(i).widget()
            if isinstance(w, FileItem): w.deleteLater()
        self._cursor_files.clear()
        self._file_items.clear()
        self._inf_mappings.clear()
        _inf_mappings_cache.clear()
        self._empty_lbl.show()
        self._refresh_state()

    def _auto_assign_all(self):
        if not self._file_items:
            return
        self._auto_btn.setEnabled(False)
        self._auto_btn.setText('Scanning...')
        self._set_status('Analysing cursor files...', 'info')
        self._aa_thread = AutoAssignThread(
            dict(self._file_items), inf_mapping=dict(self._inf_mappings))
        self._aa_thread.result.connect(self._on_aa_result)
        self._aa_thread.done.connect(self._on_aa_done)
        self._aa_thread.start()

    def _on_aa_result(self, fp, cursor_type, detect_source):
        if fp in self._file_items and cursor_type:
            self._file_items[fp].set_type(cursor_type)
            if detect_source:
                self._file_items[fp].setToolTip(
                    Path(fp).name + '  [detected via: ' + detect_source + ']')
            if fp in self._cursor_files:
                _, src = self._cursor_files[fp]
                self._cursor_files[fp] = (cursor_type, src)

    def _on_aa_done(self, count):
        self._auto_btn.setEnabled(True)
        self._auto_btn.setText('Auto-Assign')
        n = len(self._file_items)

        if self._auto_install_pending:
            if count == 0:
                self._auto_install_pending = False
                self._refresh_state()
                self._set_status('Could not auto-detect any types', 'warn')
            else:
                self._set_status(
                    'Detected ' + str(count) + '/' + str(n) +
                    ' types - installing...', 'info')
                self._do_install()
        else:
            self._refresh_state()
            if count == 0:
                self._set_status('Could not detect types - assign manually', 'warn')
            elif count < n:
                self._set_status('Auto-assigned ' + str(count) + '/' + str(n) +
                                 '  -  assign the rest manually', 'info')
            else:
                self._set_status('Auto-assigned all ' + str(count) + ' files!', 'ok')

    def _refresh_state(self):
        n          = len(self._file_items)
        assigned   = sum(1 for item in self._file_items.values() if item.current_type())
        unassigned = n - assigned
        has        = n > 0

        self._auto_btn.setEnabled(has)
        self._clear_btn.setEnabled(has)
        self._hint.setVisible(has and unassigned > 0)

        if not has:
            self._install_btn.setEnabled(False)
            self._set_style('disabled')
            self._install_btn.setText('INSTALL CURSORS')
            self._set_status('Ready  -  drop cursor files or a .zip pack to begin')
        elif assigned == 0:
            self._install_btn.setEnabled(True)
            self._set_style('ready')
            self._install_btn.setText('AUTO-DETECT & INSTALL')
            self._set_status(
                str(n) + (' files' if n>1 else ' file') +
                ' queued  -  click Install to auto-detect & apply', 'warn')
        else:
            self._install_btn.setEnabled(True)
            self._set_style('ready')
            self._install_btn.setText('INSTALL CURSORS')
            msg = str(assigned) + (' files' if assigned>1 else ' file') + ' assigned and ready'
            if unassigned:
                msg += '  -  ' + str(unassigned) + ' unassigned (skipped)'
            self._set_status(msg, 'info')

    def _install(self):
        assigned_count = sum(1 for item in self._file_items.values() if item.current_type())
        if assigned_count == 0 and self._file_items:
            self._auto_install_pending = True
            self._install_btn.setEnabled(False)
            self._install_btn.setText('Detecting...')
            self._set_style('disabled')
            self._set_status('Auto-detecting cursor types...', 'info')
            self._auto_btn.setEnabled(False)
            self._aa_thread = AutoAssignThread(
                dict(self._file_items), inf_mapping=dict(self._inf_mappings))
            self._aa_thread.result.connect(self._on_aa_result)
            self._aa_thread.done.connect(self._on_aa_done)
            self._aa_thread.start()
            return
        self._do_install()

    def _do_install(self):
        cursor_map = {item.current_type(): fp
                      for fp, item in self._file_items.items() if item.current_type()}
        if not cursor_map:
            self._set_status('No cursor types detected - assign manually', 'warn')
            self._refresh_state()
            return
        self._install_btn.setEnabled(False)
        self._install_btn.setText('Installing...')
        self._set_style('disabled')
        self._thread = InstallerThread(cursor_map)
        self._thread.progress.connect(
            lambda c,t,m: self._set_status('['+str(c)+'/'+str(t)+']  '+m, 'info'))
        self._thread.finished.connect(self._on_finished)
        self._thread.start()

    def _on_finished(self, ok, msg):
        self._auto_install_pending = False
        if ok:
            self._install_btn.setText('INSTALLED')
            self._set_style('success')
            self._install_glow.setColor(QColor(0,220,100,80))
            self._set_status(msg, 'ok')
        else:
            self._install_btn.setEnabled(True)
            self._install_btn.setText('INSTALL CURSORS')
            self._set_style('error')
            self._set_status('Error: ' + msg, 'error')

    def _revert(self):
        self._revert_btn.setEnabled(False)
        self._revert_btn.setText('Restoring...')
        self._set_status('Restoring default cursors...', 'info')
        self._rv_thread = RevertThread(dict(_SYSTEM_DEFAULTS))
        self._rv_thread.finished.connect(self._on_revert_done)
        self._rv_thread.start()

    def _on_revert_done(self, ok, msg):
        self._revert_btn.setEnabled(True)
        self._revert_btn.setText('Restore Windows Default Cursors')
        if ok:
            self._set_status('Default cursors restored!', 'ok')
        else:
            self._set_status('Restore error: ' + msg, 'error')

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_origin = e.globalPos() - self.frameGeometry().topLeft()
    def mouseMoveEvent(self, e):
        if e.buttons() == Qt.LeftButton and self._drag_origin:
            self.move(e.globalPos() - self._drag_origin)
    def mouseReleaseEvent(self, e): self._drag_origin = None
    def paintEvent(self, _): pass


# =============================================================================
def main():
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app.setApplicationName('JGR Cursor Installer')
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
