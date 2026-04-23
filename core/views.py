from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from .models import Funcionario, Cargo, Departamento, FolhaPagamento, Evento, Falta
from django.contrib.auth.models import User
from .models import Funcionario, Evento, FolhaPagamento, ItemFolha  # Adicione ItemFolha aqui
from django.contrib import messages

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
    # Busca o funcionário ou retorna 404 se não existir
    funcionario = get_object_or_404(Funcionario, id=id)
    
    if request.method == 'POST':
        # Se o usuário clicou em salvar, atualizamos o objeto
        funcionario.nome = request.POST.get('nome')
        funcionario.email = request.POST.get('email')
        funcionario.telefone = request.POST.get('telefone')
        funcionario.data_nascimento = request.POST.get('data_nascimento')
        funcionario.data_admissao = request.POST.get('data_admissao')
        funcionario.dependentes = request.POST.get('dependentes') or 0
        funcionario.endereco_completo = request.POST.get('endereco_completo')
        funcionario.cargo_id = request.POST.get('cargo')
        funcionario.salario_base = request.POST.get('salario_base') or 0
        
        funcionario.save()
        
        # Sincroniza o e-mail no User do sistema
        funcionario.user.email = funcionario.email
        funcionario.user.save()
        
        messages.success(request, "Dados atualizados com sucesso!")
        return redirect('funcionarios_view')

    # No GET, enviamos o funcionário e a lista de cargos para o template
    cargos = Cargo.objects.all().order_by('nome')
    return render(request, 'core/funcionario/form.html', {
        'funcionario': funcionario,
        'cargos': cargos
    })

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
    
    if request.method == 'POST':
        cargo.nome = request.POST.get('nome')
        cargo.nivel = request.POST.get('nivel') # Novo campo
        cargo.carga_horaria = request.POST.get('carga_horaria') # Novo campo
        cargo.departamento_id = request.POST.get('departamento')
        
        cargo.save()
        return redirect('cargos_view')

    departamentos = Departamento.objects.all().order_by('nome')
    return render(request, 'core/cargo/form.html', {
        'cargo': cargo, 
        'departamentos': departamentos
    })

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
    eventos = Evento.objects.all().order_by('nome')
    return render(request, 'core/evento/list.html', {'eventos': eventos})

def evento_create(request):
    if request.method == "POST":
        nome = request.POST.get('nome') 
        tipo = request.POST.get('tipo')
        # Pegando os nomes corretos do formulário
        valor = request.POST.get('valor_fixo') 
        percentual = request.POST.get('percentual')

        Evento.objects.create(
            nome=nome,
            tipo=tipo,
            # Correção: usando as variáveis tratadas
            valor_fixo=valor if valor else None, 
            percentual=percentual if percentual else None
        )
        return redirect('eventos_list')
    
    return render(request, 'core/evento/form.html')

def evento_update(request, id):
    evento = get_object_or_404(Evento, id=id)
    
    if request.method == "POST":
        evento.nome = request.POST.get('nome')
        evento.tipo = request.POST.get('tipo')
        
        percentual = request.POST.get('percentual')
        valor_fixo = request.POST.get('valor_fixo')
        
        # Tratamento para evitar erro de string vazia no banco
        evento.percentual = percentual if percentual else None
        evento.valor_fixo = valor_fixo if valor_fixo else None
        
        evento.save()
        return redirect('eventos_list')

    return render(request, 'core/evento/form.html', {'evento': evento})

def evento_delete(request, id):
    evento = get_object_or_404(Evento, id=id)
    evento.delete()
    return redirect('eventos_list')


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

        # 1. Criamos a folha base
        nova_folha = FolhaPagamento(
            funcionario=funcionario,
            mes=mes,
            ano=ano,
            tipo=tipo,
            fechada=False
        )
        nova_folha.save() # Dispara o cálculo inicial (Salário, INSS, etc)

        # 2. Capturamos os Eventos Extras que vieram da tabela dinâmica do HTML
        eventos_ids = request.POST.getlist('evento_id[]')
        eventos_valores = request.POST.getlist('evento_valor[]')

        for eid, valor in zip(eventos_ids, eventos_valores):
            if eid and valor: # Só salva se tiver ID e Valor
                ItemFolha.objects.create(
                    folha=nova_folha,
                    evento_id=eid,
                    valor=valor.replace(',', '.') # Garante ponto decimal
                )
        
        # 3. Recalcula após inserir os itens extras para atualizar o Líquido
        nova_folha.calcular_tudo()
        nova_folha.save()
        
        return redirect('folha_detail', id=nova_folha.id)

    # Precisamos enviar os funcionários e os eventos para o formulário
    context = {
        'funcionarios': Funcionario.objects.all().order_by('nome'),
        'eventos': Evento.objects.all().order_by('nome')
    }
    return render(request, 'core/folha/form.html', context)

def folha_detail(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)
    
    if not folha.fechada:
        folha.calcular_tudo()
        folha.save()
    
    return render(request, 'core/folha/detail.html', {'folha': folha})

def folha_update(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)

    if folha.fechada:
        from django.contrib import messages
        messages.error(request, "Folha já está fechada e não pode ser editada.")
        return redirect('folha_detail', id=id)

    if request.method == 'POST':
        folha.mes = int(request.POST.get('mes'))
        folha.ano = int(request.POST.get('ano'))
        folha.tipo = request.POST.get('tipo')
        # Aqui você também poderia atualizar os Itens da Folha se quiser
        folha.save()
        return redirect('folha_detail', id=folha.id)

    context = {
        'folha': folha,
        'funcionarios': Funcionario.objects.all().order_by('nome'),
        'eventos': Evento.objects.all().order_by('nome')
    }
    return render(request, 'core/folha/form.html', context)

def folha_fechar(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)
    folha.fechada = True  # Altera o boolean
    folha.save()
    return redirect('folha_detail', id=id)

def folha_delete(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)

    if folha.fechada:
        from django.contrib import messages
        messages.error(request, "Folha fechada não pode ser excluída.")
        return redirect('folha_detail', id=id)

    folha.delete()
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
    # Alterado de 'depto' para 'departamento' para bater com seu HTML
    departamento = get_object_or_404(Departamento, id=id)
    
    if request.method == 'POST':
        departamento.nome = request.POST.get('nome')
        departamento.descricao = request.POST.get('descricao')
        parent_id = request.POST.get('parent_id')
        departamento.parent_id = parent_id if parent_id else None
        
        departamento.save()
        return redirect('departamento_view')

    # Busca todos os departamentos exceto o atual
    departamentos = Departamento.objects.exclude(id=id) 
    return render(request, 'core/departamento/form.html', {
        'departamento': departamento, 
        'departamentos': departamentos
    })

def departamento_delete(request, id):
    depto = get_object_or_404(Departamento, id=id)
    depto.delete()
    return redirect('departamento_view')