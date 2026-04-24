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
    parent = models.ForeignKey(
        'self', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='subdepartamentos'
    )

    def __str__(self):
        return self.nome

class Cargo(models.Model):
    nome = models.CharField(max_length=100)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)
    nivel = models.CharField(max_length=50, help_text="Ex: Júnior, Pleno, Sênior")
    carga_horaria = models.IntegerField(default=44)
   

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

    SEXO_CHOICES = (
    ('M', 'Masculino'),
    ('F', 'Feminino'),
    )

    sexo = models.CharField(max_length=1, choices=SEXO_CHOICES, blank=True, null=True)
    
    # Filiação e Endereço
    nome_mae = models.CharField(max_length=150)
    nome_pai = models.CharField(max_length=150, blank=True)
    endereco_completo = models.TextField()
    
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT)
     
    salario_base = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        null=True, 
        blank=True
    )
    
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

    aplica_13 = models.BooleanField(default=False)
    incide_inss = models.BooleanField(default=True)
    incide_irrf = models.BooleanField(default=True)
    incide_fgts = models.BooleanField(default=True)

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

from django.db import models
from django.core.exceptions import ValidationError
from decimal import Decimal

class FolhaPagamento(models.Model):
    TIPOS = [
        ('MENSAL', 'Mensal'),
        ('FERIAS', 'Férias'),
        ('DECIMO', '13º Salário'),
        ('RESCISAO', 'Rescisão'),
    ]

    PARCELAS_13O = [
        (1, '1ª Parcela'),
        (2, '2ª Parcela'),
        (0, 'Parcela Única'),
    ]

    # Dados de Identificação
    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE)
    mes = models.IntegerField()
    ano = models.IntegerField()
    tipo = models.CharField(max_length=10, choices=TIPOS, default='MENSAL')
    
    # Campos Condicionais (Novas Funcionalidades)
    dias_gozo_ferias = models.IntegerField(null=True, blank=True, default=30)
    data_rescisao = models.DateField(null=True, blank=True)
    parcela_13o = models.IntegerField(choices=PARCELAS_13O, null=True, blank=True)
    motivo_rescisao = models.CharField(max_length=50, null=True, blank=True)
    
    # Campos de Snapshot e Resultados
    salario_base_Snapshot = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    inss = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    irrf = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fgts = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_proventos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_descontos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    salario_liquido = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    salario_bruto = models.DecimalField(max_digits=10, decimal_places=2)

    valor_ferias_bruto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    terco_constitucional = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    saldo_salario_rescisao = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    fechada = models.BooleanField(default=False)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('funcionario', 'mes', 'ano', 'tipo')

    def clean(self):
        if self.fechada and self.pk:
            raise ValidationError("Esta folha está fechada e não pode ser editada.")

    def calcular_tudo(self):
        # 1. Pega salário base atual
        self.salario_base_Snapshot = self.funcionario.salario_base
        bruto = Decimal('0')
        descontos_legais_ativos = True # Define se calcula INSS/IRRF

        # 2. Lógica por Tipo de Folha
        if self.tipo == 'MENSAL':
            bruto = self.salario_base_Snapshot

        elif self.tipo == 'FERIAS':
            dias = Decimal(str(self.dias_gozo_ferias or 30))
            valor_ferias = (self.salario_base_Snapshot / 30) * dias
            bruto = valor_ferias + (valor_ferias / 3)
   
            self.valor_ferias_bruto = (self.salario_base_Snapshot / 30) * dias
            self.terco_constitucional = self.valor_ferias_bruto / 3
            bruto = self.valor_ferias_bruto + self.terco_constitucional

        elif self.tipo == 'DECIMO':
            if self.parcela_13o == 1:
                bruto = self.salario_base_Snapshot / 2
                descontos_legais_ativos = False

            elif self.parcela_13o == 2:
                bruto = self.salario_base_Snapshot  # usa o total

            else:
                bruto = self.salario_base_Snapshot

            if self.tipo == 'DECIMO' and self.parcela_13o == 2:
                self.salario_liquido -= (self.salario_base_Snapshot / 2)

        elif self.tipo == 'RESCISAO' and self.data_rescisao:
            dias_trabalhados = Decimal(str(self.data_rescisao.day))
            self.saldo_salario_rescisao = (self.salario_base_Snapshot / 30) * dias_trabalhados # <-- Adicione esta linha
            bruto = self.saldo_salario_rescisao

        # 3. Processa Itens Extras (Eventos/Adicionais)
        descontos_adicionais = Decimal('0')
        # Buscamos os itens relacionados (Related Name 'itens')
        if self.pk:
            for item in self.itens.all():
                if self.tipo == 'DECIMO' and not item.evento.aplica_13:
                    continue

                if item.evento.tipo == 'P':
                    bruto += item.valor
                else:
                    descontos_adicionais += item.valor

        # 4. Processa Faltas (Apenas para folha Mensal)
        if self.tipo == 'MENSAL':
            faltas = Falta.objects.filter(
                funcionario=self.funcionario, 
                data__month=self.mes, 
                data__year=self.ano, 
                justificada=False
            ).count()
            if faltas > 0:
                valor_dia = self.salario_base_Snapshot / 30
                descontos_adicionais += (valor_dia * Decimal(str(faltas)))

        self.salario_bruto = bruto

        # 5. Cálculos de Impostos
        if descontos_legais_ativos:
            self.inss = self.calc_inss(bruto)
            # Dedução por dependente: R$ 189,59
            dependentes_valor = Decimal(str(self.funcionario.dependentes)) * Decimal('189.59')
            base_irrf = bruto - self.inss - dependentes_valor
            self.irrf = max(self.calc_irrf(base_irrf), Decimal('0'))
        else:
            self.inss = Decimal('0')
            self.irrf = Decimal('0')

        if self.tipo == 'DECIMO' and self.parcela_13o == 1:
            self.fgts = Decimal('0')
        else:
            self.fgts = bruto * Decimal('0.08')

        # 6. Totais Finais
        self.total_proventos = bruto
        self.total_descontos = self.inss + self.irrf + descontos_adicionais
        self.salario_liquido = self.total_proventos - self.total_descontos


        # ✅ AJUSTE DA 2ª PARCELA DO 13º
        if self.tipo == 'DECIMO' and self.parcela_13o == 2:
            self.salario_liquido -= (self.salario_base_Snapshot / 2)

    def calc_inss(self, salario):
        if salario <= 1518.00: return salario * Decimal('0.075')
        if salario <= 2800.00: return (salario * Decimal('0.09')) - Decimal('22.77')
        return (salario * Decimal('0.14')) - Decimal('181.00')

    def calc_irrf(self, base):
        if base <= 2259.20: return Decimal('0')
        if base <= 2826.65: return (base * Decimal('0.075')) - Decimal('169.44')
        return (base * Decimal('0.275')) - Decimal('896.00')

    def save(self, *args, **kwargs):
        # 1. Se a folha é nova (ainda não tem ID), buscamos o salário AGORA
        if not self.pk:
            self.salario_base_Snapshot = self.funcionario.salario_base
            self.salario_bruto = self.funcionario.salario_base
        
        # 2. Salva a primeira vez (O banco agora aceita, pois o salário já está preenchido)
        super().save(*args, **kwargs)
        
        # 3. Agora que já salvou e tem ID, rodamos o cálculo completo 
        # (Para processar INSS, IRRF e itens extras que precisam do ID)
        if not self.fechada:
            self.calcular_tudo()
            # 4. Atualiza os valores finais calculados
            super().save(update_fields=[
                'salario_base_Snapshot', 'salario_bruto', 'inss', 'irrf', 
                'fgts', 'total_proventos', 'total_descontos', 'salario_liquido'
            ])

class ItemFolha(models.Model):
    folha = models.ForeignKey(FolhaPagamento, on_delete=models.CASCADE, related_name='itens')
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)