from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from .models import Funcionario, Cargo, Departamento, FolhaPagamento, Evento, Falta
from django.contrib.auth.models import User

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


def funcionario_update(request, id):
    funcionario = get_object_or_404(Funcionario, id=id)
    return render(request, 'core/funcionario/form.html', {'funcionario': funcionario})

def funcionario_delete(request, id):
    funcionario = get_object_or_404(Funcionario, id=id)
    funcionario.delete()
    return redirect('funcionarios_view')


def funcionario_create(request):
    if request.method == 'POST':
        try:
            # --- DADOS DO FORM ---
            nome = request.POST.get('nome')
            cpf = request.POST.get('cpf')
            email = request.POST.get('email')
            telefone = request.POST.get('telefone')
            data_nascimento = request.POST.get('data_nascimento')
            data_admissao = request.POST.get('data_admissao')
            dependentes = request.POST.get('dependentes') or 0
            nome_mae = request.POST.get('nome_mae')
            nome_pai = request.POST.get('nome_pai')
            endereco = request.POST.get('endereco_completo')
            cargo_id = request.POST.get('cargo')
            salario_base = request.POST.get('salario_base') or 0

            # --- VALIDAÇÕES BÁSICAS ---
            if not nome or not cpf or not email:
                messages.error(request, "Preencha os campos obrigatórios.")
                return redirect('funcionario_create')

            # Remove formatação do CPF
            username = cpf.replace('.', '').replace('-', '')

            # Evita duplicidade de usuário
            if User.objects.filter(username=username).exists():
                messages.error(request, "Já existe um usuário com esse CPF.")
                return redirect('funcionario_create')

            # --- CRIA USUÁRIO ---
            novo_usuario = User.objects.create_user(
                username=username,
                email=email,
                password=username  # senha inicial = CPF
            )

            # --- CRIA FUNCIONÁRIO ---
            Funcionario.objects.create(
                user=novo_usuario,
                nome=nome,
                cpf=cpf,
                email=email,
                telefone=telefone,
                data_nascimento=data_nascimento,
                data_admissao=data_admissao,
                dependentes=dependentes,
                nome_mae=nome_mae,
                nome_pai=nome_pai,
                endereco_completo=endereco,
                cargo_id=cargo_id,
                salario_base=salario_base
            )

           
            return redirect('funcionarios_view')

        except Exception as e:
           
            return redirect('funcionario_create')

    # GET
    cargos = Cargo.objects.all().order_by('nome')
    return render(request, 'core/funcionario/form.html', {'cargos': cargos})

# --- CARGOS ---
def cargos_view(request):
    cargos = Cargo.objects.all()
    return render(request, 'core/cargo/list.html', {'cargos': cargos})

def cargo_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        nivel = request.POST.get('nivel')
        carga_horaria = request.POST.get('carga_horaria')
        departamento_id = request.POST.get('departamento')

        novo_cargo = Cargo(
            nome=nome,
            nivel=nivel,
            carga_horaria=carga_horaria,
            departamento_id=departamento_id,
        )
        novo_cargo.save()
        return redirect('cargos_view')
    
    departamentos = Departamento.objects.all()
    return render(request, 'core/cargo/form.html', {'departamentos': departamentos})

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
    if request.method == 'POST':
        nome = request.POST.get('nome')
        descricao = request.POST.get('descricao')
        parent_id = request.POST.get('parent_id')

        novo_depto = Departamento(
            nome=nome,
            descricao=descricao,
            parent_id=parent_id if parent_id else None # O Django aceita parent_id se o campo for 'parent'
        )
        novo_depto.save()
        
        return redirect('departamento_view') 
    
    departamentos = Departamento.objects.all()
    return render(request, 'core/departamento/form.html', {'departamentos': departamentos})

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
    if request.method == 'POST':
        # Aqui pegamos os dados que vêm do formulário (o 'name' de cada input)
        funcionario_id = request.POST.get('funcionario')
        data = request.POST.get('data')
        motivo = request.POST.get('motivo')
        atestado = request.FILES.get('atestado') # Arquivos usamos request.FILES
        justificada = request.POST.get('justificada') == 'on'

        # Criamos o registro no banco
        funcionario = Funcionario.objects.get(id=funcionario_id)
        Falta.objects.create(
            funcionario=funcionario,
            data=data,
            motivo=motivo,
            atestado=atestado,
            justificada=justificada
        )
        return redirect('faltas_list')
    
    funcionarios = Funcionario.objects.all().order_by('nome')
    return render(request, 'core/falta/form.html', {'funcionarios': funcionarios})

# --- FOLHA DE PAGAMENTO ---
def folha_view(request):
    folhas = FolhaPagamento.objects.all().order_by('-ano', '-mes')
    return render(request, 'core/folha/list.html', {'folhas': folhas})

def folha_create(request):
    if request.method == 'POST':
        funcionario_id = request.POST.get('funcionario')
        mes = request.POST.get('mes')
        ano = request.POST.get('ano')
        tipo = request.POST.get('tipo')

        funcionario = get_object_or_404(Funcionario, id=funcionario_id)

        # Criamos o objeto na memória primeiro (sem .create)
        nova_folha = FolhaPagamento(
            funcionario=funcionario,
            mes=mes,
            ano=ano,
            tipo=tipo,
            fechada=False
        )
        
        # O .save() vai disparar o calcular_tudo que colocamos no model
        nova_folha.save() 
        
        return redirect('folha_detail', id=nova_folha.id)

    funcionarios = Funcionario.objects.all().order_by('nome')
    return render(request, 'core/folha/form.html', {'funcionarios': funcionarios})

def folha_detail(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)
    
    if not folha.fechada:
        folha.calcular_tudo()
        folha.save()
    
    return render(request, 'core/folha/detail.html', {'folha': folha})

def folha_update(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)
    return render(request, 'core/folha/form.html', {'folha': folha})

def folha_fechar(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)
    folha.fechada = True  # Altera o boolean
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
        'salario': str(funcionario.salario_base), # Corrigido de salario_base para salario
        'cargo': funcionario.cargo.nome if funcionario.cargo else "Sem Cargo"
    }
    return JsonResponse(data)

def departamento_update(request, id):
    depto = get_object_or_404(Departamento, id=id)
    
    if request.method == 'POST':
        depto.nome = request.POST.get('nome')
        depto.descricao = request.POST.get('descricao')
        parent_id = request.POST.get('parent_id')
        depto.parent_id = parent_id if parent_id else None
        
        depto.save()
        return redirect('departamento_view')

    departamentos = Departamento.objects.exclude(id=id) # Evita que um depto seja pai de si mesmo
    return render(request, 'core/departamento/form.html', {
        'depto': depto, 
        'departamentos': departamentos
    })

def departamento_delete(request, id):
    depto = get_object_or_404(Departamento, id=id)
    depto.delete()
    return redirect('departamento_view')