"""Runs Functional, UI or Both on a link (and optionally the pages it links to)."""
import html
import json
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urldefrag, urlparse

from playwright.sync_api import sync_playwright

from .functional import run_functional
from .visual import run_ui


def discover(browser, url, limit):
    ctx = browser.new_context()
    page = ctx.new_page()
    try:
        page.goto(url, wait_until="load", timeout=30000)
        links = page.evaluate("() => [...document.querySelectorAll('a[href]')].map(a => a.href)")
    except Exception:
        links = []
    ctx.close()
    host, out = urlparse(url).netloc, [url]
    for l in links:
        l = urldefrag(l)[0]
        if urlparse(l).netloc == host and l.startswith("http") and l not in out:
            out.append(l)
    return out[:limit]


class Job:
    def __init__(self, url, mode, linked, max_pages, out_dir: Path):
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        self.url, self.mode, self.linked, self.max_pages = urldefrag(url)[0], mode, linked, max_pages
        self.out = out_dir
        self.out.mkdir(parents=True, exist_ok=True)
        self.state = {"id": out_dir.name, "url": self.url, "mode": mode, "status": "running", "step": "Opening browser",
                      "started": datetime.now().strftime("%d %b %Y, %H:%M"), "pages": [], "items": [], "error": None,
                      "done": 0, "total": 1}
        self._n = 0

    def save(self):
        (self.out / "result.json").write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def run(self):
        t0 = time.time()
        try:
            with sync_playwright() as pw:
                browser = pw.chromium.launch()
                pages = discover(browser, self.url, self.max_pages) if self.linked else [self.url]
                modes = ["functional", "ui"] if self.mode == "both" else [self.mode]
                self.state["total"] = len(pages) * len(modes)
                for pi, url in enumerate(pages):
                    rec = {"url": url, "path": urlparse(url).path or "/", "shots": {}}
                    self.state["pages"].append(rec)
                    for mode in modes:
                        self.state["step"] = f"{'Functional' if mode == 'functional' else 'UI'} tests on {rec['path']}"

                        def add(status, title, detail="", items=None, marker=None, view=None, shot=None, _m=mode, _u=url):
                            self.state["items"].append({"mode": _m, "page": _u, "status": status, "title": title,
                                                        "detail": detail, "items": (items or [])[:20], "marker": marker,
                                                        "view": view, "shot": shot})

                        def shot(page, name, _p=pi, _m=mode):
                            self._n += 1
                            fname = f"p{_p}_{_m}_{name}_{self._n}.png"
                            try:
                                page.screenshot(path=str(self.out / fname), full_page=True)
                                return fname
                            except Exception:
                                return None

                        if mode == "ui":
                            rec["shots"] = run_ui(browser, url, shot, add) or {}
                        else:
                            run_functional(browser, url, shot, add)
                        self.state["done"] += 1
                        self.save()
                browser.close()
            self.state["status"] = "done"
        except Exception as exc:
            self.state["status"], self.state["error"] = "error", f"{type(exc).__name__}: {exc}"
        self.state["seconds"] = round(time.time() - t0, 1)
        self.state["step"] = "Finished"
        self.state["summary"] = summary(self.state)
        self.save()
        (self.out / "report.html").write_text(report(self.state), encoding="utf-8")
        return self.state


def summary(st):
    out = {}
    for mode in ("functional", "ui"):
        its = [i for i in st["items"] if i["mode"] == mode]
        out[mode] = {k: sum(1 for i in its if i["status"] == k) for k in ("pass", "warn", "fail")}
    return out


def report(st):
    e = html.escape
    parts = []
    for mode, label in (("functional", "Functional tests"), ("ui", "UI tests")):
        its = [i for i in st["items"] if i["mode"] == mode]
        if not its:
            continue
        for title, keep in (("What's wrong", ("fail", "warn")), ("What worked", ("pass",))):
            rows = [i for i in its if i["status"] in keep]
            if not rows:
                continue
            body = "".join(
                f"<tr class={i['status']}><td>{'Failed' if i['status'] == 'fail' else 'Warning' if i['status'] == 'warn' else 'Passed'}</td>"
                f"<td>{('<b class=m>' + e(i['marker']) + '</b> ') if i['marker'] else ''}<b>{e(i['title'])}</b>"
                f"<div class=u>{e(i['page'])}</div>{e(i['detail'])}"
                f"{'<ul>' + ''.join('<li>' + e(str(x)) + '</li>' for x in i['items']) + '</ul>' if i['items'] else ''}"
                f"{'<img src=' + chr(34) + e(i['shot']) + chr(34) + '>' if i['shot'] else ''}</td></tr>" for i in rows)
            parts.append(f"<h2>{label}: {title}</h2><table>{body}</table>")
    shots = "".join(f"<figure><img src='{e(f)}'><figcaption>{e(p['path'])} · {k}</figcaption></figure>"
                    for p in st["pages"] for k, f in p.get("shots", {}).items() if f)
    sm = st.get("summary", {})
    return f"""<!doctype html><html lang=en><head><meta charset=utf-8><title>QuickCheck report</title><style>
body{{font:14px/1.5 system-ui;margin:0 auto;max-width:1100px;padding:30px;color:#1B2330}}
table{{border-collapse:collapse;width:100%}} td{{border-bottom:1px solid #dde2ea;padding:8px;vertical-align:top}}
tr.fail td:first-child{{color:#C62828;font-weight:700}} tr.warn td:first-child{{color:#A15C00;font-weight:700}} tr.pass td:first-child{{color:#2E7D32}}
.u{{color:#667;font:12px Consolas,monospace}} ul{{font:12px Consolas,monospace;margin:4px 0}} img{{max-width:420px;border:1px solid #ccd;margin-top:6px;display:block}}
.m{{background:#E5484D;color:#fff;border-radius:10px;padding:0 7px}} .g{{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:14px}}
figure{{margin:0}} figure img{{max-width:100%}}
</style></head><body><h1>QuickCheck: {e(st['mode'].title())} test report</h1>
<p class=u>{e(st['url'])} · {e(st['started'])} · {len(st['pages'])} page(s)</p>
<p>{' · '.join(f"{k.title()}: {v['pass']} passed, {v['warn']} warnings, {v['fail']} failed" for k, v in sm.items() if sum(v.values()))}</p>
{''.join(parts)}{'<h2>Annotated screenshots</h2><div class=g>' + shots + '</div>' if shots else ''}</body></html>"""
