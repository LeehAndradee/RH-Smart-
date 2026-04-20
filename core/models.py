from django.db import models
from decimal import Decimal
from datetime import date
from django.core.exceptions import ValidationError
from django.utils.timezone import now
import re



# ==============================
# VALIDAÇÕES
# ==============================
def validar_cpf(cpf):
    cpf = re.sub(r'\D', '', cpf)

    if len(cpf) != 11 or cpf == cpf[0] * 11:
        raise ValidationError("CPF inválido")

    # Validação do CPF
    for i in range(9, 11):
        valor = sum((int(cpf[num]) * ((i+1) - num) for num in range(0, i)))
        digito = ((valor * 10) % 11) % 10
        if digito != int(cpf[i]):
            raise ValidationError("CPF inválido")


def validar_idade(data_nascimento):
    hoje = date.today()
    idade = hoje.year - data_nascimento.year - (
        (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
    )

    if idade < 16:
        raise ValidationError("Funcionário deve ter pelo menos 16 anos")


# ==============================
# DEPARTAMENTO
# ==============================
class Departamento(models.Model):
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome


# ==============================
# CARGO
# ==============================
class Cargo(models.Model):
    nome = models.CharField(max_length=100)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)
    nivel = models.CharField(max_length=50, blank=True)
    carga_horaria = models.IntegerField(default=40)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome


# ==============================
# FUNCIONÁRIO
# ==============================
class Funcionario(models.Model):
    nome = models.CharField(max_length=100)

    cpf = models.CharField(
        max_length=14,
        unique=True,
        validators=[validar_cpf]
    )

    data_nascimento = models.DateField(
        validators=[validar_idade],
        null=True,
        blank=True
    )

    dependentes = models.IntegerField(default=0)

    escolaridade = models.CharField(
        max_length=50,
        choices=[
            ('FUNDAMENTAL', 'Fundamental'),
            ('MEDIO', 'Médio'),
            ('SUPERIOR', 'Superior'),
            ('POS', 'Pós-graduação'),
        ],
        default='MEDIO'
    )

    estado_civil = models.CharField(
    max_length=20,
    choices=[
        ('SOLTEIRO', 'Solteiro'),
        ('CASADO', 'Casado'),
        ('DIVORCIADO', 'Divorciado'),
    ],
    default='SOLTEIRO'
)

    cargo = models.ForeignKey(Cargo, on_delete=models.CASCADE)

    salario_base = models.DecimalField(max_digits=10, decimal_places=2)

    data_admissao = models.DateField()

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome


# ==============================
# EVENTO
# ==============================
class Evento(models.Model):
    TIPOS = [
        ('PROVENTO', 'Provento'),
        ('DESCONTO', 'Desconto'),
    ]

    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=10, choices=TIPOS)

    percentual = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    valor_fixo = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    def __str__(self):
        return self.nome


# ==============================
# FOLHA DE PAGAMENTO
# ==============================
class FolhaPagamento(models.Model):


    

    TIPOS = [
        ('MENSAL', 'Mensal'),
        ('FERIAS', 'Férias'),
        ('DECIMO', '13º'),
        ('RESCISÃO', 'Rescisão'),
    ]

    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=10, choices=TIPOS)

    mes = models.IntegerField()
    ano = models.IntegerField()

    salario_base = models.DecimalField(max_digits=10, decimal_places=2)

    salario_bruto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_proventos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_descontos = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    inss = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    irrf = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fgts = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    eventos = models.ManyToManyField(Evento, blank=True)

    salario_liquido = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    criado_em = models.DateTimeField(auto_now_add=True)
    fechada = models.BooleanField(default=False)
    atualizado_em = models.DateTimeField(auto_now=True)



