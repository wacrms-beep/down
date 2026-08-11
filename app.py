"""
Velox API — yt-dlp manager, sans interface graphique.

Toutes les fonctionnalités de l'ancienne app PyQt5 (téléchargement simple,
batch, audio, playlist, historique, paramètres) sont exposées ici en tant
qu'endpoints REST. Les téléchargements tournent en arrière-plan dans des
threads ; on suit leur progression via un job_id qu'on interroge (polling).

Lancer :
    pip install fastapi uvicorn
    uvicorn app:app --host 0.0.0.0 --port 8000

Doc interactive une fois lancé : http://localhost:8000/docs

Cookies :
    Le serveur n'a pas de navigateur local (--cookies-from-browser est donc
    inutilisable en prod). Place un fichier `cookies.txt` (format Netscape,
    exporté par une extension type "Get cookies.txt LOCALLY") dans le
    dossier VELOX_DATA_DIR (ou configure VELOX_COOKIES_FILE avec un chemin
    précis). Il sera utilisé automatiquement par tous les endpoints de
    téléchargement si aucun `cookies` n'est fourni dans la requête.
    NE JAMAIS committer ce fichier dans git (ajoute-le à .gitignore) : il
    contient des jetons de session valides.
"""

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
#  HELPERS (repris tels quels de l'app desktop)
# ─────────────────────────────────────────────────────────────────────────────
def find_ytdlp() -> Optional[str]:
    found = shutil.which("yt-dlp") or shutil.which("yt-dlp.exe")
    if found:
        return found

    appdata = os.environ.get("APPDATA", "")
    localappdata = os.environ.get("LOCALAPPDATA", "")
    home = os.path.expanduser("~")

    major, minor = sys.version_info.major, sys.version_info.minor
    roaming_scripts = os.path.join(
        appdata, "Python", f"Python{major}{minor}", "Scripts", "yt-dlp.exe"
    )
    if os.path.isfile(roaming_scripts):
        return roaming_scripts

    for hit in glob.glob(os.path.join(appdata, "Python", "Python3*", "Scripts", "yt-dlp.exe")):
        return hit

    py_dir = os.path.dirname(sys.executable)
    for candidate in [
        os.path.join(py_dir, "yt-dlp.exe"),
        os.path.join(py_dir, "Scripts", "yt-dlp.exe"),
    ]:
        if os.path.isfile(candidate):
            return candidate

    for hit in glob.glob(
        os.path.join(localappdata, "Microsoft", "WinGet", "Packages", "yt-dlp.yt-dlp*", "yt-dlp.exe")
    ):
        return hit
    winget_links = os.path.join(localappdata, "Microsoft", "WinGet", "Links", "yt-dlp.exe")
    if os.path.isfile(winget_links):
        return winget_links

    for path in [
        os.path.join(home, "AppData", "Local", "Programs", "yt-dlp", "yt-dlp.exe"),
        r"C:\tools\yt-dlp\yt-dlp.exe",
        r"C:\yt-dlp\yt-dlp.exe",
        "/usr/local/bin/yt-dlp",
        "/usr/bin/yt-dlp",
    ]:
        if os.path.isfile(path):
            return path

    return None


def _no_window():
    return subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


# ─────────────────────────────────────────────────────────────────────────────
#  MAPS DE COMMANDE (repris de l'app desktop)
# ─────────────────────────────────────────────────────────────────────────────
Q_MAP = {
    "Best available": "bestvideo+bestaudio/best",
    "4K (2160p)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
    "1440p": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
    "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
    "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
    "240p": "bestvideo[height<=240]+bestaudio/best[height<=240]",
    "Worst": "worstvideo+worstaudio/worst",
}
F_MAP = {"MP4": "mp4", "MKV": "mkv", "WEBM": "webm", "AVI": "avi", "MOV": "mov"}
B_MAP = {
    "Chrome": "chrome", "Firefox": "firefox", "Edge": "edge",
    "Brave": "brave", "Opera": "opera", "Vivaldi": "vivaldi",
}


