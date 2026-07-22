from datetime import date, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Max, Q
from django.utils import timezone
from .forms import ClienteForm, ErroConhecidoForm, ReleaseForm, SolicitacaoReleaseForm
from .models import Cliente, ComentarioSolicitacao, ErroConhecido, Release, SolicitacaoRelease, Task, ChecklistItem, Comment


@login_required(login_url='/login/')
def releases(request):
    release_form = ReleaseForm()
    solicitacao_form = SolicitacaoReleaseForm()

    if request.method == 'POST' and 'publicar_release' in request.POST and request.user.is_superuser:
        release_form = ReleaseForm(request.POST)
        if release_form.is_valid():
            release = release_form.save(commit=False)
            release.publicado_por = request.user
            release.save()
            messages.success(request, 'Release publicado com sucesso!')
            return redirect('releases')
    elif request.method == 'POST' and 'enviar_solicitacao' in request.POST:
        solicitacao_form = SolicitacaoReleaseForm(request.POST)
        if solicitacao_form.is_valid():
            solicitacao = solicitacao_form.save(commit=False)
            solicitacao.solicitante = request.user
            solicitacao.save()
            messages.success(request, 'Solicitação enviada com sucesso!')
            return redirect('releases')

    minhas_solicitacoes = SolicitacaoRelease.objects.filter(
        solicitante=request.user
    ).prefetch_related('comentarios__autor')
    return render(request, 'app/releases.html', {
        'releases': Release.objects.select_related('publicado_por'),
        'release_form': release_form,
        'solicitacao_form': solicitacao_form,
        'minhas_solicitacoes': minhas_solicitacoes,
        'is_admin': request.user.is_superuser,
        'pendentes_count': SolicitacaoRelease.objects.filter(status='pendente').count() if request.user.is_superuser else 0,
    })


@login_required(login_url='/login/')
def solicitacoes_releases(request):
    if not request.user.is_superuser:
        messages.error(request, 'Apenas administradores podem acessar todas as solicitações.')
        return redirect('releases')
    solicitacoes = SolicitacaoRelease.objects.select_related('solicitante').prefetch_related('comentarios__autor')
    return render(request, 'app/solicitacoes_releases.html', {'solicitacoes': solicitacoes})


@login_required(login_url='/login/')
@require_POST
def comentar_solicitacao(request, solicitacao_id):
    if not request.user.is_superuser:
        return JsonResponse({'erro': 'Não autorizado.'}, status=403)
    solicitacao = get_object_or_404(SolicitacaoRelease, id=solicitacao_id)
    texto = request.POST.get('texto', '').strip()
    if texto:
        ComentarioSolicitacao.objects.create(solicitacao=solicitacao, autor=request.user, texto=texto)
        messages.success(request, 'Comentário adicionado!')
    else:
        messages.error(request, 'Digite um comentário.')
    return redirect('solicitacoes_releases')


@login_required(login_url='/login/')
@require_POST
def alterar_status_solicitacao(request, solicitacao_id):
    if not request.user.is_superuser:
        return JsonResponse({'erro': 'Não autorizado.'}, status=403)
    solicitacao = get_object_or_404(SolicitacaoRelease, id=solicitacao_id)
    novo_status = request.POST.get('status')
    if novo_status not in dict(SolicitacaoRelease.STATUS):
        messages.error(request, 'Status inválido.')
        return redirect('solicitacoes_releases')
    solicitacao.status = novo_status
    solicitacao.concluido_em = timezone.now() if novo_status == 'feito' else None
    solicitacao.save(update_fields=['status', 'concluido_em'])
    messages.success(request, 'Solicitação atualizada!')
    return redirect('solicitacoes_releases')


@login_required(login_url='/login/')
def erros_conhecidos(request):
    busca = request.GET.get('busca', '').strip()
    lista = ErroConhecido.objects.prefetch_related('clientes')
    if busca:
        lista = lista.filter(
            Q(palavra_chave__icontains=busca)
            | Q(descricao__icontains=busca)
            | Q(versao_observada__icontains=busca)
            | Q(ticket_netcontroll__icontains=busca)
            | Q(clientes__nome_fantasia__icontains=busca)
        ).distinct()
    return render(request, 'app/erros_conhecidos.html', {'erros': lista, 'busca': busca})


