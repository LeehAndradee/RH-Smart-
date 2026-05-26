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
from django.db.models import ProtectedError
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO
from django.core.exceptions import PermissionDenied

def eh_master(user):
    # Checa se o usuário está logado e se o perfil dele é MASTER
    return user.is_authenticated and hasattr(user, 'perfil') and user.perfil.tipo_acesso == 'MASTER'


# --- DASHBOARD ---
@login_required
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
            funcionario=funcionario
        ).order_by('-ano', '-mes', '-id')[:3]

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
    # 1. Busca o funcionário
    funcionario = get_object_or_404(Funcionario, id=id)
    
    # 2. Segurança: Apenas MASTER pode desativar
    if request.user.perfil.tipo_acesso != 'MASTER':
        messages.error(request, "Você não tem permissão para realizar esta ação.")
        return redirect('dashboard')

    # 3. Lógica de Desativação (Soft Delete)
    funcionario.ativo = False
    funcionario.save()

    # 4. Desativação do Usuário (Segurança de Acesso)
    if funcionario.user:
        user = funcionario.user
        user.is_active = False 
        user.save()

    messages.success(request, f"O colaborador {funcionario.nome} foi desativado com sucesso!")
    
    # 5. Redireciona direto para a lista
    return redirect('funcionarios_view')


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

            messages.success(request, f"Colaborador {nome} cadastrado com sucesso!")
            
            return redirect('funcionarios_view')

        except Exception as e:
            messages.error(request, f"Erro ao cadastrar funcionário: {str(e)}")
            return redirect('funcionario_create')

    # GET
    cargos = Cargo.objects.all().order_by('nome')
    return render(request, 'core/funcionario/form.html', {'cargos': cargos})



@user_passes_test(lambda u: u.perfil.tipo_acesso == 'MASTER', login_url='dashboard_view')
@login_required
def funcionario_ativar(request, id):
    funcionario = get_object_or_404(Funcionario, id=id)
    
    # 1. Reativa no sistema de RH
    funcionario.ativo = True
    funcionario.save()

    # 2. Reativa o login do usuário no Django (O que estava faltando!)
    if funcionario.user:
        user = funcionario.user
        user.is_active = True 
        user.save()

    messages.success(request, f"O colaborador {funcionario.nome} foi REATIVADO com sucesso! O acesso dele já está liberado.")
    return redirect('funcionarios_view')

# --- CARGOS ---
@user_passes_test(eh_master, login_url='dashboard_view')
def cargos_view(request):
    cargos = Cargo.objects.all()
    return render(request, 'core/cargo/list.html', {'cargos': cargos})
@user_passes_test(eh_master, login_url='dashboard_view') # Padronizado para dashboard_view
@login_required
def cargo_create(request):
    if request.method == 'POST':
        try:
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
            
            # ✉️ Injeta a mensagem de sucesso
            messages.success(request, f"Cargo '{nome}' adicionado com sucesso!")
            return redirect('cargos_view')
            
        except Exception as e:
            messages.error(request, f"Erro ao criar cargo: {str(e)}")
            return redirect('cargo_create')
    
    departamentos = Departamento.objects.all().order_by('nome')
    return render(request, 'core/cargo/form.html', {'departamentos': departamentos})


@user_passes_test(eh_master, login_url='dashboard_view')
@login_required
def cargo_update(request, id):
    cargo = get_object_or_404(Cargo, id=id)
    
    if request.method == 'POST':
        try:
            cargo.nome = request.POST.get('nome')
            cargo.nivel = request.POST.get('nivel')
            cargo.carga_horaria = request.POST.get('carga_horaria')
            cargo.departamento_id = request.POST.get('departamento')
            
            cargo.save()
            
            # ✉️ Injeta a mensagem de sucesso na alteração
            messages.success(request, f"Cargo '{cargo.nome}' atualizado com sucesso!")
            return redirect('cargos_view')
            
        except Exception as e:
            messages.error(request, f"Erro ao atualizar cargo: {str(e)}")
            return redirect('cargos_view')

    departamentos = Departamento.objects.all().order_by('nome')
    return render(request, 'core/cargo/form.html', {
        'cargo': cargo, 
        'departamentos': departamentos
    })


@user_passes_test(eh_master, login_url='dashboard')
def cargo_delete(request, id):
    cargo = get_object_or_404(Cargo, id=id)
    
    try:
        cargo.delete()
        messages.success(request, f"Cargo '{cargo.nome}' excluído com sucesso!")
    except ProtectedError:
        # Captura o erro caso existam funcionários usando este cargo
        messages.error(request, f"Não é possível excluir o cargo '{cargo.nome}' porque existem funcionários vinculados a ele.")
        
    return redirect('cargos_view')



