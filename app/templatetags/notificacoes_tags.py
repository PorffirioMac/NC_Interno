from datetime import date
from calendar import monthrange

from django import template
from django.db.models import Case, IntegerField, Max, Value, When

from app.models import (
    ComunicacaoDestinatario, ConfirmacaoDespesaFinanceira,
    DespesaFinanceira, Notificacao, Task, TarefaPessoal,
)
from app.rotinas import periodo_referencia, rotinas_pendentes_usuario


register = template.Library()


@register.simple_tag(takes_context=True)
def caixa_nao_lidas(context):
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return 0
    return ComunicacaoDestinatario.objects.filter(
        destinatario=request.user,
        lida=False,
    ).count()


@register.inclusion_tag('app/painel_notificacoes.html', takes_context=True)
def painel_notificacoes(context):
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return {}

    hoje = date.today()
    tarefas_pessoais = []
    if (
        request.user.username == 'gabriel.porfirio'
        and (
            request.user.is_superuser
            or request.user.has_perm('app.acessar_area_gabriel')
        )
    ):
        tarefas_pessoais = list(
            TarefaPessoal.objects.filter(
                concluida=False,
                data_conclusao__lte=hoje,
            ).annotate(
                ordem_prioridade=Case(
                    When(prioridade='alta', then=Value(1)),
                    When(prioridade='media', then=Value(2)),
                    When(prioridade='baixa', then=Value(3)),
                    default=Value(4),
                    output_field=IntegerField(),
                ),
            ).order_by('ordem_prioridade', 'data_conclusao', 'area', 'titulo')
        )
    marcador_pessoal = max(
        (item.data_conclusao.toordinal() * 1_000_000 + item.id for item in tarefas_pessoais),
        default=0,
    )
    prazos = list(
        Task.objects.filter(
            responsavel=request.user,
            encerrada=False,
            prazo__lte=hoje,
        ).select_related('cliente').order_by('prazo', 'titulo')
    )
    tickets_plantao = list(
        Task.objects.filter(
            responsavel=request.user,
            encerrada=False,
            area='tickets',
            fase='pendencias_plantao',
        ).select_related('cliente').order_by('-atualizado_em', 'titulo')
    )
    marcador_plantao = max(
        (
            int(ticket.atualizado_em.timestamp() * 1000)
            for ticket in tickets_plantao
        ),
        default=0,
    )
    notificacoes_query = Notificacao.objects.filter(
        destinatario=request.user,
        lida=False,
        tarefa__encerrada=False,
    )
    nao_lidas = notificacoes_query.count()
    notificacoes = list(
        notificacoes_query.select_related('ator', 'tarefa')[:30]
    )
    comunicacoes_query = ComunicacaoDestinatario.objects.filter(
        destinatario=request.user,
        lida=False,
    )
    comunicacoes = list(comunicacoes_query.select_related('comunicacao')[:5])
    total_comunicacoes = comunicacoes_query.count()
    ultima_notificacao_id = (
        notificacoes_query
        .aggregate(id=Max('id'))['id'] or 0
    )
    ultima_comunicacao_id = comunicacoes_query.aggregate(id=Max('id'))['id'] or 0
    despesas_hoje = []
    if request.user.has_perm('app.acessar_financeiro'):
        confirmadas = ConfirmacaoDespesaFinanceira.objects.filter(
            usuario=request.user,
            competencia=hoje.replace(day=1),
        ).values_list('despesa_id', flat=True)
        ultimo_dia = monthrange(hoje.year, hoje.month)[1]
        filtro_dia = (
            {'dia_vencimento__gte': hoje.day}
            if hoje.day == ultimo_dia
            else {'dia_vencimento': hoje.day}
        )
        despesas_hoje = list(
            DespesaFinanceira.objects.filter(
                ativa=True,
                **filtro_dia,
            ).exclude(id__in=confirmadas)
        )
    ultima_despesa_id = max(
        (despesa.id for despesa in despesas_hoje),
        default=0,
    )
    rotinas_pendentes = rotinas_pendentes_usuario(request.user, hoje)
    marcador_rotina = max(
        (
            periodo_referencia(rotina, hoje).toordinal() * 1_000_000
            + rotina.id
            for rotina in rotinas_pendentes
        ),
        default=0,
    )

    return {
        'request': request,
        'painel_prazos': prazos,
        'painel_tickets_plantao': tickets_plantao,
        'painel_notificacoes': notificacoes,
        'painel_nao_lidas': nao_lidas,
        'painel_comunicacoes': comunicacoes,
        'painel_despesas_hoje': despesas_hoje,
        'painel_rotinas_pendentes': rotinas_pendentes,
        'painel_tarefas_pessoais': tarefas_pessoais,
        'painel_total_alertas': (
            len(prazos) + nao_lidas + total_comunicacoes
            + len(despesas_hoje) + len(rotinas_pendentes)
            + len(tickets_plantao)
            + len(tarefas_pessoais)
        ),
        'painel_total_novas': (
            nao_lidas + total_comunicacoes
            + len(despesas_hoje) + len(rotinas_pendentes)
            + len(tickets_plantao)
            + len(tarefas_pessoais)
        ),
        'painel_assinatura_novas': (
            f'{ultima_notificacao_id}:{ultima_comunicacao_id}:'
            f'{ultima_despesa_id}:{marcador_rotina}:{marcador_plantao}:'
            f'{marcador_pessoal}'
        ),
        'painel_hoje': hoje,
    }
