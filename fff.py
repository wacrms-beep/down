import subprocess
import os
import re
import sys
import glob
import shutil
import json
from datetime import datetime
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QComboBox, QTextEdit,
    QFileDialog, QProgressBar, QMessageBox, QCheckBox,
    QFrame, QSplitter, QListWidget, QListWidgetItem, QButtonGroup, QRadioButton
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor

# ─────────────────────────────────────────────────────────────────────────────
#  STYLE
# ─────────────────────────────────────────────────────────────────────────────
STYLE = """
* { font-family: 'Segoe UI', 'Helvetica Neue', sans-serif; font-size: 13px; }

QMainWindow, QWidget { background-color: #0e0e12; color: #dddde8; }

/* Sidebar */
#sidebar {
    background-color: #13131a;
    border-right: 1px solid #1f1f2e;
    min-width: 210px; max-width: 210px;
}
#logo_label  { font-size: 18px; font-weight: 700; color: #fff; letter-spacing: 1px; }
#ver_label   { font-size: 10px; color: #3a3a52; letter-spacing: 2px; }

#nav_btn {
    background: transparent; color: #7a7a99; border: none;
    border-radius: 7px; padding: 9px 12px;
    text-align: left; font-size: 13px; font-weight: 500;
}
#nav_btn:hover  { background: #1a1a26; color: #dddde8; }
#nav_btn[active="true"] {
    background: #1e1e30; color: #a78bfa;
    border-left: 3px solid #7c3aed;
    padding-left: 9px;
}

/* Content */
#content_area { background-color: #0e0e12; }
#page_title   { font-size: 21px; font-weight: 700; color: #fff; letter-spacing: -0.3px; }
#page_sub     { font-size: 11px; color: #444460; letter-spacing: 1px; }

/* Card */
#card {
    background-color: #13131a;
    border: 1px solid #1f1f2e;
    border-radius: 12px;
}
#card_title { font-size: 11px; font-weight: 600; color: #444460; letter-spacing: 1.2px; }

/* Inputs */
QLineEdit, QTextEdit {
    background: #1a1a24; color: #dddde8;
    border: 1px solid #28283a; border-radius: 7px;
    padding: 7px 11px; font-size: 13px;
    selection-background-color: #4c1d95;
}
QLineEdit:focus, QTextEdit:focus { border-color: #7c3aed; background: #1c1c28; }

QComboBox {
    background: #1a1a24; color: #dddde8;
    border: 1px solid #28283a; border-radius: 7px;
    padding: 7px 11px; font-size: 13px; min-width: 110px;
}
QComboBox:focus { border-color: #7c3aed; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow {
    width: 8px; height: 8px;
    border-left: 2px solid #5a5a78; border-bottom: 2px solid #5a5a78;
    margin-right: 6px;
}
QComboBox QAbstractItemView {
    background: #1c1c28; border: 1px solid #28283a;
    selection-background-color: #4c1d95; color: #dddde8;
    border-radius: 7px; outline: none;
}

/* Buttons */
#primary_btn {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7c3aed, stop:1 #6d28d9);
    color: #fff; border: none; border-radius: 8px;
    padding: 9px 20px; font-size: 13px; font-weight: 600;
}
#primary_btn:hover  { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #8b5cf6, stop:1 #7c3aed); }
#primary_btn:pressed{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #6d28d9, stop:1 #5b21b6); }
#primary_btn:disabled{ background: #1e1e28; color: #333344; }

#secondary_btn {
    background: #1a1a24; color: #a78bfa;
    border: 1px solid #28283a; border-radius: 7px;
    padding: 7px 14px; font-size: 12px; font-weight: 500;
}
#secondary_btn:hover { background: #1e1e30; border-color: #4c1d95; }

#danger_btn {
    background: #1a0a0a; color: #f87171;
    border: 1px solid #2a1010; border-radius: 7px;
    padding: 7px 14px; font-size: 12px; font-weight: 500;
}
#danger_btn:hover    { background: #220e0e; border-color: #dc2626; }
#danger_btn:disabled { background: #111116; color: #2a2a36; border-color: #1e1e26; }

#icon_btn {
    background: #1a1a24; color: #7a7a99;
    border: 1px solid #28283a; border-radius: 6px;
    padding: 6px 10px; font-size: 12px;
}
#icon_btn:hover { background: #1e1e30; color: #a78bfa; }

/* Mode toggle buttons (Video / Audio) */
#mode_btn {
    background: #1a1a24; color: #7a7a99;
    border: 1px solid #28283a; border-radius: 8px;
    padding: 10px 22px; font-size: 13px; font-weight: 600;
    min-width: 120px;
}
#mode_btn:hover  { background: #1e1e30; color: #dddde8; border-color: #3a3a52; }
#mode_btn[active="true"] {
    background: #1e1e30; color: #a78bfa;
    border: 2px solid #7c3aed;
}

/* Progress */
QProgressBar {
    background: #1a1a24; border: none; border-radius: 4px; height: 5px;
}
QProgressBar::chunk {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7c3aed, stop:1 #a78bfa);
    border-radius: 4px;
}

/* Log */
#log_area {
    background: #0a0a0f; color: #6a6a88;
    border: 1px solid #1a1a26; border-radius: 8px;
    padding: 10px;
    font-family: 'Cascadia Code','Consolas','Courier New',monospace;
    font-size: 11px;
}

/* Checkbox */
QCheckBox { color: #7a7a99; spacing: 7px; font-size: 12px; }
QCheckBox:hover { color: #dddde8; }
QCheckBox::indicator {
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid #28283a; background: #1a1a24;
}
QCheckBox::indicator:checked { background: #7c3aed; border-color: #7c3aed; }

/* Labels */
#field_label { font-size: 11px; font-weight: 600; color: #444460; letter-spacing: 0.5px; }
#status_label{ font-size: 11px; color: #444460; }
#status_ok   { color: #34d399; font-size: 11px; font-weight: 600; }
#status_err  { color: #f87171; font-size: 11px; font-weight: 600; }
#stat_value  { font-size: 20px; font-weight: 700; color: #fff; }
#stat_label  { font-size: 10px; color: #3a3a52; letter-spacing: 1.5px; }

/* Playlist info banner */
#pl_info_card {
    background: #0f0f1a;
    border: 1px solid #1f1f2e;
    border-radius: 8px;
}
#pl_count_lbl { font-size: 22px; font-weight: 700; color: #a78bfa; }
#pl_title_lbl { font-size: 13px; color: #7a7a99; }
#pl_mode_video { color: #a78bfa; font-size: 12px; font-weight: 600; }
#pl_mode_audio { color: #34d399; font-size: 12px; font-weight: 600; }

/* History list */
QListWidget {
    background: #0a0a0f; border: 1px solid #1a1a26;
    border-radius: 8px; color: #7a7a99; outline: none;
}
QListWidget::item { padding: 9px 13px; border-bottom: 1px solid #141420; }
QListWidget::item:selected { background: #1a1a30; color: #a78bfa; }
QListWidget::item:hover    { background: #13131e; }

/* Separator */
#hsep { background: #1f1f2e; max-height: 1px; }

/* Scrollbar */
QScrollBar:vertical   { background: transparent; width: 5px; }
QScrollBar::handle:vertical { background: #28283a; border-radius: 3px; min-height: 28px; }
QScrollBar::handle:vertical:hover { background: #3c3c58; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal  { background: transparent; height: 5px; }
QScrollBar::handle:horizontal { background: #28283a; border-radius: 3px; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
"""


# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def find_ytdlp():
    found = shutil.which("yt-dlp") or shutil.which("yt-dlp.exe")
    if found:
        return found

    appdata      = os.environ.get("APPDATA",      "")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    home         = os.path.expanduser("~")

    major = sys.version_info.major
    minor = sys.version_info.minor
    roaming_scripts = os.path.join(appdata, "Python",
                                   f"Python{major}{minor}",
                                   "Scripts", "yt-dlp.exe")
    if os.path.isfile(roaming_scripts):
        return roaming_scripts

    for hit in glob.glob(os.path.join(appdata, "Python", "Python3*",
                                      "Scripts", "yt-dlp.exe")):
        return hit

    py_dir = os.path.dirname(sys.executable)
    for candidate in [
        os.path.join(py_dir, "yt-dlp.exe"),
        os.path.join(py_dir, "Scripts", "yt-dlp.exe"),
    ]:
        if os.path.isfile(candidate):
            return candidate

    for hit in glob.glob(os.path.join(localappdata, "Microsoft", "WinGet",
                                      "Packages", "yt-dlp.yt-dlp*",
                                      "yt-dlp.exe")):
        return hit
    winget_links = os.path.join(localappdata, "Microsoft", "WinGet",
                                "Links", "yt-dlp.exe")
    if os.path.isfile(winget_links):
        return winget_links

    for path in [
        os.path.join(home, "AppData", "Local", "Programs", "yt-dlp", "yt-dlp.exe"),
        r"C:\tools\yt-dlp\yt-dlp.exe",
        r"C:\yt-dlp\yt-dlp.exe",
    ]:
        if os.path.isfile(path):
            return path

    return None


def _no_window():
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


def make_label(text, obj="field_label"):
    lbl = QLabel(text)
    lbl.setObjectName(obj)
    return lbl


def hsep():
    f = QFrame()
    f.setObjectName("hsep")
    f.setFrameShape(QFrame.HLine)
    return f


# ─────────────────────────────────────────────────────────────────────────────
#  WORKER THREADS
# ─────────────────────────────────────────────────────────────────────────────
class DownloadThread(QThread):
    log_sig      = pyqtSignal(str)
    pct_sig      = pyqtSignal(float)
    speed_sig    = pyqtSignal(str)
    eta_sig      = pyqtSignal(str)
    done_sig     = pyqtSignal(bool, str)

    def __init__(self, command, url=""):
        super().__init__()
        self.command  = command
        self.url      = url
        self._proc    = None

    def run(self):
        try:
            self._proc = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, bufsize=1,
                creationflags=_no_window(),
            )
            for line in self._proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                self.log_sig.emit(line)
                m = re.search(r"(\d+(?:\.\d+)?)%", line)
                if m:
                    self.pct_sig.emit(float(m.group(1)))
                m2 = re.search(r"at\s+([\d.]+\s*\S+/s)", line)
                if m2:
                    self.speed_sig.emit(m2.group(1))
                m3 = re.search(r"ETA\s+(\d+:\d+)", line)
                if m3:
                    self.eta_sig.emit(m3.group(1))
            self._proc.wait()
            self.done_sig.emit(self._proc.returncode == 0, self.url)
        except Exception as e:
            self.log_sig.emit(f"[ERROR] {e}")
            self.done_sig.emit(False, self.url)

    def abort(self):
        if self._proc:
            self._proc.terminate()


class UpdateThread(QThread):
    log_sig  = pyqtSignal(str)
    done_sig = pyqtSignal(bool)

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            proc = subprocess.Popen(
                [self.path, "-U"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, creationflags=_no_window(),
            )
            for line in proc.stdout:
                self.log_sig.emit(line.strip())
            proc.wait()
            self.done_sig.emit(proc.returncode == 0)
        except Exception as e:
            self.log_sig.emit(f"[ERROR] {e}")
            self.done_sig.emit(False)


# Thread pour récupérer les infos d'une playlist (titre, nombre de vidéos)
class PlaylistInfoThread(QThread):
    info_sig = pyqtSignal(dict)
    err_sig  = pyqtSignal(str)

    def __init__(self, path, url):
        super().__init__()
        self.path = path
        self.url  = url

    def run(self):
        try:
            proc = subprocess.Popen(
                [self.path, "--flat-playlist", "--dump-single-json", "--no-warnings", self.url],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True, creationflags=_no_window(),
            )
            out, err = proc.communicate()
            if proc.returncode != 0:
                self.err_sig.emit(err.strip() or "Erreur inconnue")
                return
            data = json.loads(out)
            title   = data.get("title", "Playlist inconnue")
            entries = data.get("entries", [])
            count   = len(entries)
            self.info_sig.emit({"title": title, "count": count})
        except Exception as e:
            self.err_sig.emit(str(e))


# ─────────────────────────────────────────────────────────────────────────────
#  STAT CARD
# ─────────────────────────────────────────────────────────────────────────────
class StatCard(QFrame):
    def __init__(self, value, label, color="#a78bfa"):
        super().__init__()
        self.setObjectName("card")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 13, 16, 13)
        lay.setSpacing(2)
        self._val = QLabel(value)
        self._val.setObjectName("stat_value")
        self._val.setStyleSheet(f"color:{color};")
        lay.addWidget(self._val)
        lbl = QLabel(label)
        lbl.setObjectName("stat_label")
        lay.addWidget(lbl)

    def set_value(self, v):
        self._val.setText(v)


