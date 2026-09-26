"""HTTP helper tests with a mocked urlopen. No network."""

from __future__ import annotations

import io
import unittest
import urllib.error
from email.message import Message
from pathlib import Path
from unittest import mock

from wiki_interest.http import DEFAULT_TIMEOUT_SECONDS, DEFAULT_USER_AGENT, HttpError, get_json

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "pageviews"


def _response(body: bytes, status: int = 200) -> mock.MagicMock:
    response = mock.MagicMock()
    response.__enter__.return_value = response
    response.read.return_value = body
    response.status = status
    response.getcode.return_value = status
    return response


class HttpHelperTests(unittest.TestCase):
    @mock.patch("wiki_interest.http.urllib.request.urlopen")
    def test_user_agent_and_timeout(self, urlopen: mock.MagicMock) -> None:
        urlopen.return_value = _response(b"{}")
        self.assertEqual(get_json("https://example.test/api", {"a": "b"}), {})
        request = urlopen.call_args.args[0]
        self.assertEqual(request.get_header("User-agent"), DEFAULT_USER_AGENT)
        self.assertIn("wiki-interest", DEFAULT_USER_AGENT)
        self.assertEqual(urlopen.call_args.kwargs["timeout"], DEFAULT_TIMEOUT_SECONDS)
        self.assertIn("a=b", request.full_url)

    @mock.patch("wiki_interest.http.urllib.request.urlopen")
    def test_http_error_keeps_status_code(self, urlopen: mock.MagicMock) -> None:
        urlopen.side_effect = urllib.error.HTTPError(
            "https://example.test/api",
            429,
            "Too Many Requests",
            Message(),
            io.BytesIO(b"slow down"),
        )
        with self.assertRaises(HttpError) as caught:
            get_json("https://example.test/api", {})
        self.assertEqual(caught.exception.status_code, 429)
        self.assertFalse(caught.exception.timed_out)

    @mock.patch("wiki_interest.http.urllib.request.urlopen")
    def test_timeout_and_malformed_json(self, urlopen: mock.MagicMock) -> None:
        urlopen.side_effect = urllib.error.URLError(TimeoutError("timed out"))
        with self.assertRaises(HttpError) as timed:
            get_json("https://example.test/api", {})
        self.assertTrue(timed.exception.timed_out)

        urlopen.side_effect = None
        urlopen.return_value = _response((FIXTURES / "not_json.txt").read_bytes())
        with self.assertRaises(HttpError) as malformed:
            get_json("https://example.test/api", {})
        self.assertIn("not JSON", str(malformed.exception))
        self.assertIsNone(malformed.exception.status_code)