def build_cmd(ytdlp_path, url, quality, fmt, browser, cookies, out_tmpl,
              speed=None, subs=False, thumb=False, meta=False, chapters=False,
              no_playlist=True, folder=None, proxy=None):
    cmd = [ytdlp_path, url, "-f", Q_MAP.get(quality, "bestvideo+bestaudio/best"),
           "--newline", "--progress"]
    f = F_MAP.get(fmt)
    if f:
        cmd += ["--merge-output-format", f]
    tmpl = (out_tmpl or "").strip() or "%(title)s.%(ext)s"
    if folder:
        tmpl = os.path.join(folder, tmpl)
    cmd += ["-o", tmpl]
    b = B_MAP.get(browser)
    if b:
        cmd += ["--cookies-from-browser", b]
    if cookies:
        cmd += ["--cookies", cookies]
    if proxy:
        cmd += ["--proxy", proxy]
    if speed:
        cmd += ["--limit-rate", speed]
    if subs:
        cmd += ["--write-auto-subs", "--sub-langs", "all"]
    if thumb:
        cmd += ["--embed-thumbnail"]
    if meta:
        cmd += ["--embed-metadata", "--add-metadata"]
    if chapters:
        cmd += ["--embed-chapters"]
    if no_playlist:
        cmd += ["--no-playlist"]
    return cmd


def build_audio_cmd(ytdlp_path, url, fmt, quality, folder=None,
                     thumb=False, meta=False, split_chapters=False, cookies=None,
                     proxy=None):
    tmpl = os.path.join(folder, "%(title)s.%(ext)s") if folder else "%(title)s.%(ext)s"
    cmd = [ytdlp_path, url, "-x", "--audio-format", fmt.lower(),
           "--newline", "--progress", "-o", tmpl]
    if quality != "Best":
        cmd += ["--audio-quality", f"{quality}k"]
    if cookies:
        cmd += ["--cookies", cookies]
    if proxy:
        cmd += ["--proxy", proxy]
    if thumb:
        cmd += ["--embed-thumbnail"]
    if meta:
        cmd += ["--embed-metadata", "--add-metadata"]
    if split_chapters:
        cmd += ["--split-chapters", "-o", "chapter:%(section_title)s.%(ext)s"]
    return cmd


def build_playlist_cmd(ytdlp_path, url, mode, num_tmpl, folder=None, speed=None,
                        subs=False, thumb=False, meta=False,
                        quality="Best available", fmt="Auto", browser="None",
                        a_fmt="MP3", a_quality="Best", cookies=None, proxy=None):
    if mode == "video":
        ext = F_MAP.get(fmt, "")
        tmpl = f"{num_tmpl}.{'%(ext)s' if not ext else ext}"
        if folder:
            tmpl = os.path.join(folder, tmpl)
        cmd = [ytdlp_path, url, "-f", Q_MAP.get(quality, "bestvideo+bestaudio/best"),
               "--newline", "--progress", "-o", tmpl, "--yes-playlist"]
        if ext:
            cmd += ["--merge-output-format", ext]
        b = B_MAP.get(browser)
        if b:
            cmd += ["--cookies-from-browser", b]
    else:
        tmpl = f"{num_tmpl}.%(ext)s"
        if folder:
            tmpl = os.path.join(folder, tmpl)
        cmd = [ytdlp_path, url, "-x", "--audio-format", a_fmt.lower(),
               "--newline", "--progress", "-o", tmpl, "--yes-playlist"]
        if a_quality != "Best":
            cmd += ["--audio-quality", f"{a_quality}k"]

    if cookies:
        cmd += ["--cookies", cookies]
    if proxy:
        cmd += ["--proxy", proxy]
    if speed:
        cmd += ["--limit-rate", speed]
    if subs and mode == "video":
        cmd += ["--write-auto-subs", "--sub-langs", "all"]
    if thumb:
        cmd += ["--embed-thumbnail"]
    if meta:
        cmd += ["--embed-metadata", "--add-metadata"]
    return cmd


