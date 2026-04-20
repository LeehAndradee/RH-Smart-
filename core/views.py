from django.shortcuts import render, redirect, get_object_or_404
from .models import Funcionario, Cargo, Departamento, FolhaPagamento
from django.contrib import messages
from django.db.models import Sum
from django.http import JsonResponse


# =========================
# DASHBOARD
# =========================
def dashboard_view(request):
    total_funcionarios = Funcionario.objects.count()
    folhas_fechadas = FolhaPagamento.objects.filter(fechada=True).count()
    folhas_pendentes = FolhaPagamento.objects.filter(fechada=False).count()

    total_pago = FolhaPagamento.objects.aggregate(
        total=Sum('salario_liquido')
    )['total'] or 0

    return render(request, 'core/dashboard.html', {
        'total_funcionarios': total_funcionarios,
        'folhas_fechadas': folhas_fechadas,
        'folhas_pendentes': folhas_pendentes,
        'total_pago': total_pago
    })


# =========================
# FUNCIONÁRIOS
# =========================
def funcionarios_view(request):
    funcionarios = Funcionario.objects.all()
    return render(request, 'core/funcionarios.html', {'funcionarios': funcionarios})


# 🔧 Função auxiliar (evita repetir código)
def tratar_campos_funcionario(request):
    salario = request.POST.get('salario')
    dependentes = request.POST.get('dependentes')

    return {
        'nome': request.POST.get('nome'),
        'cpf': request.POST.get('cpf'),
        'data_nascimento': request.POST.get('data_nascimento') or None,
        'dependentes': int(dependentes) if dependentes else 0,
        'escolaridade': request.POST.get('escolaridade') or None,
        'estado_civil': request.POST.get('estado_civil') or None,
        'salario_base': salario if salario else None,
        'data_admissao': request.POST.get('admissao'),
        'cargo_id': request.POST.get('cargo')
    }


def funcionario_create(request):
    if request.method == 'POST':
        dados = tratar_campos_funcionario(request)
        Funcionario.objects.create(**dados)
        return redirect('/funcionarios/')

    cargos = Cargo.objects.all()
    return render(request, 'core/form_funcionario.html', {'cargos': cargos})


def funcionario_update(request, id):
    funcionario = get_object_or_404(Funcionario, id=id)

    if request.method == 'POST':
        dados = tratar_campos_funcionario(request)

        for campo, valor in dados.items():
            setattr(funcionario, campo, valor)

        funcionario.save()
        return redirect('/funcionarios/')

    cargos = Cargo.objects.all()
    return render(request, 'core/form_funcionario.html', {
        'funcionario': funcionario,
        'cargos': cargos
    })


def funcionario_delete(request, id):
    funcionario = get_object_or_404(Funcionario, id=id)
    funcionario.delete()
    return redirect('/funcionarios/')


# =========================
# CARGOS
# =========================
def cargos_view(request):
    cargos = Cargo.objects.select_related('departamento').all()
    return render(request, 'core/cargos.html', {'cargos': cargos})


def cargo_create(request):
    if request.method == 'POST':
        carga = request.POST.get('carga')

        Cargo.objects.create(
            nome=request.POST.get('nome'),
            nivel=request.POST.get('nivel'),
            carga_horaria=int(carga) if carga else 40,
            departamento_id=request.POST.get('departamento')
        )
        return redirect('/cargos/')

    departamentos = Departamento.objects.all()
    return render(request, 'core/form_cargo.html', {'departamentos': departamentos})


def cargo_update(request, id):
    cargo = get_object_or_404(Cargo, id=id)

    if request.method == 'POST':
        carga = request.POST.get('carga')

        cargo.nome = request.POST.get('nome')
        cargo.nivel = request.POST.get('nivel')
        cargo.carga_horaria = int(carga) if carga else 40
        cargo.departamento_id = request.POST.get('departamento')
        cargo.save()

        return redirect('/cargos/')

    departamentos = Departamento.objects.all()
    return render(request, 'core/form_cargo.html', {
        'cargo': cargo,
        'departamentos': departamentos
    })


