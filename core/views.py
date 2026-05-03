from decimal import Decimal
from datetime import datetime
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse
from .models import Funcionario, Cargo, Departamento, FolhaPagamento, Evento, Falta, ItemFolha
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum, Avg
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import user_passes_test
from django.core.mail import send_mail 
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO

def eh_master(user):
    # Checa se o usuário está logado e se o perfil dele é MASTER
    return user.is_authenticated and hasattr(user, 'perfil') and user.perfil.tipo_acesso == 'MASTER'


# --- DASHBOARD ---
def dashboard_view(request):
    perfil = request.user.perfil
    hoje = datetime.now()
    
    # --- LÓGICA DE COMPETÊNCIA ANTERIOR ---
    # Se estamos em Maio, a competência alvo é Abril.
    # Se estamos em Janeiro, a competência alvo é Dezembro do ano anterior.
    if hoje.month == 1:
        mes_ref = 12
        ano_ref = hoje.year - 1
    else:
        mes_ref = hoje.month - 1
        ano_ref = hoje.year

    # --- DASHBOARD PARA MASTER (RH/ADMIN) ---
    if perfil.tipo_acesso == 'MASTER':
        total_funcionarios = Funcionario.objects.count()
        total_cargos = Cargo.objects.count()
        total_departamentos = Departamento.objects.count()

        # Contador focado na competência do mês passado
        quant_folhas_mes = FolhaPagamento.objects.filter(
            mes=mes_ref, 
            ano=ano_ref
        ).count()

        ultimos_funcionarios = Funcionario.objects.order_by('-id')[:5]
        aniversariantes = Funcionario.objects.filter(data_nascimento__month=hoje.month)
        faltas = Falta.objects.select_related('funcionario').order_by('-data')[:5]

        context = {
            'total_funcionarios': total_funcionarios,
            'total_cargos': total_cargos,
            'total_departamentos': total_departamentos,
            'quant_folhas_mes': quant_folhas_mes,
            'mes_ref': mes_ref,
            'ano_ref': ano_ref,
            'ultimos_funcionarios': ultimos_funcionarios,
            'aniversariantes': aniversariantes,
            'faltas': faltas,
            'hoje': hoje,
        }
        return render(request, 'dashboard.html', context)

    # --- DASHBOARD PARA USUÁRIO (FUNCIONÁRIO) ---
    else:
        funcionario = get_object_or_404(Funcionario, user=request.user)
        minhas_faltas = Falta.objects.filter(funcionario=funcionario).order_by('-data')[:5]
        
        # O funcionário vê apenas seus holerites já liberados (status=True)
        meus_holerites = FolhaPagamento.objects.filter(
            funcionario=funcionario, 
            status=True 
        ).order_by('-ano', '-mes')[:3]

        context = {
            'funcionario': funcionario,
            'minhas_faltas': minhas_faltas,
            'meus_holerites': meus_holerites,
            'e_aniversariante': funcionario.data_nascimento.month == hoje.month
        }
        return render(request, 'dashboard.html', context)
    
# --- FUNCIONÁRIOS ---
@login_required
def funcionarios_view(request):
    # 1. Se for MASTER, ele vê a lista completa de funcionários
    if request.user.perfil.tipo_acesso == 'MASTER':
        funcionarios = Funcionario.objects.all()
        return render(request, 'core/funcionario/list.html', {'funcionarios': funcionarios})
    
    # 2. Se for USUARIO, ele não deve ver a lista, mas sim os PRÓPRIOS dados
    else:
        # Buscamos apenas o registro que pertence ao usuário logado
        funcionario_proprio = get_object_or_404(Funcionario, user=request.user)
        
        # Enviamos ele para a tela de formulário, mas com uma flag de bloqueio
        return render(request, 'core/funcionario/form.html', {
            'funcionario': funcionario_proprio,
            'cargos': Cargo.objects.all(),
            'somente_leitura': True # Flag para desabilitar campos no HTML
        })

