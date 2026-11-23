from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import Libro
from .views import VERSION_KEY


def _invalidar():
    """Sube la versión: todas las claves anteriores dejan de usarse."""
    try:
        cache.incr(VERSION_KEY)
    except ValueError:
        cache.set(VERSION_KEY, 2, None)


@receiver(post_save, sender=Libro)
def libro_guardado(sender, **kwargs):
    # Cubre creación y edición
    _invalidar()


@receiver(post_delete, sender=Libro)
def libro_eliminado(sender, **kwargs):
    _invalidar()
