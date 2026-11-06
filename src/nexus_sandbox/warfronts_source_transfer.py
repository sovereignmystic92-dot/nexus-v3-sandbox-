"""Read-only public transcript fetch and source-transfer diagnostics.

This is a candidate fetch, NOT verified caption/audio transcription.
The Notion source is provided as a local exact-text file by an authorized host.
"""
import argparse
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import Request, urlopen

from nexus_sandbox.warfronts_transcript_diff import compare_transcripts

URL = "https://podcastrex.com/shows/warfronts/el-salvador-has-invaded-haiti-heres-what-you-need-to-know/transcript"
START = "In the Caribbean nation of Haiti"
END = "Thank you for watching."


class PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = 0
    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self.skip += 1
        if not self.skip and tag in ("p", "div", "br", "section", "h1", "h2", "h3"):
            self.parts.append(" ")
    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript") and self.skip:
            self.skip -= 1
        if not self.skip and tag in ("p", "div", "section", "h1", "h2", "h3"):
            self.parts.append(" ")
    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def extract_episode(html):
    parser = PageText()
    parser.feed(html)
    text = "".join(parser.parts)
    start = text.find(START)
    if start < 0:
        raise ValueError("episode start marker not found")
    end = text.find(END, start)
    if end < 0:
        raise ValueError("episode end marker not found")
    candidate = text[start:end + len(END)]
    if len(candidate) < 1000:
        raise ValueError("candidate transcript too short")
    return candidate


def fetch_episode(url=URL):
    if url != URL:
        raise ValueError("source URL not allowlisted")
    with urlopen(Request(url, headers={"User-Agent": "Mozilla/5.0 Nexus-read-only-source-check"}), timeout=20) as response:
        if response.status != 200:
            raise ValueError("public source fetch failed")
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError("page exceeds size limit")
        encoding = response.headers.get_content_charset() or "utf-8"
    return extract_episode(raw.decode(encoding))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--notion-raw-file", required=True, type=Path)
    ap.add_argument("--candidate-file", type=Path, help="Use exact saved candidate instead of public fetch")
    ap.add_argument("--candidate-provenance", help="Required when supplying a candidate file; identify its real source")
    ap.add_argument("--report", required=True, type=Path)
    args = ap.parse_args()
    if args.candidate_file and not args.candidate_provenance:
        ap.error("--candidate-provenance is required with --candidate-file")
    if not args.candidate_file and args.candidate_provenance:
        ap.error("--candidate-provenance only applies to --candidate-file")
    original = args.notion_raw_file.read_bytes().decode("utf-8")
    candidate = (args.candidate_file.read_bytes().decode("utf-8")
                 if args.candidate_file else fetch_episode())
    result = compare_transcripts(
        original=original, candidate=candidate,
        original_provenance="notion:4088c067-daa4-813b-b1f0-e1f1993120fb",
        candidate_provenance=(args.candidate_provenance if args.candidate_file
                              else "podcastrex:warfronts-haiti-2026"))
    report = dict(result.__dict__)
    report["candidate_source"] = str(args.candidate_file) if args.candidate_file else URL
    report["warning"] = "HTML extraction is not verbatim audio proof; human review required."
    args.report.write_bytes((json.dumps(report, indent=2) + "\n").encode("utf-8"))
    print("Read-only report written:", args.report)


if __name__ == "__main__":
    main()
