"""
Functional mode: does the page actually work when you use it?

  - Navigation: clicks each link on the page and checks where it lands.
  - Forms: submits each form empty (should be blocked or show an error),
           then filled with sample data (should give a response, not an error).
  - Buttons: clicks each stand-alone button and watches for JavaScript errors.
"""
from urllib.parse import urlparse

from playwright.sync_api import TimeoutError as PWTimeout

from .annotate import mark

SAMPLE = {"email": "qa.test@example.com", "number": "5", "tel": "03001234567", "url": "https://example.com",
          "password": "Test1234!", "date": "2026-01-15", "search": "test", "text": "Test", "": "Test"}

SUBMIT_JS = """
(i) => {
  const f = document.forms[i];
  const btn = f.querySelector('button[type=submit],input[type=submit],button:not([type])');
  if (btn) { btn.click(); return 'button'; }
  f.requestSubmit ? f.requestSubmit() : f.submit(); return 'script';
}
"""


class Session:
    """One page plus listeners that remember errors and the last navigation."""

    def __init__(self, browser):
        self.ctx = browser.new_context(viewport={"width": 1366, "height": 800}, ignore_https_errors=True)
        self.page = self.ctx.new_page()
        self.page.set_default_timeout(6000)
        self.errors, self.doc_status = [], None
        self.page.on("pageerror", lambda e: self.errors.append(str(e).splitlines()[0]))
        self.page.on("response", self._resp)

    def _resp(self, r):
        if r.request.resource_type == "document" and r.frame == self.page.main_frame:
            self.doc_status = r.status

    def open(self, url):
        self.errors.clear()
        self.page.goto(url, wait_until="load", timeout=30000)
        self.errors.clear()
        self.doc_status = None

    def settle(self):
        try:
            self.page.wait_for_load_state("load", timeout=6000)
        except PWTimeout:
            pass
        self.page.wait_for_timeout(700)

    def close(self):
        self.ctx.close()


