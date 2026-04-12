from django.contrib import admin
from .models import *


# ==============================
# INLINE - ITENS DA FOLHA
# ==============================
class ItemFolhaInline(admin.TabularInline):
    model = ItemFolha
    extra = 1
    autocomplete_fields = ['evento']  # 🔥 profissional


# ==============================
# FOLHA DE PAGAMENTO
# ==============================
@admin.register(FolhaPagamento)
class FolhaPagamentoAdmin(admin.ModelAdmin):
    inlines = [ItemFolhaInline]

    list_display = (
        'funcionario',
        'mes',
        'ano',
        'salario_base',
        'salario_bruto',
        'salario_liquido'
    )

    list_filter = ('mes', 'ano')
    search_fields = ('funcionario__nome',)

    readonly_fields = (
        'salario_base',
        'salario_bruto',
        'total_proventos',
        'total_descontos',
        'inss',
        'fgts',
        'irrf',
        'salario_liquido'
    )

    fieldsets = (
        ('📌 Dados iniciais', {
            'fields': ('funcionario', 'mes', 'ano')
        }),

        # 👉 INLINE (itens) aparece automaticamente aqui

        ('💰 Cálculos automáticos', {
            'fields': (
                'salario_base',
                'salario_bruto',
                'total_proventos',
                'total_descontos',
                'inss',
                'fgts',
                'irrf',
                'salario_liquido'
            )
        }),
    )


# ==============================
# FUNCIONÁRIO
# ==============================
@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'cpf',
        'cargo',
        'salario_base',
        'data_admissao'
    )

    list_filter = ('cargo',)
    search_fields = ('nome', 'cpf')


# ==============================
# CARGO
# ==============================
@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'departamento')
    list_filter = ('departamento',)
    search_fields = ('nome',)


# ==============================
# DEPARTAMENTO
# ==============================
@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nome',)
    search_fields = ('nome',)


# ==============================
# EVENTO
# ==============================
@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = (
        'nome',
        'tipo',
        'percentual',
        'valor_fixo'
    )

    list_filter = ('tipo',)
    search_fields = ('nome',)


# ==============================
# ITEM DA FOLHA (OPCIONAL)
# ==============================
@admin.register(ItemFolha)
class ItemFolhaAdmin(admin.ModelAdmin):
    list_display = ('folha', 'evento', 'valor')
    search_fields = ('evento__nome',)
    list_filter = ('evento__tipo',)