@user_passes_test(eh_master, login_url='dashboard_view')
@login_required
def funcionario_update(request, id):
    funcionario = get_object_or_404(Funcionario, id=id)
    
    # --- LOGICA DE PERMISSÃO ---
    eh_admin = (request.user.perfil.tipo_acesso == 'MASTER')
    eh_dono = (funcionario.user == request.user)

    # Se não for Master e nem o dono do perfil, barra o acesso
    if not eh_admin and not eh_dono:
        messages.error(request, "Você não tem permissão para acessar este perfil.")
        return redirect('dashboard_view')

    if request.method == 'POST':
        # Bloqueio de segurança: mesmo que ele tente forçar o POST, só Master salva
        if not eh_admin:
            messages.error(request, "Apenas o RH pode alterar dados cadastrais.")
            return redirect('dashboard_view')

        # --- LÓGICA DE SALVAMENTO (SÓ MASTER CHEGA AQUI) ---
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
        
        # Sincroniza o e-mail no User
        funcionario.user.email = funcionario.email
        funcionario.user.save()
        
        messages.success(request, "Dados atualizados com sucesso!")
        return redirect('funcionarios_view')

    # --- GET (VISUALIZAÇÃO) ---
    cargos = Cargo.objects.all().order_by('nome')
    return render(request, 'core/funcionario/form.html', {
        'funcionario': funcionario,
        'cargos': cargos
    })

@user_passes_test(eh_master, login_url='dashboard')

@login_required
def funcionario_delete(request, id):
    # 1. Busca o funcionário ou dá erro 404 se não existir
    funcionario = get_object_or_404(Funcionario, id=id)
    
    # 2. Segurança: Apenas MASTER pode desativar alguém
    if request.user.perfil.tipo_acesso != 'MASTER':
        messages.error(request, "Você não tem permissão para realizar esta ação.")
        return redirect('dashboard')

    # 3. Só processa a "exclusão" se for um método POST (por segurança)
    if request.method == 'POST':
        # DESATIVAÇÃO DO FUNCIONÁRIO
        funcionario.ativo = False
        funcionario.save()

        # DESATIVAÇÃO DO LOGIN (Se ele tiver um usuário vinculado)
        if funcionario.user:
            user = funcionario.user
            user.is_active = False  # O usuário perde o acesso ao sistema na hora
            user.save()

        messages.success(request, f"O colaborador {funcionario.nome} foi desativado com sucesso!")
        return redirect('funcionarios_view')

    # Se alguém tentar acessar o link direto via GET, mandamos para uma página de confirmação
    return render(request, 'core/funcionario/confirm_delete.html', {'funcionario': funcionario})

@user_passes_test(eh_master, login_url='dashboard')
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
@user_passes_test(eh_master, login_url='dashboard_view')
def cargos_view(request):
    cargos = Cargo.objects.all()
    return render(request, 'core/cargo/list.html', {'cargos': cargos})

@user_passes_test(eh_master, login_url='dashboard')
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

@user_passes_test(eh_master, login_url='dashboard_view')
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


@user_passes_test(eh_master, login_url='dashboard')
def cargo_delete(request, id):
    get_object_or_404(Cargo, id=id).delete()
    return redirect('cargos_view')

# --- DEPARTAMENTOS ---
@user_passes_test(eh_master, login_url='dashboard_view')
def departamentos_view(request):
    departamentos = Departamento.objects.all()
    return render(request, 'core/departamento/list.html', {'departamentos': departamentos})


@user_passes_test(eh_master, login_url='dashboard')
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

@user_passes_test(eh_master, login_url='dashboard_view')
def departamento_update(request, id):
    departamento = get_object_or_404(Departamento, id=id)
    return render(request, 'core/departamento/form.html', {'departamento': departamento})


@user_passes_test(eh_master, login_url='dashboard')
def departamento_delete(request, id):
    get_object_or_404(Departamento, id=id).delete()
    return redirect('departamentos_view')


# --- EVENTOS ---
@user_passes_test(eh_master, login_url='dashboard_view')
def eventos_view(request):
    eventos = Evento.objects.all().order_by('nome')
    return render(request, 'core/evento/list.html', {'eventos': eventos})


@user_passes_test(eh_master, login_url='dashboard')
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

@user_passes_test(eh_master, login_url='dashboard_view')
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

@user_passes_test(eh_master, login_url='dashboard')
def evento_delete(request, id):
    evento = get_object_or_404(Evento, id=id)
    evento.delete()
    return redirect('eventos_list')


