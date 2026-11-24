"""Prueba del modo navegador contra una página simulada que carga resultados como el sitio real."""
import json, http.server, threading, os, tempfile, sys
os.environ["NO_PROXY"] = "127.0.0.1"
import monitor, home_monitor
PAGE = b"""<html><title>CeX</title><body style='height:5000px'><script>
fetch('/search.webuy.io/1/indexes/*/queries',{method:'POST'}).then(r=>r.json()).then(()=>{});
</script></body></html>"""
STATE = {"out": 1}
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self): self.send_response(200); self.send_header("Content-Type","text/html"); self.end_headers(); self.wfile.write(PAGE)
    def do_POST(self):
        hits = [{"objectID": "A1", "boxName": "Juego PS2", "sellPrice": 100, "outOfStock": STATE["out"], "ecomQuantityOnHand": 0 if STATE["out"] else 2}]
        self.send_response(200); self.send_header("Content-Type","application/json"); self.end_headers()
        self.wfile.write(json.dumps({"results": [{"hits": hits}]}).encode())
srv = http.server.HTTPServer(("127.0.0.1", 0), H); threading.Thread(target=srv.serve_forever, daemon=True).start()
sent = []; monitor.notify = lambda c, t, b, u=None: sent.append(b)
cfg = {"site_base": "x", "headless": True, "browser_executable": "/opt/pw-browsers/chromium", "max_scrolls": 6,
       "scroll_wait_ms": 300, "disable_store_lookups": True, "watch": [{"url": f"http://127.0.0.1:{srv.server_port}/"}]}
monitor.SEARCH = home_monitor.collect
db = monitor.open_db(os.path.join(tempfile.mkdtemp(), "s.db"))
assert monitor.check_once(cfg, db) == 0
STATE["out"] = 0
assert monitor.check_once(cfg, db) == 1, sent
print("OK", sent)