@login_required(login_url='/login/')
def criar_erro_conhecido(request):
    form = ErroConhecidoForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        erro = form.save()
        messages.success(request, 'Erro conhecido cadastrado com sucesso!')
        return redirect('detalhes_erro_conhecido', erro_id=erro.id)
    return render(request, 'app/form_erro_conhecido.html', {'form': form})


@login_required(login_url='/login/')
def detalhes_erro_conhecido(request, erro_id):
    erro = get_object_or_404(ErroConhecido.objects.prefetch_related('clientes'), id=erro_id)
    return render(request, 'app/detalhes_erro_conhecido.html', {'erro': erro})


@login_required(login_url='/login/')
def clientes(request):
    busca = request.GET.get('busca', '').strip()
    lista = Cliente.objects.filter(ativo=True)
    if busca:
        lista = lista.filter(
            Q(nome_fantasia__icontains=busca)
            | Q(razao_social__icontains=busca)
            | Q(cnpj__icontains=busca)
            | Q(proprietario__icontains=busca)
        )
    return render(request, 'app/clientes.html', {'clientes': lista, 'busca': busca})


@login_required(login_url='/login/')
def criar_cliente(request):
    form = ClienteForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        cliente = form.save()
        messages.success(request, 'Cliente cadastrado com sucesso!')
        return redirect('detalhes_cliente', cliente_id=cliente.id)
    return render(request, 'app/form_cliente.html', {'form': form})


@login_required(login_url='/login/')
def detalhes_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    return render(request, 'app/detalhes_cliente.html', {'cliente': cliente})


@login_required(login_url='/login/')
def inativar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id, ativo=True)
    if request.method != 'POST':
        return redirect('detalhes_cliente', cliente_id=cliente.id)

    motivo = request.POST.get('motivo_inativacao', '').strip()
    if not motivo:
        messages.error(request, 'Informe o motivo do cancelamento para inativar o cliente.')
        return redirect('detalhes_cliente', cliente_id=cliente.id)

    cliente.ativo = False
    cliente.motivo_inativacao = motivo
    cliente.inativado_em = timezone.now()
    cliente.save(update_fields=['ativo', 'motivo_inativacao', 'inativado_em', 'atualizado_em'])
    messages.success(request, 'Cliente inativado com sucesso!')
    return redirect('clientes_inativos')


@login_required(login_url='/login/')
def clientes_inativos(request):
    busca = request.GET.get('busca', '').strip()
    lista = Cliente.objects.filter(ativo=False)
    if busca:
        lista = lista.filter(
            Q(nome_fantasia__icontains=busca)
            | Q(razao_social__icontains=busca)
            | Q(cnpj__icontains=busca)
            | Q(motivo_inativacao__icontains=busca)
        )
    return render(request, 'app/clientes_inativos.html', {'clientes': lista, 'busca': busca})


@login_required(login_url='/login/')
def reativar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id, ativo=False)
    if request.method == 'POST':
        cliente.ativo = True
        cliente.motivo_inativacao = ''
        cliente.inativado_em = None
        cliente.save(update_fields=['ativo', 'motivo_inativacao', 'inativado_em', 'atualizado_em'])
        messages.success(request, 'Cliente reativado com sucesso!')
    return redirect('detalhes_cliente', cliente_id=cliente.id)

