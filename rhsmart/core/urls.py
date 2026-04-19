from django.urls import path
from .views import (
    funcionarios_view,
    cargos_view,
    departamentos_view
)

urlpatterns = [
    path('funcionarios/', funcionarios_view),
    path('cargos/', cargos_view),
    path('departamentos/', departamentos_view),
]