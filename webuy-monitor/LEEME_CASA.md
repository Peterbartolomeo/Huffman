# Correrlo en tu PC (Windows)

## Instalación (una sola vez)
1. Instala **Python 3.11+** desde python.org (marca "Add Python to PATH").
2. Descarga el repo (GitHub → Code → Download ZIP) y descomprímelo. Abre la carpeta `webuy-monitor`.
3. En esa carpeta, escribe `cmd` en la barra de direcciones y pulsa Enter. Ejecuta:
   ```
   pip install -r requirements.txt
   playwright install chromium
   ```
4. Copia `config.home.example.json` como `config.json` y cambia `PON-AQUI-TU-TEMA-DE-NTFY`
   por el nombre de tu tema de ntfy (el mismo que ya te sonó en el celular).

## Primera prueba
```
python home_monitor.py --debug
```
Se abre una ventana de Chrome/Chromium y carga las búsquedas de PS2 y PS3. **No la cierres.**
- Si Cloudflare muestra una verificación ("Verifica que eres humano"), resuélvela a mano una vez.
- La primera pasada solo memoriza lo que hay (no manda alertas).
- Con `--debug` se guarda `debug/resp0.json`... Mándame ese archivo: sirve para confirmar los
  nombres de campo (precio, cantidad, agotado) antes de fiarte de las alertas.

## Uso diario
`python home_monitor.py` y deja la ventana abierta. Revisa cada 10 min.
- La PC debe estar encendida y **sin suspender** (Configuración → Energía → Suspender: nunca).
- Para que arranque sola: Win+R → `shell:startup` → pon ahí un acceso directo a `iniciar.bat`.

## Notas
- Sin consulta por tienda en este modo (solo stock online); falta ver en el navegador cómo
  muestra "disponibilidad en tienda" para añadirlo.
- Es acceso automatizado al sitio: manténlo a 10 min o más y úsalo solo para ti.
