"""Every ```json block in docs/ must actually parse.

Three separate instances of the same defect reached main before this existed,
all from the same cause: a long error string wrapped across lines to satisfy
markdownlint, which puts a raw newline inside a JSON string and makes the block
invalid. The rendered page looks fine. Only a reader who copies it finds out.

That matters more here than in most repos, because these blocks are the
documented output of a live API — a reader pastes them to check their own
response against ours.

Django-free and dependency-free, so it joins the fast CI gate.

    python3 -m unittest docs.developers.test_docs_json -v
"""
import json
import pathlib
import re
import unittest

DOCS = pathlib.Path(__file__).resolve().parents[1]
FENCE = re.compile(r"```json\n(.*?)```", re.S)


def _blocks():
    for path in sorted(DOCS.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for match in FENCE.finditer(text):
            line = text[: match.start()].count("\n") + 2
            yield path.relative_to(DOCS.parent), line, match.group(1)


class JsonBlocksParse(unittest.TestCase):
    def test_every_json_fence_is_valid_json(self):
        failures = []
        for path, line, body in _blocks():
            try:
                json.loads(body)
            except ValueError as exc:
                failures.append(f"{path}:{line} — {exc}")

        self.assertEqual(
            failures, [],
            "\n\nA ```json block does not parse. If it is meant to be "
            "abbreviated, fence it as ```text instead — `{...}` is not JSON. "
            "If it is real output, do not wrap long strings across lines; a "
            "raw newline inside a JSON string is invalid.\n\n"
            + "\n".join(failures),
        )

    def test_the_checker_finds_something_to_check(self):
        """A control: an empty sweep would pass the test above vacuously."""
        self.assertGreater(len(list(_blocks())), 0,
                           "no ```json blocks found — the regex or the path is wrong")


if __name__ == "__main__":
    unittest.main()