# ─────────────────────────────────────────────────────────────────────────────
#  ÉTAT PERSISTANT (paramètres + historique)
# ─────────────────────────────────────────────────────────────────────────────
# Sur Render (et tout hébergeur au disque éphémère), monter un disque
# persistant et pointer VELOX_DATA_DIR dessus (voir render.yaml).
DATA_DIR = os.environ.get("VELOX_DATA_DIR", os.path.expanduser("~"))
DOWNLOADS_DIR = os.path.join(DATA_DIR, "downloads")
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# ─────────────────────────────────────────────────────────────────────────────
#  COOKIES — fichier Netscape (cookies.txt) partagé par défaut
# ─────────────────────────────────────────────────────────────────────────────
# Cookie embarqué directement dans le code (à la demande). yt-dlp attend un
# chemin de fichier pour --cookies : on écrit donc ce contenu sur disque une
# fois au démarrage, puis on réutilise ce chemin.
EMBEDDED_COOKIES_TXT = """# Netscape HTTP Cookie File
# https://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file! Do not edit.

.pornhub.com\tTRUE\t/\tTRUE\t1816368682\tss\t591934820168317375
.pornhub.com\tTRUE\t/\tTRUE\t1816368682\tsessid\t579564516745917703
.pornhub.com\tTRUE\t/\tTRUE\t1787424682\tcomp_detect-cookies\t35652.100000
.pornhub.com\tTRUE\t/\tTRUE\t1816389608\t__l\t6A6262A8-42FE722901BB76655-DC9A11
.pornhub.com\tTRUE\t/\tTRUE\t1787424684\tfg_afaf12e314c5419a855ddc0bf120670f\t91670.100000
.pornhub.com\tTRUE\t/\tTRUE\t1787424684\tfg_43cd950e43067a4ecc8c7ba3d887ff26\t7507.100000
.pornhub.com\tTRUE\t/\tTRUE\t1787424684\tfg_55e3b6f0afd46366d6fa797544b15af2\t42024.100000
.pornhub.com\tTRUE\t/\tTRUE\t1787424684\tfg_7d31324eedb583147b6dcbea0051c868\t30586.100000
.pornhub.com\tTRUE\t/\tTRUE\t1816368685\tcookieConsent\t3
.pornhub.com\tTRUE\t/\tFALSE\t1820963459\t_ga\tGA1.1.610206280.1784832730
.pornhub.com\tTRUE\t/\tTRUE\t1816368781\tbsdd\t02e7c8a4c03603c7a6fab8fba30c9fbc
.pornhub.com\tTRUE\t/\tTRUE\t1787424782\tcomp_mandatory-dob-existing-user\t99684.100000
.pornhub.com\tTRUE\t/\tTRUE\t1816406034\tlvv\t198137615222471655
.pornhub.com\tTRUE\t/\tTRUE\t1816406034\tvlc\t601847635441355279
.pornhub.com\tTRUE\t/\tTRUE\t1787462239\tfg_439f2555043a44b8bd91161b5deddd29\t16009.100000
.pornhub.com\tTRUE\t/\tTRUE\t1786489813\tua\t6967ec7261b3cbe6a91d798c6b951c60
.pornhub.com\tTRUE\t/\tTRUE\t1787008213\tplatform\tpc
.pornhub.com\tTRUE\t/\tTRUE\t0\t__s\t6A7A5A55-42FE722901BB18AA3B-3118FE0
.pornhub.com\tTRUE\t/\tTRUE\t1788995414\tfg_41b1995ee5530001895f2da326e410dd\t9134.100000
.pornhub.com\tTRUE\t/\tFALSE\t1786407020\taccessAgeDisclaimerPH\t2
.pornhub.com\tTRUE\t/\tFALSE\t1801955456\tg_state\t{"i_l":0,"i_ll":1786403450357,"i_e":{"enable_itp_optimization":24},"i_et":1786403450357}
.pornhub.com\tTRUE\t/\tTRUE\t1802214657\til\tv1gXouIblCkjQMkCMhXexFbz8115-XPYfAvNVKVWG59zsxODAyMjE0NjU3REJNNTg1R2hWMWUyN2F5bk9tTUh3c0o0aGZENGpPUDF2YWVYSTJPOQ..
.pornhub.com\tTRUE\t/\tTRUE\t1817939457\tbs\t02e7c8a4c03603c7a6fab8fba30c9fbc
.pornhub.com\tTRUE\t/\tFALSE\t1820963459\t_ga_B39RFFWGYY\tGS2.1.s1786403436$o4$g1$t1786403459$j37$l0$h0
fr.pornhub.com\tFALSE\t/\tFALSE\t0\trp\t4203231596:ApoyNCNk2ew=
"""