# ─────────────────────────────────────────────────────────────────────────────
#  MAIN WINDOW
# ─────────────────────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Velox — YT-DLP Manager")
        self.setMinimumSize(1020, 700)
        self.resize(1140, 760)

        self._ytdlp_path    = find_ytdlp() or "yt-dlp"
        self._dl_thread     = None
        self._info_thread   = None
        self._history       = []
        self._total_dl      = 0
        self._batch_cmds    = []
        self._batch_idx     = 0
        self._pl_mode       = "video"   # "video" ou "audio"
        self._settings_file = os.path.join(os.path.expanduser("~"), ".velox_settings.json")
        self._load_settings()
        self._build_ui()
        self._check_status()

    # ── persistence ──────────────────────────────────────────────────────────
    def _load_settings(self):
        try:
            with open(self._settings_file) as f:
                d = json.load(f)
            self._ytdlp_path = d.get("ytdlp_path") or self._ytdlp_path
            self._history    = d.get("history", [])
            self._total_dl   = d.get("total", 0)
        except Exception:
            pass

    def _save_settings(self):
        try:
            with open(self._settings_file, "w") as f:
                json.dump({"ytdlp_path": self._ytdlp_path,
                           "history": self._history[-200:],
                           "total": self._total_dl}, f, indent=2)
        except Exception:
            pass

    # ── UI skeleton ───────────────────────────────────────────────────────────
    def _build_ui(self):
        root = QWidget()
        rl   = QHBoxLayout(root)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(0)
        self.setCentralWidget(root)

        # sidebar
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(14, 22, 14, 22)
        sl.setSpacing(3)

        logo = QLabel("⬡  VELOX")
        logo.setObjectName("logo_label")
        sl.addWidget(logo)
        ver = QLabel("YT-DLP MANAGER  v2.2")
        ver.setObjectName("ver_label")
        sl.addWidget(ver)
        sl.addSpacing(22)

        self._nav = {}
        for key, icon, label in [
            ("download", "⬇", "Download"),
            ("batch",    "≡", "Batch Queue"),
            ("audio",    "♪", "Audio Only"),
            ("playlist", "▶", "Playlist"),     # ← NOUVEAU
            ("history",  "⏱", "History"),
            ("settings", "⚙", "Settings"),
        ]:
            btn = QPushButton(f"  {icon}  {label}")
            btn.setObjectName("nav_btn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._switch(k))
            sl.addWidget(btn)
            self._nav[key] = btn

        sl.addStretch()
        self._status_lbl = QLabel("● yt-dlp")
        self._status_lbl.setObjectName("status_label")
        sl.addWidget(self._status_lbl)
        rl.addWidget(sidebar)

        # pages
        self._stack = QWidget()
        self._stack.setObjectName("content_area")
        self._sl = QVBoxLayout(self._stack)
        self._sl.setContentsMargins(0, 0, 0, 0)
        self._sl.setSpacing(0)

        self._pages = {
            "download": self._page_download(),
            "batch":    self._page_batch(),
            "audio":    self._page_audio(),
            "playlist": self._page_playlist(),   # ← NOUVEAU
            "history":  self._page_history(),
            "settings": self._page_settings(),
        }
        for p in self._pages.values():
            self._sl.addWidget(p)
            p.hide()

        rl.addWidget(self._stack, 1)
        self._switch("download")

    def _switch(self, key):
        for k, b in self._nav.items():
            b.setProperty("active", k == key)
            b.style().unpolish(b); b.style().polish(b)
        for k, p in self._pages.items():
            p.setVisible(k == key)
        if key == "history":
            self._refresh_history()

    # ── Download page ─────────────────────────────────────────────────────────
    def _page_download(self):
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(32, 26, 32, 26)
        lay.setSpacing(0)

        hdr = QHBoxLayout()
        titles = QVBoxLayout()
        t = QLabel("Download")
        t.setObjectName("page_title")
        titles.addWidget(t)
        s = QLabel("SINGLE VIDEO  ·  SUPPORTS 1000+ SITES")
        s.setObjectName("page_sub")
        titles.addWidget(s)
        hdr.addLayout(titles)
        hdr.addStretch()
        self._spd_card = StatCard("—", "SPEED", "#34d399")
        self._eta_card = StatCard("—", "ETA",   "#a78bfa")
        hdr.addWidget(self._spd_card)
        hdr.addSpacing(8)
        hdr.addWidget(self._eta_card)
        lay.addLayout(hdr)
        lay.addSpacing(18)

        card = QFrame(); card.setObjectName("card")
        cl   = QVBoxLayout(card)
        cl.setContentsMargins(20, 17, 20, 17)
        cl.setSpacing(13)

        cl.addWidget(make_label("VIDEO URL"))
        ur = QHBoxLayout()
        self._url = QLineEdit()
        self._url.setPlaceholderText("https://www.youtube.com/watch?v=…")
        self._url.returnPressed.connect(self._do_download)
        ur.addWidget(self._url)
        pb = QPushButton("Paste")
        pb.setObjectName("icon_btn")
        pb.clicked.connect(lambda: self._url.setText(QApplication.clipboard().text()))
        ur.addWidget(pb)
        cl.addLayout(ur)
        cl.addWidget(hsep())

        r1 = QHBoxLayout(); r1.setSpacing(14)
        for attr, label, items in [
            ("_q_combo",  "QUALITY",
             ["Best available","4K (2160p)","1440p","1080p","720p","480p","360p","240p","Worst"]),
            ("_fmt_combo","FORMAT",   ["Auto","MP4","MKV","WEBM","AVI","MOV"]),
            ("_brw_combo","BROWSER COOKIES",
             ["None","Chrome","Firefox","Edge","Brave","Opera","Vivaldi"]),
        ]:
            col = QVBoxLayout()
            col.addWidget(make_label(label))
            cb = QComboBox(); cb.addItems(items)
            setattr(self, attr, cb)
            col.addWidget(cb)
            r1.addLayout(col)
        col = QVBoxLayout()
        col.addWidget(make_label("SPEED LIMIT"))
        self._speed = QLineEdit(); self._speed.setPlaceholderText("e.g. 5M")
        col.addWidget(self._speed)
        r1.addLayout(col)
        cl.addLayout(r1)

        r2 = QHBoxLayout(); r2.setSpacing(14)
        c1 = QVBoxLayout(); c1.addWidget(make_label("OUTPUT FILE"))
        or_ = QHBoxLayout()
        self._out = QLineEdit(); self._out.setPlaceholderText("%(title)s.%(ext)s")
        or_.addWidget(self._out)
        ob = QPushButton("Browse"); ob.setObjectName("icon_btn")
        ob.clicked.connect(self._browse_out); or_.addWidget(ob)
        c1.addLayout(or_); r2.addLayout(c1, 2)
        c2 = QVBoxLayout(); c2.addWidget(make_label("COOKIES FILE"))
        ck_ = QHBoxLayout()
        self._cookies = QLineEdit(); self._cookies.setPlaceholderText("cookies.txt (optional)")
        ck_.addWidget(self._cookies)
        ckb = QPushButton("Browse"); ckb.setObjectName("icon_btn")
        ckb.clicked.connect(self._browse_cookies); ck_.addWidget(ckb)
        c2.addLayout(ck_); r2.addLayout(c2, 1)
        cl.addLayout(r2)

        chk_row = QHBoxLayout(); chk_row.setSpacing(18)
        self._sub_chk  = QCheckBox("Subtitles")
        self._thb_chk  = QCheckBox("Embed thumbnail")
        self._met_chk  = QCheckBox("Embed metadata")
        self._chp_chk  = QCheckBox("Chapters")
        self._pls_chk  = QCheckBox("Playlist")
        for c in [self._sub_chk, self._thb_chk, self._met_chk, self._chp_chk, self._pls_chk]:
            chk_row.addWidget(c)
        chk_row.addStretch()
        cl.addLayout(chk_row)
        cl.addWidget(hsep())

        act = QHBoxLayout()
        self._dl_btn = QPushButton("⬇  Start Download")
        self._dl_btn.setObjectName("primary_btn")
        self._dl_btn.setCursor(Qt.PointingHandCursor)
        self._dl_btn.clicked.connect(self._do_download)
        act.addWidget(self._dl_btn)
        self._cancel_btn = QPushButton("✕  Cancel")
        self._cancel_btn.setObjectName("danger_btn")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel)
        act.addWidget(self._cancel_btn)
        act.addStretch()
        self._dl_status = QLabel("")
        self._dl_status.setObjectName("status_label")
        act.addWidget(self._dl_status)
        cl.addLayout(act)

        self._dl_bar = QProgressBar()
        self._dl_bar.setValue(0); self._dl_bar.setMaximumHeight(5)
        cl.addWidget(self._dl_bar)
        lay.addWidget(card)
        lay.addSpacing(14)

        log_hdr = QHBoxLayout()
        log_hdr.addWidget(make_label("OUTPUT LOG"))
        log_hdr.addStretch()
        clr = QPushButton("Clear"); clr.setObjectName("icon_btn")
        clr.clicked.connect(lambda: self._dl_log.clear())
        log_hdr.addWidget(clr)
        lay.addLayout(log_hdr)
        lay.addSpacing(5)
        self._dl_log = QTextEdit()
        self._dl_log.setObjectName("log_area")
        self._dl_log.setReadOnly(True)
        self._dl_log.setMinimumHeight(130)
        lay.addWidget(self._dl_log)
        return page

    # ── Batch page ────────────────────────────────────────────────────────────
    def _page_batch(self):
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(32, 26, 32, 26)
        lay.setSpacing(0)
        t = QLabel("Batch Queue"); t.setObjectName("page_title"); lay.addWidget(t)
        s = QLabel("DOWNLOAD MULTIPLE VIDEOS"); s.setObjectName("page_sub"); lay.addWidget(s)
        lay.addSpacing(18)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget(); ll = QVBoxLayout(left)
        ll.setContentsMargins(0,0,8,0); ll.setSpacing(8)
        ll.addWidget(make_label("URLS  —  ONE PER LINE"))
        self._b_urls = QTextEdit()
        self._b_urls.setObjectName("log_area")
        self._b_urls.setPlaceholderText("https://youtu.be/…\nhttps://vimeo.com/…")
        self._b_urls.setStyleSheet("color:#a0a0bc;")
        ll.addWidget(self._b_urls)
        cnt_r = QHBoxLayout()
        self._b_cnt = QLabel("0 URLs"); self._b_cnt.setObjectName("status_label")
        cnt_r.addWidget(self._b_cnt); cnt_r.addStretch()
        imp = QPushButton("Import .txt"); imp.setObjectName("icon_btn")
        imp.clicked.connect(self._import_urls); cnt_r.addWidget(imp)
        ll.addLayout(cnt_r)
        self._b_urls.textChanged.connect(self._update_b_count)
        splitter.addWidget(left)

        right = QWidget(); rl = QVBoxLayout(right)
        rl.setContentsMargins(8,0,0,0); rl.setSpacing(0)
        card = QFrame(); card.setObjectName("card")
        cl   = QVBoxLayout(card)
        cl.setContentsMargins(18,16,18,16); cl.setSpacing(11)
        cl.addWidget(make_label("BATCH OPTIONS"))
        for attr, label, items in [
            ("_bq", "QUALITY",
             ["Best available","4K (2160p)","1440p","1080p","720p","480p","360p"]),
            ("_bf", "FORMAT", ["Auto","MP4","MKV","WEBM"]),
            ("_bb", "BROWSER COOKIES", ["None","Chrome","Firefox","Edge","Brave","Opera"]),
        ]:
            cl.addWidget(make_label(label))
            cb = QComboBox(); cb.addItems(items)
            setattr(self, attr, cb); cl.addWidget(cb)
        cl.addWidget(make_label("OUTPUT PATTERN"))
        self._b_tmpl = QLineEdit()
        self._b_tmpl.setPlaceholderText("%(autonumber)s - %(title)s.%(ext)s")
        cl.addWidget(self._b_tmpl)
        cl.addWidget(make_label("OUTPUT FOLDER"))
        fr = QHBoxLayout()
        self._b_fold = QLineEdit(); self._b_fold.setPlaceholderText("Current directory")
        fr.addWidget(self._b_fold)
        fb = QPushButton("…"); fb.setObjectName("icon_btn")
        fb.clicked.connect(self._browse_b_folder); fr.addWidget(fb)
        cl.addLayout(fr)
        cl.addWidget(hsep())
        self._b_sub = QCheckBox("Subtitles")
        self._b_thb = QCheckBox("Embed thumbnail")
        self._b_met = QCheckBox("Embed metadata")
        for c in [self._b_sub, self._b_thb, self._b_met]:
            cl.addWidget(c)
        cl.addWidget(hsep())
        self._b_btn = QPushButton("⬇  Start Batch")
        self._b_btn.setObjectName("primary_btn"); self._b_btn.setCursor(Qt.PointingHandCursor)
        self._b_btn.clicked.connect(self._do_batch); cl.addWidget(self._b_btn)
        self._b_cancel = QPushButton("✕  Cancel")
        self._b_cancel.setObjectName("danger_btn"); self._b_cancel.setEnabled(False)
        self._b_cancel.clicked.connect(self._cancel); cl.addWidget(self._b_cancel)
        cl.addWidget(hsep())
        self._b_bar = QProgressBar(); cl.addWidget(self._b_bar)
        self._b_status = QLabel("")
        self._b_status.setObjectName("status_label"); self._b_status.setWordWrap(True)
        cl.addWidget(self._b_status)
        cl.addStretch(); rl.addWidget(card)
        splitter.addWidget(right)
        splitter.setSizes([550, 370])
        lay.addWidget(splitter, 1)
        lay.addSpacing(10)
        lay.addWidget(make_label("OUTPUT LOG")); lay.addSpacing(4)
        self._b_log = QTextEdit()
        self._b_log.setObjectName("log_area"); self._b_log.setReadOnly(True)
        self._b_log.setMaximumHeight(120); lay.addWidget(self._b_log)
        return page

    # ── Audio page ────────────────────────────────────────────────────────────
    def _page_audio(self):
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(32, 26, 32, 26); lay.setSpacing(0)
        t = QLabel("Audio Only"); t.setObjectName("page_title"); lay.addWidget(t)
        s = QLabel("EXTRACT AUDIO FROM ANY VIDEO"); s.setObjectName("page_sub"); lay.addWidget(s)
        lay.addSpacing(18)

        card = QFrame(); card.setObjectName("card")
        cl   = QVBoxLayout(card)
        cl.setContentsMargins(20,17,20,17); cl.setSpacing(13)
        cl.addWidget(make_label("VIDEO URL"))
        ar = QHBoxLayout()
        self._a_url = QLineEdit()
        self._a_url.setPlaceholderText("https://www.youtube.com/watch?v=…")
        self._a_url.returnPressed.connect(self._do_audio)
        ar.addWidget(self._a_url)
        p2 = QPushButton("Paste"); p2.setObjectName("icon_btn")
        p2.clicked.connect(lambda: self._a_url.setText(QApplication.clipboard().text()))
        ar.addWidget(p2); cl.addLayout(ar)
        cl.addWidget(hsep())

        r1 = QHBoxLayout(); r1.setSpacing(14)
        c1 = QVBoxLayout(); c1.addWidget(make_label("FORMAT"))
        self._a_fmt = QComboBox()
        self._a_fmt.addItems(["MP3","M4A","OPUS","OGG","FLAC","WAV","AAC"])
        c1.addWidget(self._a_fmt); r1.addLayout(c1)
        c2 = QVBoxLayout(); c2.addWidget(make_label("QUALITY (KBPS)"))
        self._a_q = QComboBox()
        self._a_q.addItems(["Best","320","256","192","128","96","64"])
        c2.addWidget(self._a_q); r1.addLayout(c2)
        c3 = QVBoxLayout(); c3.addWidget(make_label("OUTPUT FOLDER"))
        f3 = QHBoxLayout()
        self._a_fold = QLineEdit(); self._a_fold.setPlaceholderText("Current directory")
        f3.addWidget(self._a_fold)
        fb3 = QPushButton("…"); fb3.setObjectName("icon_btn")
        fb3.clicked.connect(self._browse_a_folder); f3.addWidget(fb3)
        c3.addLayout(f3); r1.addLayout(c3, 2); cl.addLayout(r1)

        r2 = QHBoxLayout(); r2.setSpacing(18)
        self._a_thb = QCheckBox("Embed thumbnail")
        self._a_met = QCheckBox("Embed metadata")
        self._a_spl = QCheckBox("Split chapters")
        for c in [self._a_thb, self._a_met, self._a_spl]:
            r2.addWidget(c)
        r2.addStretch(); cl.addLayout(r2)
        cl.addWidget(hsep())

        act = QHBoxLayout()
        self._a_btn = QPushButton("♪  Extract Audio")
        self._a_btn.setObjectName("primary_btn"); self._a_btn.setCursor(Qt.PointingHandCursor)
        self._a_btn.clicked.connect(self._do_audio); act.addWidget(self._a_btn)
        self._a_cancel = QPushButton("✕  Cancel")
        self._a_cancel.setObjectName("danger_btn"); self._a_cancel.setEnabled(False)
        self._a_cancel.clicked.connect(self._cancel)
        act.addWidget(self._a_cancel); act.addStretch(); cl.addLayout(act)
        self._a_bar = QProgressBar(); self._a_bar.setMaximumHeight(5); cl.addWidget(self._a_bar)
        lay.addWidget(card); lay.addSpacing(14)
        lay.addWidget(make_label("OUTPUT LOG")); lay.addSpacing(5)
        self._a_log = QTextEdit()
        self._a_log.setObjectName("log_area"); self._a_log.setReadOnly(True)
        lay.addWidget(self._a_log)
        return page

    # ── Playlist page (NOUVEAU) ───────────────────────────────────────────────
    def _page_playlist(self):
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(32, 26, 32, 26)
        lay.setSpacing(0)

        # Header
        hdr = QHBoxLayout()
        titles = QVBoxLayout()
        t = QLabel("Playlist")
        t.setObjectName("page_title")
        titles.addWidget(t)
        s = QLabel("TÉLÉCHARGER UNE PLAYLIST YOUTUBE COMPLÈTE  ·  VIDÉO OU AUDIO")
        s.setObjectName("page_sub")
        titles.addWidget(s)
        hdr.addLayout(titles)
        hdr.addStretch()
        lay.addLayout(hdr)
        lay.addSpacing(18)

        # URL card
        url_card = QFrame(); url_card.setObjectName("card")
        ucl = QVBoxLayout(url_card)
        ucl.setContentsMargins(20, 17, 20, 17)
        ucl.setSpacing(12)

        ucl.addWidget(make_label("URL DE LA PLAYLIST"))
        ur = QHBoxLayout()
        self._pl_url = QLineEdit()
        self._pl_url.setPlaceholderText("https://www.youtube.com/playlist?list=…")
        ur.addWidget(self._pl_url)
        pb = QPushButton("Paste"); pb.setObjectName("icon_btn")
        pb.clicked.connect(lambda: self._pl_url.setText(QApplication.clipboard().text()))
        ur.addWidget(pb)
        fetch_btn = QPushButton("🔍 Analyser"); fetch_btn.setObjectName("secondary_btn")
        fetch_btn.setCursor(Qt.PointingHandCursor)
        fetch_btn.clicked.connect(self._fetch_playlist_info)
        ur.addWidget(fetch_btn)
        ucl.addLayout(ur)

        # Info banner (masqué par défaut)
        self._pl_info_frame = QFrame()
        self._pl_info_frame.setObjectName("pl_info_card")
        pl_info_lay = QHBoxLayout(self._pl_info_frame)
        pl_info_lay.setContentsMargins(16, 12, 16, 12)
        pl_info_lay.setSpacing(20)
        self._pl_count_lbl = QLabel("—")
        self._pl_count_lbl.setObjectName("pl_count_lbl")
        pl_info_lay.addWidget(self._pl_count_lbl)
        info_texts = QVBoxLayout()
        self._pl_title_lbl = QLabel("Aucune playlist analysée")
        self._pl_title_lbl.setObjectName("pl_title_lbl")
        info_texts.addWidget(self._pl_title_lbl)
        self._pl_info_status = QLabel("")
        self._pl_info_status.setObjectName("status_label")
        info_texts.addWidget(self._pl_info_status)
        pl_info_lay.addLayout(info_texts, 1)
        ucl.addWidget(self._pl_info_frame)

        ucl.addWidget(hsep())

        # ── MODE : Vidéo ou Audio ──────────────────────────────────────────
        mode_row = QHBoxLayout(); mode_row.setSpacing(10)
        mode_row.addWidget(make_label("MODE DE TÉLÉCHARGEMENT"))
        mode_row.addStretch()

        self._pl_video_btn = QPushButton("📹  Vidéo")
        self._pl_video_btn.setObjectName("mode_btn")
        self._pl_video_btn.setCursor(Qt.PointingHandCursor)
        self._pl_video_btn.clicked.connect(lambda: self._set_pl_mode("video"))

        self._pl_audio_btn = QPushButton("🎵  Audio")
        self._pl_audio_btn.setObjectName("mode_btn")
        self._pl_audio_btn.setCursor(Qt.PointingHandCursor)
        self._pl_audio_btn.clicked.connect(lambda: self._set_pl_mode("audio"))

        mode_row.addWidget(self._pl_video_btn)
        mode_row.addWidget(self._pl_audio_btn)
        ucl.addLayout(mode_row)

        # ── Options vidéo ──────────────────────────────────────────────────
        self._pl_video_opts = QFrame()
        vo_lay = QHBoxLayout(self._pl_video_opts)
        vo_lay.setContentsMargins(0, 0, 0, 0); vo_lay.setSpacing(14)

        c1 = QVBoxLayout(); c1.addWidget(make_label("QUALITÉ"))
        self._pl_q = QComboBox()
        self._pl_q.addItems(["Best available","4K (2160p)","1440p","1080p","720p","480p","360p","240p"])
        c1.addWidget(self._pl_q); vo_lay.addLayout(c1)

        c2 = QVBoxLayout(); c2.addWidget(make_label("FORMAT"))
        self._pl_fmt = QComboBox()
        self._pl_fmt.addItems(["Auto","MP4","MKV","WEBM"])
        c2.addWidget(self._pl_fmt); vo_lay.addLayout(c2)

        c3 = QVBoxLayout(); c3.addWidget(make_label("COOKIES NAVIGATEUR"))
        self._pl_brw = QComboBox()
        self._pl_brw.addItems(["None","Chrome","Firefox","Edge","Brave","Opera"])
        c3.addWidget(self._pl_brw); vo_lay.addLayout(c3)

        vo_lay.addStretch()
        ucl.addWidget(self._pl_video_opts)

        # ── Options audio ──────────────────────────────────────────────────
        self._pl_audio_opts = QFrame()
        ao_lay = QHBoxLayout(self._pl_audio_opts)
        ao_lay.setContentsMargins(0, 0, 0, 0); ao_lay.setSpacing(14)

        ca1 = QVBoxLayout(); ca1.addWidget(make_label("FORMAT AUDIO"))
        self._pl_a_fmt = QComboBox()
        self._pl_a_fmt.addItems(["MP3","M4A","OPUS","OGG","FLAC","WAV","AAC"])
        ca1.addWidget(self._pl_a_fmt); ao_lay.addLayout(ca1)

        ca2 = QVBoxLayout(); ca2.addWidget(make_label("QUALITÉ (KBPS)"))
        self._pl_a_q = QComboBox()
        self._pl_a_q.addItems(["Best","320","256","192","128","96","64"])
        ca2.addWidget(self._pl_a_q); ao_lay.addLayout(ca2)

        ao_lay.addStretch()
        ucl.addWidget(self._pl_audio_opts)
        self._pl_audio_opts.hide()   # vidéo par défaut

        # ── Dossier de sortie ───────────────────────────────────────────────
        ucl.addWidget(hsep())
        fo_row = QHBoxLayout(); fo_row.setSpacing(14)
        fc = QVBoxLayout(); fc.addWidget(make_label("DOSSIER DE SORTIE"))
        f_r = QHBoxLayout()
        self._pl_fold = QLineEdit()
        self._pl_fold.setPlaceholderText("Dossier actuel")
        f_r.addWidget(self._pl_fold)
        fbb = QPushButton("…"); fbb.setObjectName("icon_btn")
        fbb.clicked.connect(self._browse_pl_folder); f_r.addWidget(fbb)
        fc.addLayout(f_r); fo_row.addLayout(fc, 2)

        nc = QVBoxLayout(); nc.addWidget(make_label("NUMÉROTATION"))
        self._pl_num = QComboBox()
        self._pl_num.addItems([
            "%(autonumber)s - %(title)s",
            "%(playlist_index)s - %(title)s",
            "%(title)s",
        ])
        nc.addWidget(self._pl_num); fo_row.addLayout(nc, 1)
        ucl.addLayout(fo_row)

        # ── Checkboxes communes ─────────────────────────────────────────────
        chk_row = QHBoxLayout(); chk_row.setSpacing(18)
        self._pl_sub = QCheckBox("Sous-titres")
        self._pl_thb = QCheckBox("Embed thumbnail")
        self._pl_met = QCheckBox("Embed metadata")
        self._pl_lmt = QCheckBox("Limite de vitesse")
        for c in [self._pl_sub, self._pl_thb, self._pl_met, self._pl_lmt]:
            chk_row.addWidget(c)
        chk_row.addStretch()
        ucl.addLayout(chk_row)

        self._pl_speed_line = QLineEdit()
        self._pl_speed_line.setPlaceholderText("ex: 5M  (actif si la case est cochée)")
        self._pl_speed_line.setEnabled(False)
        self._pl_lmt.toggled.connect(self._pl_speed_line.setEnabled)
        ucl.addWidget(self._pl_speed_line)

        ucl.addWidget(hsep())

        # ── Actions ─────────────────────────────────────────────────────────
        act = QHBoxLayout()
        self._pl_btn = QPushButton("⬇  Télécharger la Playlist")
        self._pl_btn.setObjectName("primary_btn")
        self._pl_btn.setCursor(Qt.PointingHandCursor)
        self._pl_btn.clicked.connect(self._do_playlist)
        act.addWidget(self._pl_btn)

        self._pl_cancel = QPushButton("✕  Annuler")
        self._pl_cancel.setObjectName("danger_btn")
        self._pl_cancel.setEnabled(False)
        self._pl_cancel.clicked.connect(self._cancel)
        act.addWidget(self._pl_cancel)
        act.addStretch()

        self._pl_status = QLabel("")
        self._pl_status.setObjectName("status_label")
        act.addWidget(self._pl_status)
        ucl.addLayout(act)

        self._pl_bar = QProgressBar()
        self._pl_bar.setValue(0); self._pl_bar.setMaximumHeight(5)
        ucl.addWidget(self._pl_bar)

        lay.addWidget(url_card)
        lay.addSpacing(14)

        log_hdr = QHBoxLayout()
        log_hdr.addWidget(make_label("OUTPUT LOG"))
        log_hdr.addStretch()
        clr = QPushButton("Clear"); clr.setObjectName("icon_btn")
        clr.clicked.connect(lambda: self._pl_log.clear())
        log_hdr.addWidget(clr)
        lay.addLayout(log_hdr)
        lay.addSpacing(5)

        self._pl_log = QTextEdit()
        self._pl_log.setObjectName("log_area")
        self._pl_log.setReadOnly(True)
        lay.addWidget(self._pl_log, 1)

        # Init mode
        self._set_pl_mode("video")
        return page

    def _set_pl_mode(self, mode):
        """Bascule entre mode vidéo et mode audio pour la playlist."""
        self._pl_mode = mode
        is_video = (mode == "video")
        self._pl_video_opts.setVisible(is_video)
        self._pl_audio_opts.setVisible(not is_video)

        self._pl_video_btn.setProperty("active", is_video)
        self._pl_audio_btn.setProperty("active", not is_video)
        for btn in [self._pl_video_btn, self._pl_audio_btn]:
            btn.style().unpolish(btn); btn.style().polish(btn)

    def _fetch_playlist_info(self):
        """Récupère le titre et le nombre de vidéos de la playlist."""
        url = self._pl_url.text().strip()
        if not url:
            self._pl_info_status.setText("✗  Entrez une URL d'abord")
            return
        self._pl_info_status.setText("⏳  Analyse en cours…")
        self._pl_title_lbl.setText("Chargement…")
        self._pl_count_lbl.setText("…")
        self._info_thread = PlaylistInfoThread(self._ytdlp_path, url)
        self._info_thread.info_sig.connect(self._on_pl_info)
        self._info_thread.err_sig.connect(self._on_pl_info_err)
        self._info_thread.start()

    def _on_pl_info(self, data):
        self._pl_title_lbl.setText(data["title"])
        self._pl_count_lbl.setText(str(data["count"]))
        self._pl_info_status.setText(f"✓  {data['count']} vidéos trouvées")

    def _on_pl_info_err(self, err):
        self._pl_title_lbl.setText("Erreur lors de l'analyse")
        self._pl_count_lbl.setText("✗")
        self._pl_info_status.setText(f"Erreur: {err[:80]}")

    def _do_playlist(self):
        url = self._pl_url.text().strip()
        if not url:
            self._pl_log.append("<span style='color:#f87171'>✗  Entrez une URL de playlist</span>")
            return

        folder   = self._pl_fold.text().strip() or None
        num_tmpl = self._pl_num.currentText()
        speed    = self._pl_speed_line.text().strip() if self._pl_lmt.isChecked() else None

        if self._pl_mode == "video":
            # ── Commande Vidéo ──────────────────────────────────────────────
            quality = self._pl_q.currentText()
            fmt     = self._pl_fmt.currentText()
            browser = self._pl_brw.currentText()
            ext     = self._F_MAP.get(fmt, "")
            tmpl    = f"{num_tmpl}.{'%(ext)s' if not ext else ext}"
            if folder:
                tmpl = os.path.join(folder, tmpl)

            cmd = [self._ytdlp_path, url,
                   "-f", self._Q_MAP.get(quality, "bestvideo+bestaudio/best"),
                   "--newline", "--progress",
                   "-o", tmpl,
                   "--yes-playlist"]
            if ext:
                cmd += ["--merge-output-format", ext]
            b = self._B_MAP.get(browser)
            if b:
                cmd += ["--cookies-from-browser", b]
            if speed:
                cmd += ["--limit-rate", speed]
            if self._pl_sub.isChecked():
                cmd += ["--write-auto-subs", "--sub-langs", "all"]
            if self._pl_thb.isChecked():
                cmd += ["--embed-thumbnail"]
            if self._pl_met.isChecked():
                cmd += ["--embed-metadata", "--add-metadata"]

            mode_label = "📹 Vidéo"

        else:
            # ── Commande Audio ──────────────────────────────────────────────
            a_fmt  = self._pl_a_fmt.currentText().lower()
            a_q    = self._pl_a_q.currentText()
            tmpl   = f"{num_tmpl}.%(ext)s"
            if folder:
                tmpl = os.path.join(folder, tmpl)

            cmd = [self._ytdlp_path, url,
                   "-x", "--audio-format", a_fmt,
                   "--newline", "--progress",
                   "-o", tmpl,
                   "--yes-playlist"]
            if a_q != "Best":
                cmd += ["--audio-quality", a_q + "k"]
            if speed:
                cmd += ["--limit-rate", speed]
            if self._pl_thb.isChecked():
                cmd += ["--embed-thumbnail"]
            if self._pl_met.isChecked():
                cmd += ["--embed-metadata", "--add-metadata"]

            mode_label = "🎵 Audio"

        self._pl_log.clear()
        self._pl_log.append(
            f"<span style='color:#a78bfa'>▶  Démarrage playlist  [{mode_label}]…</span>")
        self._pl_log.append(f"<span style='color:#3a3a52'>URL: {url}</span>")
        self._pl_btn.setEnabled(False)
        self._pl_cancel.setEnabled(True)
        self._pl_bar.setValue(0)
        self._pl_status.setText("Téléchargement en cours…")

        self._cur_log  = self._pl_log
        self._cur_bar  = self._pl_bar
        self._cur_mode = "playlist"
        self._run(cmd, url)

    # ── History page ──────────────────────────────────────────────────────────
    def _page_history(self):
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(32, 26, 32, 26); lay.setSpacing(0)
        hdr = QHBoxLayout()
        t = QLabel("History"); t.setObjectName("page_title"); hdr.addWidget(t)
        hdr.addStretch()
        clr = QPushButton("Clear All"); clr.setObjectName("danger_btn")
        clr.clicked.connect(self._clear_history); hdr.addWidget(clr)
        lay.addLayout(hdr)
        s = QLabel("DOWNLOAD HISTORY"); s.setObjectName("page_sub"); lay.addWidget(s)
        lay.addSpacing(16)

        sr = QHBoxLayout(); sr.setSpacing(10)
        self._tot_card  = StatCard(str(self._total_dl), "TOTAL",      "#a78bfa")
        self._ok_card   = StatCard("0",                 "SUCCESSFUL", "#34d399")
        self._fail_card = StatCard("0",                 "FAILED",     "#f87171")
        for c in [self._tot_card, self._ok_card, self._fail_card]:
            sr.addWidget(c)
        sr.addStretch(); lay.addLayout(sr); lay.addSpacing(16)
        self._hist_list = QListWidget(); lay.addWidget(self._hist_list, 1)
        return page

    # ── Settings page ─────────────────────────────────────────────────────────
    def _page_settings(self):
        page = QWidget()
        lay  = QVBoxLayout(page)
        lay.setContentsMargins(32, 26, 32, 26); lay.setSpacing(0)
        t = QLabel("Settings"); t.setObjectName("page_title"); lay.addWidget(t)
        s = QLabel("CONFIGURATION"); s.setObjectName("page_sub"); lay.addWidget(s)
        lay.addSpacing(18)

        card = QFrame(); card.setObjectName("card")
        cl   = QVBoxLayout(card)
        cl.setContentsMargins(20,17,20,17); cl.setSpacing(13)

        cl.addWidget(make_label("YT-DLP EXECUTABLE"))
        pr = QHBoxLayout()
        self._path_input = QLineEdit(self._ytdlp_path)
        pr.addWidget(self._path_input)
        bex = QPushButton("Browse"); bex.setObjectName("icon_btn")
        bex.clicked.connect(self._browse_exe); pr.addWidget(bex)
        cl.addLayout(pr)
        self._path_status = QLabel(""); self._path_status.setObjectName("status_label")
        cl.addWidget(self._path_status)
        cl.addWidget(hsep())

        sv = QPushButton("Save & Verify"); sv.setObjectName("primary_btn")
        sv.clicked.connect(self._save_path); cl.addWidget(sv)
        cl.addWidget(hsep())
        cl.addWidget(make_label("UPDATE / INSTALL"))
        row = QHBoxLayout()
        upd = QPushButton("⟳  Update yt-dlp"); upd.setObjectName("secondary_btn")
        upd.clicked.connect(self._update_ytdlp); row.addWidget(upd)
        pip = QPushButton("pip install yt-dlp"); pip.setObjectName("secondary_btn")
        pip.clicked.connect(self._pip_install); row.addWidget(pip)
        row.addStretch(); cl.addLayout(row)
        cl.addStretch(); lay.addWidget(card); lay.addSpacing(14)
        self._set_log = QTextEdit()
        self._set_log.setObjectName("log_area"); self._set_log.setReadOnly(True)
        self._set_log.setMaximumHeight(150); lay.addWidget(self._set_log)
        lay.addStretch()
        return page

    # ── yt-dlp status ─────────────────────────────────────────────────────────
    def _check_status(self):
        ok = bool(shutil.which(self._ytdlp_path) or os.path.isfile(self._ytdlp_path))
        if ok:
            self._status_lbl.setText("● yt-dlp  ✓")
            self._status_lbl.setObjectName("status_ok")
        else:
            self._status_lbl.setText("● yt-dlp  ✗  (see Settings)")
            self._status_lbl.setObjectName("status_err")
        self._status_lbl.style().unpolish(self._status_lbl)
        self._status_lbl.style().polish(self._status_lbl)

    # ── Browse helpers ────────────────────────────────────────────────────────
    def _browse_out(self):
        f,_ = QFileDialog.getSaveFileName(self,"Save as","","Video (*.mp4 *.mkv *.webm);;All (*)")
        if f: self._out.setText(f)
    def _browse_cookies(self):
        f,_ = QFileDialog.getOpenFileName(self,"Cookies file","","Text (*.txt);;All (*)")
        if f: self._cookies.setText(f)
    def _browse_b_folder(self):
        d = QFileDialog.getExistingDirectory(self,"Output folder")
        if d: self._b_fold.setText(d)
    def _browse_a_folder(self):
        d = QFileDialog.getExistingDirectory(self,"Output folder")
        if d: self._a_fold.setText(d)
    def _browse_pl_folder(self):
        d = QFileDialog.getExistingDirectory(self,"Dossier de sortie")
        if d: self._pl_fold.setText(d)
    def _browse_exe(self):
        f,_ = QFileDialog.getOpenFileName(self,"yt-dlp executable","","Exe (*.exe);;All (*)")
        if f: self._path_input.setText(f)
    def _import_urls(self):
        f,_ = QFileDialog.getOpenFileName(self,"Import URLs","","Text (*.txt);;All (*)")
        if f:
            with open(f) as fh: self._b_urls.setPlainText(fh.read())

    # ── Command builder maps ──────────────────────────────────────────────────
    _Q_MAP = {
        "Best available": "bestvideo+bestaudio/best",
        "4K (2160p)":     "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
        "1440p":          "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
        "1080p":          "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
        "720p":           "bestvideo[height<=720]+bestaudio/best[height<=720]",
        "480p":           "bestvideo[height<=480]+bestaudio/best[height<=480]",
        "360p":           "bestvideo[height<=360]+bestaudio/best[height<=360]",
        "240p":           "bestvideo[height<=240]+bestaudio/best[height<=240]",
        "Worst":          "worstvideo+worstaudio/worst",
    }
    _F_MAP = {"MP4":"mp4","MKV":"mkv","WEBM":"webm","AVI":"avi","MOV":"mov"}
    _B_MAP = {"Chrome":"chrome","Firefox":"firefox","Edge":"edge",
              "Brave":"brave","Opera":"opera","Vivaldi":"vivaldi"}

    def _build_cmd(self, url, quality, fmt, browser, cookies,
                   out_tmpl, speed=None,
                   subs=False, thumb=False, meta=False, chapters=False,
                   no_playlist=True, folder=None):
        cmd = [self._ytdlp_path, url,
               "-f", self._Q_MAP.get(quality, "bestvideo+bestaudio/best"),
               "--newline", "--progress"]
        f = self._F_MAP.get(fmt)
        if f: cmd += ["--merge-output-format", f]
        tmpl = out_tmpl.strip() or "%(title)s.%(ext)s"
        if folder: tmpl = os.path.join(folder, tmpl)
        cmd += ["-o", tmpl]
        b = self._B_MAP.get(browser)
        if b: cmd += ["--cookies-from-browser", b]
        if cookies: cmd += ["--cookies", cookies]
        if speed:   cmd += ["--limit-rate", speed]
        if subs:    cmd += ["--write-auto-subs","--sub-langs","all"]
        if thumb:   cmd += ["--embed-thumbnail"]
        if meta:    cmd += ["--embed-metadata","--add-metadata"]
        if chapters:cmd += ["--embed-chapters"]
        if no_playlist: cmd += ["--no-playlist"]
        return cmd

    # ── Download actions ──────────────────────────────────────────────────────
    def _do_download(self):
        url = self._url.text().strip()
        if not url:
            self._dl_log.append("<span style='color:#f87171'>✗  Please enter a URL</span>")
            return
        cmd = self._build_cmd(
            url, self._q_combo.currentText(), self._fmt_combo.currentText(),
            self._brw_combo.currentText(), self._cookies.text().strip(),
            self._out.text().strip(), self._speed.text().strip() or None,
            subs=self._sub_chk.isChecked(), thumb=self._thb_chk.isChecked(),
            meta=self._met_chk.isChecked(), chapters=self._chp_chk.isChecked(),
            no_playlist=not self._pls_chk.isChecked(),
        )
        self._dl_log.clear()
        self._dl_log.append("<span style='color:#a78bfa'>▶  Starting download…</span>")
        self._dl_log.append(f"<span style='color:#3a3a52'>URL: {url}</span>")
        self._dl_btn.setEnabled(False); self._cancel_btn.setEnabled(True)
        self._dl_bar.setValue(0)
        self._cur_log = self._dl_log; self._cur_bar = self._dl_bar
        self._cur_mode = "single"
        self._run(cmd, url)

    def _do_batch(self):
        urls = [u.strip() for u in self._b_urls.toPlainText().splitlines() if u.strip()]
        if not urls:
            self._b_log.append("<span style='color:#f87171'>✗  No URLs</span>"); return
        folder = self._b_fold.text().strip() or None
        tmpl   = self._b_tmpl.text().strip() or "%(autonumber)s - %(title)s.%(ext)s"
        self._batch_cmds = [(u, self._build_cmd(
            u, self._bq.currentText(), self._bf.currentText(),
            self._bb.currentText(), "", tmpl, folder=folder,
            subs=self._b_sub.isChecked(), thumb=self._b_thb.isChecked(),
            meta=self._b_met.isChecked(), no_playlist=False,
        )) for u in urls]
        self._batch_idx = 0
        self._b_bar.setMaximum(len(self._batch_cmds)); self._b_bar.setValue(0)
        self._b_log.clear(); self._b_btn.setEnabled(False); self._b_cancel.setEnabled(True)
        self._cur_mode = "batch"; self._cur_log = self._b_log; self._cur_bar = self._b_bar
        self._next_batch()

    def _next_batch(self):
        if self._batch_idx >= len(self._batch_cmds):
            self._b_btn.setEnabled(True); self._b_cancel.setEnabled(False)
            self._b_status.setText("✓  All done!")
            self._b_log.append("<span style='color:#34d399'>✓  Batch complete!</span>"); return
        url, cmd = self._batch_cmds[self._batch_idx]
        n = len(self._batch_cmds)
        self._b_status.setText(f"Downloading {self._batch_idx+1}/{n}…")
        self._cur_log.append(
            f"<span style='color:#a78bfa'>▶  [{self._batch_idx+1}/{n}] {url}</span>")
        self._run(cmd, url)

    def _do_audio(self):
        url = self._a_url.text().strip()
        if not url:
            self._a_log.append("<span style='color:#f87171'>✗  Please enter a URL</span>"); return
        fmt    = self._a_fmt.currentText().lower()
        q      = self._a_q.currentText()
        folder = self._a_fold.text().strip()
        tmpl   = os.path.join(folder, "%(title)s.%(ext)s") if folder else "%(title)s.%(ext)s"
        cmd    = [self._ytdlp_path, url, "-x", "--audio-format", fmt,
                  "--newline", "--progress", "-o", tmpl]
        if q != "Best": cmd += ["--audio-quality", q+"k"]
        if self._a_thb.isChecked(): cmd += ["--embed-thumbnail"]
        if self._a_met.isChecked(): cmd += ["--embed-metadata","--add-metadata"]
        if self._a_spl.isChecked(): cmd += ["--split-chapters","-o","chapter:%(section_title)s.%(ext)s"]
        self._a_log.clear()
        self._a_log.append("<span style='color:#a78bfa'>▶  Extracting audio…</span>")
        self._a_btn.setEnabled(False); self._a_cancel.setEnabled(True)
        self._a_bar.setValue(0)
        self._cur_log = self._a_log; self._cur_bar = self._a_bar
        self._cur_mode = "audio"
        self._run(cmd, url)

    # ── Thread runner ─────────────────────────────────────────────────────────
    def _run(self, cmd, url):
        self._dl_thread = DownloadThread(cmd, url)
        self._dl_thread.log_sig.connect(self._on_log)
        self._dl_thread.pct_sig.connect(self._on_pct)
        self._dl_thread.speed_sig.connect(self._spd_card.set_value)
        self._dl_thread.eta_sig.connect(self._eta_card.set_value)
        self._dl_thread.done_sig.connect(self._on_done)
        self._dl_thread.start()

    def _cancel(self):
        if self._dl_thread and self._dl_thread.isRunning():
            self._dl_thread.abort()
            self._cur_log.append("<span style='color:#f87171'>✗  Annulé</span>")
        self._batch_cmds = []
        self._reset_ui()

    def _on_log(self, line):
        color = "#6a6a88"
        if "[download]"  in line: color = "#a78bfa"
        elif any(x in line for x in ["[ExtractAudio]","[ffmpeg]","[Merger]"]): color = "#34d399"
        elif "ERROR" in line or "error" in line: color = "#f87171"
        elif "WARNING"   in line: color = "#fbbf24"
        self._cur_log.append(f"<span style='color:{color}'>{line}</span>")
        sb = self._cur_log.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_pct(self, pct):
        if self._cur_mode in ("single", "audio", "playlist"):
            self._cur_bar.setMaximum(100)
            self._cur_bar.setValue(int(pct))

    def _on_done(self, ok, url):
        self._total_dl += 1
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")
        mode_tag = self._cur_mode
        self._history.append({"url": url, "success": ok, "ts": ts, "mode": mode_tag})
        self._save_settings()
        self._tot_card.set_value(str(self._total_dl))

        if self._cur_mode == "batch":
            self._batch_idx += 1
            self._cur_bar.setValue(self._batch_idx)
            self._cur_log.append(
                "<span style='color:#34d399'>✓  Done</span>" if ok
                else "<span style='color:#f87171'>✗  Failed</span>")
            if self._batch_cmds:
                self._next_batch()
            else:
                self._reset_ui()
        elif self._cur_mode == "playlist":
            self._cur_log.append(
                "<span style='color:#34d399'>✓  Playlist terminée !</span>" if ok
                else "<span style='color:#f87171'>✗  Échec !</span>")
            self._pl_status.setText("✓  Terminé !" if ok else "✗  Échec")
            self._reset_ui()
        else:
            self._cur_log.append(
                "<span style='color:#34d399'>✓  Complete!</span>" if ok
                else "<span style='color:#f87171'>✗  Failed!</span>")
            if ok and self._cur_mode == "single":
                self._cur_bar.setValue(100)
            self._reset_ui()

    def _reset_ui(self):
        self._dl_btn.setEnabled(True);    self._cancel_btn.setEnabled(False)
        self._b_btn.setEnabled(True);     self._b_cancel.setEnabled(False)
        self._a_btn.setEnabled(True);     self._a_cancel.setEnabled(False)
        self._pl_btn.setEnabled(True);    self._pl_cancel.setEnabled(False)

    # ── History ───────────────────────────────────────────────────────────────
    def _refresh_history(self):
        self._hist_list.clear()
        ok   = sum(1 for h in self._history if h["success"])
        fail = len(self._history) - ok
        self._ok_card.set_value(str(ok))
        self._fail_card.set_value(str(fail))
        self._tot_card.set_value(str(self._total_dl))
        for h in reversed(self._history[-100:]):
            icon  = "✓" if h["success"] else "✗"
            color = "#34d399" if h["success"] else "#f87171"
            mode  = h.get("mode", "")
            mode_icon = {"playlist": "▶", "audio": "♪", "batch": "≡"}.get(mode, "⬇")
            item  = QListWidgetItem(f"{icon} {mode_icon}  {h['ts']}   {h['url']}")
            item.setForeground(QColor(color))
            self._hist_list.addItem(item)

    def _clear_history(self):
        self._history = []
        self._save_settings()
        self._refresh_history()

    # ── Settings ──────────────────────────────────────────────────────────────
    def _save_path(self):
        p = self._path_input.text().strip()
        if not p: return
        self._ytdlp_path = p
        self._save_settings()
        self._check_status()
        found = shutil.which(p) or os.path.isfile(p)
        if found:
            try:
                v = subprocess.check_output([p,"--version"], creationflags=_no_window()
                    ).decode().strip()
                self._path_status.setText(f"✓  Found  —  version {v}")
            except Exception:
                self._path_status.setText("✓  Found!")
            self._path_status.setObjectName("status_ok")
        else:
            self._path_status.setText("✗  Not found — check path or use Install below")
            self._path_status.setObjectName("status_err")
        self._path_status.style().unpolish(self._path_status)
        self._path_status.style().polish(self._path_status)

    def _update_ytdlp(self):
        self._set_log.clear()
        self._set_log.append("<span style='color:#a78bfa'>▶  Updating yt-dlp…</span>")
        t = UpdateThread(self._ytdlp_path)
        t.log_sig.connect(lambda l: self._set_log.append(f"<span style='color:#6a6a88'>{l}</span>"))
        t.done_sig.connect(lambda ok: self._set_log.append(
            "<span style='color:#34d399'>✓  Updated!</span>" if ok
            else "<span style='color:#f87171'>✗  Update failed</span>"))
        t.start(); self._upd_thread = t

    def _pip_install(self):
        self._set_log.clear()
        self._set_log.append("<span style='color:#a78bfa'>▶  pip install -U yt-dlp …</span>")
        try:
            proc = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                universal_newlines=True, creationflags=_no_window(),
            )
            out,_ = proc.communicate()
            for line in out.splitlines():
                self._set_log.append(f"<span style='color:#6a6a88'>{line}</span>")
            if proc.returncode == 0:
                self._set_log.append(
                    "<span style='color:#34d399'>✓  Installed! Searching for yt-dlp…</span>")
                new = find_ytdlp()
                if new:
                    self._ytdlp_path = new
                    self._path_input.setText(new)
                    self._check_status()
                    self._set_log.append(
                        f"<span style='color:#34d399'>✓  Detected: {new}</span>")
                else:
                    self._set_log.append(
                        "<span style='color:#fbbf24'>⚠  Installed but not found on PATH yet. "
                        "Use Browse to set the path manually.</span>")
            else:
                self._set_log.append("<span style='color:#f87171'>✗  Installation failed</span>")
        except Exception as e:
            self._set_log.append(f"<span style='color:#f87171'>✗  {e}</span>")

    # ── Misc ──────────────────────────────────────────────────────────────────
    def _update_b_count(self):
        n = len([u for u in self._b_urls.toPlainText().splitlines() if u.strip()])
        self._b_cnt.setText(f"{n} URL{'s' if n!=1 else ''}")

    def closeEvent(self, event):
        if self._dl_thread and self._dl_thread.isRunning():
            r = QMessageBox.question(self, "Téléchargement en cours",
                "Un téléchargement est en cours. Quitter quand même ?",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if r == QMessageBox.Yes:
                self._dl_thread.abort(); event.accept()
            else:
                event.ignore(); return
        self._save_settings(); event.accept()


# ─────────────────────────────────────────────────────────────────────────────
#  ENTRY
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())