def cargo_delete(request, id):
    cargo = get_object_or_404(Cargo, id=id)
    cargo.delete()
    return redirect('/cargos/')


# =========================
# DEPARTAMENTOS
# =========================
def departamentos_view(request):
    departamentos = Departamento.objects.all()
    return render(request, 'core/departamentos.html', {'departamentos': departamentos})


def departamento_create(request):
    if request.method == 'POST':
        Departamento.objects.create(
            nome=request.POST.get('nome'),
            descricao=request.POST.get('descricao')
        )
        return redirect('/departamentos/')

    return render(request, 'core/form_departamento.html')


def departamento_update(request, id):
    departamento = get_object_or_404(Departamento, id=id)

    if request.method == 'POST':
        departamento.nome = request.POST.get('nome')
        departamento.descricao = request.POST.get('descricao')
        departamento.save()

        return redirect('/departamentos/')

    return render(request, 'core/form_departamento.html', {
        'departamento': departamento
    })


def departamento_delete(request, id):
    departamento = get_object_or_404(Departamento, id=id)
    departamento.delete()
    return redirect('/departamentos/')

def folha_view(request):
    folhas = FolhaPagamento.objects.select_related('funcionario').all()

    return render(request, 'core/folha.html', {
        'folhas': folhas
    })


def folha_create(request):
    funcionarios = Funcionario.objects.all()

    if request.method == 'POST':
        funcionario_id = request.POST.get('funcionario')
        mes = request.POST.get('mes')
        ano = request.POST.get('ano')
        tipo = request.POST.get('tipo')

        funcionario = Funcionario.objects.get(id=funcionario_id)

        salario = funcionario.salario_base

        # Regras simples (depois podemos melhorar)
        inss = salario * 0.10
        irrf = salario * 0.08
        fgts = salario * 0.08
        liquido = salario - inss - irrf

        Folha.objects.create(
            funcionario=funcionario,
            mes=mes,
            ano=ano,
            tipo=tipo,
            salario_base=salario,
            inss=inss,
            irrf=irrf,
            fgts=fgts,
            salario_liquido=liquido
        )

        return redirect('/folha/')

    # 👉 ESSE CARA AQUI QUE ESTAVA FALTANDO
    return render(request, 'core/form_folha.html', {
        'funcionarios': funcionarios
    })

def folha_update(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)

    if folha.fechada:
        return redirect('/folha/')  # não deixa editar

    if request.method == 'POST':
        descontos = float(request.POST.get('descontos') or 0)

        folha.descontos = descontos
        folha.salario_liquido = folha.salario_base - descontos
        folha.save()

        return redirect('/folha/')

    return render(request, 'core/form_folha.html', {'folha': folha})

def folha_detail(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)
    return render(request, 'core/folha_detail.html', {'folha': folha})

def folha_fechar(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)

    folha.fechada = True
    folha.save()

    return redirect('/folha/')


def folha_delete(request, id):
    if request.method == 'POST':
        folha = get_object_or_404(FolhaPagamento, id=id)

        if folha.fechada:
            messages.error(request, 'Não é possível excluir uma folha já fechada.')
        else:
            folha.delete()
            messages.success(request, 'Folha excluída com sucesso!')

    return redirect('/folha/')

def calcular_folha(tipo, salario):
    inss = 0
    irrf = 0
    fgts = 0
    liquido = 0

    if tipo == 'normal':
        inss = salario * 0.10
        irrf = salario * 0.08
        fgts = salario * 0.08
        liquido = salario - inss - irrf

    elif tipo == 'ferias':
        bruto = salario + (salario / 3)
        inss = bruto * 0.10
        irrf = bruto * 0.08
        fgts = bruto * 0.08
        liquido = bruto - inss - irrf

    elif tipo == 'decimo':
        bruto = salario
        inss = bruto * 0.10
        irrf = bruto * 0.08
        fgts = bruto * 0.08
        liquido = bruto - inss - irrf

    return {
        'inss': inss,
        'irrf': irrf,
        'fgts': fgts,
        'liquido': liquido
    }

def get_funcionario(request, id):
    func = Funcionario.objects.get(id=id)

    return JsonResponse({
        'salario': float(func.salario_base)
    })