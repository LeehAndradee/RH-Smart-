from django.urls import path
from . import views

urlpatterns = [
    # Funcionários
    path('funcionarios/', views.funcionarios_view),
    path('funcionarios/novo/', views.funcionario_create),
    path('funcionarios/editar/<int:id>/', views.funcionario_update),
    path('funcionarios/excluir/<int:id>/', views.funcionario_delete),

    # Cargos
    path('cargos/', views.cargos_view),
    path('cargos/novo/', views.cargo_create),
    path('cargos/editar/<int:id>/', views.cargo_update),
    path('cargos/excluir/<int:id>/', views.cargo_delete),

    # Departamentos
    path('departamentos/', views.departamentos_view),
    path('departamentos/novo/', views.departamento_create),
    path('departamentos/editar/<int:id>/', views.departamento_update),
    path('departamentos/excluir/<int:id>/', views.departamento_delete),

    path('folha/', views.folha_view, name='folha'),
    path('folha/nova/', views.folha_create, name='folha_create'),
    path('folha/<int:id>/', views.folha_detail, name='folha_detail'),
    path('folha/editar/<int:id>/', views.folha_update, name='folha_update'),
    path('folha/fechar/<int:id>/', views.folha_fechar, name='folha_fechar'),
    path('folha/excluir/<int:id>/', views.folha_delete, name='folha_delete'),
    path('folha/', views.folha_view),
    path('folha/nova/', views.folha_create),

    path('api/funcionario/<int:id>/', views.get_funcionario),
]