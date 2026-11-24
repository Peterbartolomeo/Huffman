import json, http.server, threading, tempfile, os, monitor

STATE = {"qty": 0, "pol": 0}
class H(http.server.BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        if "neareststores" in self.path:
            body = json.dumps({"response": {"data": {"stores": [
                {"storeName": "Polanco", "quantityOnHand": STATE["pol"]},
                {"storeName": "Reforma", "quantityOnHand": 1}]}}}).encode()
            self.send_response(200); self.end_headers(); self.wfile.write(body); return
        box = {"boxId": "SZEL001", "boxName": "Zelda TOTK Switch", "sellPrice": 899,
               "outOfStock": 0 if STATE["qty"] else 1, "ecomQuantityOnHand": STATE["qty"]}
        body = json.dumps({"response": {"data": {"boxes": [box], "totalRecords": 1}}}).encode()
        self.send_response(200); self.end_headers(); self.wfile.write(body)

srv = http.server.HTTPServer(("127.0.0.1", 0), H)
threading.Thread(target=srv.serve_forever, daemon=True).start()
sent = []
monitor.notify = lambda cfg, t, b, u=None: sent.append(t)
cfg = {"site_base": "https://x", "api_base": f"http://127.0.0.1:{srv.server_port}", "watch": ["zelda"]}
db = monitor.open_db(os.path.join(tempfile.mkdtemp(), "s.db"))

assert monitor.check_once(cfg, db) == 0 and not sent        # 1ª pasada: solo registra
STATE["qty"] = 2
assert monitor.check_once(cfg, db) == 1                     # agotado -> disponible: alerta
assert monitor.check_once(cfg, db) == 0                     # sigue disponible: sin repetir
STATE["qty"] = 0; monitor.check_once(cfg, db)
STATE["qty"] = 1
assert monitor.check_once(cfg, db) == 1                     # vuelve a stock: alerta
STATE["pol"] = 3
assert monitor.check_once(cfg, db) == 1                     # sube stock en tienda Polanco
assert monitor.check_once(cfg, db) == 0
STATE["pol"] = 2
assert monitor.check_once(cfg, db) == 0                     # bajar no alerta
print("OK", sent)