# --- LISTAGEM ---
@user_passes_test(eh_master, login_url='dashboard_view')
def departamentos_view(request):
    departamentos = Departamento.objects.all()
    return render(request, 'core/departamento/list.html', {'departamentos': departamentos})

# --- CRIAR ---
@user_passes_test(eh_master, login_url='dashboard')
def departamento_create(request):
    if request.method == 'POST':
        nome = request.POST.get('nome')
        descricao = request.POST.get('descricao')
        parent_id = request.POST.get('parent_id')

        Departamento.objects.create(
            nome=nome,
            descricao=descricao,
            parent_id=parent_id if parent_id else None
        )
        messages.success(request, "Departamento criado com sucesso!")
        return redirect('departamento_view') # Ajustado para o plural
    
    departamentos = Departamento.objects.all()
    return render(request, 'core/departamento/form.html', {'departamentos': departamentos})

# --- EDITAR (Corrigido para salvar os dados) ---
@user_passes_test(eh_master, login_url='dashboard_view')
def departamento_update(request, id):
    departamento = get_object_or_404(Departamento, id=id)
    
    if request.method == 'POST':
        departamento.nome = request.POST.get('nome')
        departamento.descricao = request.POST.get('descricao')
        parent_id = request.POST.get('parent_id')
        departamento.parent_id = parent_id if parent_id else None
        departamento.save()
        
        # MENSAGEM DE SUCESSO AO EDITAR
        messages.success(request, f"Departamento '{departamento.nome}' atualizado com sucesso!")
        return redirect('departamento_view') # Verifique se o nome na urls.py é este
    
        messages.success(request, f"Departamento '{departamento.nome}' atualizado com sucesso!")
        return redirect('departamentos_view') # Ajustado para o plural

    departamentos = Departamento.objects.exclude(id=id)
    return render(request, 'core/departamento/form.html', {
        'departamento': departamento, 
        'departamentos': departamentos
    })

# --- EXCLUIR (Padronizado e Seguro) ---
@user_passes_test(eh_master, login_url='dashboard')
def departamento_delete(request, id):
    departamento = get_object_or_404(Departamento, id=id)
    try:
        departamento.delete()
        messages.success(request, "Departamento removido com sucesso.")
    except Exception as e: 
        # Aqui capturamos o ProtectedError e enviamos a mensagem
        messages.error(request, f"Não foi possível excluir '{departamento.nome}'. Verifique se existem funcionários vinculados.")
    
    return redirect('departamentos_view') # Ajustado para o plural


# --- EVENTOS ---
@user_passes_test(eh_master, login_url='dashboard_view')
@login_required
def eventos_view(request):
    eventos = Evento.objects.all().order_by('nome')
    return render(request, 'core/evento/list.html', {'eventos': eventos})


@user_passes_test(eh_master, login_url='dashboard_view')
@login_required
def evento_create(request):
    if request.method == "POST":
        try:
            nome = request.POST.get('nome') 
            tipo = request.POST.get('tipo')
            valor = request.POST.get('valor_fixo') 

            # Validação básica
            if not nome or not tipo:
                messages.error(request, "Preencha os campos obrigatórios (Nome e Tipo).")
                return redirect('evento_create')

            Evento.objects.create(
                nome=nome,
                tipo=tipo,
                valor_fixo=valor if valor else None, 
            )
            
            # ✉️ Alerta de Sucesso
            messages.success(request, f"Evento '{nome}' criado com sucesso!")
            return redirect('eventos_view') # Redireciona para o nome correto da rota
            
        except Exception as e:
            messages.error(request, f"Erro ao criar evento: {str(e)}")
            return redirect('evento_create')
    
    return render(request, 'core/evento/form.html')


@user_passes_test(eh_master, login_url='dashboard_view')
@login_required
def evento_update(request, id):
    evento = get_object_or_404(Evento, id=id)
    
    if request.method == "POST":
        try:
            evento.nome = request.POST.get('nome')
            evento.tipo = request.POST.get('tipo')
            
            valor_fixo = request.POST.get('valor_fixo')
            evento.valor_fixo = valor_fixo if valor_fixo else None
            
            evento.save()
            
            # ✉️ Alerta de Sucesso
            messages.success(request, f"Evento '{evento.nome}' atualizado com sucesso!")
            return redirect('eventos_view')
            
        except Exception as e:
            messages.error(request, f"Erro ao atualizar evento: {str(e)}")
            return redirect('eventos_view')

    return render(request, 'core/evento/form.html', {'evento': evento})


