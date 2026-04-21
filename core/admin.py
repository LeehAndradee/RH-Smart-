from django.contrib import admin
from .models import Departamento, Cargo, Funcionario, Evento, Falta, FolhaPagamento, ItemFolha

@admin.register(Funcionario)
class FuncionarioAdmin(admin.ModelAdmin):
    list_display = ('matricula', 'nome', 'cargo', 'data_admissao')
    search_fields = ('nome', 'cpf', 'matricula')
    list_filter = ('cargo__departamento', 'cargo')

class ItemFolhaInline(admin.TabularInline):
    model = ItemFolha
    extra = 1

@admin.register(FolhaPagamento)
class FolhaPagamentoAdmin(admin.ModelAdmin):
    list_display = ('funcionario', 'mes', 'ano', 'tipo', 'salario_liquido', 'fechada')
    list_filter = ('mes', 'ano', 'tipo', 'fechada')
    inlines = [ItemFolhaInline] # Permite adicionar eventos direto na folha
    readonly_fields = ('salario_base_Snapshot', 'inss', 'irrf', 'fgts', 'total_proventos', 'total_descontos', 'salario_liquido')

admin.site.register([Departamento, Cargo, Evento, Falta])