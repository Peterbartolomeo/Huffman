# Monitor de stock mx.webuy.com

Revisa cada minuto (de 00:00 a 08:00; cada 5 min el resto del día) tus juegos y te
manda una alerta **en cuanto pasan a disponible**, antes del correo oficial de las 7:30.
Si la página se cae (cargando stock), reintenta cada 30 s y alerta apenas regrese.

## Uso
1. `cp config.example.json config.json` y edita `watch` con tus juegos.
2. Alertas al celular (lo más fácil): instala la app **ntfy**, suscríbete a un tema
   secreto y ponlo en `ntfy_topic`. También soporta Telegram y correo SMTP.
3. `python3 monitor.py` (déjalo corriendo: PC encendida, Raspberry Pi o un VPS barato).
   `python3 monitor.py --once` hace una sola pasada. Pruebas: `python3 test_monitor.py`.

La primera pasada solo memoriza el estado actual (no alerta por lo que ya estaba).
Sin dependencias externas.

## En GitHub Actions (sin PC encendida)
Ya incluido en `.github/workflows/webuy-monitor.yml`. Edita `watch.json` con tus juegos y
agrega en *Settings → Secrets and variables → Actions* el secreto `NTFY_TOPIC`
(o `TELEGRAM_TOKEN` + `TELEGRAM_CHAT_ID`). Madrugada CDMX: revisa cada 30 s casi sin parar;
resto del día: cada hora. Gratis en repos públicos; en privados consume minutos del plan.

## Stock por tienda
Además del stock online, consulta la disponibilidad por tienda (la sección "disponibilidad
en tienda" del producto) y alerta cuando **sube** la cantidad en cualquiera
(ej. `tienda: Polanco: 0 → 3`). Opciones en el JSON: `only_stores` (lista de tiendas que te
interesan), `store_origins` (coordenadas lat/lon desde donde consultar), `max_store_lookups`.

## Alertas en el celular (ntfy, 2 minutos)
1. Instala la app **ntfy** (Android / iPhone) y permite notificaciones.
2. Toca "+" y suscríbete a un tema con nombre largo e impredecible, ej. `juegos-peter-7x9k2q41`.
   (Quien conozca el nombre puede leerlo: no uses algo obvio.)
3. Pon ese mismo nombre en el secreto `NTFY_TOPIC` de GitHub (o `ntfy_topic` en `config.json`).
4. Prueba: pestaña Actions → webuy-monitor → *Run workflow* con "test" activado,
   o local: `python3 monitor.py --test`. Debe sonar el celular.
Las alertas llegan con prioridad urgente y al tocarlas abren el producto.