# --- FALTAS ---
@user_passes_test(eh_master, login_url='dashboard_view')
def faltas_view(request):
    faltas = Falta.objects.all()
    return render(request, 'core/falta/list.html', {'faltas': faltas})

@user_passes_test(eh_master, login_url='dashboard_view')
def cadastrar_falta(request):
    if request.method == 'POST':
        funcionario_id = request.POST.get('funcionario')
        data = request.POST.get('data')
        motivo = request.POST.get('motivo')
        atestado = request.FILES.get('atestado')
        justificada = request.POST.get('justificada') == 'on'
        
        # NOVOS CAMPOS QUE ESTAVAM FALTANDO NA VIEW:
        mes_referencia = request.POST.get('mes_referencia')
        ano_referencia = request.POST.get('ano_referencia')
        valor_desconto = request.POST.get('valor_desconto')

        funcionario = get_object_or_404(Funcionario, id=funcionario_id)

        # Atualizamos o .create() para incluir as novas variáveis
        Falta.objects.create(
            funcionario=funcionario,
            data=data,
            motivo=motivo,
            atestado=atestado,
            justificada=justificada,
            mes_referencia=int(mes_referencia) if mes_referencia else 0,
            ano_referencia=int(ano_referencia) if ano_referencia else 0,
            valor_desconto=valor_desconto.replace(',', '.') if valor_desconto else 0.00
        )

        return redirect('faltas_list')

    context = {
        'funcionarios': Funcionario.objects.all().order_by('nome'),
    }
    return render(request, 'core/falta/form.html', context)

@user_passes_test(eh_master, login_url='dashboard')
def excluir_falta(request, id):
    falta = get_object_or_404(Falta, id=id)
    
    # 🔍 Verificamos se já existe uma folha criada para este funcionário no mesmo mês/ano da falta
    folha_existe = FolhaPagamento.objects.filter(
        funcionario=falta.funcionario, 
        mes=falta.mes_referencia, 
        ano=falta.ano_referencia
    ).exists()

    if folha_existe:
        messages.error(request, "Não é possível excluir! Já existe uma folha de pagamento para este período.")
        return redirect('faltas_list')
    
    falta.delete()
    messages.success(request, "Falta removida com sucesso!")
    return redirect('faltas_list')

@user_passes_test(eh_master, login_url='dashboard_view')
def editar_falta(request, id):
    falta = get_object_or_404(Falta, id=id)
    
    # Trava de segurança para não editar se a folha já existir
    if FolhaPagamento.objects.filter(funcionario=falta.funcionario, mes=falta.mes_referencia, ano=falta.ano_referencia).exists():
        messages.warning(request, "Não é possível editar: este período já possui folha de pagamento.")
        return redirect('faltas_list')

    if request.method == 'POST':
        # Lógica de salvar (POST)...
        pass

    context = {
        'falta': falta,
        'funcionarios': Funcionario.objects.all(), # Para o select de funcionários
    }
    return render(request, 'core/falta/form.html', context)
    if request.method == 'POST':
        # ... sua lógica de salvamento aqui ...
        falta.data = request.POST.get('data')
        falta.mes_referencia = request.POST.get('mes')
        falta.ano_referencia = request.POST.get('ano')
        falta.valor_desconto = request.POST.get('valor_desconto').replace(',', '.')
        # Lembre-se de tratar o atestado se houver novo upload
        if request.FILES.get('atestado'):
            falta.atestado = request.FILES.get('atestado')
            
        falta.save()
        messages.success(request, "Falta editada com sucesso!")
        return redirect('faltas_list')
    
    context = {
        'falta': falta,
        'funcionarios': Funcionario.objects.all()
    }
    return render(request, 'core/falta/form.html', context)


# --- FOLHA DE PAGAMENTO ---
@login_required
def folha_view(request):
    if request.user.perfil.tipo_acesso == 'MASTER':
        # Master vê todas as folhas de todos os funcionários
        folhas = FolhaPagamento.objects.all().order_by('-ano', '-mes')
    else:
        # Usuário comum vê APENAS as folhas ligadas ao seu perfil de funcionário
        folhas = FolhaPagamento.objects.filter(funcionario__user=request.user).order_by('-ano', '-mes')
    
    return render(request, 'core/folha/list.html', {'folhas': folhas})