def clean(self):
    if self.mes < 1 or self.mes > 12:
        raise ValidationError("Mês inválido")

    if self.ano < 2000:
        raise ValidationError("Ano inválido")

    if self.fechado and self.pk:
        raise ValidationError("Folha já fechada não pode ser alterada")
    
    # ==============================
    # MESES TRABALHADOS
    # ==============================
    def meses_trabalhados(self):
        hoje = date(self.ano, self.mes, 1)
        admissao = self.funcionario.data_admissao

        meses = (hoje.year - admissao.year) * 12 + (hoje.month - admissao.month)
        return max(meses, 0)

    # ==============================
    # INSS
    # ==============================
    def calcular_inss(self, salario):
        faixas = [
            (Decimal('1412.00'), Decimal('0.075')),
            (Decimal('2666.68'), Decimal('0.09')),
            (Decimal('4000.03'), Decimal('0.12')),
            (Decimal('7786.02'), Decimal('0.14')),
        ]

        inss_total = Decimal('0')
        limite_anterior = Decimal('0')

        for limite, aliquota in faixas:
            if salario > limite:
                faixa = limite - limite_anterior
            else:
                faixa = salario - limite_anterior

            if faixa > 0:
                inss_total += faixa * aliquota

            limite_anterior = limite

            if salario <= limite:
                break

        return inss_total

    # ==============================
    # IRRF
    # ==============================
    def calcular_irrf(self, base):
        faixas = [
            (Decimal('2259.20'), Decimal('0'), Decimal('0')),
            (Decimal('2826.65'), Decimal('0.075'), Decimal('169.44')),
            (Decimal('3751.05'), Decimal('0.15'), Decimal('381.44')),
            (Decimal('4664.68'), Decimal('0.225'), Decimal('662.77')),
            (Decimal('999999.99'), Decimal('0.275'), Decimal('896.00')),
        ]

        for limite, aliquota, deducao in faixas:
            if base <= limite:
                return (base * aliquota) - deducao

        return Decimal('0')

    # ==============================
    # CÁLCULO PRINCIPAL
    # ==============================
def calcular_salario(self):
    self.salario_bruto = self.salario_base

    # =========================
    # REGRAS POR TIPO
    # =========================
    if self.tipo == 'FERIAS':
        self.salario_bruto += self.salario_base / Decimal('3')

    elif self.tipo == 'DECIMO':
        meses = self.meses_trabalhados()
        self.salario_bruto = (self.salario_base / 12) * meses

    elif self.tipo == 'RESCISAO':
        meses = self.meses_trabalhados()
        self.salario_bruto = (self.salario_base / 12) * meses

    # =========================
    # EVENTOS
    # =========================
    itens = self.itemfolha_set.all()

    proventos = Decimal('0')
    descontos = Decimal('0')

    for item in itens:
        if item.evento.tipo == 'PROVENTO':
            proventos += item.valor
        else:
            descontos += item.valor

    self.total_proventos = proventos
    self.total_descontos = descontos

    self.salario_bruto += proventos

    # =========================
    # IMPOSTOS
    # =========================
    self.inss = self.calcular_inss(self.salario_bruto)

    base_irrf = self.salario_bruto - self.inss - (self.funcionario.dependentes * Decimal('189.59'))
    self.irrf = max(self.calcular_irrf(base_irrf), Decimal('0'))

    self.fgts = self.salario_bruto * Decimal('0.08')

    # =========================
    # FINAL
    # =========================
    self.salario_liquido = (
        self.salario_bruto
        - self.inss
        - self.irrf
        - descontos
    )


def save(self, *args, **kwargs):
    if self.funcionario:
        self.salario_base = self.funcionario.salario_base

    self.full_clean()
    self.calcular_salario()

    super().save(*args, **kwargs)

# ==============================
# ITEM DA FOLHA
# ==============================
class ItemFolha(models.Model):
    folha = models.ForeignKey(FolhaPagamento, on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def calcular_valor(self):
        if self.evento.percentual:
            return self.folha.salario_base * (self.evento.percentual / Decimal('100'))
        elif self.evento.valor_fixo:
            return self.evento.valor_fixo
        return Decimal('0')

    def save(self, *args, **kwargs):
        self.valor = self.calcular_valor()
        super().save(*args, **kwargs)

        # Recalcula folha após salvar evento
        self.folha.calcular_salario()
        self.folha.save()

    def __str__(self):
        return f"{self.evento.nome} - {self.valor}"
    

    
