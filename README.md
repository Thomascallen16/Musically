# Musically

A small local browser-audio capture utility.

Musically opens its own Chromium browser, watches the browser's network traffic, and saves accessible audio media as MP3. It does NOT record the laptop speakers or microphone.

Use it only for audio you have the right or permission to save. It does not bypass DRM, decrypt protected media, defeat paywalls, or bypass access controls.

Requirements:
- Windows, macOS, or Linux
- Python 3.10+
- FFmpeg on PATH for conversion/remuxing
- Playwright Chromium (installed by the launcher)

Optional:
- Demucs for AI stem separation. This is deliberately optional because the model is much larger than the core app.

Quick start:
- Windows: run run_musically.bat
- macOS/Linux: chmod +x run_musically.sh && ./run_musically.sh

Operation:
1. Start Browser.
2. Navigate to the site and press Play.
3. Enter a filename.
4. Click Capture Current Audio.
5. MP3 files are saved in Downloads.
6. Use Split Selected MP3 into Stems when Demucs is installed.

The core project is intentionally one Python file plus one dependency. No server, database, account, or cloud service is required.

Important: some sites deliver encrypted or otherwise protected media. Musically will not circumvent those protections. Some sites also prohibit downloading in their terms.