@user_passes_test(eh_master, login_url='dashboard')
def folha_create(request):
    if request.method == 'POST':
        funcionario_id = request.POST.get('funcionario')
        mes = int(request.POST.get('mes'))
        ano = int(request.POST.get('ano'))
        tipo = request.POST.get('tipo')

        funcionario = get_object_or_404(Funcionario, id=funcionario_id)

        # ✅ 13º parcela
        valor_parcela = request.POST.get('parcela_13o')
        parcela = int(valor_parcela) if valor_parcela else None

        # ✅ RESCISÃO
        data_rescisao = request.POST.get('data_rescisao')
        motivo_rescisao = request.POST.get('motivo_rescisao')

        if data_rescisao:
            data_rescisao = datetime.strptime(data_rescisao, '%Y-%m-%d').date()
        else:
            data_rescisao = None

        # ✅ Criação da folha
        nova_folha = FolhaPagamento(
            funcionario=funcionario,
            mes=mes,
            ano=ano,
            tipo=tipo,
            parcela_13o=parcela,
            data_rescisao=data_rescisao,
            motivo_rescisao=motivo_rescisao,
            fechada=False
        )

        nova_folha.save()

       # ✅ 2. Salvar Eventos Extras (os que você preenche manualmente na tela)
        eventos_ids = request.POST.getlist('evento_id[]')
        eventos_valores = request.POST.getlist('evento_valor[]')

        for eid, valor in zip(eventos_ids, eventos_valores):
            if eid and valor:
                ItemFolha.objects.create(
                    folha=nova_folha,
                    evento_id=eid,
                    valor=valor.replace(',', '.')
                )

        # ✅ 3. PROCESSAR FALTAS AUTOMATICAMENTE
        # Corrigido: usando 'nova_folha' e não 'folha'
        faltas_do_mes = Falta.objects.filter(
            funcionario=nova_folha.funcionario,
            mes_referencia=nova_folha.mes,
            ano_referencia=nova_folha.ano,
            justificada=False
        )

        total_desconto_faltas = sum(falta.valor_desconto for falta in faltas_do_mes)

        # ✅ 4. Transformar o total de faltas em um Item de Folha
        if total_desconto_faltas > 0:
            # Buscamos o evento 'Falta' que você cadastrou no banco
            # Certifique-se de que o nome no banco seja exatamente este ou use o ID fixo
            evento_falta = Evento.objects.filter(nome__icontains="Falta", tipo='DESCONTO').first()
            
            if evento_falta:
                ItemFolha.objects.create(
                    folha=nova_folha,
                    evento=evento_falta,
                    valor=total_desconto_faltas,
                    observacao=f"Desconto de {faltas_do_mes.count()} faltas injustificadas."
                )

        # ✅ Recalcular com tudo aplicado
        nova_folha.calcular_tudo()
        nova_folha.save()

        return redirect('folha_detail', id=nova_folha.id)

    context = {
        'funcionarios': Funcionario.objects.all().order_by('nome'),
        'eventos': Evento.objects.all().order_by('nome')
    }

    return render(request, 'core/folha/form.html', context)

def folha_detail(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)
    
    # SEGURANÇA: Se não for MASTER e a folha não for do usuário logado, bloqueia!
    if request.user.perfil.tipo_acesso != 'MASTER' and folha.funcionario.user != request.user:
        from django.core.exceptions import PermissionDenied
        raise PermissionDenied("Você não tem permissão para visualizar esta folha.")
    
    if not folha.fechada:
        folha.calcular_tudo()
        folha.save()
    
    return render(request, 'core/folha/detail.html', {'folha': folha})

@user_passes_test(eh_master, login_url='dashboard_view')
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

@user_passes_test(eh_master, login_url='dashboard_view')
def folha_fechar(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)
    folha.fechada = True  # Altera o boolean
    folha.save()
    return redirect('folha_detail', id=id)


@user_passes_test(eh_master, login_url='dashboard')
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

@user_passes_test(eh_master, login_url='dashboard')
def departamento_delete(request, id):
    depto = get_object_or_404(Departamento, id=id)
    depto.delete()
    return redirect('departamento_view')

