from calendar import monthrange
from datetime import date, timedelta

from .models import Rotina, RotinaConclusao


def periodo_referencia(rotina, hoje=None):
    hoje = hoje or date.today()
    if rotina.periodicidade == 'diaria':
        return hoje
    if rotina.periodicidade == 'semanal':
        return hoje - timedelta(days=hoje.weekday())
    if rotina.periodicidade == 'mensal':
        ultimo_dia = monthrange(hoje.year, hoje.month)[1]
        vencimento = hoje.replace(day=min(rotina.dia_mes, ultimo_dia))
        return vencimento if hoje >= vencimento else None
    return None


def rotinas_pendentes_usuario(usuario, hoje=None):
    hoje = hoje or date.today()
    rotinas = list(
        Rotina.objects.filter(responsavel=usuario, ativa=True)
        .select_related('responsavel')
        .order_by('periodicidade', 'titulo')
    )
    rotinas_com_periodo = [
        (rotina, periodo_referencia(rotina, hoje))
        for rotina in rotinas
    ]
    referencias = {
        referencia for _, referencia in rotinas_com_periodo
        if referencia is not None
    }
    concluidas = set(
        RotinaConclusao.objects.filter(
            rotina__in=rotinas,
            periodo_referencia__in=referencias,
        ).values_list('rotina_id', 'periodo_referencia')
    )
    return [
        rotina for rotina, referencia in rotinas_com_periodo
        if (
            referencia is not None
            and (rotina.id, referencia) not in concluidas
        )
    ]
