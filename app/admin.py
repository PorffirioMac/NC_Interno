from django.contrib import admin
from .models import Cliente, ErroConhecido, Lead, Task, ChecklistItem, Comment

admin.site.register(Lead)
admin.site.register(Task)
admin.site.register(ChecklistItem)
admin.site.register(Comment)
admin.site.register(Cliente)
admin.site.register(ErroConhecido)