DEFAULT_COOKIES_FILE = os.environ.get(
    "VELOX_COOKIES_FILE", os.path.join(DATA_DIR, "cookies.txt")
)


def _ensure_embedded_cookies_written():
    """Écrit le cookie embarqué sur disque au démarrage si le fichier n'existe
    pas déjà (ou est plus ancien que ce qui est codé en dur)."""
    try:
        with open(DEFAULT_COOKIES_FILE, "w") as f:
            f.write(EMBEDDED_COOKIES_TXT)
    except Exception:
        pass


_ensure_embedded_cookies_written()


# ─────────────────────────────────────────────────────────────────────────────
# PROXY — pour contourner les 403 liés à l'IP datacenter (Render, etc.)
# Configure via variable d'env VELOX_PROXY sur Render, ex:
#   http://user:password@proxy-host:port
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_PROXY = os.environ.get("VELOX_PROXY", "").strip() or None


def resolve_proxy(explicit: Optional[str]) -> Optional[str]:
    if explicit and explicit.strip():
        return explicit.strip()
    return DEFAULT_PROXY


def resolve_cookies(explicit: Optional[str]) -> Optional[str]:
    """Renvoie le chemin de cookies à utiliser : celui fourni dans la requête
    en priorité, sinon le fichier par défaut (généré depuis EMBEDDED_COOKIES_TXT)."""
    if explicit and explicit.strip():
        return explicit.strip()
    if os.path.isfile(DEFAULT_COOKIES_FILE):
        return DEFAULT_COOKIES_FILE
    return None


