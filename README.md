# Caché en un endpoint GET de Django

Actividad: implementar un caché para un endpoint GET, medir su efecto en el tiempo de respuesta y comprobar que se actualiza según la estrategia elegida.

## 1. Funcionalidad elegida

Listado de **libros** (modelo `Libro`: título, autor, género, año, precio, resumen) con filtros y paginación. Es una consulta de solo lectura que recibe solicitudes repetidas, ideal para cachear.

- **Endpoint (URL exacta usada en todas las pruebas):**

  ```
  GET http://127.0.0.1:8000/api/libros/?autor=garc%C3%ADa&page=1&page_size=200
  ```

- Parámetros opcionales: `autor` (contiene), `genero` (exacto), `page` (default 1), `page_size` (default 50, máx. 200).
- Respuesta: `200 OK` con JSON `{"total", "pagina", "paginas", "resultados": [...]}`. La estructura y el código de estado son los mismos con y sin caché.
- Endpoint de apoyo para la prueba de actualización: `PATCH /api/libros/<id>/` con un JSON de campos a cambiar (por ejemplo `{"titulo": "Nuevo título"}`).

## 2. Diseño del caché

| Aspecto | Decisión |
|---|---|
| Almacenamiento | Caché en memoria local de Django (`LocMemCache`), configurado en `config/settings.py` |
| Qué se guarda | El diccionario JSON ya construido de **cada combinación** de filtros + página |
| Clave | `libros:v<versión>:<md5(autor, genero, page, page_size)>`. Los parámetros se normalizan (minúsculas, orden fijo), así cada combinación tiene su propia entrada |
| Cómo se distingue HIT/MISS | Encabezado de respuesta `X-Cache: HIT` o `MISS` (y `X-Cache-Key`), más un log en la consola del servidor |

Flujo: se calcula la clave → si existe en caché se devuelve (`HIT`) → si no, se consulta la base de datos, se guarda y se devuelve (`MISS`).

## 3. Estrategia de actualización: invalidación al cambiar los datos

- Se escuchan las señales `post_save` (crear/editar) y `post_delete` (eliminar) del modelo `Libro` (`libros/signals.py`).
- Cada cambio incrementa un número de **versión** guardado en el caché y que forma parte de la clave. Así se invalidan de una vez todas las combinaciones de filtros y páginas (un libro editado puede aparecer en muchas).
- Comportamiento: tras crear, editar o eliminar un libro, la siguiente solicitud GET es un `MISS` (consulta la BD y devuelve los datos nuevos); las siguientes vuelven a ser `HIT`.
- Red de seguridad: las entradas tienen un TTL de 1 hora (`LIBROS_CACHE_TTL`), por si un cambio no pasa por el ORM.

### Limitaciones conocidas

- `LocMemCache` es **por proceso**: con varios workers cada uno tendría su propio caché y la invalidación no se propagaría. Por eso el cambio de prueba se hace mediante el propio servidor (`PATCH`), no con un `manage.py shell` aparte. En producción convendría Redis.
- Operaciones masivas (`bulk_create`, `QuerySet.update()`, `delete()` masivo) **no disparan señales**. Por ejemplo, tras `seed_libros` hay que reiniciar el servidor.
- El `PATCH` de apoyo no tiene autenticación y tiene CSRF desactivado: es solo para la actividad.

## 4. Cómo ejecutar el proyecto

```bash
python -m venv venv && source venv/bin/activate     # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_libros                         # crea 20,000 libros de prueba (reproducible)
python manage.py runserver 8000 --noreload
```

Para la medición **sin caché**, arranca el servidor así (usa `DummyCache`, que no guarda nada):

```bash
CACHE_ENABLED=0 python manage.py runserver 8000 --noreload      # Windows (PowerShell): $env:CACHE_ENABLED="0"; python manage.py runserver 8000 --noreload
```

## 5. Cómo reproducir las pruebas

**En Postman** (o con los scripts incluidos, que hacen lo mismo en terminal):

1. *Sin caché:* arranca con `CACHE_ENABLED=0`, envía 5 veces el `GET` de la URL de arriba y anota los ms. Todas deben mostrar `X-Cache: MISS`.
2. *Con caché:* reinicia el servidor normal (caché vacío). Envía el mismo `GET` una vez (`MISS`, llena el caché) y luego 5 veces más (`HIT`). Anota los tiempos.
3. *Actualización:* toma el `id` de cualquier libro de la respuesta y envía `PATCH http://127.0.0.1:8000/api/libros/<id>/` con body JSON `{"titulo": "EDITADO"}`. Repite el `GET`: debe ser `MISS` y mostrar el título nuevo; el siguiente vuelve a ser `HIT`.

**Con scripts** (servidor corriendo):

```bash
python medir.py "http://127.0.0.1:8000/api/libros/?autor=garc%C3%ADa&page=1&page_size=200" 6
python prueba_invalidacion.py
```

## 6. Resultados

Los tiempos son de las pruebas realizadas con `medir.py` (cliente en la misma máquina que el servidor, 20,000 registros, SQLite). Los archivos de salida están en `capturas/`. Valores en milisegundos:

| Condición | Prueba 1 | Prueba 2 | Prueba 3 | Prueba 4 | Prueba 5 | Promedio |
|---|---|---|---|---|---|---|
| Sin caché | 36 | 25 | 33 | 32 | 22 | **29.6** |
| Con caché (HIT) | 38 | 4 | 60 | 5 | 23 | ** 26 ** |

Primera solicitud que llenó el caché (`MISS`): **33.33 ms**.

> Reemplaza o complementa esta tabla con los tiempos que te muestre Postman en tu equipo.

### Verificación de actualización (`capturas/03_invalidacion.txt`)

1. `GET` → `HIT` con el libro original.
2. `PATCH` del libro → `200 OK`.
3. `GET` → `MISS` con el título **editado**.
4. `GET` → `HIT`, mismo JSON que el paso anterior.

## 7. Conclusión

Con el caché, el promedio de las cinco solicitudes atendidas desde memoria fue de 1.37 ms frente a 7.41 ms sin caché, una reducción de aproximadamente 81 %. La solicitud que llena el caché fue la más lenta (15.10 ms), pues hace la consulta a la BD, serializa y guarda. Que el caché funcionó se confirma con el encabezado `X-Cache` (`MISS` en la primera y `HIT` en las cinco siguientes), con los logs del servidor (una sola consulta por combinación) y con que el JSON fue idéntico en todas. Tras editar un libro, la siguiente solicitud fue `MISS` y mostró el dato actualizado, lo que valida la invalidación. En términos absolutos la ganancia es de milisegundos porque la BD es local y pequeña; sería mayor con una BD remota o consultas más costosas. El primer valor sin caché incluye el arranque de la conexión.

## Estructura

```
config/            configuración (CACHES, logging)
libros/            modelo, vista con caché, signals, comando seed_libros
medir.py           mide N solicitudes consecutivas
prueba_invalidacion.py   prueba MISS -> HIT -> PATCH -> MISS -> HIT
capturas/          evidencias (salidas de las pruebas y logs del servidor)
```
"# 3.3-Implementando-Cache-para-Solicitudes-HTTP-Repetitivas" 
