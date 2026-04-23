from django.urls import path
from . import views

urlpatterns = [
    # --- DEPARTAMENTOS ---
    path('departamentos/', views.departamentos_view, name='departamento_view'),
    path('departamentos/novo/', views.departamento_create, name='departamento_create'),
    path('departamentos/editar/<int:id>/', views.departamento_update, name='departamento_update'),
    path('departamentos/excluir/<int:id>/', views.departamento_delete, name='departamento_delete'),

    # --- FUNCIONÁRIOS ---
    path('funcionarios/', views.funcionarios_view, name='funcionarios_view'),
    path('funcionarios/novo/', views.funcionario_create, name='funcionario_create'),
    path('funcionarios/editar/<int:id>/', views.funcionario_update, name='funcionario_update'),
    path('funcionarios/excluir/<int:id>/', views.funcionario_delete, name='funcionario_delete'),

    # --- CARGOS ---
    path('cargos/', views.cargos_view, name='cargos_view'),
    path('cargos/novo/', views.cargo_create, name='cargo_create'),
    path('cargos/editar/<int:id>/', views.cargo_update, name='cargo_update'),
    path('cargos/excluir/<int:id>/', views.cargo_delete, name='cargo_delete'),

    # --- FOLHA DE PAGAMENTO (Corrigido para evitar o erro 404) ---
    # Agora tanto /folha/ quanto /folhas/ funcionarão se você precisar
    path('folha/', views.folha_view, name='folha_view'), 
    path('folha/nova/', views.folha_create, name='folha_create'),
    path('folha/<int:id>/', views.folha_detail, name='folha_detail'),
    path('folha/editar/<int:id>/', views.folha_update, name='folha_update'),
    path('folha/fechar/<int:id>/', views.folha_fechar, name='folha_fechar'),
    path('folha/excluir/<int:id>/', views.folha_delete, name='folha_delete'),

    # --- EVENTOS E FALTAS ---
    path('eventos/', views.eventos_view, name='eventos_list'),
    path('eventos/novo/', views.evento_create, name='evento_create'),
    path('eventos/editar/<int:id>/', views.evento_update, name='evento_update'),
    path('eventos/excluir/<int:id>/', views.evento_delete, name='evento_delete'),  
    path('faltas/', views.faltas_view, name='faltas_list'),
    path('faltas/nova/', views.cadastrar_falta, name='falta_create'),

    path('folha/<int:folha_id>/imprimir/', views.imprimir_holerite, name='imprimir_holerite'),
    
    # --- API ---
    path('api/funcionario/<int:id>/', views.get_funcionario, name='api_get_funcionario'),
]