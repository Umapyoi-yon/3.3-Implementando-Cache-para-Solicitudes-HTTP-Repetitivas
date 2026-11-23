"""Prueba de invalidación: MISS -> HIT -> PATCH -> MISS con datos nuevos -> HIT.

Uso: python prueba_invalidacion.py [ID_LIBRO]
     Si no se indica ID, se usa el primer libro de la respuesta.
"""
import json
import sys
import time
import urllib.request

BASE = "http://127.0.0.1:8000/api/libros/"
URL = BASE + "?autor=garc%C3%ADa&page=1&page_size=200"
ID = int(sys.argv[1]) if len(sys.argv) > 1 else None


def get():
    t = time.perf_counter()
    with urllib.request.urlopen(URL) as r:
        cuerpo = json.loads(r.read())
        return r.status, r.headers["X-Cache"], (time.perf_counter() - t) * 1000, cuerpo


def titulo(cuerpo):
    return next(l["titulo"] for l in cuerpo["resultados"] if l["id"] == ID)


def patch(datos):
    req = urllib.request.Request(f"{BASE}{ID}/", data=json.dumps(datos).encode(),
                                 method="PATCH", headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as r:
        return r.status, json.loads(r.read())


if ID is None:
    with urllib.request.urlopen(URL) as r:
        ID = json.loads(r.read())["resultados"][0]["id"]
nuevo = f"Libro de prueba {ID} (EDITADO {int(time.time())})"

s, c, ms, d1 = get(); print(f"1) GET  -> {s} X-Cache={c:4} {ms:6.2f} ms | titulo[{ID}] = {titulo(d1)!r}")
s, c, ms, d2 = get(); print(f"2) GET  -> {s} X-Cache={c:4} {ms:6.2f} ms | JSON idéntico al 1): {d1 == d2}")
s, r = patch({"titulo": nuevo});  print(f"3) PATCH -> {s} {r}")
s, c, ms, d3 = get(); print(f"4) GET  -> {s} X-Cache={c:4} {ms:6.2f} ms | titulo[{ID}] = {titulo(d3)!r}")
s, c, ms, d4 = get(); print(f"5) GET  -> {s} X-Cache={c:4} {ms:6.2f} ms | JSON idéntico al 4): {d3 == d4}")
assert titulo(d3) == nuevo, "el cambio NO se reflejó"
print("OK: tras el cambio, la nueva solicitud devolvió los datos actualizados.")