@login_required(login_url='/login/')
def dashboard(request):
    tarefas_visiveis = Task.objects.filter(encerrada=False, area='tickets')
    if not request.user.is_superuser:
        tarefas_visiveis = tarefas_visiveis.filter(responsavel=request.user)

    status_counts = {
        'pendente_cliente': tarefas_visiveis.filter(status='pendente_cliente').count(),
        'pendente_netcamp': tarefas_visiveis.filter(status='pendente_netcamp').count(),
        'pendente_netcontroll': tarefas_visiveis.filter(status='pendente_netcontroll').count(),
    }

    comerciais_visiveis = Task.objects.filter(encerrada=False, area='comercial')
    if not request.user.is_superuser:
        comerciais_visiveis = comerciais_visiveis.filter(responsavel=request.user)
    comercial_counts = {
        'aguardando_implantacao': comerciais_visiveis.filter(fase='aprovado_aguardando_implantacao').count(),
        'lead_inicial': comerciais_visiveis.filter(fase='lead_inicial').count(),
        'apresentacao': comerciais_visiveis.filter(fase='apresentacao').count(),
        'propostas': comerciais_visiveis.filter(fase='enviar_proposta').count(),
        'aguardando_retorno': comerciais_visiveis.filter(fase='aguardando_retorno').count(),
    }

    if request.user.is_superuser:
        hoje = date.today()
        total_tarefas = Task.objects.filter(encerrada=False, area='tickets').count()
        tarefas_ativas = Task.objects.filter(encerrada=False, area='tickets', prazo__gt=hoje).count()
        tarefas_para_hoje = Task.objects.filter(encerrada=False, area='tickets', prazo=hoje).count()
        tarefas_atrasadas = Task.objects.filter(encerrada=False, area='tickets', prazo__lt=hoje).count()
        minhas_tarefas = Task.objects.filter(encerrada=False, area='tickets', responsavel=request.user).count()
        return render(request, 'app/dashboard.html', {
            'total_tarefas': total_tarefas,
            'tarefas_ativas': tarefas_ativas,
            'tarefas_para_hoje': tarefas_para_hoje,
            'tarefas_atrasadas': tarefas_atrasadas,
            'minhas_tarefas': minhas_tarefas,
            'comercial_counts': comercial_counts,
            'is_admin': True,
            'status_counts': status_counts,
        })
    else:
        hoje = date.today()
        total_tarefas = Task.objects.filter(encerrada=False, area='tickets', responsavel=request.user).count()
        minhas_tarefas = total_tarefas
        tarefas_ativas = Task.objects.filter(encerrada=False, area='tickets', responsavel=request.user, prazo__gt=hoje).count()
        tarefas_para_hoje = Task.objects.filter(encerrada=False, area='tickets', responsavel=request.user, prazo=hoje).count()
        tarefas_atrasadas = Task.objects.filter(encerrada=False, area='tickets', responsavel=request.user, prazo__lt=hoje).count()
        return render(request, 'app/dashboard.html', {
            'total_tarefas': total_tarefas,
            'minhas_tarefas': minhas_tarefas,
            'tarefas_ativas': tarefas_ativas,
            'tarefas_para_hoje': tarefas_para_hoje,
            'tarefas_atrasadas': tarefas_atrasadas,
            'comercial_counts': comercial_counts,
            'is_admin': False,
            'status_counts': status_counts,
        })

