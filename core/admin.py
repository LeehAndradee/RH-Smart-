from django.contrib import admin
from .models import (
    Departamento,
    Cargo,
    Funcionario,
    Evento,
    FolhaPagamento,
    ItemFolha
)

# ==============================
# INLINE - ITENS DA FOLHA
# ==============================
class ItemFolhaInline(admin.TabularInline):
    model = ItemFolha
    extra = 1
    autocomplete_fields = ['evento']


# ==============================
# DEPARTAMENTO
# ==============================
@admin.register(Departamento)
class DepartamentoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'descricao', 'criado_em')
    search_fields = ('nome',)

    readonly_fields = ('criado_em', 'atualizado_em')

    fieldsets = (
        ('📌 Dados', {
            'fields': ('nome', 'descricao')
        }),
        ('🕒 Auditoria', {
            'fields': ('criado_em', 'atualizado_em')
        }),
    )


# ==============================
# CARGO
# ==============================
@admin.register(Cargo)
class CargoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'departamento', 'nivel', 'carga_horaria')
    list_filter = ('departamento', 'nivel')
    search_fields = ('nome',)

    readonly_fields = ('criado_em', 'atualizado_em')

    fieldsets = (
        ('📌 Dados', {
            'fields': ('nome', 'departamento', 'nivel', 'carga_horaria')
        }),
        ('🕒 Auditoria', {
            'fields': ('criado_em', 'atualizado_em')
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

    list_filter = ('cargo', 'estado_civil', 'escolaridade')
    search_fields = ('nome', 'cpf')

    readonly_fields = ('criado_em', 'atualizado_em')

    fieldsets = (
        ('📌 Dados pessoais', {
            'fields': (
                'nome',
                'cpf',
                'data_nascimento',
                'estado_civil',
                'dependentes',
                'escolaridade'
            )
        }),
        ('💼 Dados profissionais', {
            'fields': (
                'cargo',
                'salario_base',
                'data_admissao'
            )
        }),
        ('🕒 Auditoria', {
            'fields': ('criado_em', 'atualizado_em')
        }),
    )


# ==============================
# EVENTO
# ==============================
@admin.register(Evento)
class EventoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'percentual', 'valor_fixo')
    list_filter = ('tipo',)
    search_fields = ('nome',)


# ==============================
# FOLHA DE PAGAMENTO
# ==============================
@admin.register(FolhaPagamento)
class FolhaPagamentoAdmin(admin.ModelAdmin):
    inlines = [ItemFolhaInline]

    list_display = (
        'funcionario',
        'tipo',
        'mes',
        'ano',
        'salario_bruto',
        'salario_liquido',
        'fechada'
    )

    list_filter = ('tipo', 'mes', 'ano', 'fechada')
    search_fields = ('funcionario__nome',)

    readonly_fields = (
        'salario_base',
        'salario_bruto',
        'total_proventos',
        'total_descontos',
        'inss',
        'irrf',
        'fgts',
        'salario_liquido',
        'criado_em',
        'atualizado_em'
    )

    fieldsets = (
        ('📌 Dados', {
            'fields': ('funcionario', 'tipo', 'mes', 'ano', 'fechada')
        }),

        ('💰 Cálculos', {
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

        ('🕒 Auditoria', {
            'fields': ('criado_em', 'atualizado_em')
        }),
    )


# ==============================
# ITEM DA FOLHA (opcional)
# ==============================
@admin.register(ItemFolha)
class ItemFolhaAdmin(admin.ModelAdmin):
    list_display = ('folha', 'evento', 'valor')
    list_filter = ('evento__tipo',)
    search_fields = ('evento__nome',)