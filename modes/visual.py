"""
UI mode: how the page looks and whether it is usable.
Every problem element is tagged, boxed in red and numbered on the screenshot.
"""
from playwright.sync_api import TimeoutError as PWTimeout

from .annotate import mark

FIND_JS = """
() => {
  const tag = (els, name) => { els.forEach(e => e.setAttribute('data-qc-mark', name)); return els; };
  const visible = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
                         return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none'; };
  const desc = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (e.getAttribute('name') ? '[name=' + e.getAttribute('name') + ']' : '')
                   + (e.getAttribute('src') ? ' ' + e.getAttribute('src').slice(0, 70) : '');
  const out = {};
  out.brokenImg = tag([...document.images].filter(i => i.getAttribute('src') && i.complete && i.naturalWidth === 0), 'brokenImg').map(desc);
  out.noAlt = tag([...document.images].filter(i => !i.hasAttribute('alt') && visible(i)), 'noAlt').map(desc);
  out.unlabeled = tag([...document.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]),select,textarea')]
      .filter(el => visible(el) && !((el.id && document.querySelector('label[for="' + CSS.escape(el.id) + '"]')) || el.closest('label')
        || el.getAttribute('aria-label') || el.getAttribute('aria-labelledby'))), 'unlabeled').map(desc);
  out.empty = tag([...document.querySelectorAll('button,a[href],[role=button]')]
      .filter(e => visible(e) && !(e.innerText || e.getAttribute('aria-label') || e.getAttribute('title') || '').trim()
                   && !e.querySelector('img[alt]:not([alt=""]),svg[aria-label]')), 'empty').map(desc);
  const small = [];
  document.querySelectorAll('body *').forEach(e => {
    if (!visible(e) || small.length > 30) return;
    const own = [...e.childNodes].some(n => n.nodeType === 3 && n.textContent.trim().length > 2);
    if (own && parseFloat(getComputedStyle(e).fontSize) < 12) small.push(e);
  });
  out.smallText = tag(small, 'smallText').map(e => desc(e) + ' "' + e.innerText.trim().slice(0, 40) + '"');
  out.title = document.title.trim();
  out.h1 = document.querySelectorAll('h1').length;
  return out;
}
"""

MOBILE_JS = """
() => {
  const vw = document.documentElement.clientWidth;
  const visible = e => { const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const wide = [...document.querySelectorAll('body *')].filter(e => e.getBoundingClientRect().right > vw + 2);
  // keep only the outermost overflowing elements
  const top = wide.filter(e => !wide.includes(e.parentElement));
  top.forEach(e => e.setAttribute('data-qc-mark', 'wide'));
  // inline text links are allowed to be small; buttons, fields and block links are not
  const tiny = [...document.querySelectorAll('a[href],button,input:not([type=hidden]):not([type=checkbox]):not([type=radio]),select,[role=button]')]
     .filter(e => { if (!visible(e)) return false;
                    if (e.tagName === 'A' && getComputedStyle(e).display === 'inline') return false;
                    const r = e.getBoundingClientRect(); return r.height < 20 || r.width < 20; });
  tiny.forEach(e => e.setAttribute('data-qc-mark', 'tiny'));
  const d = e => e.tagName.toLowerCase() + (e.id ? '#' + e.id : '') + (typeof e.className === 'string' && e.className.trim() ? '.' + e.className.trim().split(/\\s+/)[0] : '');
  return {extra: document.documentElement.scrollWidth - vw, wide: top.slice(0, 10).map(d),
          tiny: tiny.slice(0, 15).map(e => d(e) + ' "' + (e.innerText || e.value || '').trim().slice(0, 25) + '"')};
}
"""


def run_ui(browser, url, shot, add):
    """shot(page, name) saves a screenshot and returns its file name; add(**item) records a result."""
    ctx = browser.new_context(viewport={"width": 1366, "height": 800}, ignore_https_errors=True)
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e).splitlines()[0]))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    try:
        resp = page.goto(url, wait_until="load", timeout=30000)
    except Exception as exc:
        add(status="fail", title="Page could not be opened", detail=str(exc).splitlines()[0][:200])
        ctx.close()
        return
    try:
        page.wait_for_load_state("networkidle", timeout=4000)
    except PWTimeout:
        pass
    code = resp.status if resp else 0
    if code >= 400:
        add(status="fail", title=f"Page returns HTTP {code}", detail="The page loaded an error instead of content")
        ctx.close()
        return
    found = page.evaluate(FIND_JS)

    n = 0
    rules = [
        ("brokenImg", "fail", "Broken images", "These images did not load"),
        ("empty", "fail", "Buttons or links with no text", "Users can't tell what these do"),
        ("unlabeled", "warn", "Form fields without labels", "Users and screen readers can't tell what to type"),
        ("noAlt", "warn", "Images without alt text", "Screen readers can't describe them"),
        ("smallText", "warn", "Text smaller than 12px", "Hard to read, especially on phones"),
    ]
    numbered = []
    for key, status, title, detail in rules:
        items = found[key]
        if items:
            n += 1
            numbered.append((key, str(n)))
            add(status=status, title=title, detail=detail, items=items, marker=str(n), view="desktop")
    if found["title"]:
        add(status="pass", title="Page has a title", detail=f"“{found['title']}”")
    else:
        add(status="fail", title="Page title is missing", detail="The browser tab will be blank")
    if found["h1"]:
        add(status="pass", title="Has a main heading")
    else:
        add(status="warn", title="No main heading (h1)")
    if errors:
        add(status="fail", title="Errors shown in the browser console", items=errors)
    else:
        add(status="pass", title="No console errors while loading")
    for key, _, title, _ in rules:
        if not found[key]:
            add(status="pass", title={"brokenImg": "All images load", "empty": "All buttons and links have text",
                                      "unlabeled": "All form fields are labelled", "noAlt": "All images have alt text",
                                      "smallText": "Text is a readable size"}[key])

    for key, label in numbered:
        mark(page, "@" + key, label)
    desktop_file = shot(page, "desktop")
    ctx.close()

    # phone
    mctx = browser.new_context(viewport={"width": 375, "height": 760}, is_mobile=True, has_touch=True, ignore_https_errors=True)
    m = mctx.new_page()
    try:
        m.goto(url, wait_until="load", timeout=30000)
        res = m.evaluate(MOBILE_JS)
        labels = []
        if res["extra"] > 20 or (res["extra"] > 2 and res["wide"]):
            n += 1
            labels.append(("wide", str(n)))
            add(status="fail", title="Doesn't fit a phone screen", view="phone", marker=str(n), items=res["wide"],
                detail=f"Content is {res['extra']}px wider than the 375px screen")
        else:
            add(status="pass", title="Fits a phone screen", view="phone")
        if res["tiny"]:
            n += 1
            labels.append(("tiny", str(n)))
            add(status="warn", title="Tap targets too small on phones", view="phone", marker=str(n), items=res["tiny"],
                detail="Buttons, fields or block links under 20px are hard to tap")
        else:
            add(status="pass", title="Tap targets are big enough", view="phone")
        for key, label in labels:
            mark(m, "@" + key, label)
        phone_file = shot(m, "phone")
    except Exception as exc:
        add(status="fail", title="Page failed on a phone screen", detail=str(exc).splitlines()[0][:200])
        phone_file = None
    mctx.close()
    return {"desktop": desktop_file, "phone": phone_file}
