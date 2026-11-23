"""Mide el tiempo de respuesta de N solicitudes GET consecutivas (equivalente a Postman).

Uso:
    python medir.py [URL] [N]
"""
import statistics
import sys
import time
import urllib.request

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000/api/libros/?page=1&page_size=50"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 5

tiempos = []
print(f"URL: {URL}")
for i in range(1, N + 1):
    inicio = time.perf_counter()
    with urllib.request.urlopen(URL) as r:
        cuerpo = r.read()
        estado = r.status
        x_cache = r.headers.get("X-Cache")
    ms = (time.perf_counter() - inicio) * 1000
    tiempos.append(ms)
    print(f"Solicitud {i}: HTTP {estado} | X-Cache: {x_cache} | {ms:8.2f} ms | {len(cuerpo)} bytes")
print(f"Promedio de {N}: {statistics.mean(tiempos):.2f} ms")
