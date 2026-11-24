#!/usr/bin/env python3
"""Monitor de stock para mx.webuy.com (solo librería estándar de Python).

Detecta productos que pasan de "agotado" a "disponible" (o que aparecen nuevos)
y te avisa al instante por Telegram / ntfy / correo, sin esperar al correo oficial.
"""
import json, os, random, smtplib, sqlite3, sys, time, urllib.parse, urllib.request
from datetime import datetime
from email.message import EmailMessage

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("WEBUY_CONFIG", os.path.join(HERE, "config.json"))
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36"


def log(msg):
    print(f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}", flush=True)


# ---------- Consulta a la API ----------
def fetch_json(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def search(cfg, query, category_ids=None):
    """Devuelve la lista de productos (dicts) para un término de búsqueda."""
    out, first, page = [], 1, 50
    while True:
        params = {"q": query, "firstRecord": first, "count": page,
                  "sortBy": "prod_cat_name", "sortOrder": "desc"}
        if category_ids:
            params["categoryIds"] = ",".join(map(str, category_ids))
        data = fetch_json(cfg["api_base"] + "/v3/boxes?" + urllib.parse.urlencode(params))
        d = data.get("response", {}).get("data", {})
        boxes = d.get("boxes") or []
        out += boxes
        total = d.get("totalRecords", len(boxes))
        first += page
        if not boxes or first > total or first > cfg.get("max_results", 500):
            return out


def _first(d, keys, default=None):
    for k in keys:
        if d.get(k) is not None:
            return d[k]
    return default


def store_stock(cfg, box_id):
    """{nombre_tienda: cantidad} para un producto, combinando varios puntos de origen."""
    out = {}
    for lat, lon in cfg.get("store_origins", [[19.43, -99.13], [20.67, -103.35], [25.67, -100.31]]):
        url = f"{cfg['api_base']}/v3/boxes/{urllib.parse.quote(str(box_id))}/neareststores?" + \
              urllib.parse.urlencode({"latitude": lat, "longitude": lon})
        d = fetch_json(url).get("response", {}).get("data", {})
        for st in _first(d, ["stores", "nearestStores", "storeStock"], []) or []:
            name = _first(st, ["storeName", "name", "branchName"])
            qty = _first(st, ["quantityOnHand", "qtyOnHand", "quantity", "stock"], 0)
            if name:
                out[name] = int(qty or 0)
    only = cfg.get("only_stores")
    return {k: v for k, v in out.items() if not only or k in only}


def in_stock(b):
    if b.get("outOfStock") in (1, True) or b.get("outOfEcomStock") in (1, True):
        return False
    q = b.get("ecomQuantityOnHand")
    return q is None or q > 0


def product(b):
    return {"id": str(b["boxId"]), "name": b.get("boxName", "?"),
            "price": b.get("sellPrice"), "qty": b.get("ecomQuantityOnHand"),
            "in_stock": in_stock(b), "category": b.get("categoryFriendlyName", "")}


# ---------- Notificaciones ----------
def notify(cfg, title, body, url=None):
    n = cfg.get("notify", {})
    log(f"ALERTA: {title} | {body}")
    try:
        if n.get("ntfy_topic"):
            req = urllib.request.Request(
                f"{n.get('ntfy_server', 'https://ntfy.sh')}/{n['ntfy_topic']}",
                data=body.encode(), method="POST",
                headers={k: v for k, v in {
                    "Title": title.encode("latin-1", "ignore").decode("latin-1"),
                    "Priority": "urgent", "Tags": "video_game,rotating_light",
                    "Click": url}.items() if v})
            urllib.request.urlopen(req, timeout=15)
        if n.get("telegram_token") and n.get("telegram_chat_id"):
            data = urllib.parse.urlencode({"chat_id": n["telegram_chat_id"],
                                           "text": f"{title}\n{body}\n{url or ''}"}).encode()
            urllib.request.urlopen(
                f"https://api.telegram.org/bot{n['telegram_token']}/sendMessage", data, timeout=15)
        if n.get("smtp_host"):
            m = EmailMessage()
            m["Subject"], m["From"], m["To"] = title, n["smtp_user"], n["email_to"]
            m.set_content(f"{body}\n{url or ''}")
            with smtplib.SMTP_SSL(n["smtp_host"], n.get("smtp_port", 465)) as s:
                s.login(n["smtp_user"], n["smtp_password"])
                s.send_message(m)
    except Exception as e:  # una notificación fallida no debe tumbar el monitor
        log(f"Error enviando notificación: {e}")


# ---------- Estado ----------
def open_db(path):
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, name TEXT, price REAL, in_stock INT, updated TEXT)")
    db.execute("CREATE TABLE IF NOT EXISTS qty (id TEXT, k TEXT, qty INT, PRIMARY KEY(id,k))")
    return db


