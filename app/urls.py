from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='app/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('tarefas/', views.tarefas, name='tarefas'),
    path('comercial/', views.comercial, name='comercial'),
    path('tarefa/criar/', views.criar_tarefa, name='criar_tarefa'),
    path('tarefa/<int:tarefa_id>/atribuir/', views.atribuir_tarefa, name='atribuir_tarefa'),
    path('tarefa/<int:tarefa_id>/mover/', views.mover_tarefa, name='mover_tarefa'),
    path('tarefa/<int:tarefa_id>/', views.detalhes_tarefa, name='detalhes_tarefa'),
    path('tarefa/<int:tarefa_id>/encerrar/', views.encerrar_tarefa, name='encerrar_tarefa'),
    path('tarefa/<int:tarefa_id>/reabrir/', views.reabrir_tarefa, name='reabrir_tarefa'),
    path('encerradas/', views.tarefas_encerradas, name='tarefas_encerradas'),
    path('calendario/', views.calendario, name='calendario'),
    path('clientes/', views.clientes, name='clientes'),
    path('cliente/criar/', views.criar_cliente, name='criar_cliente'),
    path('cliente/<int:cliente_id>/', views.detalhes_cliente, name='detalhes_cliente'),
    path('cliente/<int:cliente_id>/inativar/', views.inativar_cliente, name='inativar_cliente'),
    path('cliente/<int:cliente_id>/reativar/', views.reativar_cliente, name='reativar_cliente'),
    path('clientes-inativos/', views.clientes_inativos, name='clientes_inativos'),
    path('erros-conhecidos/', views.erros_conhecidos, name='erros_conhecidos'),
    path('erro-conhecido/criar/', views.criar_erro_conhecido, name='criar_erro_conhecido'),
    path('erro-conhecido/<int:erro_id>/', views.detalhes_erro_conhecido, name='detalhes_erro_conhecido'),
    path('releases/', views.releases, name='releases'),
    path('releases/solicitacoes/', views.solicitacoes_releases, name='solicitacoes_releases'),
    path('releases/solicitacao/<int:solicitacao_id>/comentar/', views.comentar_solicitacao, name='comentar_solicitacao'),
    path('releases/solicitacao/<int:solicitacao_id>/status/', views.alterar_status_solicitacao, name='alterar_status_solicitacao'),
]