@user_passes_test(eh_master, login_url='dashboard_view')
@login_required
def evento_delete(request, id):
    try:
        evento = get_object_or_404(Evento, id=id)
        nome_evento = evento.nome
        evento.delete()
        
        # ✉️ Alerta de Sucesso na exclusão
        messages.success(request, f"Evento '{nome_evento}' excluído permanentemente!")
        
    except Exception as e:
        messages.error(request, f"Não foi possível excluir o evento: {str(e)}")
        
    return redirect('eventos_view')


# --- FALTAS ---
@user_passes_test(eh_master, login_url='dashboard_view')
def faltas_view(request):
    faltas = Falta.objects.all()
    return render(request, 'core/falta/list.html', {'faltas': faltas})
@user_passes_test(eh_master, login_url='dashboard_view')
@login_required
def cadastrar_falta(request):
    if request.method == 'POST':
        try:
            funcionario_id = request.POST.get('funcionario')
            data = request.POST.get('data')
            motivo = request.POST.get('motivo')
            atestado = request.FILES.get('atestado')
            justificada = request.POST.get('justificada') == 'on'
            
            # NOVOS CAMPOS QUE ESTAVAM FALTANDO NA VIEW:
            mes_referencia = request.POST.get('mes_referencia')
            ano_referencia = request.POST.get('ano_referencia')
            valor_desconto = request.POST.get('valor_desconto')

            # Validação básica de segurança
            if not funcionario_id or not data:
                messages.error(request, "Selecione o colaborador e informe a data da ocorrência.")
                return redirect('cadastrar_falta')

            funcionario = get_object_or_404(Funcionario, id=funcionario_id)

            # Tratamento seguro para converter valores numéricos e decimais
            mes_ref = int(mes_referencia) if mes_referencia else 0
            ano_ref = int(ano_referencia) if ano_referencia else 0
            
            # Garante a formatação correta de float/decimal para o banco de dados
            v_desconto = valor_desconto.replace(',', '.') if valor_desconto else "0.00"

            # Cria o registro da falta no banco
            Falta.objects.create(
                funcionario=funcionario,
                data=data,
                motivo=motivo,
                atestado=atestado,
                justificada=justificada,
                mes_referencia=mes_ref,
                ano_referencia=ano_ref,
                valor_desconto=v_desconto
            )

            # ✉️ Alerta de Sucesso
            messages.success(request, f"Ocorrência de falta registrada para {funcionario.nome} com sucesso!")
            return redirect('faltas_view') # Padronizado para acompanhar o padrão 'nome_view' do seu urls.py
            
        except Exception as e:
            messages.error(request, f"Erro ao registrar falta: {str(e)}")
            return redirect('cadastrar_falta')

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
    
    # Trava de segurança (Mantenha no topo)
    if FolhaPagamento.objects.filter(
        funcionario=falta.funcionario, 
        mes=falta.mes_referencia, 
        ano=falta.ano_referencia
    ).exists():
        messages.warning(request, "Não é possível editar: este período já possui folha de pagamento.")
        return redirect('faltas_list')

    if request.method == 'POST':
        # OS NOMES ABAIXO DEVEM SER IGUAIS AO 'name=' DO HTML
        falta.funcionario_id = request.POST.get('funcionario') # No HTML está name="funcionario"
        falta.data = request.POST.get('data')
        falta.mes_referencia = request.POST.get('mes_referencia') # Corrigido: era 'mes'
        falta.ano_referencia = request.POST.get('ano_referencia') # Corrigido: era 'ano'
        falta.motivo = request.POST.get('motivo')
        
        # Tratamento do checkbox (justificada)
        # Checkbox só envia valor se estiver marcado
        falta.justificada = 'justificada' in request.POST 
        
        # Tratamento do valor decimal
        valor = request.POST.get('valor_desconto', '0')
        falta.valor_desconto = valor.replace(',', '.')
        
        if request.FILES.get('atestado'):
            falta.atestado = request.FILES.get('atestado')
            
        falta.save()
        messages.success(request, "Falta atualizada com sucesso!")
        return redirect('faltas_list')

    # Se for GET, renderiza o formulário
    context = {
        'falta': falta,
        'funcionarios': Funcionario.objects.all(),
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

from datetime import datetime

@user_passes_test(eh_master, login_url='dashboard_view') # Padronizado para dashboard_view
@login_required
def folha_create(request):
    if request.method == 'POST':
        try:
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

            # ✅ 2. Salvar Eventos Extras (preenchidos manualmente na tela)
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
            faltas_do_mes = Falta.objects.filter(
                funcionario=nova_folha.funcionario,
                mes_referencia=nova_folha.mes,
                ano_referencia=nova_folha.ano,
                justificada=False
            )

            total_desconto_faltas = sum(falta.valor_desconto for falta in faltas_do_mes)

            # ✅ 4. Transformar o total de faltas em um Item de Folha
            if total_desconto_faltas > 0:
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

            # ✉️ Alerta de Sucesso (Será exibido na tela de destino detalhada)
            messages.success(
                request, 
                f"Folha de Pagamento de {funcionario.nome} ({mes:02d}/{ano}) gerada e calculada com sucesso!"
            )
            return redirect('folha_detail', id=nova_folha.id)

        except Exception as e:
            # ✉️ Alerta de Erro caso o banco rejeite (Ex: Unique contraint de folha duplicada)
            messages.error(request, f"Erro ao processar e gerar a folha: {str(e)}")
            return redirect('folha_create')

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
@login_required
def folha_update(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)

    # 🛑 Bloqueio preventivo: Se a folha já foi fechada oficialmente, impede a edição
    if folha.fechada:
        messages.error(request, "Esta folha de pagamento já está fechada e não pode mais ser editada ou recalculada.")
        return redirect('folha_detail', id=id)

    if request.method == 'POST':
        try:
            folha.mes = int(request.POST.get('mes'))
            folha.ano = int(request.POST.get('ano'))
            folha.tipo = request.POST.get('tipo')
            
            # 🔄 Executa as fórmulas de cálculo do backend com os novos dados do POST
            if hasattr(folha, 'calcular_tudo'):
                folha.calcular_tudo()
                
            folha.save()
            
            # ✉️ Alerta de Sucesso
            messages.success(request, f"Folha de pagamento atualizada e recalculada com sucesso!")
            return redirect('folha_detail', id=folha.id)
            
        except Exception as e:
            messages.error(request, f"Erro ao atualizar e recalcular a folha: {str(e)}")
            return redirect('folha_update', id=id)

    context = {
        'folha': folha,
        'funcionarios': Funcionario.objects.all().order_by('nome'),
        'eventos': Evento.objects.all().order_by('nome')
    }
    return render(request, 'core/folha/form.html', context)
@user_passes_test(eh_master, login_url='dashboard_view')
@login_required
def folha_fechar(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)
    
    try:
        folha.fechada = True  # Altera o boolean para travar edições
        folha.save()
        
        # ✉️ Alerta de Sucesso
        messages.success(
            request, 
            f"Folha de pagamento de {folha.funcionario.nome} foi FECHADA oficialmente! O holerite já está disponível para o colaborador."
        )
    except Exception as e:
        messages.error(request, f"Erro ao fechar a folha: {str(e)}")
        
    return redirect('folha_detail', id=id)


@user_passes_test(eh_master, login_url='dashboard_view') # Padronizado para dashboard_view
@login_required
def folha_delete(request, id):
    folha = get_object_or_404(FolhaPagamento, id=id)

    # 🛑 Trava de Segurança: impede a exclusão física se a folha já foi encerrada
    if folha.fechada:
        messages.error(request, "Atenção: Uma folha de pagamento já encerrada/fechada não pode ser excluída do sistema.")
        return redirect('folha_detail', id=id)

    try:
        nome_colaborador = folha.funcionario.nome
        competencia = f"{folha.mes:02d}/{folha.ano}"
        
        folha.delete()
        
        # ✉️ Alerta de Sucesso
        messages.success(request, f"A folha de pagamento de {nome_colaborador} ({competencia}) foi excluída com sucesso.")
        return redirect('folhas_view') # Ajuste para o nome exato da sua rota de listagem de folhas
        
    except Exception as e:
        messages.error(request, f"Erro ao excluir a folha de pagamento: {str(e)}")
        return redirect('folha_detail', id=id)
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

@login_required # Garante apenas que o usuário esteja logado
def imprimir_holerite(request, folha_id):
    folha = get_object_or_404(FolhaPagamento, id=folha_id)
    
    # 🛡️ NOVA TRAVA DE SEGURANÇA MISTA:
    # Se NÃO for MASTER E a folha NÃO pertencer ao usuário logado, BARRA!
    if request.user.perfil.tipo_acesso != 'MASTER' and folha.funcionario.user != request.user:
        raise PermissionDenied("Você não tem permissão para visualizar este holerite.")
    
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
        
        # Mantém o inline para abrir direto no navegador/celular
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