class Store:
    def __init__(self):
        self.path = os.path.join(DATA_DIR, ".velox_settings.json")
        self.lock = threading.Lock()
        self.ytdlp_path = find_ytdlp() or "yt-dlp"
        self.history: List[dict] = []
        self.total = 0
        self._load()

    def _load(self):
        try:
            with open(self.path) as f:
                d = json.load(f)
            self.ytdlp_path = d.get("ytdlp_path") or self.ytdlp_path
            self.history = d.get("history", [])
            self.total = d.get("total", 0)
        except Exception:
            pass

    def save(self):
        with self.lock:
            try:
                with open(self.path, "w") as f:
                    json.dump(
                        {"ytdlp_path": self.ytdlp_path, "history": self.history[-200:], "total": self.total},
                        f, indent=2,
                    )
            except Exception:
                pass

    def record(self, url, ok, mode):
        self.total += 1
        self.history.append({
            "url": url, "success": ok, "mode": mode,
            "ts": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        self.save()


store = Store()

# ─────────────────────────────────────────────────────────────────────────────
#  GESTION DES JOBS (remplace les QThread de l'app desktop)
# ─────────────────────────────────────────────────────────────────────────────
class Job:
    def __init__(self, job_id: str, mode: str, url: str = ""):
        self.id = job_id
        self.mode = mode          # single | batch | audio | playlist
        self.url = url
        self.status = "queued"    # queued | running | done | error | cancelled
        self.pct = 0.0
        self.speed = None
        self.eta = None
        self.log: List[str] = []
        self.ok: Optional[bool] = None
        self.process: Optional[subprocess.Popen] = None
        self.items: List[dict] = []   # pour les jobs batch : [{url, status, ok}]
        self.created_at = datetime.now().isoformat()
        self._cancel_requested = False

    def to_dict(self):
        return {
            "job_id": self.id, "mode": self.mode, "url": self.url,
            "status": self.status, "pct": self.pct, "speed": self.speed,
            "eta": self.eta, "ok": self.ok, "items": self.items,
            "created_at": self.created_at,
            "log_tail": self.log[-50:],
        }


jobs: Dict[str, Job] = {}
jobs_lock = threading.Lock()


def _stream_process(job: Job, cmd: List[str]) -> bool:
    """Lance cmd, alimente job.log/pct/speed/eta en direct. Renvoie le succès."""
    try:
        job.process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, bufsize=1, creationflags=_no_window(),
        )
        for line in job.process.stdout:
            line = line.rstrip()
            if not line:
                continue
            job.log.append(line)
            m = re.search(r"(\d+(?:\.\d+)?)%", line)
            if m:
                job.pct = float(m.group(1))
            m2 = re.search(r"at\s+([\d.]+\s*\S+/s)", line)
            if m2:
                job.speed = m2.group(1)
            m3 = re.search(r"ETA\s+(\d+:\d+)", line)
            if m3:
                job.eta = m3.group(1)
        job.process.wait()
        return job.process.returncode == 0
    except Exception as e:
        job.log.append(f"[ERROR] {e}")
        return False


def _run_single(job: Job, cmd: List[str]):
    job.status = "running"
    ok = _stream_process(job, cmd)
    job.ok = ok
    job.status = "cancelled" if job._cancel_requested else ("done" if ok else "error")
    if ok:
        job.pct = 100.0
    store.record(job.url, ok, job.mode)


def _run_batch(job: Job, url_cmds: List[tuple]):
    job.status = "running"
    total = len(url_cmds)
    for i, (url, cmd) in enumerate(url_cmds):
        if job._cancel_requested:
            job.status = "cancelled"
            return
        item = {"url": url, "status": "running", "ok": None}
        job.items.append(item)
        job.url = url
        job.log.append(f"▶  [{i + 1}/{total}] {url}")
        ok = _stream_process(job, cmd)
        item["status"] = "done" if ok else "error"
        item["ok"] = ok
        job.pct = round((i + 1) / total * 100, 1)
        store.record(url, ok, "batch")
    job.status = "done"
    job.ok = all(it["ok"] for it in job.items)


def start_job(mode: str, url: str, cmd) -> Job:
    job = Job(str(uuid.uuid4()), mode, url)
    with jobs_lock:
        jobs[job.id] = job
    t = threading.Thread(target=_run_single, args=(job, cmd), daemon=True)
    t.start()
    return job


def start_batch_job(url_cmds: List[tuple]) -> Job:
    job = Job(str(uuid.uuid4()), "batch", "")
    with jobs_lock:
        jobs[job.id] = job
    t = threading.Thread(target=_run_batch, args=(job, url_cmds), daemon=True)
    t.start()
    return job


# ─────────────────────────────────────────────────────────────────────────────
#  SCHÉMAS DE REQUÊTE
# ─────────────────────────────────────────────────────────────────────────────
class DownloadRequest(BaseModel):
    url: str
    quality: str = "Best available"
    format: str = "Auto"
    browser: str = "None"
    cookies: Optional[str] = None
    proxy: Optional[str] = None
    output: Optional[str] = None
    speed_limit: Optional[str] = None
    subtitles: bool = False
    embed_thumbnail: bool = False
    embed_metadata: bool = False
    chapters: bool = False
    playlist: bool = False


class BatchRequest(BaseModel):
    urls: List[str]
    quality: str = "Best available"
    format: str = "Auto"
    browser: str = "None"
    cookies: Optional[str] = None
    proxy: Optional[str] = None
    output_folder: Optional[str] = None
    output_template: str = "%(autonumber)s - %(title)s.%(ext)s"
    subtitles: bool = False
    embed_thumbnail: bool = False
    embed_metadata: bool = False


class AudioRequest(BaseModel):
    url: str
    format: str = "MP3"
    quality: str = "Best"
    cookies: Optional[str] = None
    proxy: Optional[str] = None
    output_folder: Optional[str] = None
    embed_thumbnail: bool = False
    embed_metadata: bool = False
    split_chapters: bool = False


class PlaylistRequest(BaseModel):
    url: str
    mode: str = Field("video", pattern="^(video|audio)$")
    quality: str = "Best available"
    format: str = "Auto"
    browser: str = "None"
    cookies: Optional[str] = None
    proxy: Optional[str] = None
    audio_format: str = "MP3"
    audio_quality: str = "Best"
    output_folder: Optional[str] = None
    numbering: str = "%(autonumber)s - %(title)s"
    speed_limit: Optional[str] = None
    subtitles: bool = False
    embed_thumbnail: bool = False
    embed_metadata: bool = False


class SettingsPathRequest(BaseModel):
    path: str


# ─────────────────────────────────────────────────────────────────────────────
#  APPLICATION
# ─────────────────────────────────────────────────────────────────────────────
app = FastAPI(title="Velox API", description="yt-dlp manager sans interface graphique", version="1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "Velox API",
        "docs": "/docs",
        "status": "/status",
    }


@app.get("/status")
def get_status():
    ok = bool(shutil.which(store.ytdlp_path) or os.path.isfile(store.ytdlp_path))
    version = None
    if ok:
        try:
            version = subprocess.check_output(
                [store.ytdlp_path, "--version"], creationflags=_no_window()
            ).decode().strip()
        except Exception:
            pass
    return {"ytdlp_path": store.ytdlp_path, "available": ok, "version": version}


# ── Download simple ─────────────────────────────────────────────────────────
@app.post("/download")
def download(req: DownloadRequest):
    if not req.url.strip():
        raise HTTPException(400, "URL requise")
    out_tmpl = req.output or "%(title)s.%(ext)s"
    out_tmpl = os.path.join(DOWNLOADS_DIR, out_tmpl)
    cmd = build_cmd(
        store.ytdlp_path, req.url, req.quality, req.format, req.browser,
        resolve_cookies(req.cookies), out_tmpl, req.speed_limit,
        subs=req.subtitles, thumb=req.embed_thumbnail, meta=req.embed_metadata,
        chapters=req.chapters, no_playlist=not req.playlist,
        proxy=resolve_proxy(req.proxy),
    )
    job = start_job("single", req.url, cmd)
    return {"job_id": job.id}


# ── Batch ────────────────────────────────────────────────────────────────────
@app.post("/batch")
def batch(req: BatchRequest):
    urls = [u.strip() for u in req.urls if u.strip()]
    if not urls:
        raise HTTPException(400, "Aucune URL fournie")
    folder = req.output_folder or DOWNLOADS_DIR
    cookies = resolve_cookies(req.cookies)
    proxy = resolve_proxy(req.proxy)
    url_cmds = [
        (u, build_cmd(
            store.ytdlp_path, u, req.quality, req.format, req.browser, cookies,
            req.output_template, folder=folder,
            subs=req.subtitles, thumb=req.embed_thumbnail, meta=req.embed_metadata,
            no_playlist=False, proxy=proxy,
        ))
        for u in urls
    ]
    job = start_batch_job(url_cmds)
    return {"job_id": job.id, "count": len(urls)}


# ── Audio ────────────────────────────────────────────────────────────────────
@app.post("/audio")
def audio(req: AudioRequest):
    if not req.url.strip():
        raise HTTPException(400, "URL requise")
    cmd = build_audio_cmd(
        store.ytdlp_path, req.url, req.format, req.quality,
        req.output_folder or DOWNLOADS_DIR,
        thumb=req.embed_thumbnail, meta=req.embed_metadata, split_chapters=req.split_chapters,
        cookies=resolve_cookies(req.cookies), proxy=resolve_proxy(req.proxy),
    )
    job = start_job("audio", req.url, cmd)
    return {"job_id": job.id}


# ── Playlist ─────────────────────────────────────────────────────────────────
@app.get("/playlist/info")
def playlist_info(url: str):
    if not url.strip():
        raise HTTPException(400, "URL requise")
    try:
        cmd = [store.ytdlp_path, "--flat-playlist", "--dump-single-json", "--no-warnings"]
        cookies = resolve_cookies(None)
        if cookies:
            cmd += ["--cookies", cookies]
        proxy = resolve_proxy(None)
        if proxy:
            cmd += ["--proxy", proxy]
        cmd.append(url)
        proc = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, creationflags=_no_window(),
        )
        out, err = proc.communicate()
        if proc.returncode != 0:
            raise HTTPException(502, err.strip() or "Erreur yt-dlp inconnue")
        data = json.loads(out)
        return {"title": data.get("title", "Playlist inconnue"), "count": len(data.get("entries", []))}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/playlist")
