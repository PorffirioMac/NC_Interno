from django.contrib import admin
from .models import Cliente, ComentarioSolicitacao, DespesaFinanceira, ErroConhecido, Lead, Release, Rotina, RotinaConclusao, SolicitacaoRelease, Task, ChecklistItem, Comment

admin.site.register(Lead)
admin.site.register(Task)
admin.site.register(ChecklistItem)
admin.site.register(Comment)
admin.site.register(Cliente)
admin.site.register(ErroConhecido)
admin.site.register(Release)
admin.site.register(SolicitacaoRelease)
admin.site.register(ComentarioSolicitacao)
admin.site.register(DespesaFinanceira)
admin.site.register(Rotina)
admin.site.register(RotinaConclusao)

