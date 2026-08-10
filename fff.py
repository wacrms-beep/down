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
              no_playlist=True, folder=None):
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
                     thumb=False, meta=False, split_chapters=False):
    tmpl = os.path.join(folder, "%(title)s.%(ext)s") if folder else "%(title)s.%(ext)s"
    cmd = [ytdlp_path, url, "-x", "--audio-format", fmt.lower(),
           "--newline", "--progress", "-o", tmpl]
    if quality != "Best":
        cmd += ["--audio-quality", f"{quality}k"]
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
                        a_fmt="MP3", a_quality="Best"):
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
class Store:
    def __init__(self):
        self.path = os.path.join(os.path.expanduser("~"), ".velox_settings.json")
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
    output_folder: Optional[str] = None
    output_template: str = "%(autonumber)s - %(title)s.%(ext)s"
    subtitles: bool = False
    embed_thumbnail: bool = False
    embed_metadata: bool = False


class AudioRequest(BaseModel):
    url: str
    format: str = "MP3"
    quality: str = "Best"
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
    cmd = build_cmd(
        store.ytdlp_path, req.url, req.quality, req.format, req.browser,
        req.cookies, req.output, req.speed_limit,
        subs=req.subtitles, thumb=req.embed_thumbnail, meta=req.embed_metadata,
        chapters=req.chapters, no_playlist=not req.playlist,
    )
    job = start_job("single", req.url, cmd)
    return {"job_id": job.id}


# ── Batch ────────────────────────────────────────────────────────────────────
@app.post("/batch")
def batch(req: BatchRequest):
    urls = [u.strip() for u in req.urls if u.strip()]
    if not urls:
        raise HTTPException(400, "Aucune URL fournie")
    url_cmds = [
        (u, build_cmd(
            store.ytdlp_path, u, req.quality, req.format, req.browser, "",
            req.output_template, folder=req.output_folder,
            subs=req.subtitles, thumb=req.embed_thumbnail, meta=req.embed_metadata,
            no_playlist=False,
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
        store.ytdlp_path, req.url, req.format, req.quality, req.output_folder,
        thumb=req.embed_thumbnail, meta=req.embed_metadata, split_chapters=req.split_chapters,
    )
    job = start_job("audio", req.url, cmd)
    return {"job_id": job.id}


# ── Playlist ─────────────────────────────────────────────────────────────────
@app.get("/playlist/info")
def playlist_info(url: str):
    if not url.strip():
        raise HTTPException(400, "URL requise")
    try:
        proc = subprocess.Popen(
            [store.ytdlp_path, "--flat-playlist", "--dump-single-json", "--no-warnings", url],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
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
        folder=req.output_folder, speed=req.speed_limit,
        subs=req.subtitles, thumb=req.embed_thumbnail, meta=req.embed_metadata,
        quality=req.quality, fmt=req.format, browser=req.browser,
        a_fmt=req.audio_format, a_quality=req.audio_quality,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