@login_required(login_url='/login/')
def tarefas(request):
    filtro = request.GET.get('filtro', 'todas')
    cliente_filtro = request.GET.get('cliente', '').strip()
    responsavel_filtro = request.GET.get('responsavel', '').strip()
    status_filtros = dict(Task.STATUS_CHOICES)
    hoje = date.today()
    if request.user.is_superuser:
        if filtro in status_filtros:
            tarefas = Task.objects.filter(encerrada=False, status=filtro).order_by('-atualizado_em')
        elif filtro == 'minhas':
            tarefas = Task.objects.filter(encerrada=False, responsavel=request.user).order_by('-atualizado_em')
        elif filtro == 'ativas':
            tarefas = Task.objects.filter(encerrada=False, prazo__gt=hoje).order_by('-atualizado_em')
        elif filtro == 'hoje':
            tarefas = Task.objects.filter(encerrada=False, prazo=hoje).order_by('-atualizado_em')
        elif filtro == 'atrasadas':
            tarefas = Task.objects.filter(encerrada=False, prazo__lt=hoje).order_by('-atualizado_em')
        else:
            tarefas = Task.objects.filter(encerrada=False).order_by('-atualizado_em')
    else:
        if filtro in status_filtros:
            tarefas = Task.objects.filter(
                encerrada=False,
                responsavel=request.user,
                status=filtro,
            ).order_by('-atualizado_em')
        elif filtro == 'minhas':
            tarefas = Task.objects.filter(encerrada=False, responsavel=request.user).order_by('-atualizado_em')
        elif filtro == 'ativas':
            tarefas = Task.objects.filter(encerrada=False, responsavel=request.user, prazo__gt=hoje).order_by('-atualizado_em')
        elif filtro == 'hoje':
            tarefas = Task.objects.filter(encerrada=False, responsavel=request.user, prazo=hoje).order_by('-atualizado_em')
        elif filtro == 'atrasadas':
            tarefas = Task.objects.filter(encerrada=False, responsavel=request.user, prazo__lt=hoje).order_by('-atualizado_em')
        else:
            tarefas = Task.objects.filter(encerrada=False, responsavel=request.user).order_by('-atualizado_em')
    tarefas = tarefas.filter(area='tickets')
    selected_responsavel_id = None
    if request.user.is_superuser and responsavel_filtro.isdigit() and User.objects.filter(
        id=responsavel_filtro,
        is_active=True,
    ).exists():
        selected_responsavel_id = int(responsavel_filtro)
        tarefas = tarefas.filter(responsavel_id=selected_responsavel_id)
    else:
        responsavel_filtro = ''

    selected_cliente_id = None
    if cliente_filtro == 'sem_cliente':
        tarefas = tarefas.filter(cliente__isnull=True)
    elif cliente_filtro.isdigit() and Cliente.objects.filter(id=cliente_filtro).exists():
        selected_cliente_id = int(cliente_filtro)
        tarefas = tarefas.filter(cliente_id=selected_cliente_id)
    else:
        cliente_filtro = ''

    tarefas = tarefas.select_related('cliente', 'responsavel').annotate(
        ultima_atualizacao_comentario=Max('comentarios__criado_em')
    )
    fases = dict(Task.FASES_TICKETS)
    view_mode = request.GET.get('view', 'kanban')
    if view_mode not in ['kanban', 'lista']:
        view_mode = 'kanban'
    users = User.objects.filter(is_active=True).order_by('username') if request.user.is_superuser else None
    # contador de tarefas encerradas para exibir no botão interno
    if request.user.is_superuser:
        encerradas_count = Task.objects.filter(encerrada=True, area='tickets').count()
    else:
        encerradas_count = Task.objects.filter(encerrada=True, area='tickets', responsavel=request.user).count()

    return render(request, 'app/kanban.html', {
        'tarefas': tarefas,
        'fases': fases,
        'filtro_atual': filtro,
        'view_mode': view_mode,
        'is_admin': request.user.is_superuser,
        'users': users,
        'encerradas_count': encerradas_count,
        'clientes': Cliente.objects.all(),
        'cliente_filtro': cliente_filtro,
        'selected_cliente_id': selected_cliente_id,
        'responsavel_filtro': responsavel_filtro,
        'selected_responsavel_id': selected_responsavel_id,
    })


@login_required(login_url='/login/')
def comercial(request):
    tarefas = Task.objects.filter(encerrada=False, area='comercial')
    if not request.user.is_superuser:
        tarefas = tarefas.filter(responsavel=request.user)

    fase_filtro = request.GET.get('fase', '')
    if fase_filtro in dict(Task.FASES_COMERCIAL):
        tarefas = tarefas.filter(fase=fase_filtro)
    else:
        fase_filtro = ''

    tarefas = tarefas.select_related('cliente', 'responsavel').annotate(
        ultima_atualizacao_comentario=Max('comentarios__criado_em')
    ).order_by('-atualizado_em')
    view_mode = request.GET.get('view', 'kanban')
    if view_mode not in ('kanban', 'lista'):
        view_mode = 'kanban'

    return render(request, 'app/comercial.html', {
        'tarefas': tarefas,
        'fases': dict(Task.FASES_COMERCIAL),
        'view_mode': view_mode,
        'is_admin': request.user.is_superuser,
        'fase_filtro': fase_filtro,
    })


