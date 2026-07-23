from datetime import date

from django import template

from app.models import ComunicacaoDestinatario, Notificacao, Task


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
    notificacoes = list(
        Notificacao.objects.filter(destinatario=request.user)
        .select_related('ator', 'tarefa')[:30]
    )
    nao_lidas = sum(not item.lida for item in notificacoes)
    comunicacoes = list(
        ComunicacaoDestinatario.objects.filter(
            destinatario=request.user,
            lida=False,
        ).select_related('comunicacao')[:5]
    )

    return {
        'request': request,
        'painel_prazos': prazos,
        'painel_notificacoes': notificacoes,
        'painel_nao_lidas': nao_lidas,
        'painel_comunicacoes': comunicacoes,
        'painel_total_alertas': len(prazos) + nao_lidas + len(comunicacoes),
        'painel_hoje': hoje,
    }
