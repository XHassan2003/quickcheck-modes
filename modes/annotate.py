"""
Marks problem elements on the live page with a red outline and a numbered
badge, so the screenshot itself shows where each issue is.
"""

MARK_JS = """
([selector, label]) => {
  const els = selector.startsWith('@')
     ? [...document.querySelectorAll('[data-qc-mark="' + selector.slice(1) + '"]')]
     : [...document.querySelectorAll(selector)];
  if (!document.getElementById('qc-mark-style')) {
    const st = document.createElement('style');
    st.id = 'qc-mark-style';
    st.textContent = `.qc-box{position:absolute;border:3px solid #E5484D;border-radius:4px;pointer-events:none;z-index:2147483646;
       box-shadow:0 0 0 2px rgba(255,255,255,.8)}
     .qc-num{position:absolute;top:-14px;left:-14px;background:#E5484D;color:#fff;font:700 12px/24px system-ui;
       min-width:24px;height:24px;border-radius:12px;text-align:center;padding:0 6px;box-shadow:0 0 0 2px #fff}`;
    document.head.appendChild(st);
  }
  let n = 0;
  els.slice(0, 15).forEach(el => {
    const r = el.getBoundingClientRect();
    const w = Math.max(r.width, 18), h = Math.max(r.height, 18);
    const box = document.createElement('div');
    box.className = 'qc-box';
    box.style.cssText = `left:${r.left + scrollX - 3}px;top:${r.top + scrollY - 3}px;width:${w + 6}px;height:${h + 6}px`;
    const num = document.createElement('span');
    num.className = 'qc-num'; num.textContent = label;
    box.appendChild(num);
    document.body.appendChild(box);
    n++;
  });
  return n;
}
"""

def mark(page, selector: str, label: str) -> int:
    """selector is a CSS selector, or '@name' for elements tagged with data-qc-mark="name"."""
    try:
        return page.evaluate(MARK_JS, [selector, label])
    except Exception:
        return 0


def clear(page):
    try:
        page.evaluate("() => document.querySelectorAll('.qc-box').forEach(b => b.remove())")
    except Exception:
        pass
