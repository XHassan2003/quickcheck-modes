# QuickCheck Modes
**Variant by Hassan** · part of the QuickCheck automated testing project

Give it a link and pick what to test: **Functional**, **UI**, or **Both**.
A three-step wizard runs the tests in a real Chromium browser and shows the
results on separate Functional and UI tabs, each split into *What's wrong* and
*What worked*. Problems are boxed in red and numbered directly on the
screenshots.

## Run it

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate     macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
python app.py
```

Open http://localhost:8080. Different port: `$env:PORT=8765; python app.py`.

1. **Link**: paste a page, or click *Use the practice site*.
2. **What to test**: Functional, UI or Both. Tick *Also test pages this page links to* to cover up to 25 linked pages.
3. **Results**: switch between tabs, click any screenshot to enlarge, or open the full HTML report.

## Functional mode

| Test | How | Fails / warns when |
|---|---|---|
| Navigation | Clicks every same-site link (up to 10 per page) | Link leads to HTTP 4xx/5xx or a page with JavaScript errors |
| Forms, empty | Submits each form with nothing filled in | Server error (fail), accepted blank (warn), nothing happens (warn) |
| Forms, filled | Fills each field with sample data by type (email, number, phone, date…) and submits | Server error or JavaScript error (fail), no visible response (warn) |
| Buttons | Clicks each stand-alone button (up to 8) | JavaScript error or error page |

Failed form submissions include a screenshot with the form outlined.

## UI mode

| Check | Fails / warns when |
|---|---|
| Broken images | An image doesn't load (fail) |
| Empty buttons and links | No text or label (fail) |
| Title, h1 | Missing title (fail), missing h1 (warn) |
| Console errors | Any error while loading (fail) |
| Labels, alt text | Unlabelled fields, images without alt (warn) |
| Small text | Text below 12px (warn) |
| Phone layout | Wider than 375px (fail) |
| Tap targets | Buttons or fields under 20px on a phone (warn) |

Each numbered issue matches a red numbered box on the desktop or phone screenshot.

## Pytest / CI

```bash
python app.py                      # only needed for the practice site
pytest --html=reports/report.html --self-contained-html
TEST_URL=https://your-site.com TEST_MODE=functional pytest
```

Failures fail; warnings show as xfail. The GitHub Actions workflow runs on
every push and can be started by hand with a mode of your choice.

## Files

```
app.py                Flask server and API
modes/functional.py   Functional tests (links, forms, buttons)
modes/visual.py       UI checks and phone checks
modes/annotate.py     Draws numbered red boxes on screenshots
modes/runner.py       Picks pages, runs modes, writes report.html
ui/index.html         The three-step wizard
tests/test_modes.py   Pytest wrapper for CI
practice_site/        Practice website with deliberate bugs (served at /demo)
```
