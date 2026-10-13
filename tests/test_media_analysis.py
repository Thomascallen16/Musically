import unittest
from media_analysis import choose_candidate, inspect_dash_manifest, inspect_hls_manifest, media_kind


class MediaAnalysisTests(unittest.TestCase):
    def test_media_kind(self):
        self.assertEqual(media_kind("https://x.test/a.m3u8?q=1"), "hls_manifest")
        self.assertEqual(media_kind("https://x.test/live", "application/dash+xml"), "dash_manifest")
        self.assertEqual(media_kind("https://x.test/song", "audio/mpeg"), "direct_media")
        self.assertEqual(media_kind("https://x.test/page.html", "text/html"), "unknown")

    def test_candidate_prefers_successful_manifest_over_failed_large_response(self):
        manifest = {"url": "https://x.test/a.m3u8", "status": 200}
        failed = {"url": "https://x.test/b.mp3", "status": 403, "length": 999999}
        self.assertIs(choose_candidate([failed, manifest]), manifest)
        self.assertIsNone(choose_candidate([]))

    def test_hls_summary(self):
        text = '#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="key"\n#EXTINF:4,\nseg1.ts\n'
        result = inspect_hls_manifest(text)
        self.assertTrue(result["valid"])
        self.assertEqual(result["segments"], 1)
        self.assertTrue(result["encrypted_or_keyed"])
        self.assertFalse(inspect_hls_manifest("nope")["valid"])

    def test_dash_summary(self):
        text = '<MPD xmlns="urn:mpeg:dash:schema:mpd:2011"><Period><AdaptationSet contentType="audio"><Representation id="a"/></AdaptationSet></Period></MPD>'
        result = inspect_dash_manifest(text)
        self.assertTrue(result["valid"])
        self.assertEqual(result["representations"], 1)
        self.assertEqual(result["content_types"], ["audio"])
        self.assertFalse(inspect_dash_manifest("<not-mpd/>")["valid"])


if __name__ == "__main__":
    unittest.main()