@login_required(login_url='/login/')
@require_POST
def mover_tarefa(request, tarefa_id):
    tarefas_permitidas = Task.objects.filter(encerrada=False)
    if not request.user.is_superuser:
        tarefas_permitidas = tarefas_permitidas.filter(responsavel=request.user)

    tarefa = get_object_or_404(tarefas_permitidas, id=tarefa_id)
    nova_fase = request.POST.get('fase', '')
    fases_permitidas = Task.FASES_COMERCIAL if tarefa.area == 'comercial' else Task.FASES_TICKETS
    if nova_fase not in dict(fases_permitidas):
        return JsonResponse({'erro': 'Coluna inválida.'}, status=400)

    tarefa.fase = nova_fase
    tarefa.save(update_fields=['fase', 'atualizado_em'])
    return JsonResponse({
        'sucesso': True,
        'fase': nova_fase,
        'fase_nome': tarefa.get_fase_display(),
    })


@login_required(login_url='/login/')
@require_POST
def gerar_ticket_implantacao(request, tarefa_id):
    permitidas = Task.objects.filter(id=tarefa_id, area='comercial', encerrada=False)
    if not request.user.is_superuser:
        permitidas = permitidas.filter(responsavel=request.user)
    comercial = get_object_or_404(permitidas)

    if hasattr(comercial, 'ticket_implantacao'):
        messages.info(request, 'Este ticket comercial já possui um ticket de implantação.')
        return redirect('detalhes_tarefa', tarefa_id=comercial.ticket_implantacao.id)

    implantacao = Task.objects.create(
        titulo=comercial.titulo,
        descricao=comercial.descricao,
        area='tickets',
        fase='implantacao',
        status='pendente_netcamp',
        prioridade=comercial.prioridade,
        responsavel=comercial.responsavel,
        cliente=comercial.cliente,
        prazo=comercial.prazo,
        origem_comercial=comercial,
    )

    checklist_implantacao = [
        'SQL/Concentrador/PDV/Terminais/SAT',
        'Configuração de Impressoras e fixação de IP das mesmas',
        'Checar se possui demais licenças e se possuir, instalar (E-commerce, Xbot, Marketing, QR Code Mesa)',
        'Criar grupo de suporte e colocar todos da NetCamp como ADM',
        'Inserir descrição de atendimento no grupo de suporte',
        'Instalar Anydesks e colocar nossa senha padrão',
        'Inserir acessos do Anydesk na planilha ACESSOS ONLINE',
        'Criar Usuário NetCamp 999 com senha 753951',
        'Entregar manual de procedimentos básicos do sistema',
        'Treinamento básico conforme itens do mesmo manual',
        'Enviar Planilha Fiscal para Contador preencher',
        'Orientar cliente sobre obrigações e importância da Planilha Fiscal',
    ]
    ChecklistItem.objects.bulk_create([
        ChecklistItem(task=implantacao, descricao=descricao, criado_por=request.user)
        for descricao in checklist_implantacao
    ])
    messages.success(request, 'Ticket técnico de implantação gerado com sucesso!')
    return redirect('detalhes_tarefa', tarefa_id=implantacao.id)

@login_required(login_url='/login/')
def atribuir_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Task, id=tarefa_id)
    if not request.user.is_superuser:
        messages.error(request, 'Apenas administradores podem atribuir responsáveis.')
        return redirect('tarefas')

    if request.method == 'POST':
        responsavel_id = request.POST.get('responsavel')
        if responsavel_id:
            tarefa.responsavel = get_object_or_404(User, id=responsavel_id)
        else:
            tarefa.responsavel = None
        tarefa.save()
        messages.success(request, 'Responsável atualizado!')

    return redirect('tarefas')

