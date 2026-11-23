import hashlib
import logging

from django.conf import settings
from django.core.cache import cache
from django.core.paginator import EmptyPage, Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_GET

from .models import Libro

logger = logging.getLogger(__name__)

# Se incrementa cada vez que cambia un Libro (ver signals.py). Forma parte de
# la clave de caché, de modo que subir la versión invalida TODAS las
# combinaciones de filtros/páginas a la vez.
VERSION_KEY = "libros:version"


def _version():
    version = cache.get(VERSION_KEY)
    if version is None:
        cache.set(VERSION_KEY, 1, None)  # None = sin expiración
        version = 1
    return version


def construir_clave(request):
    """Clave única por combinación de parámetros (autor, genero, page, page_size)."""
    params = {
        "autor": request.GET.get("autor", "").strip().lower(),
        "genero": request.GET.get("genero", "").strip().lower(),
        "page": request.GET.get("page", "1"),
        "page_size": request.GET.get("page_size", "50"),
    }
    # Orden fijo para que ?a=1&b=2 y ?b=2&a=1 produzcan la misma clave.
    raw = "|".join(f"{k}={params[k]}" for k in sorted(params))
    digest = hashlib.md5(raw.encode()).hexdigest()
    return f"libros:v{_version()}:{digest}"


def generar_respuesta(request):
    """Consulta la base de datos y construye el diccionario JSON."""
    qs = Libro.objects.all()
    autor = request.GET.get("autor", "").strip()
    genero = request.GET.get("genero", "").strip()
    if autor:
        qs = qs.filter(autor__icontains=autor)
    if genero:
        qs = qs.filter(genero__iexact=genero)

    try:
        page_size = max(1, min(int(request.GET.get("page_size", 50)), 200))
        page_num = int(request.GET.get("page", 1))
    except ValueError:
        page_size, page_num = 50, 1

    paginator = Paginator(qs, page_size)
    try:
        page = paginator.page(page_num)
    except EmptyPage:
        page = paginator.page(paginator.num_pages)

    resultados = [
        {
            "id": l.id,
            "titulo": l.titulo,
            "autor": l.autor,
            "genero": l.genero,
            "anio": l.anio,
            "precio": str(l.precio),
            "resumen": l.resumen,
        }
        for l in page.object_list
    ]
    return {
        "total": paginator.count,
        "pagina": page.number,
        "paginas": paginator.num_pages,
        "resultados": resultados,
    }


@require_GET
def listar_libros(request):
    clave = construir_clave(request)
    datos = cache.get(clave)

    if datos is not None:
        estado = "HIT"
    else:
        datos = generar_respuesta(request)
        cache.set(clave, datos, settings.LIBROS_CACHE_TTL)
        estado = "MISS"

    logger.info("GET /api/libros/ -> cache %s (clave=%s)", estado, clave)
    respuesta = JsonResponse(datos, json_dumps_params={"ensure_ascii": False})
    respuesta["X-Cache"] = estado
    respuesta["X-Cache-Key"] = clave
    return respuesta


# ---------------------------------------------------------------------------
# Endpoint de apoyo para la prueba de invalidación (editar un libro desde
# Postman). Solo para la actividad: sin autenticación y con CSRF desactivado.
# ---------------------------------------------------------------------------
import json  # noqa: E402

from django.http import Http404  # noqa: E402
from django.views.decorators.csrf import csrf_exempt  # noqa: E402
from django.views.decorators.http import require_http_methods  # noqa: E402


@csrf_exempt
@require_http_methods(["PATCH"])
def actualizar_libro(request, pk):
    try:
        libro = Libro.objects.get(pk=pk)
    except Libro.DoesNotExist:
        raise Http404("Libro no encontrado")
    try:
        cambios = json.loads(request.body or b"{}")
    except json.JSONDecodeError:
        return JsonResponse({"error": "JSON inválido"}, status=400)
    for campo in ("titulo", "autor", "genero", "anio", "precio", "resumen"):
        if campo in cambios:
            setattr(libro, campo, cambios[campo])
    libro.save()  # dispara post_save -> invalida el caché
    return JsonResponse({"id": libro.id, "titulo": libro.titulo, "precio": str(libro.precio)})
