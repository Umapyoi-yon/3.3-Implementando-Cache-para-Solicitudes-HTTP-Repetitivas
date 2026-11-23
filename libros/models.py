from django.db import models


class Libro(models.Model):
    titulo = models.CharField(max_length=200)
    autor = models.CharField(max_length=120)
    genero = models.CharField(max_length=60)
    anio = models.PositiveIntegerField()
    precio = models.DecimalField(max_digits=8, decimal_places=2)
    resumen = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]

    def __str__(self):
        return f"{self.titulo} - {self.autor}"