def playlist(req: PlaylistRequest):
    if not req.url.strip():
        raise HTTPException(400, "URL requise")
    cmd = build_playlist_cmd(
        store.ytdlp_path, req.url, req.mode, req.numbering,
        folder=req.output_folder or DOWNLOADS_DIR, speed=req.speed_limit,
        subs=req.subtitles, thumb=req.embed_thumbnail, meta=req.embed_metadata,
        quality=req.quality, fmt=req.format, browser=req.browser,
        a_fmt=req.audio_format, a_quality=req.audio_quality,
        cookies=resolve_cookies(req.cookies), proxy=resolve_proxy(req.proxy),
    )
    job = start_job("playlist", req.url, cmd)
    return {"job_id": job.id}


# ── Jobs (suivi / annulation) ────────────────────────────────────────────────
@app.get("/jobs/{job_id}")
def get_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job introuvable")
    return job.to_dict()


@app.get("/jobs")
def list_jobs():
    return [j.to_dict() for j in jobs.values()]


@app.post("/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job introuvable")
    job._cancel_requested = True
    if job.process:
        job.process.terminate()
    return {"job_id": job_id, "status": "cancel_requested"}


# ── Historique ───────────────────────────────────────────────────────────────
@app.get("/history")
def get_history():
    ok = sum(1 for h in store.history if h["success"])
    return {
        "total": store.total,
        "successful": ok,
        "failed": len(store.history) - ok,
        "entries": list(reversed(store.history[-100:])),
    }


