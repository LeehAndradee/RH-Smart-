from django.urls import path
from .views import criar_folha

urlpatterns = [
    path('folha/', criar_folha, name='criar_folha'),
]