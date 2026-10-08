from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from urllib.parse import urlparse

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
DOWNLOADS = ROOT / "Downloads"
STEMS = ROOT / "Stems"
DOWNLOADS.mkdir(exist_ok=True)
STEMS.mkdir(exist_ok=True)

AUDIO_TYPES = (
    "audio/",
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "application/dash+xml",
)
AUDIO_EXTS = {".mp3",".m4a",".aac",".wav",".flac",".ogg",".opus",".webm",".mp4",".m3u8",".mpd"}

def safe_name(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9._ -]+", "_", value).strip(" .")
    return value[:150] or "captured_audio"

def unique_path(directory: Path, stem: str, suffix: str) -> Path:
    p = directory / f"{stem}{suffix}"
    n = 2
    while p.exists():
        p = directory / f"{stem} ({n}){suffix}"
        n += 1
    return p

def ffmpeg_path():
    return shutil.which("ffmpeg")

def ffmpeg_convert(source: Path, target: Path):
    exe = ffmpeg_path()
    if not exe:
        return False, "FFmpeg is not installed or is not on PATH."
    cmd = [exe,"-hide_banner","-loglevel","error","-y","-i",str(source),
           "-vn","-codec:a","libmp3lame","-q:a","2",str(target)]
    try:
        r = subprocess.run(cmd,capture_output=True,text=True,timeout=900)
        if r.returncode == 0 and target.exists():
            return True, str(target)
        return False, r.stderr.strip() or "FFmpeg failed."
    except Exception as e:
        return False, str(e)

class MusicallyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Musically")
        self.root.geometry("760x520")
        self.root.minsize(650,450)
        self.pw = None
        self.browser = None
        self.context = None
        self.page = None
        self.media = []
        self.lock = threading.Lock()
        self.status = tk.StringVar(value="Ready.")
        self.url = tk.StringVar(value="https://www.google.com")
        self.filename = tk.StringVar(value="captured_audio")
        self.build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def build_ui(self):
        outer = ttk.Frame(self.root,padding=16)
        outer.pack(fill="both",expand=True)
        ttk.Label(outer,text="Musically",font=("TkDefaultFont",20,"bold")).pack(anchor="w")
        ttk.Label(outer,text="Capture the browser's accessible audio stream — not the laptop speakers.").pack(anchor="w",pady=(0,14))
        row = ttk.Frame(outer)
        row.pack(fill="x")
        ttk.Entry(row,textvariable=self.url).pack(side="left",fill="x",expand=True)
        ttk.Button(row,text="Start Browser",command=self.start_browser).pack(side="left",padx=(8,0))
        opts = ttk.Frame(outer)
        opts.pack(fill="x",pady=12)
        ttk.Label(opts,text="Save as:").pack(side="left")
        ttk.Entry(opts,textvariable=self.filename,width=36).pack(side="left",padx=8)
        ttk.Button(opts,text="Capture Current Audio",command=self.capture).pack(side="left")
        ttk.Button(opts,text="Split Selected MP3 into Stems",command=self.split_stems).pack(side="left",padx=(8,0))
        ttk.Label(outer,text="Recent media detected:").pack(anchor="w",pady=(8,4))
        self.listbox = tk.Listbox(outer,height=13)
        self.listbox.pack(fill="both",expand=True)
        ttk.Label(outer,textvariable=self.status).pack(anchor="w",pady=(10,0))

    def set_status(self,text):
        self.root.after(0,self.status.set,text)

    def start_browser(self):
        if self.page:
            self.set_status("Browser is already running.")
            return
        def worker():
            try:
                self.pw = sync_playwright().start()
                self.browser = self.pw.chromium.launch(headless=False)
                self.context = self.browser.new_context(accept_downloads=True)
                self.page = self.context.new_page()
                self.page.on("response",self.on_response)
                self.page.goto(self.url.get().strip(),wait_until="domcontentloaded",timeout=60000)
                self.set_status("Browser ready. Navigate and press Play.")
            except Exception as e:
                self.set_status(f"Could not start browser: {e}")
        threading.Thread(target=worker,daemon=True).start()

    def on_response(self,response):
        try:
            headers = response.headers
            ctype = (headers.get("content-type") or "").lower()
            url = response.url
            path = urlparse(url).path.lower()
            is_audio = any(ctype.startswith(t) for t in AUDIO_TYPES) or any(path.endswith(ext) for ext in AUDIO_EXTS)
            if not is_audio:
                return
            item = {"url":url,"content_type":ctype,"time":time.time(),"status":response.status}
            with self.lock:
                if not any(x["url"] == url for x in self.media):
                    self.media.append(item)
                    self.media = self.media[-100:]
            self.root.after(0,self.listbox.insert,tk.END,f"{ctype or 'media'} | {url[:120]}")
            self.set_status("Audio/media detected.")
        except Exception:
            pass

    def capture(self):
        if not self.page:
            messagebox.showinfo("Musically","Start the browser first.")
            return
        with self.lock:
            candidates = list(reversed(self.media))
        if not candidates:
            messagebox.showinfo("Musically","No accessible audio request has been detected yet. Start playback and try again.")
            return
        name = safe_name(self.filename.get())
        threading.Thread(target=self.capture_worker,args=(candidates[0],name),daemon=True).start()

    def capture_worker(self,item,name):
        url = item["url"]
        self.set_status("Capturing accessible audio...")
        try:
            parsed = urlparse(url)
            ext = Path(parsed.path).suffix.lower()
            if ext in {".mp3",".m4a",".aac",".wav",".flac",".ogg",".opus",".webm",".mp4"}:
                response = self.context.request.get(url,timeout=120000)
                if not response.ok:
                    raise RuntimeError(f"Media request returned HTTP {response.status}")
                raw = unique_path(DOWNLOADS,name,ext)
                raw.write_bytes(response.body())
                self.finish_mp3(raw,name)
                return
            if ext in {".m3u8",".mpd"} or "mpegurl" in item["content_type"] or "dash" in item["content_type"]:
                exe = ffmpeg_path()
                if not exe:
                    raise RuntimeError("This site supplied a streaming manifest. Install FFmpeg and put it on PATH.")
                target = unique_path(DOWNLOADS,name,".mp3")
                cmd = [exe,"-hide_banner","-loglevel","error","-y","-i",url,"-vn","-codec:a","libmp3lame","-q:a","2",str(target)]
                r = subprocess.run(cmd,capture_output=True,text=True,timeout=900)
                if r.returncode != 0 or not target.exists():
                    raise RuntimeError(r.stderr.strip() or "FFmpeg could not read the stream.")
                self.set_status(f"Saved {target.name}")
                return
            raise RuntimeError("Detected media, but its format was not directly usable.")
        except Exception as e:
            self.set_status(f"Capture failed: {e}")
            self.root.after(0,lambda: messagebox.showerror("Musically",str(e)))

    def finish_mp3(self,raw,name):
        if raw.suffix.lower() == ".mp3":
            self.set_status(f"Saved {raw.name}")
            return
        target = unique_path(DOWNLOADS,name,".mp3")
        ok,msg = ffmpeg_convert(raw,target)
        if ok:
            try: raw.unlink()
            except OSError: pass
            self.set_status(f"Saved {target.name}")
        else:
            self.set_status(f"Saved original media as {raw.name}; MP3 conversion failed: {msg}")

    def split_stems(self):
        selected = filedialog.askopenfilename(initialdir=DOWNLOADS,title="Choose an MP3",filetypes=[("MP3 files","*.mp3"),("Audio","*.*")])
        if not selected:
            return
        demucs = shutil.which("demucs")
        if not demucs:
            messagebox.showinfo("Stem separation","Demucs is not installed. The core Musically app stays lightweight; stem separation is an optional add-on because its AI model is much larger.")
            return
        source = Path(selected)
        def worker():
            self.set_status("Separating stems — this can take a while...")
            try:
                r = subprocess.run([demucs,"-o",str(STEMS),str(source)],capture_output=True,text=True,timeout=3600)
                if r.returncode == 0:
                    self.set_status("Stem separation complete.")
                else:
                    raise RuntimeError(r.stderr.strip() or "Demucs failed.")
            except Exception as e:
                self.set_status(f"Stem separation failed: {e}")
                self.root.after(0,lambda: messagebox.showerror("Stem separation",str(e)))
        threading.Thread(target=worker,daemon=True).start()

    def close(self):
        try:
            if self.context: self.context.close()
            if self.browser: self.browser.close()
            if self.pw: self.pw.stop()
        finally:
            self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    try: ttk.Style().theme_use("clam")
    except tk.TclError: pass
    MusicallyApp(root)
    root.mainloop()