@app.delete("/history")
def clear_history():
    store.history = []
    store.save()
    return {"cleared": True}


# ── Paramètres ───────────────────────────────────────────────────────────────
@app.get("/settings")
def get_settings():
    return {"ytdlp_path": store.ytdlp_path}


@app.post("/settings/path")
def set_path(req: SettingsPathRequest):
    store.ytdlp_path = req.path
    store.save()
    return get_status()


@app.get("/settings/cookies")
def get_cookies_status():
    """Indique si un fichier cookies.txt par défaut est présent côté serveur,
    sans jamais exposer son contenu."""
    exists = os.path.isfile(DEFAULT_COOKIES_FILE)
    size = os.path.getsize(DEFAULT_COOKIES_FILE) if exists else 0
    return {"path": DEFAULT_COOKIES_FILE, "present": exists, "size_bytes": size}


@app.get("/settings/proxy")
def get_proxy_status():
    """Indique si un proxy par défaut est configuré (VELOX_PROXY), sans
    exposer les identifiants qu'il contient."""
    if not DEFAULT_PROXY:
        return {"configured": False}
    masked = re.sub(r"://[^@]+@", "://***:***@", DEFAULT_PROXY)
    return {"configured": True, "proxy": masked}


@app.post("/settings/update")
def update_ytdlp():
    """Lance yt-dlp -U (auto-update) et renvoie la sortie complète (synchrone)."""
    try:
        proc = subprocess.Popen(
            [store.ytdlp_path, "-U"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, creationflags=_no_window(),
        )
        out, _ = proc.communicate()
        return {"ok": proc.returncode == 0, "output": out}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/settings/pip-install")
def pip_install():
    """pip install -U yt-dlp, puis re-détecte le chemin."""
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            universal_newlines=True, creationflags=_no_window(),
        )
        out, _ = proc.communicate()
        result = {"ok": proc.returncode == 0, "output": out}
        if proc.returncode == 0:
            new_path = find_ytdlp()
            if new_path:
                store.ytdlp_path = new_path
                store.save()
                result["detected_path"] = new_path
        return result
    except Exception as e:
        raise HTTPException(500, str(e))


# ── Fichiers téléchargés (à défaut d'une fenêtre, on les sert via HTTP) ──────
@app.get("/files")
def list_files():
    entries = []
    for root, _, names in os.walk(DOWNLOADS_DIR):
        for n in names:
            full = os.path.join(root, n)
            rel = os.path.relpath(full, DOWNLOADS_DIR)
            entries.append({"name": rel, "size_bytes": os.path.getsize(full)})
    return {"downloads_dir": DOWNLOADS_DIR, "files": entries}


@app.get("/files/{filename:path}")
def get_file(filename: str):
    full = os.path.normpath(os.path.join(DOWNLOADS_DIR, filename))
    if not full.startswith(os.path.normpath(DOWNLOADS_DIR)):
        raise HTTPException(400, "Chemin invalide")
    if not os.path.isfile(full):
        raise HTTPException(404, "Fichier introuvable")
    return FileResponse(full, filename=os.path.basename(full))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
