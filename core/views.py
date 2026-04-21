from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from .models import Funcionario, Cargo, Departamento, FolhaPagamento, Evento, Falta

# --- HELPER DE PERMISSÃO ---
def e_rh(user):
    return user.is_staff or user.groups.filter(name='RH').exists()

# --- DASHBOARD ---
# No core/views.py, dentro da dashboard_view:

@login_required
def dashboard_view(request):
    context = {
        'total_funcionarios': Funcionario.objects.count(),
        'total_departamentos': Departamento.objects.count(),
        # Trocamos status='ABERTO' por fechada=False
        'folhas_abertas': FolhaPagamento.objects.filter(fechada=False).count(),
    }
    return render(request, 'core/dashboard.html', context)

# --- FUNCIONÁRIOS ---
@login_required
def funcionarios_view(request):
    funcionarios = Funcionario.objects.all()
    return render(request, 'core/funcionario/list.html', {'funcionarios': funcionarios})

def funcionario_create(request):
    # Lógica de POST virá aqui com o FuncionarioForm
    return render(request, 'core/funcionario/form.html')

def funcionario_update(request, id):
    funcionario = get_object_or_404(Funcionario, id=id)
    return render(request, 'core/funcionario/form.html', {'funcionario': funcionario})

def funcionario_delete(request, id):
    funcionario = get_object_or_404(Funcionario, id=id)
    funcionario.delete()
    return redirect('funcionarios_view')

# --- CARGOS ---
def cargos_view(request):
    cargos = Cargo.objects.all()
    return render(request, 'core/cargo/list.html', {'cargos': cargos})

def cargo_create(request):
    return render(request, 'core/cargo/form.html')

def cargo_update(request, id):
    cargo = get_object_or_404(Cargo, id=id)
    return render(request, 'core/cargo/form.html', {'cargo': cargo})

def cargo_delete(request, id):
    get_object_or_404(Cargo, id=id).delete()
    return redirect('cargos_view')

# --- DEPARTAMENTOS ---
def departamentos_view(request):
    departamentos = Departamento.objects.all()
    return render(request, 'core/departamento/list.html', {'departamentos': departamentos})

def departamento_create(request):
    return render(request, 'core/departamento/form.html')

def departamento_update(request, id):
    departamento = get_object_or_404(Departamento, id=id)
    return render(request, 'core/departamento/form.html', {'departamento': departamento})

def departamento_delete(request, id):
    get_object_or_404(Departamento, id=id).delete()
    return redirect('departamentos_view')

# --- EVENTOS ---
def eventos_view(request):
    eventos = Evento.objects.all()
    return render(request, 'core/evento/list.html', {'eventos': eventos})

def evento_create(request):
    return render(request, 'core/evento/form.html')

# --- FALTAS ---
def faltas_view(request):
    faltas = Falta.objects.all()
    return render(request, 'core/falta/list.html', {'faltas': faltas})

def cadastrar_falta(request):
    return render(request, 'core/falta/form.html')

# --- FOLHA DE PAGAMENTO ---
def folha_view(request):
    folhas = FolhaPagamento.objects.all().order_by('-ano', '-mes')
    return render(request, 'core/folha/list.html', {'folhas': folhas})

def folha_create(request):
    return render(request, 'core/folha/form.html')

def folha_detail(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)
    return render(request, 'core/folha/detail.html', {'folha': folha})

def folha_update(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)
    return render(request, 'core/folha/form.html', {'folha': folha})

def folha_fechar(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)
    folha.status = 'FECHADO'
    folha.save()
    return redirect('folha_detail', id=id)

def folha_delete(request, id):
    get_object_or_404(FolhaPagamento, id=id).delete()
    return redirect('folha_view')

# --- API ---
def get_funcionario(request, id):
    funcionario = get_object_or_404(Funcionario, id=id)
    data = {
        'id': funcionario.id,
        'nome': funcionario.nome,
        'salario_base': str(funcionario.salario_base),
    }
    return JsonResponse(data)