@login_required(login_url='/login/')
def criar_tarefa(request):
    area = request.POST.get('area', request.GET.get('area', 'tickets'))
    if area not in dict(Task.AREAS):
        area = 'tickets'
    fases_disponiveis = Task.FASES_COMERCIAL if area == 'comercial' else Task.FASES_TICKETS
    if request.method == 'POST':
        status = request.POST.get('status')
        if status not in dict(Task.STATUS_CHOICES):
            messages.error(request, 'Selecione um status válido.')
            users = User.objects.filter(is_active=True).order_by('username') if request.user.is_superuser else None
            return render(request, 'app/criar_tarefa.html', {
                'users': users,
                'status_choices': Task.STATUS_CHOICES,
                'fases': fases_disponiveis,
                'area': area,
                'clientes': Cliente.objects.filter(ativo=True),
            })

        responsavel = None
        if request.user.is_superuser and request.POST.get('responsavel'):
            responsavel = get_object_or_404(User, id=request.POST['responsavel'])
        elif not request.user.is_superuser:
            responsavel = request.user

        prazo = request.POST.get('prazo')
        if not prazo:
            prazo = date.today() + timedelta(days=3)

        cliente = None
        if request.POST.get('cliente'):
            cliente = get_object_or_404(Cliente, id=request.POST['cliente'], ativo=True)

        tarefa = Task.objects.create(
            titulo=request.POST['titulo'],
            descricao=request.POST.get('descricao', ''),
            area=area,
            fase=request.POST['fase'],
            status=status,
            prioridade=request.POST.get('prioridade', 'media'),
            responsavel=responsavel,
            cliente=cliente,
            prazo=prazo,
        )

        checklists_padrao = {
            'comercial': [
                'Apresentar sistema',
                'Proposta',
                'Pedido Aprovado',
                'Criar Grupo de Suporte',
                'Cliente orientado',
                'Solicitação dos dados',
                'Cardápio',
                'Inserido Cardápio',
                'Contrato Enviado',
                'Contrato Assinado',
            ],
            'implantacao': [
                'SQL/Concentrador/PDV/Terminais/SAT',
                'Configuração de Impressoras e fixação de IP das mesmas',
                'Checar se possui demais licenças e se possuir, instalar (E-commerce, Xbot, Marketing, QR Code Mesa)',
                'Criar grupo de suporte e colocar todos da NetCamp como ADM',
                'Inserir descrição de atendimento no grupo de suporte',
                'Instalar Anydesks e colocar nossa senha padrão',
                'Inserir acessos do Anydesk na planilha ACESSOS ONLINE',
                'Criar Usuário NetCamp 999 com senha 753951',
                'Entregar manual de procedimentos básicos do sistema',
                'Treinamento básico conforme itens do mesmo manual',
                'Enviar Planilha Fiscal para Contador preencher',
                'Orientar cliente sobre obrigações e importância da Planilha Fiscal',
            ],
            'tickets_abertos': [
                'Chamado registrado e categorizado',
                'Diagnóstico inicial realizado',
                'Solução aplicada / testada',
                'Cliente notificado sobre resolução',
                'Chamado encerrado',
            ],
        }

        fase = tarefa.fase
        if fase in checklists_padrao:
            for descricao in checklists_padrao[fase]:
                ChecklistItem.objects.create(
                    task=tarefa,
                    descricao=descricao,
                    criado_por=request.user,
                )

        messages.success(request, 'Ticket criado com checklists automáticos!')
        return redirect('comercial' if area == 'comercial' else 'tarefas')
    users = User.objects.filter(is_active=True).order_by('username') if request.user.is_superuser else None
    return render(request, 'app/criar_tarefa.html', {
        'users': users,
        'status_choices': Task.STATUS_CHOICES,
        'fases': fases_disponiveis,
        'area': area,
        'clientes': Cliente.objects.filter(ativo=True),
    })