def check_once(cfg, db, first_run_silent=True):
    """Una pasada completa. Devuelve cuántas alertas se enviaron."""
    base = cfg["site_base"]
    alerts = 0
    prior_empty = db.execute("SELECT COUNT(*) FROM seen").fetchone()[0] == 0
    for w in cfg["watch"]:
        term = w if isinstance(w, str) else w["query"]
        cats = None if isinstance(w, str) else w.get("category_ids")
        max_price = None if isinstance(w, str) else w.get("max_price")
        for i, b in enumerate(search(cfg, term, cats)):
            p = product(b)
            row = db.execute("SELECT in_stock FROM seen WHERE id=?", (p["id"],)).fetchone()
            was = None if row is None else bool(row[0])
            silent = prior_empty and first_run_silent
            cur = {}
            if p["qty"] is not None:
                cur["online"] = int(p["qty"])
            if i < cfg.get("max_store_lookups", 20):
                try:
                    cur.update({f"tienda: {k}": v for k, v in store_stock(cfg, p["id"]).items()})
                except Exception as e:
                    log(f"Sin datos de tiendas para {p['id']}: {e}")
            lines = []
            for k, n in cur.items():
                r = db.execute("SELECT qty FROM qty WHERE id=? AND k=?", (p["id"], k)).fetchone()
                old = 0 if r is None else r[0]
                if n > old:
                    lines.append(f"{k}: {old} → {n}")
                db.execute("INSERT OR REPLACE INTO qty VALUES (?,?,?)", (p["id"], k, n))
            if not lines and p["in_stock"] and not was and "online" not in cur:
                lines.append("disponible")  # sin cantidades: usa solo el cambio de estado
            if lines and not silent and (max_price is None or (p["price"] or 0) <= max_price):
                notify(cfg, f"¡Más stock! {p['name']}",
                       f"${p['price']} MXN\n" + "\n".join(lines),
                       f"{base}/product-detail?id={p['id']}")
                alerts += 1
            db.execute("INSERT OR REPLACE INTO seen VALUES (?,?,?,?,?)",
                       (p["id"], p["name"], p["price"], int(p["in_stock"]), datetime.now().isoformat()))
        db.commit()
    return alerts


def interval(cfg):
    """Más frecuente en la ventana nocturna cuando suben el stock."""
    h = datetime.now().hour
    s, e = cfg.get("night_window", [0, 8])
    sec = cfg["night_interval_seconds"] if s <= h < e else cfg["day_interval_seconds"]
    return sec * random.uniform(0.85, 1.15)  # jitter para no ser un patrón rígido


def main():
    with open(CONFIG_PATH) as f:
        cfg = json.load(f)
    # Secretos de notificación desde variables de entorno (GitHub Secrets)
    env = {"ntfy_topic": "NTFY_TOPIC", "telegram_token": "TELEGRAM_TOKEN",
           "telegram_chat_id": "TELEGRAM_CHAT_ID"}
    for k, v in env.items():
        if os.environ.get(v):
            cfg.setdefault("notify", {})[k] = os.environ[v]
    if "--test" in sys.argv:
        notify(cfg, "Prueba del monitor", "Si ves esto en tu celular, las alertas funcionan.",
               cfg["site_base"])
        return
    db = open_db(os.environ.get("WEBUY_STATE", os.path.join(HERE, "state.db")))
    duration = int(sys.argv[sys.argv.index("--duration") + 1]) if "--duration" in sys.argv else 0
    deadline = time.time() + duration
    down_since = None
    log(f"Monitor iniciado. Vigilando: {cfg['watch']}")
    while True:
        try:
            n = check_once(cfg, db)
            if down_since:
                log(f"Sitio de vuelta tras {datetime.now() - down_since}. "
                    f"Alertas en esta pasada: {n}")
                down_since = None
            else:
                log(f"Pasada OK, alertas: {n}")
        except Exception as e:
            # Si la página cae (p. ej. cargando stock de madrugada) seguimos
            # reintentando con frecuencia: al volver es cuando hay que ser el primero.
            if down_since is None:
                down_since = datetime.now()
                log(f"Sitio no responde ({e}). Reintentando cada "
                    f"{cfg.get('retry_when_down_seconds', 30)}s — probable carga de stock.")
            if "--once" in sys.argv:
                sys.exit(1)
            if duration and time.time() >= deadline:
                return
            time.sleep(cfg.get("retry_when_down_seconds", 30))
            continue
        if "--once" in sys.argv or (duration and time.time() >= deadline):
            return
        time.sleep(interval(cfg))


if __name__ == "__main__":
    main()
