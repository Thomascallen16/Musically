# Musically

A small local browser-audio capture utility.

Musically opens its own Chromium browser, watches the browser's network traffic, and saves accessible audio media as MP3. It does **not** record the laptop speakers or microphone.

## USB-ready Windows version

The repository can build a self-contained Windows folder containing:

- `Musically.exe`
- its Playwright Chromium browser
- `ffmpeg.exe`
- `Downloads\\` for captured MP3s
- `Stems\\` for optional stem separation

Copy the resulting folder to a USB/external drive. Double-click **Musically.exe**. No Python installation is required for that packaged version.

The first packaged build is produced by GitHub Actions as a ZIP artifact named **Musically-USB-Windows**.

## What it does

1. Start Musically.
2. Musically opens a normal, visible Chromium browser.
3. Navigate to the music site and press Play.
4. Musically watches for audio/media requests delivered to that browser.
5. Click **Capture Current Audio**.
6. The accessible media is saved/converted to MP3 in `Downloads\\`.

It captures the browser-delivered media itself. It does **not** use the microphone, Windows loopback audio, speaker recording, or a virtual sound card.

## DRM / access-control boundary

Musically is intentionally an **accessible-media downloader/converter**, not a DRM circumvention tool.

It only attempts to use media that the browser has already been allowed to request. It does not:

- decrypt DRM-protected media
- crack encryption or license systems
- defeat paywalls or subscriptions
- bypass login/access controls
- extract protected keys
- patch or modify DRM systems

If a site supplies encrypted/protected media, Musically should fail rather than defeat that protection. A site can also prohibit downloading in its terms even when media is technically accessible.

Use it only for audio you have the right or permission to save.

## Stem separation

The **Split Selected MP3 into Stems** button is optional. The lightweight core does not bundle Demucs because its AI models are much larger. If Demucs is installed separately and available on PATH, Musically can invoke it to create separated stems.

## Source/developer version

For Windows development:

- Python 3.10+
- FFmpeg on PATH
- Playwright Chromium

Run `run_musically.bat`.

For macOS/Linux development:

`chmod +x run_musically.sh && ./run_musically.sh`

The core project remains intentionally small: one Python application plus Playwright. No server, database, account, or cloud service is required.

## Limitations

Some sites use segmented, encrypted, authenticated, or otherwise protected delivery. Those cases may not be capturable, and Musically does not attempt to circumvent those protections. Some authenticated streams may also require browser-specific session state that a direct media fetch cannot reproduce.

