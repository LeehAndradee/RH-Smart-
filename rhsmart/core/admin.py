from django.contrib import admin
from .models import (
    Departamento,
    Cargo,
    Funcionario,
    Evento,
    ItemFolha,
    FolhaMensal,
    FolhaFerias,
    FolhaDecimoTerceiro
)

# ==============================
# INLINE - ITENS DA FOLHA
# ==============================
class ItemFolhaInline(admin.TabularInline):
    model = ItemFolha
    extra = 1
    autocomplete_fields = ['evento']


# ==============================
# BASE ADMIN (REUTILIZÁVEL)
# ==============================
class BaseFolhaAdmin(admin.ModelAdmin):
    inlines = [ItemFolhaInline]

    list_display = (
        'funcionario',
        'mes',
        'ano',
        'salario_base',
        'salario_liquido'
    )

    search_fields = ('funcionario__nome',)
    list_filter = ('mes', 'ano')

    readonly_fields = (
        'salario_base',
        'salario_bruto',
        'total_proventos',
        'total_descontos',
        'inss',
        'irrf',
        'fgts',
        'salario_liquido'
    )

    exclude = ('tipo',)  # 👈 não aparece no form

    fieldsets = (
        ('📌 Dados iniciais', {
            'fields': ('funcionario', 'mes', 'ano')
        }),
        ('💰 Cálculos automáticos', {
            'fields': (
                'salario_base',
                'salario_bruto',
                'total_proventos',
                'total_descontos',
                'inss',
                'irrf',
                'fgts',
                'salario_liquido'
            )
        }),
    )


# ==============================
# FOLHA MENSAL
# ==============================
@admin.register(FolhaMensal)
class FolhaMensalAdmin(BaseFolhaAdmin):

    def get_queryset(self, request):
        return super().get_queryset(request).filter(tipo='MENSAL')

    def save_model(self, request, obj, form, change):
        obj.tipo = 'MENSAL'
        super().save_model(request, obj, form, change)


# ==============================
# FOLHA DE FÉRIAS
# ==============================
@admin.register(FolhaFerias)
class FolhaFeriasAdmin(BaseFolhaAdmin):

    def get_queryset(self, request):
        return super().get_queryset(request).filter(tipo='FERIAS')

    def save_model(self, request, obj, form, change):
        obj.tipo = 'FERIAS'
        super().save_model(request, obj, form, change)


# ==============================
# FOLHA DE 13º
# ==============================
@admin.register(FolhaDecimoTerceiro)
class FolhaDecimoTerceiroAdmin(BaseFolhaAdmin):

    def get_queryset(self, request):
        return super().get_queryset(request).filter(tipo='DECIMO')

    def save_model(self, request, obj, form, change):
        obj.tipo = 'DECIMO'
        super().save_model(request, obj, form, change)


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