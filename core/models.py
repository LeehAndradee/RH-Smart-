from django.db import models
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from decimal import Decimal
from datetime import date
import re

# --- VALIDAÇÕES ---
def validar_cpf(value):
    cpf = re.sub(r'\D', '', value)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValidationError("CPF inválido.")
    for i in range(9, 11):
        valor = sum((int(cpf[num]) * ((i+1) - num) for num in range(0, i)))
        digito = ((valor * 10) % 11) % 10
        if digito != int(cpf[i]):
            raise ValidationError("CPF inválido.")

# --- TABELAS ---
class Departamento(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)

    def __str__(self):
        return self.nome

class Cargo(models.Model):
    nome = models.CharField(max_length=100)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)
    nivel = models.CharField(max_length=50, help_text="Ex: Júnior, Pleno, Sênior")
    carga_horaria = models.IntegerField(default=44)
    salario_base = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.nome} ({self.nivel})"

class Funcionario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil')
    matricula = models.CharField(max_length=20, unique=True, editable=False)
    nome = models.CharField(max_length=150)
    cpf = models.CharField(max_length=14, unique=True, validators=[validar_cpf])
    email = models.EmailField()
    telefone = models.CharField(max_length=20)
    data_nascimento = models.DateField()
    data_admissao = models.DateField()
    dependentes = models.IntegerField(default=0)
    
    # Filiação e Endereço
    nome_mae = models.CharField(max_length=150)
    nome_pai = models.CharField(max_length=150, blank=True)
    endereco_completo = models.TextField()
    
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT)

    def save(self, *args, **kwargs):
        if not self.matricula:
            # Gera matrícula automática: Ano + ID sequencial
            ultimo = Funcionario.objects.last()
            id_prox = (ultimo.id + 1) if ultimo else 1
            self.matricula = f"{date.today().year}{id_prox:04d}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.matricula} - {self.nome}"

class Evento(models.Model):
    TIPOS = [('PROVENTO', 'Provento (+)'), ('DESCONTO', 'Desconto (-)')]
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    percentual = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    valor_fixo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return f"{self.nome} ({self.tipo})"

class Falta(models.Model):
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE)
    data = models.DateField()
    justificada = models.BooleanField(default=False)
    documento = models.FileField(upload_to='justificativas/', null=True, blank=True)
    observacao = models.TextField(blank=True)

    def __str__(self):
        status = "Justificada" if self.justificada else "Não Justificada"
        return f"Falta {self.funcionario.nome} - {self.data} ({status})"

class FolhaPagamento(models.Model):
    TIPOS = [
        ('MENSAL', 'Mensal'),
        ('FERIAS', 'Férias'),
        ('DECIMO', '13º Salário'),
        ('RESCISAO', 'Rescisão'),
    ]

    # Dados Históricos (Snapshot do momento da geração)
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE)
    mes = models.IntegerField()
    ano = models.IntegerField()
    tipo = models.CharField(max_length=10, choices=TIPOS, default='MENSAL')
    
    # Campos que trazem dados automáticos
    salario_base_Snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    inss = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    irrf = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fgts = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_proventos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_descontos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    salario_liquido = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    fechada = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('funcionario', 'mes', 'ano', 'tipo')

    def clean(self):
        if self.fechada and self.pk:
            raise ValidationError("Esta folha está fechada e não pode ser editada.")

    def calcular_tudo(self):
        # 1. Pega salário base do cargo no momento
        self.salario_base_Snapshot = self.funcionario.cargo.salario_base
        bruto = self.salario_base_Snapshot
        descontos_adicionais = Decimal('0')

        # 2. Regras Específicas de Férias/13º
        if self.tipo == 'FERIAS':
            bruto += (bruto / 3)
        
        # 3. Processa Faltas não justificadas
        faltas = Falta.objects.filter(
            funcionario=self.funcionario, 
            data__month=self.mes, 
            data__year=self.ano, 
            justificada=False
        ).count()
        if faltas > 0:
            valor_dia = self.salario_base_Snapshot / 30
            descontos_adicionais += (valor_dia * faltas)

        # 4. Processa Itens Extras (Eventos)
        for item in self.itens.all(): # 'itens' é o related_name de ItemFolha
            if item.evento.tipo == 'PROVENTO':
                bruto += item.valor
            else:
                descontos_adicionais += item.valor

        # 5. Cálculos Legais (INSS e IRRF simplificados para 2025/2026)
        self.inss = self.calc_inss(bruto)
        base_irrf = bruto - self.inss - (self.funcionario.dependentes * Decimal('189.59'))
        self.irrf = max(self.calc_irrf(base_irrf), Decimal('0'))
        self.fgts = bruto * Decimal('0.08')

        # 6. Totais
        self.total_proventos = bruto
        self.total_descontos = self.inss + self.irrf + descontos_adicionais
        self.salario_liquido = self.total_proventos - self.total_descontos

    def calc_inss(self, salario):
        # Tabela INSS 2026 (Estimada)
        if salario <= 1518.00: return salario * Decimal('0.075')
        if salario <= 2800.00: return (salario * Decimal('0.09')) - Decimal('22.77')
        return (salario * Decimal('0.14')) - Decimal('181.00') # Simplificado para o exemplo

    def calc_irrf(self, base):
        if base <= 2259.20: return Decimal('0')
        if base <= 2826.65: return (base * Decimal('0.075')) - Decimal('169.44')
        return (base * Decimal('0.275')) - Decimal('896.00')

    def save(self, *args, **kwargs):
        if not self.fechada:
            self.calcular_tudo()
        super().save(*args, **kwargs)

class ItemFolha(models.Model):
    folha = models.ForeignKey(FolhaPagamento, on_delete=models.CASCADE, related_name='itens')
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)