def run_functional(browser, url, shot, add, max_links=10, max_forms=5, max_buttons=8):
    s = Session(browser)
    page = s.page
    try:
        s.open(url)
    except Exception as exc:
        add(status="fail", title="Page could not be opened", detail=str(exc).splitlines()[0][:200])
        s.close()
        return
    host = urlparse(url).netloc

    # ---------- navigation ----------
    links = page.evaluate("""() => [...document.querySelectorAll('a[href]')].map((a, i) => ({i, href: a.href,
        text: (a.innerText || a.getAttribute('aria-label') || '').trim().slice(0, 40),
        visible: a.getBoundingClientRect().width > 0}))""")
    seen, tested, broken = set(), 0, 0
    for link in links:
        href = link["href"].split("#")[0]
        p = urlparse(href)
        if not link["visible"] or p.scheme not in ("http", "https") or p.netloc != host or href in seen or href == url.split("#")[0]:
            continue
        if tested >= max_links:
            break
        seen.add(href)
        tested += 1
        name = f"“{link['text'] or href}”"
        try:
            s.open(url)
            page.locator("a[href]").nth(link["i"]).click()
            s.settle()
            if s.doc_status and s.doc_status >= 400:
                broken += 1
                code = s.doc_status
                s.open(url)
                page.evaluate("(i) => document.querySelectorAll('a[href]')[i].setAttribute('data-qc-mark','badlink')", link["i"])
                mark(page, "@badlink", "!")
                add(status="fail", title=f"Link {name} leads to an error page", detail=f"Clicking it opened {href} which returned HTTP {code}",
                    shot=shot(page, f"link{tested}"))
            elif s.errors:
                add(status="fail", title=f"Link {name} opens a page with JavaScript errors", items=list(s.errors))
            else:
                add(status="pass", title=f"Link {name} works", detail=f"Opens {urlparse(page.url).path or '/'}")
        except Exception as exc:
            add(status="warn", title=f"Couldn't click link {name}", detail=str(exc).splitlines()[0][:160])
    if not tested:
        add(status="pass", title="No same-site links to follow on this page")

    # ---------- forms ----------
    try:
        s.open(url)
        forms = page.evaluate("""() => [...document.forms].map((f, i) => ({i, id: f.id || f.getAttribute('name') || ('form ' + (i + 1)),
            fields: f.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]),select,textarea').length,
            visible: f.getBoundingClientRect().height > 0}))""")
    except Exception:
        forms = []
    for f in [f for f in forms if f["visible"]][:max_forms]:
        fname = f"Form “{f['id']}”"
        # a) empty submit
        try:
            s.open(url)
            before = page.inner_text("body")
            start_url = page.url
            page.evaluate(SUBMIT_JS, f["i"])
            s.settle()
            invalid = page.evaluate("(i) => document.forms[i] ? document.forms[i].querySelectorAll(':invalid').length : 0", f["i"]) \
                if page.url == start_url else 0
            if s.doc_status and s.doc_status >= 400:
                add(status="fail", title=f"{fname}: submitting it empty gives HTTP {s.doc_status}",
                    detail="The form sends users to an error page instead of asking them to fill it in")
            elif invalid:
                add(status="pass", title=f"{fname}: blocks empty submission", detail=f"{invalid} required field(s) flagged by the browser")
            elif page.url != start_url and f["fields"]:
                add(status="warn", title=f"{fname}: accepts an empty submission",
                    detail="It submitted with every field blank. Required fields should be validated.", items=list(s.errors))
            elif s.errors:
                add(status="fail", title=f"{fname}: JavaScript error when submitted empty", items=list(s.errors))
            elif page.inner_text("body") != before:
                add(status="pass", title=f"{fname}: shows a message when submitted empty")
            elif f["fields"]:
                add(status="warn", title=f"{fname}: nothing happens when submitted empty",
                    detail="No error message, no validation, no change on the page")
        except Exception as exc:
            add(status="warn", title=f"{fname}: couldn't submit it empty", detail=str(exc).splitlines()[0][:160])

        # b) filled submit
        try:
            s.open(url)
            filled = page.evaluate("""([i, sample]) => {
                const f = document.forms[i]; let n = 0;
                f.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]),select,textarea').forEach(el => {
                  const t = (el.type || '').toLowerCase();
                  if (el.disabled || el.readOnly) return;
                  if (t === 'checkbox' || t === 'radio') { el.checked = true; }
                  else if (el.tagName === 'SELECT') { if (el.options.length > 1) el.selectedIndex = 1; }
                  else if (el.tagName === 'TEXTAREA') { el.value = 'Automated test message from QuickCheck.'; }
                  else { el.value = sample[t] ?? sample['text']; }
                  el.dispatchEvent(new Event('input', {bubbles: true})); el.dispatchEvent(new Event('change', {bubbles: true}));
                  n++;
                });
                return n; }""", [f["i"], SAMPLE])
            page.evaluate("(i) => document.forms[i].setAttribute('data-qc-mark', 'form')", f["i"])
            mark(page, "@form", "!")
            before_shot = shot(page, f"form{f['i']}")
            page.evaluate("() => document.querySelectorAll('.qc-box').forEach(b => b.remove())")
            before = page.inner_text("body")
            start_url = page.url
            page.evaluate(SUBMIT_JS, f["i"])
            s.settle()
            navigated = page.url != start_url
            if s.errors and not navigated:
                add(status="fail", title=f"{fname}: JavaScript error after submitting", items=list(s.errors), shot=before_shot)
            elif s.doc_status and s.doc_status >= 400:
                add(status="fail", title=f"{fname}: submitting it gives HTTP {s.doc_status}",
                    detail=f"Filled {filled} field(s) with sample data and submitted. The server answered with an error.",
                    shot=before_shot)
            elif navigated and s.errors:
                add(status="fail", title=f"{fname}: lands on a page with JavaScript errors", items=list(s.errors), shot=before_shot)
            elif navigated or page.inner_text("body") != before:
                add(status="pass", title=f"{fname}: works when filled in",
                    detail=f"Filled {filled} field(s), submitted, and the site responded")
            else:
                add(status="warn", title=f"{fname}: no visible response after submitting",
                    detail="Users get no confirmation that anything happened", shot=before_shot)
        except Exception as exc:
            add(status="warn", title=f"{fname}: couldn't fill and submit it", detail=str(exc).splitlines()[0][:160])
    if not forms:
        add(status="pass", title="No forms on this page")

    # ---------- stand-alone buttons ----------
    try:
        s.open(url)
        buttons = page.evaluate("""() => [...document.querySelectorAll('button,[role=button],input[type=button]')]
            .map((b, i) => ({i, inForm: !!b.closest('form') && b.type !== 'button', text: (b.innerText || b.value || b.getAttribute('aria-label') || '').trim().slice(0, 30),
                             visible: b.getBoundingClientRect().width > 0}))""")
    except Exception:
        buttons = []
    for b in [b for b in buttons if b["visible"] and not b["inForm"]][:max_buttons]:
        label = f"Button “{b['text'] or 'unnamed'}”"
        try:
            s.open(url)
            page.locator("button,[role=button],input[type=button]").nth(b["i"]).click()
            s.settle()
            if s.errors:
                add(status="fail", title=f"{label} causes a JavaScript error", items=list(s.errors))
            elif s.doc_status and s.doc_status >= 400:
                add(status="fail", title=f"{label} leads to HTTP {s.doc_status}")
            else:
                add(status="pass", title=f"{label} clicks without errors")
        except Exception as exc:
            add(status="warn", title=f"Couldn't click {label}", detail=str(exc).splitlines()[0][:160])
    s.close()
