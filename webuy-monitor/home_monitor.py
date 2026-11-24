#!/usr/bin/env python3
"""Versión para correr en tu casa: abre la página de búsqueda con un navegador real
(como lo haría una persona) y lee los resultados que la propia página carga.
Uso:  python home_monitor.py            (vigila)
      python home_monitor.py --debug    (además guarda las respuestas crudas en ./debug)
"""
import json, os, sys, time
from playwright.sync_api import sync_playwright
import monitor

HERE = os.path.dirname(os.path.abspath(__file__))
DEBUG = "--debug" in sys.argv
_ctx = {}


def get_context(cfg):
    if "ctx" not in _ctx:
        pw = sync_playwright().start()
        kw = dict(user_data_dir=os.path.join(HERE, "browser-profile"),  # conserva cookies entre pasadas
                  headless=cfg.get("headless", False), locale="es-MX", viewport={"width": 1280, "height": 900})
        if cfg.get("browser_executable"):
            kw["executable_path"] = cfg["browser_executable"]
            kw["args"] = ["--no-sandbox"]
        if cfg.get("browser_channel"):
            kw["channel"] = cfg["browser_channel"]  # ej. "chrome" o "msedge"
        _ctx["pw"], _ctx["ctx"] = pw, pw.chromium.launch_persistent_context(**kw)
    return _ctx["ctx"]


def collect(cfg, w):
    """Abre la URL de la búsqueda, baja hasta el final y junta todos los productos."""
    url, marker = w["url"], cfg.get("api_url_contains", "search.webuy.io")
    hits, n_dump = {}, [0]

    def on_response(r):
        if marker not in r.url:
            return
        try:
            d = r.json()
        except Exception:
            return
        if DEBUG and n_dump[0] < 5:
            os.makedirs(os.path.join(HERE, "debug"), exist_ok=True)
            with open(os.path.join(HERE, "debug", f"resp{n_dump[0]}.json"), "w") as f:
                json.dump({"url": r.url, "body": d}, f, ensure_ascii=False, indent=1)
            n_dump[0] += 1
        for res in (d.get("results") if isinstance(d, dict) and "results" in d else [d]):
            for h in (res.get("hits") or []) if isinstance(res, dict) else []:
                k = h.get("boxId") or h.get("objectID")
                if k:
                    hits[k] = h

    page = get_context(cfg).new_page()
    page.on("response", on_response)
    try:
        page.goto(url, wait_until="networkidle", timeout=90000)
        title = page.title().lower()
        if "just a moment" in title or "un momento" in title or "attention required" in title:
            raise RuntimeError("Cloudflare pide verificación: resuélvela en la ventana del navegador")
        last, stable = -1, 0
        for _ in range(w.get("max_scrolls", cfg.get("max_scrolls", 200))):
            page.mouse.wheel(0, 25000)
            for b in page.get_by_role("button", name=__import__("re").compile(r"(ver|cargar|mostrar) m[aá]s|siguiente|next|load more", 2)).all():
                try: b.click(timeout=1000)
                except Exception: pass
            page.wait_for_timeout(cfg.get("scroll_wait_ms", 1500))
            stable = stable + 1 if len(hits) == last else 0
            last = len(hits)
            if stable >= 3:
                break
        if not hits:
            raise RuntimeError("No llegaron resultados de la búsqueda (revisa api_url_contains / usa --debug)")
        return list(hits.values())
    finally:
        page.close()


if __name__ == "__main__":
    monitor.SEARCH = collect
    sys.argv = [a for a in sys.argv if a != "--debug"]
    monitor.main()
