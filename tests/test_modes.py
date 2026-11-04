"""
Runs the chosen mode once and turns every result into a pytest test.

    TEST_URL=https://your-site.com TEST_MODE=both LINKED=1 pytest --html=report.html --self-contained-html
TEST_MODE is functional, ui or both. Warnings are reported as xfail, failures fail.
"""
import os
from pathlib import Path

import pytest

from modes.runner import Job

URL = os.environ.get("TEST_URL", "http://localhost:8080/demo/")
MODE = os.environ.get("TEST_MODE", "both")
LINKED = os.environ.get("LINKED", "1") == "1"
OUT = Path(__file__).resolve().parent.parent / "results" / "pytest"

STATE = Job(URL, MODE, LINKED, int(os.environ.get("MAX_PAGES", 6)), OUT).run()


def test_run_completed():
    assert STATE["status"] == "done", STATE["error"]


@pytest.mark.parametrize("item", STATE["items"], ids=lambda i: f"{i['mode']}|{i['page'].split('//')[-1]}|{i['title']}")
def test_result(item):
    msg = f"{item['title']}: {item['detail']} {'; '.join(map(str, item['items']))}"
    if item["status"] == "fail":
        pytest.fail(msg)
    if item["status"] == "warn":
        pytest.xfail(msg)