@login_required(login_url='/login/')
def detalhes_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Task, id=tarefa_id)
    if request.method == 'POST':
        if 'atualizar_cliente' in request.POST:
            cliente_id = request.POST.get('cliente')
            tarefa.cliente = get_object_or_404(Cliente, id=cliente_id, ativo=True) if cliente_id else None
            tarefa.save()
            messages.success(request, 'Cliente vinculado ao ticket!')
        elif 'responsavel' in request.POST and request.user.is_superuser:
            responsavel_id = request.POST.get('responsavel')
            if responsavel_id:
                tarefa.responsavel = get_object_or_404(User, id=responsavel_id)
            else:
                tarefa.responsavel = None
            tarefa.save()
            messages.success(request, 'Responsável atualizado!')
        elif 'checklist' in request.POST:
            ChecklistItem.objects.create(
                task=tarefa,
                descricao=request.POST['descricao'],
                criado_por=request.user,
            )
        elif 'comentario' in request.POST:
            Comment.objects.create(
                task=tarefa,
                autor=request.user,
                texto=request.POST['texto'],
            )
            messages.success(request, 'Comentário adicionado!')
        elif 'concluir_check' in request.POST:
            item = get_object_or_404(ChecklistItem, id=request.POST['item_id'])
            item.concluido = not item.concluido
            item.save()
        elif 'atualizar_status' in request.POST:
            novo_status = request.POST.get('novo_status')
            if novo_status in dict(Task.STATUS_CHOICES):
                tarefa.status = novo_status
                tarefa.save()
                messages.success(request, 'Status atualizado!')
            else:
                messages.error(request, 'Selecione um status válido.')
        return redirect('detalhes_tarefa', tarefa_id=tarefa.id)
    users = User.objects.filter(is_active=True).order_by('username') if request.user.is_superuser else None
    return render(request, 'app/detalhes_tarefa.html', {
        'tarefa': tarefa,
        'is_admin': request.user.is_superuser,
        'users': users,
        'status_choices': Task.STATUS_CHOICES,
        'clientes': Cliente.objects.filter(ativo=True),
    })

@login_required(login_url='/login/')
def calendario(request):
    hoje = date.today()
    semana_inicio = hoje - timedelta(days=hoje.weekday())
    semana_fim = semana_inicio + timedelta(days=6)

    week_days = []
    for i in range(7):
        dia = semana_inicio + timedelta(days=i)
        week_days.append({
            'label': dia.strftime('%a'),
            'date': dia,
            'is_today': dia == hoje,
            'tasks': Task.objects.filter(encerrada=False, prazo=dia).order_by('titulo'),
        })

    month_start = hoje.replace(day=1)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    month_end = next_month - timedelta(days=1)

    month_weeks = []
    first_weekday = month_start.weekday()
    first_calendar_day = month_start - timedelta(days=first_weekday)
    day_cursor = first_calendar_day
    while day_cursor <= month_end or day_cursor.weekday() != 0:
        week = []
        for _ in range(7):
            week.append({
                'date': day_cursor,
                'is_current_month': day_cursor.month == month_start.month,
                'is_today': day_cursor == hoje,
                'tasks': Task.objects.filter(encerrada=False, prazo=day_cursor).order_by('titulo'),
            })
            day_cursor += timedelta(days=1)
        month_weeks.append(week)

    month_tasks = Task.objects.filter(encerrada=False, prazo__month=hoje.month, prazo__year=hoje.year)

    return render(request, 'app/calendario.html', {
        'week_days': week_days,
        'week_start': semana_inicio,
        'week_end': semana_fim,
        'month_weeks': month_weeks,
        'month_name': month_start.strftime('%B').capitalize(),
        'current_year': hoje.year,
        'month_tasks': month_tasks,
    })

@login_required(login_url='/login/')
def encerrar_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Task, id=tarefa_id)
    tarefa.encerrada = True
    tarefa.save()
    messages.success(request, 'Ticket encerrado com sucesso!')
    return redirect('tarefas_encerradas')

@login_required(login_url='/login/')
def reabrir_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Task, id=tarefa_id)
    tarefa.encerrada = False
    tarefa.save()
    messages.success(request, 'Ticket reaberto!')
    return redirect('tarefas')

@login_required(login_url='/login/')
def tarefas_encerradas(request):
    if request.user.is_superuser:
        tarefas = Task.objects.filter(encerrada=True).order_by('-atualizado_em')
    else:
        tarefas = Task.objects.filter(encerrada=True, responsavel=request.user).order_by('-atualizado_em')
    fases = dict(Task.FASES)
    return render(request, 'app/tarefas_encerradas.html', {
        'tarefas': tarefas,
        'fases': fases,
        'is_admin': request.user.is_superuser,
    })