@user_passes_test(eh_master, login_url='dashboard_view')
def imprimir_holerite(request, folha_id):
    folha = get_object_or_404(FolhaPagamento, id=folha_id)
    
    # 1. Carrega o template HTML que você já criou
    template = get_template('core/folha/folha_impressao.html')
    html = template.render({'folha': folha})
    
    # 2. Cria um buffer na memória para o PDF
    result = BytesIO()
    
    # 3. Transforma o HTML em PDF
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    # 4. Se não houver erro, prepara a resposta para o navegador
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        
        # O segredo da "tela preta" é o 'inline' aqui:
        response['Content-Disposition'] = f'inline; filename="holerite_{folha.funcionario.nome}.pdf"'
        return response
    
    return HttpResponse("Erro ao gerar PDF", status=400)


# --- AUTENTICAÇÃO DE PRIMEIRO ACESSO ---

def primeiro_acesso_view(request):
    if request.method == 'POST':
        cpf_digitado = request.POST.get('cpf').strip()
        senha = request.POST.get('password')
        confirmar_senha = request.POST.get('confirm_password')

        # 1. Busca o funcionário pelo CPF
        funcionario = Funcionario.objects.filter(cpf=cpf_digitado).first()

        if not funcionario:
            messages.error(request, "CPF não encontrado. Por favor, entre em contato com o RH para realizar seu pré-cadastro.")
            return redirect('primeiro_acesso')

        # 2. Verifica se ele já tem um usuário vinculado
        if funcionario.user:
            messages.warning(request, "Este CPF já possui um acesso criado. Tente recuperar sua senha.")
            return redirect('login')

        # 3. Validação básica de senha
        if senha != confirmar_senha:
            messages.error(request, "As senhas não coincidem.")
            # Corrigido: Aspas duplas removidas e caminho ajustado
            return render(request, 'registration/primeiro_acesso.html', {'cpf': cpf_digitado})

        if len(senha) < 6:
            messages.error(request, "A senha deve ter pelo menos 6 caracteres.")
            return render(request, 'registration/primeiro_acesso.html', {'cpf': cpf_digitado})

        # 4. CRIA O USUÁRIO E VINCULA
        # Usamos o CPF (sem pontos/traços) como username padrão
        username = cpf_digitado.replace('.', '').replace('-', '')
        
        # Criação do usuário
        novo_user = User.objects.create_user(
            username=username,
            password=senha,
            email=funcionario.email
        )
        
        # Vincula o usuário ao funcionário já existente e salva
        funcionario.user = novo_user
        funcionario.save()

        messages.success(request, "Acesso criado com sucesso! Agora você já pode entrar no sistema.")
        return redirect('login')

    
    return render(request, 'registration/primeiro_acesso.html')

def password_reset_view(request):
    if request.method == 'POST':
        email_digitado = request.POST.get('email')
        
        # 1. Busca o funcionário pelo e-mail
        funcionario = Funcionario.objects.filter(email=email_digitado).first()
        
        # O link só deve ser gerado se o funcionário existir E tiver um usuário vinculado
        if funcionario and funcionario.user:
            user = funcionario.user
            
            # 2. GERAÇÃO DOS CÓDIGOS DE SEGURANÇA
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            
            # 3. MONTAGEM DA URL REAL
            # 'password_reset_confirm' deve ser o nome da sua rota no urls.py
            protocol = 'https' if request.is_secure() else 'http'
            domain = request.get_host()
            link_path = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})
            
            link_real = f"{protocol}://{domain}{link_path}"
            
            # 4. ENVIO DO E-MAIL (Aparecerá no seu console)
            send_mail(
                subject='Recuperação de Senha - RH Smart',
                message=f'Olá, {funcionario.nome}!\n\nRecebemos um pedido para redefinir sua senha. Clique no link abaixo para criar uma nova:\n\n{link_real}\n\nSe você não solicitou isso, ignore este e-mail.',
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email_digitado],
                fail_silently=False,
            )
            
            messages.success(request, "Se o e-mail estiver correto, você receberá um link em instantes!")
        else:
            # Mantemos a mensagem genérica por segurança (não confirmar se e-mail existe)
            messages.info(request, "Instruções enviadas para o e-mail informado.")
            
        return redirect('login')

    # Ajuste o caminho se o seu template estiver em 'core/registration/...'
    return render(request, 'registration/password_reset.html')