from django.db import models
from decimal import Decimal
from datetime import date


# ==============================
# DEPARTAMENTO
# ==============================
class Departamento(models.Model):
    nome = models.CharField(max_length=100)

    def __str__(self):
        return self.nome


# ==============================
# CARGO
# ==============================
class Cargo(models.Model):
    nome = models.CharField(max_length=100)
    departamento = models.ForeignKey(Departamento, on_delete=models.CASCADE)

    def __str__(self):
        return self.nome


# ==============================
# FUNCIONÁRIO
# ==============================
class Funcionario(models.Model):
    nome = models.CharField(max_length=100)
    cpf = models.CharField(max_length=14)
    cargo = models.ForeignKey(Cargo, on_delete=models.CASCADE)
    salario_base = models.DecimalField(max_digits=10, decimal_places=2)
    data_admissao = models.DateField()

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

    TIPOS_FOLHA = [
        ('MENSAL', 'Mensal'),
        ('FERIAS', 'Férias'),
        ('DECIMO', '13º'),
    ]

    funcionario = models.ForeignKey(Funcionario, on_delete=models.CASCADE)
    mes = models.IntegerField()
    ano = models.IntegerField()

    tipo = models.CharField(max_length=10, choices=TIPOS_FOLHA, default='MENSAL')

    salario_base = models.DecimalField(max_digits=10, decimal_places=2)

    salario_bruto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_proventos = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_descontos = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    inss = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    irrf = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    fgts = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    salario_liquido = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # ==============================
    # INSS PROGRESSIVO
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
    # IRRF PROGRESSIVO
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
    # TEMPO DE EMPRESA (para 13º)
    # ==============================
    def meses_trabalhados(self):
        hoje = date(self.ano, self.mes, 1)
        admissao = self.funcionario.data_admissao

        meses = (hoje.year - admissao.year) * 12 + (hoje.month - admissao.month)
        return max(0, min(meses, 12))

    # ==============================
    # SOMA DOS ITENS
    # ==============================
    def calcular_totais(self):
        itens = self.itemfolha_set.all()

        proventos = Decimal('0')
        descontos = Decimal('0')

        for item in itens:
            if item.evento.tipo == 'PROVENTO':
                proventos += item.valor
            else:
                descontos += item.valor

        return proventos, descontos

    # ==============================
    # CÁLCULO COMPLETO
    # ==============================
    def calcular_salario(self):
        proventos, descontos = self.calcular_totais()

        self.total_proventos = proventos
        self.total_descontos = descontos

        self.salario_bruto = self.salario_base + proventos

        # ==================
        # FÉRIAS
        # ==================
        if self.tipo == 'FERIAS':
            adicional = self.salario_base / Decimal('3')
            self.salario_bruto += adicional

        # ==================
        # 13º PROPORCIONAL
        # ==================
        if self.tipo == 'DECIMO':
            meses = self.meses_trabalhados()
            self.salario_bruto = (self.salario_base / 12) * meses

        # ==================
        # INSS
        # ==================
        self.inss = self.calcular_inss(self.salario_bruto)

        # ==================
        # IRRF
        # ==================
        base_irrf = self.salario_bruto - self.inss
        self.irrf = max(self.calcular_irrf(base_irrf), Decimal('0'))

        # ==================
        # FGTS
        # ==================
        self.fgts = self.salario_bruto * Decimal('0.08')

        # ==================
        # SALÁRIO LÍQUIDO
        # ==================
        self.salario_liquido = (
            self.salario_bruto
            - self.inss
            - self.irrf
            - descontos
        )

    def save(self, *args, **kwargs):
        if self.funcionario:
            self.salario_base = self.funcionario.salario_base

        super().save(*args, **kwargs)

        self.calcular_salario()

        super().save(update_fields=[
            'salario_base',
            'salario_bruto',
            'total_proventos',
            'total_descontos',
            'inss',
            'irrf',
            'fgts',
            'salario_liquido'
        ])

    def __str__(self):
        return f"{self.funcionario} - {self.mes}/{self.ano} ({self.tipo})"


# ==============================
# ITEM DA FOLHA
# ==============================
class ItemFolha(models.Model):
    folha = models.ForeignKey(FolhaPagamento, on_delete=models.CASCADE)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        if self.evento.percentual:
            self.valor = self.folha.salario_base * (self.evento.percentual / 100)
        elif self.evento.valor_fixo:
            self.valor = self.evento.valor_fixo

        super().save(*args, **kwargs)

        # recalcula folha automaticamente
        self.folha.calcular_salario()
        self.folha.save()

    def __str__(self):
        return f"{self.evento} - {self.valor}"
    

# ==============================
# PROXY MODELS (TIPOS DE FOLHA)
# ==============================

class FolhaMensal(FolhaPagamento):
    class Meta:
        proxy = True
        verbose_name = "Folha Mensal"
        verbose_name_plural = "Folhas Mensais"


class FolhaFerias(FolhaPagamento):
    class Meta:
        proxy = True
        verbose_name = "Folha de Férias"
        verbose_name_plural = "Folhas de Férias"


class FolhaDecimoTerceiro(FolhaPagamento):
    class Meta:
        proxy = True
        verbose_name = "Folha de 13º"
        verbose_name_plural = "Folhas de 13º"