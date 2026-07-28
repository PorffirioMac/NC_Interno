from datetime import date
from calendar import monthrange

from django import template
from django.db.models import Max

from app.models import (
    ComunicacaoDestinatario, DespesaFinanceira, Notificacao, Task,
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
    notificacoes = list(
        Notificacao.objects.filter(destinatario=request.user)
        .select_related('ator', 'tarefa')[:30]
    )
    nao_lidas = sum(not item.lida for item in notificacoes)
    comunicacoes_query = ComunicacaoDestinatario.objects.filter(
        destinatario=request.user,
        lida=False,
    )
    comunicacoes = list(comunicacoes_query.select_related('comunicacao')[:5])
    total_comunicacoes = comunicacoes_query.count()
    ultima_notificacao_id = (
        Notificacao.objects.filter(destinatario=request.user, lida=False)
        .aggregate(id=Max('id'))['id'] or 0
    )
    ultima_comunicacao_id = comunicacoes_query.aggregate(id=Max('id'))['id'] or 0
    despesas_hoje = []
    if request.user.has_perm('app.acessar_financeiro'):
        ultimo_dia = monthrange(hoje.year, hoje.month)[1]
        filtro_dia = (
            {'dia_vencimento__gte': hoje.day}
            if hoje.day == ultimo_dia
            else {'dia_vencimento': hoje.day}
        )
        despesas_hoje = list(
            DespesaFinanceira.objects.filter(ativa=True, **filtro_dia)
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
        'painel_total_alertas': (
            len(prazos) + nao_lidas + total_comunicacoes
            + len(despesas_hoje) + len(rotinas_pendentes)
            + len(tickets_plantao)
        ),
        'painel_total_novas': (
            nao_lidas + total_comunicacoes
            + len(despesas_hoje) + len(rotinas_pendentes)
            + len(tickets_plantao)
        ),
        'painel_assinatura_novas': (
            f'{ultima_notificacao_id}:{ultima_comunicacao_id}:'
            f'{ultima_despesa_id}:{marcador_rotina}:{marcador_plantao}'
        ),
        'painel_hoje': hoje,
    }
