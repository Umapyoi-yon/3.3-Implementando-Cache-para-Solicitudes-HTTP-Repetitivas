import random
from decimal import Decimal

from django.core.management.base import BaseCommand

from libros.models import Libro

AUTORES = ["Gabriel García Márquez", "Julio Cortázar", "Isabel Allende", "Jorge Luis Borges",
           "Octavio Paz", "Laura Esquivel", "Carlos Fuentes", "Elena Poniatowska",
           "Mario Vargas Llosa", "Rosario Castellanos", "Juan Rulfo", "Roberto Bolaño"]
GENEROS = ["Novela", "Cuento", "Poesía", "Ensayo", "Historia", "Ciencia ficción"]


class Command(BaseCommand):
    help = "Crea registros de prueba de libros (por defecto 20000)."

    def add_arguments(self, parser):
        parser.add_argument("--cantidad", type=int, default=20000)

    def handle(self, *args, **opts):
        random.seed(42)  # datos reproducibles
        Libro.objects.all().delete()
        libros = []
        for i in range(1, opts["cantidad"] + 1):
            libros.append(Libro(
                titulo=f"Libro de prueba {i}",
                autor=random.choice(AUTORES),
                genero=random.choice(GENEROS),
                anio=random.randint(1900, 2024),
                precio=Decimal(random.randint(5000, 60000)) / 100,
                resumen=("Texto de ejemplo para el libro %d. " % i) * 6,
            ))
        Libro.objects.bulk_create(libros, batch_size=2000)
        self.stdout.write(self.style.SUCCESS(f"{opts['cantidad']} libros creados."))
