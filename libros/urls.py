from django.urls import path

from . import views

urlpatterns = [
    path("libros/", views.listar_libros, name="listar_libros"),
    path("libros/<int:pk>/", views.actualizar_libro, name="actualizar_libro"),
]
