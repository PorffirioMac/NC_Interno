from datetime import date, timedelta
from decimal import Decimal
import shutil
import tempfile

from django.contrib.auth.models import User
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.hashers import check_password, make_password
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    AcessoAreaGabriel, AnexoErroConhecido, AnexoProcedimento, AnexoSugestaoDesenvolvimento,
    AnexoTicket, Cliente, ClienteProtestado, Comment, ComentarioTarefaPessoal, Comunicacao,
    ComunicacaoDestinatario, ConfirmacaoDespesaFinanceira, CreditoMatriz,
    DespesaFinanceira,
    ErroConhecido, Notificacao,
    ProcedimentoInterno, Release, Rotina, RotinaConclusao,
    SugestaoDesenvolvimento, Task, TarefaPessoal,
)
from .rotinas import periodo_referencia, rotinas_pendentes_usuario
from .views import _data_vencimento_mensal


class PainelNotificacoesTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'senha')
        self.operador = User.objects.create_user('operador', password='senha')
        self.outro = User.objects.create_user('outro', password='senha')
        self.tarefa = Task.objects.create(
            titulo='Ticket de teste',
            prazo=date.today(),
            responsavel=self.operador,
        )

    def test_painel_mostra_prazo_do_proprio_operador(self):
        self.client.force_login(self.operador)
        resposta = self.client.get(reverse('dashboard'))

        self.assertContains(resposta, 'Central de avisos')
        self.assertContains(resposta, 'Ticket de teste')
        self.assertContains(resposta, 'Vence hoje')

    def test_secoes_do_popup_respeitam_ordem_de_prioridade(self):
        self.operador.user_permissions.add(
            Permission.objects.get(codename='acessar_financeiro')
        )
        Task.objects.create(
            titulo='Ticket do plantão',
            responsavel=self.operador,
            area='tickets',
            fase='pendencias_plantao',
        )
        DespesaFinanceira.objects.create(
            titulo='Despesa de hoje',
            valor=Decimal('10.00'),
            dia_vencimento=date.today().day,
            criado_por=self.admin,
        )
        comunicado = Comunicacao.objects.create(
            categoria='aviso',
            titulo='Comunicado para ordenar',
            conteudo='Conteúdo.',
            autor=self.admin,
        )
        ComunicacaoDestinatario.objects.create(
            comunicacao=comunicado,
            destinatario=self.operador,
        )
        Notificacao.objects.create(
            destinatario=self.operador,
            ator=self.admin,
            tarefa=self.tarefa,
            tipo='atribuicao',
            mensagem='Atualização para ordenar.',
        )
        self.client.force_login(self.operador)

        resposta = self.client.get(reverse('dashboard'))
        conteudo = resposta.content.decode()

        self.assertLess(conteudo.index('Prazos</h3>'), conteudo.index('Plantão</h3>'))
        self.assertLess(conteudo.index('Plantão</h3>'), conteudo.index('Financeiro hoje</h3>'))
        self.assertLess(conteudo.index('Financeiro hoje</h3>'), conteudo.index('Comunicados</h3>'))
        self.assertLess(conteudo.index('Comunicados</h3>'), conteudo.index('Atualizações</h3>'))

    def test_comentario_notifica_responsavel(self):
        self.client.force_login(self.outro)
        self.client.post(reverse('detalhes_tarefa', args=[self.tarefa.id]), {
            'comentario': '1',
            'texto': 'Uma atualização importante.',
        })

        notificacao = Notificacao.objects.get()
        self.assertEqual(notificacao.destinatario, self.operador)
        self.assertEqual(notificacao.tipo, 'comentario')
        self.assertIn('outro comentou', notificacao.mensagem)

    def test_comentario_mais_recente_aparece_primeiro_no_ticket(self):
        Comment.objects.create(
            task=self.tarefa,
            autor=self.operador,
            texto='Comentário mais antigo',
        )
        Comment.objects.create(
            task=self.tarefa,
            autor=self.operador,
            texto='Comentário mais recente',
        )
        self.client.force_login(self.operador)

        resposta = self.client.get(
            reverse('detalhes_tarefa', args=[self.tarefa.id]),
        )
        conteudo = resposta.content.decode()

        self.assertLess(
            conteudo.index('Comentário mais recente'),
            conteudo.index('Comentário mais antigo'),
        )

    def test_autor_pode_editar_proprio_comentario(self):
        comentario = Comment.objects.create(
            task=self.tarefa,
            autor=self.operador,
            texto='Texto original',
        )
        self.client.force_login(self.operador)

        resposta = self.client.post(
            reverse('editar_comentario_ticket', args=[self.tarefa.id, comentario.id]),
            {'texto': 'Texto corrigido'},
        )

        self.assertEqual(resposta.status_code, 302)
        comentario.refresh_from_db()
        self.assertEqual(comentario.texto, 'Texto corrigido')

    def test_usuario_nao_pode_alterar_comentario_de_outro(self):
        comentario = Comment.objects.create(
            task=self.tarefa,
            autor=self.operador,
            texto='Comentário protegido',
        )
        self.client.force_login(self.outro)

        self.client.post(
            reverse('editar_comentario_ticket', args=[self.tarefa.id, comentario.id]),
            {'texto': 'Tentativa de alteração'},
        )
        self.client.post(
            reverse('excluir_comentario_ticket', args=[self.tarefa.id, comentario.id]),
        )

        comentario.refresh_from_db()
        self.assertEqual(comentario.texto, 'Comentário protegido')

    def test_admin_pode_excluir_comentario(self):
        comentario = Comment.objects.create(
            task=self.tarefa,
            autor=self.operador,
            texto='Comentário a remover',
        )
        self.client.force_login(self.admin)

        resposta = self.client.post(
            reverse('excluir_comentario_ticket', args=[self.tarefa.id, comentario.id]),
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(Comment.objects.filter(id=comentario.id).exists())

    def test_nova_atribuicao_notifica_operador(self):
        self.tarefa.responsavel = None
        self.tarefa.save()
        self.client.force_login(self.admin)
        self.client.post(reverse('detalhes_tarefa', args=[self.tarefa.id]), {
            'responsavel': self.operador.id,
        })

        notificacao = Notificacao.objects.get()
        self.assertEqual(notificacao.destinatario, self.operador)
        self.assertEqual(notificacao.tipo, 'atribuicao')

    def test_usuario_nao_pode_marcar_notificacao_de_outro(self):
        notificacao = Notificacao.objects.create(
            destinatario=self.operador,
            ator=self.admin,
            tarefa=self.tarefa,
            tipo='atribuicao',
            mensagem='Teste',
        )
        self.client.force_login(self.outro)
        resposta = self.client.post(
            reverse('marcar_notificacao_lida', args=[notificacao.id])
        )

        self.assertEqual(resposta.status_code, 404)
        notificacao.refresh_from_db()
        self.assertFalse(notificacao.lida)

    def test_status_reune_atualizacoes_e_mensagens_nao_lidas(self):
        notificacao = Notificacao.objects.create(
            destinatario=self.operador,
            ator=self.admin,
            tarefa=self.tarefa,
            tipo='atribuicao',
            mensagem='Nova atribuição.',
        )
        comunicacao = Comunicacao.objects.create(
            categoria='aviso',
            titulo='Novo comunicado',
            conteudo='Conteúdo.',
            autor=self.admin,
        )
        entrega = ComunicacaoDestinatario.objects.create(
            comunicacao=comunicacao,
            destinatario=self.operador,
        )
        self.client.force_login(self.operador)

        resposta = self.client.get(reverse('status_notificacoes'))

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json()['total'], 2)
        self.assertEqual(
            resposta.json()['assinatura'],
            f'{notificacao.id}:{entrega.id}:0:0:0:0',
        )
        self.assertEqual(resposta['Cache-Control'], 'no-store')

    def test_painel_exibe_somente_atualizacoes_nao_lidas_de_ticket_ativo(self):
        Notificacao.objects.create(
            destinatario=self.operador,
            ator=self.admin,
            tarefa=self.tarefa,
            tipo='atribuicao',
            mensagem='Atualização já confirmada.',
            lida=True,
        )
        self.tarefa.encerrada = True
        self.tarefa.save()
        Notificacao.objects.create(
            destinatario=self.operador,
            ator=self.admin,
            tarefa=self.tarefa,
            tipo='comentario',
            mensagem='Atualização de ticket encerrado.',
        )
        self.client.force_login(self.operador)

        painel = self.client.get(reverse('dashboard'))
        status = self.client.get(reverse('status_notificacoes'))

        self.assertNotContains(painel, 'Atualização já confirmada.')
        self.assertNotContains(painel, 'Atualização de ticket encerrado.')
        self.assertEqual(status.json()['total'], 0)

    def test_confirmar_atualizacao_marca_como_lida(self):
        notificacao = Notificacao.objects.create(
            destinatario=self.operador,
            ator=self.admin,
            tarefa=self.tarefa,
            tipo='comentario',
            mensagem='Confirmar esta atualização.',
        )
        self.client.force_login(self.operador)

        resposta = self.client.post(
            reverse('marcar_notificacao_lida', args=[notificacao.id]),
        )

        self.assertEqual(resposta.status_code, 200)
        notificacao.refresh_from_db()
        self.assertTrue(notificacao.lida)

    def test_encerrar_ticket_confirma_atualizacoes_pendentes(self):
        notificacao = Notificacao.objects.create(
            destinatario=self.operador,
            ator=self.admin,
            tarefa=self.tarefa,
            tipo='atribuicao',
            mensagem='Atualização pendente antes do encerramento.',
        )
        self.client.force_login(self.operador)

        self.client.get(reverse('encerrar_tarefa', args=[self.tarefa.id]))

        notificacao.refresh_from_db()
        self.assertTrue(notificacao.lida)


    def test_responsavel_pode_editar_dados_do_ticket(self):
        self.client.force_login(self.operador)
        self.client.post(reverse('detalhes_tarefa', args=[self.tarefa.id]), {
            'editar_ticket': '1',
            'titulo': 'Ticket atualizado',
            'descricao': 'Nova descrição',
            'fase': 'tarefas_internas',
            'status': 'pendente_netcamp',
            'prioridade': 'urgente',
            'prazo': '2026-08-15',
            'cliente': '',
        })

        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.titulo, 'Ticket atualizado')
        self.assertEqual(self.tarefa.fase, 'tarefas_internas')
        self.assertEqual(self.tarefa.status, 'pendente_netcamp')
        self.assertEqual(self.tarefa.prioridade, 'urgente')

    def test_admin_nao_responsavel_nao_pode_editar_ticket(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('detalhes_tarefa', args=[self.tarefa.id]), {
            'editar_ticket': '1',
            'titulo': 'Alteração indevida',
            'descricao': '',
            'fase': 'diversos',
            'status': 'pendente_cliente',
            'prioridade': 'baixa',
            'prazo': '',
            'cliente': '',
        })

        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.titulo, 'Ticket de teste')
        self.assertNotEqual(self.tarefa.fase, 'diversos')

    def test_formulario_aparece_somente_para_responsavel(self):
        self.client.force_login(self.operador)
        resposta = self.client.get(reverse('detalhes_tarefa', args=[self.tarefa.id]))
        self.assertContains(resposta, 'Editar dados do ticket')

        self.client.force_login(self.outro)
        resposta = self.client.get(reverse('detalhes_tarefa', args=[self.tarefa.id]))
        self.assertNotContains(resposta, 'Editar dados do ticket')


class DesempenhoDashboardTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'senha')
        self.operador = User.objects.create_user(
            'operador',
            first_name='Maria',
            last_name='Silva',
            password='senha',
        )
        hoje = date.today()
        Task.objects.create(
            titulo='Em dia',
            responsavel=self.operador,
            prazo=hoje + timedelta(days=2),
        )
        Task.objects.create(
            titulo='Vence hoje',
            responsavel=self.operador,
            prazo=hoje,
        )
        Task.objects.create(
            titulo='Atrasado',
            responsavel=self.operador,
            prazo=hoje - timedelta(days=1),
        )
        Task.objects.create(
            titulo='Sem prazo',
            responsavel=self.operador,
        )

    def test_admin_visualiza_metricas_individuais(self):
        self.client.force_login(self.admin)
        resposta = self.client.get(reverse('dashboard'))

        self.assertContains(resposta, 'Desempenho individual da equipe')
        self.assertContains(resposta, 'Maria Silva')
        self.assertContains(resposta, 'Vencendo hoje')
        membro = resposta.context['desempenho_usuarios'].get(pk=self.operador.pk)
        self.assertEqual(membro.tickets_abertos, 4)
        self.assertEqual(membro.tickets_em_dia, 1)
        self.assertEqual(membro.tickets_hoje, 1)
        self.assertEqual(membro.tickets_atrasados, 1)
        self.assertEqual(membro.tickets_sem_prazo, 1)

    def test_usuario_comum_nao_visualiza_desempenho_da_equipe(self):
        self.client.force_login(self.operador)
        resposta = self.client.get(reverse('dashboard'))

        self.assertNotContains(resposta, 'Desempenho individual da equipe')

    def test_encerramento_registra_data_e_reabertura_limpa(self):
        tarefa = Task.objects.filter(responsavel=self.operador).first()
        self.client.force_login(self.operador)

        self.client.get(reverse('encerrar_tarefa', args=[tarefa.id]))
        tarefa.refresh_from_db()
        self.assertTrue(tarefa.encerrada)
        self.assertIsNotNone(tarefa.encerrado_em)

        self.client.get(reverse('reabrir_tarefa', args=[tarefa.id]))
        tarefa.refresh_from_db()
        self.assertFalse(tarefa.encerrada)
        self.assertIsNone(tarefa.encerrado_em)


class ClientesOrdenacaoTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('usuario_clientes', password='senha')

    def criar_cliente(self, codigo, nome):
        return Cliente.objects.create(
            codigo=codigo,
            nome_fantasia=nome,
            razao_social=f'{nome} LTDA',
            cnpj=f'CNPJ {nome}',
            proprietario='Proprietário',
            telefone='(11) 99999-9999',
        )

    def test_lista_clientes_ordena_pela_id_digitavel(self):
        self.criar_cliente('00120', 'Cliente 120')
        self.criar_cliente('00003', 'Cliente 3')
        self.criar_cliente('00045', 'Cliente 45')
        self.client.force_login(self.usuario)

        resposta = self.client.get(reverse('clientes'))

        codigos = [cliente.codigo for cliente in resposta.context['clientes']]
        self.assertEqual(codigos, ['00003', '00045', '00120'])

    def test_observacoes_podem_ser_atualizadas_apos_cadastro(self):
        cliente = self.criar_cliente('00001', 'Cliente observado')
        self.client.force_login(self.usuario)

        resposta = self.client.post(
            reverse('detalhes_cliente', args=[cliente.id]),
            {
                'salvar_observacoes': '1',
                'observacoes': 'Cliente prefere contato no período da tarde.',
            },
        )

        self.assertRedirects(
            resposta,
            reverse('detalhes_cliente', args=[cliente.id]),
        )
        cliente.refresh_from_db()
        self.assertEqual(
            cliente.observacoes,
            'Cliente prefere contato no período da tarde.',
        )


    def test_cliente_inativo_pode_ser_editado_e_reativado(self):
        cliente = self.criar_cliente('00123', 'Cadastro incorreto')
        cliente.ativo = False
        cliente.motivo_inativacao = 'Cadastro feito por engano'
        cliente.save()
        self.client.force_login(self.usuario)

        resposta = self.client.post(reverse('editar_cliente', args=[cliente.id]), {
            'codigo': '00999',
            'nome_fantasia': 'Cliente corrigido',
            'razao_social': 'Cliente Corrigido LTDA',
            'cnpj': '00.000.000/0001-00',
            'proprietario': 'Responsável',
            'telefone': '(11) 99999-9999',
            'observacoes': 'Dados conferidos.',
        })

        self.assertRedirects(resposta, reverse('detalhes_cliente', args=[cliente.id]))
        cliente.refresh_from_db()
        self.assertEqual(cliente.codigo, '00999')
        self.assertFalse(cliente.ativo)

        resposta = self.client.post(reverse('reativar_cliente', args=[cliente.id]))
        self.assertRedirects(resposta, reverse('detalhes_cliente', args=[cliente.id]))
        cliente.refresh_from_db()
        self.assertTrue(cliente.ativo)
        self.assertEqual(cliente.motivo_inativacao, '')

    def test_lista_de_inativos_exibe_edicao_e_reativacao(self):
        cliente = self.criar_cliente('00124', 'Cliente inativo')
        cliente.ativo = False
        cliente.save()
        self.client.force_login(self.usuario)

        resposta = self.client.get(reverse('clientes_inativos'))

        self.assertContains(resposta, reverse('editar_cliente', args=[cliente.id]))
        self.assertContains(resposta, reverse('reativar_cliente', args=[cliente.id]))


class FinanceiroTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user('financeiro', password='senha')
        self.sem_permissao = User.objects.create_user('comum', password='senha')
        self.permissao = Permission.objects.get(codename='acessar_financeiro')
        self.usuario.user_permissions.add(self.permissao)

    def test_usuario_sem_permissao_nao_acessa_financeiro(self):
        self.client.force_login(self.sem_permissao)

        resposta = self.client.get(reverse('financeiro'))

        self.assertEqual(resposta.status_code, 403)

    def test_usuario_autorizado_cadastra_despesa_recorrente(self):
        self.client.force_login(self.usuario)

        resposta = self.client.post(reverse('financeiro'), {
            'salvar_despesa': '1',
            'titulo': 'Aluguel',
            'valor': '1.250,50',
            'dia_vencimento': '10',
            'descricao': 'Escritório',
        })

        self.assertRedirects(resposta, reverse('financeiro'))
        despesa = DespesaFinanceira.objects.get()
        self.assertEqual(despesa.valor, Decimal('1250.50'))
        self.assertEqual(despesa.criado_por, self.usuario)

    def test_usuario_autorizado_cadastra_credito_da_matriz(self):
        self.client.force_login(self.usuario)

        resposta = self.client.post(reverse('financeiro'), {
            'salvar_credito': '1',
            'valor': '475,90',
            'origem': 'Royalty do cliente cancelado',
        })

        self.assertRedirects(resposta, reverse('financeiro'))
        credito = CreditoMatriz.objects.get()
        self.assertEqual(credito.valor, Decimal('475.90'))
        self.assertEqual(credito.criado_por, self.usuario)
        self.assertFalse(credito.utilizado)

    def test_credito_utilizado_exige_identificacao_do_boleto(self):
        self.client.force_login(self.usuario)

        resposta = self.client.post(reverse('financeiro'), {
            'salvar_credito': '1',
            'valor': '100,00',
            'origem': 'Crédito anterior',
            'utilizado': 'on',
            'boleto_utilizado': '',
        })

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Informe em qual boleto')
        self.assertFalse(CreditoMatriz.objects.exists())

    def test_edita_credito_e_registra_boleto_utilizado(self):
        credito = CreditoMatriz.objects.create(
            valor=Decimal('200.00'),
            origem='Cliente antigo',
            criado_por=self.usuario,
        )
        self.client.force_login(self.usuario)

        pagina = self.client.get(reverse('financeiro'))
        self.assertContains(pagina, f'id="credito-inline-{credito.id}"')
        self.assertNotContains(pagina, '?editar_credito=')

        resposta = self.client.post(reverse('financeiro'), {
            'salvar_credito': '1',
            'credito_id': credito.id,
            'valor': '200,00',
            'origem': 'Cliente antigo',
            'utilizado': 'on',
            'boleto_utilizado': 'Boleto 12345',
        })

        self.assertRedirects(resposta, reverse('financeiro'))
        credito.refresh_from_db()
        self.assertTrue(credito.utilizado)
        self.assertEqual(credito.boleto_utilizado, 'Boleto 12345')

    def test_registra_e_baixa_cliente_protestado_na_propria_tabela(self):
        cliente = Cliente.objects.create(
            codigo='98765',
            nome_fantasia='Cliente Protestado',
            razao_social='Cliente Protestado Ltda.',
            cnpj='98.765.432/0001-10',
            proprietario='Responsável',
            telefone='11999999999',
        )
        self.client.force_login(self.usuario)
        resposta = self.client.post(reverse('financeiro'), {
            'salvar_protesto': '1',
            'cliente': cliente.id,
            'data_boleto': '2026-10-10',
            'valor': '850,00',
        })
        self.assertRedirects(resposta, reverse('financeiro'))
        protesto = ClienteProtestado.objects.get()
        self.assertFalse(protesto.pago)

        pagina = self.client.get(reverse('financeiro'))
        self.assertContains(pagina, f'id="protesto-inline-{protesto.id}"')

        resposta = self.client.post(reverse('financeiro'), {
            'salvar_protesto': '1',
            'protesto_id': protesto.id,
            'cliente': cliente.id,
            'data_boleto': '2026-10-10',
            'valor': '850,00',
            'pago': 'on',
            'data_pagamento': '2026-10-14',
        })
        self.assertRedirects(resposta, reverse('financeiro'))
        protesto.refresh_from_db()
        self.assertTrue(protesto.pago)
        self.assertEqual(protesto.data_pagamento, date(2026, 10, 14))

    def test_despesa_do_dia_aparece_no_popup_apenas_para_autorizado(self):
        despesa = DespesaFinanceira.objects.create(
            titulo='Internet',
            valor=Decimal('199.90'),
            dia_vencimento=date.today().day,
            criado_por=self.usuario,
        )
        self.client.force_login(self.usuario)

        resposta = self.client.get(reverse('dashboard'))

        self.assertContains(resposta, 'Financeiro hoje')
        self.assertContains(resposta, despesa.titulo)

        self.client.force_login(self.sem_permissao)
        resposta = self.client.get(reverse('dashboard'))
        self.assertNotContains(resposta, 'Financeiro hoje')
        self.assertNotContains(resposta, despesa.titulo)

    def test_usuario_confirma_pagamento_e_item_some_do_popup(self):
        despesa = DespesaFinanceira.objects.create(
            titulo='Pagamento confirmado',
            valor=Decimal('250.00'),
            dia_vencimento=date.today().day,
            criado_por=self.usuario,
        )
        self.client.force_login(self.usuario)
        painel = self.client.get(reverse('dashboard'))
        self.assertContains(painel, despesa.titulo)
        self.assertContains(
            painel,
            reverse('confirmar_despesa_popup', args=[despesa.id]),
        )

        resposta = self.client.post(
            reverse('confirmar_despesa_popup', args=[despesa.id]),
        )

        self.assertEqual(resposta.status_code, 200)
        confirmacao = ConfirmacaoDespesaFinanceira.objects.get()
        self.assertEqual(confirmacao.usuario, self.usuario)
        self.assertEqual(confirmacao.competencia, date.today().replace(day=1))
        painel = self.client.get(reverse('dashboard'))
        self.assertNotContains(painel, despesa.titulo)
        self.assertEqual(
            self.client.get(reverse('status_notificacoes')).json()['total'],
            0,
        )

    def test_confirmacao_e_individual_por_usuario(self):
        outro_autorizado = User.objects.create_user(
            'financeiro_outro',
            password='senha',
        )
        outro_autorizado.user_permissions.add(self.permissao)
        despesa = DespesaFinanceira.objects.create(
            titulo='Despesa compartilhada',
            valor=Decimal('90.00'),
            dia_vencimento=date.today().day,
            criado_por=self.usuario,
        )
        ConfirmacaoDespesaFinanceira.objects.create(
            despesa=despesa,
            usuario=self.usuario,
            competencia=date.today().replace(day=1),
        )

        self.client.force_login(outro_autorizado)
        painel = self.client.get(reverse('dashboard'))

        self.assertContains(painel, despesa.titulo)

    def test_usuario_sem_permissao_nao_confirma_pagamento(self):
        despesa = DespesaFinanceira.objects.create(
            titulo='Despesa protegida',
            valor=Decimal('50.00'),
            dia_vencimento=date.today().day,
            criado_por=self.usuario,
        )
        self.client.force_login(self.sem_permissao)

        resposta = self.client.post(
            reverse('confirmar_despesa_popup', args=[despesa.id]),
        )

        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(ConfirmacaoDespesaFinanceira.objects.exists())

    def test_vencimento_dia_31_ajusta_para_fim_de_mes_curto(self):
        despesa = DespesaFinanceira(
            titulo='Fechamento',
            valor=Decimal('10.00'),
            dia_vencimento=31,
        )

        vencimento = _data_vencimento_mensal(despesa, 2026, 2)

        self.assertEqual(vencimento, date(2026, 2, 28))


class PendenciasPlantaoTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            'usuario_plantao',
            password='senha',
        )
        self.tarefa = Task.objects.create(
            titulo='Pendência acolhida no plantão',
            responsavel=self.usuario,
            area='tickets',
            fase='tickets_abertos',
        )
        self.client.force_login(self.usuario)

    def test_coluna_aparece_no_kanban_de_tickets(self):
        resposta = self.client.get(reverse('tarefas'))

        self.assertContains(resposta, 'Pendências Plantão')

    def test_ticket_tecnico_pode_ser_movido_para_pendencias_plantao(self):
        resposta = self.client.post(
            reverse('mover_tarefa', args=[self.tarefa.id]),
            {'fase': 'pendencias_plantao'},
        )

        self.assertEqual(resposta.status_code, 200)
        self.tarefa.refresh_from_db()
        self.assertEqual(self.tarefa.fase, 'pendencias_plantao')
        self.assertEqual(resposta.json()['fase_nome'], 'Pendências Plantão')

    def test_popup_mostra_somente_ticket_aberto_na_coluna_plantao(self):
        self.tarefa.fase = 'pendencias_plantao'
        self.tarefa.save()

        dashboard = self.client.get(reverse('dashboard'))

        self.assertContains(dashboard, 'Plantão</h3>', html=False)
        self.assertContains(dashboard, self.tarefa.titulo)

        self.client.post(
            reverse('mover_tarefa', args=[self.tarefa.id]),
            {'fase': 'tarefas_internas'},
        )
        dashboard = self.client.get(reverse('dashboard'))
        self.assertNotContains(dashboard, self.tarefa.titulo)

        self.tarefa.fase = 'pendencias_plantao'
        self.tarefa.encerrada = True
        self.tarefa.save()
        dashboard = self.client.get(reverse('dashboard'))
        self.assertNotContains(dashboard, self.tarefa.titulo)

    def test_popup_nao_mostra_plantao_de_outro_usuario(self):
        outro = User.objects.create_user('outro_plantao', password='senha')
        Task.objects.create(
            titulo='Pendência de outro funcionário',
            responsavel=outro,
            area='tickets',
            fase='pendencias_plantao',
        )

        dashboard = self.client.get(reverse('dashboard'))

        self.assertNotContains(dashboard, 'Pendência de outro funcionário')

    def test_encerrar_ticket_tecnico_remove_de_todas_as_secoes_do_popup(self):
        self.tarefa.fase = 'pendencias_plantao'
        self.tarefa.prazo = date.today()
        self.tarefa.save()
        notificacao = Notificacao.objects.create(
            destinatario=self.usuario,
            ator=self.usuario,
            tarefa=self.tarefa,
            tipo='comentario',
            mensagem='Atualização do ticket técnico a encerrar.',
        )

        antes = self.client.get(reverse('dashboard'))
        self.assertContains(antes, self.tarefa.titulo)
        self.assertContains(antes, notificacao.mensagem)

        self.client.get(reverse('encerrar_tarefa', args=[self.tarefa.id]))
        depois = self.client.get(reverse('dashboard'))

        self.assertNotContains(depois, self.tarefa.titulo)
        self.assertNotContains(depois, notificacao.mensagem)
        notificacao.refresh_from_db()
        self.assertTrue(notificacao.lida)


class AtribuicaoNaCriacaoTests(TestCase):
    def setUp(self):
        self.criadora = User.objects.create_user('gabriela', password='senha')
        self.destinatario = User.objects.create_user('gabriel', password='senha')
        self.client.force_login(self.criadora)

    def dados_ticket(self, **extras):
        dados = {
            'area': 'tickets',
            'titulo': 'Tarefa criada por operadora',
            'descricao': '',
            'modulo': '',
            'fase': 'diversos',
            'status': 'pendente_netcamp',
            'prioridade': 'media',
            'prazo': '',
            'cliente': '',
        }
        dados.update(extras)
        return dados

    def test_operadora_pode_atribuir_novo_ticket_a_outro_usuario(self):
        formulario = self.client.get(reverse('criar_tarefa'))
        self.assertContains(formulario, 'gabriel')

        resposta = self.client.post(
            reverse('criar_tarefa'),
            self.dados_ticket(responsavel=self.destinatario.id),
        )

        self.assertRedirects(resposta, reverse('tarefas'))
        tarefa = Task.objects.get(titulo='Tarefa criada por operadora')
        self.assertEqual(tarefa.responsavel, self.destinatario)
        self.assertTrue(
            Notificacao.objects.filter(
                tarefa=tarefa,
                destinatario=self.destinatario,
                tipo='atribuicao',
            ).exists()
        )

    def test_operadora_sem_selecao_recebe_o_proprio_ticket(self):
        self.client.post(
            reverse('criar_tarefa'),
            self.dados_ticket(responsavel=''),
        )

        tarefa = Task.objects.get(titulo='Tarefa criada por operadora')
        self.assertEqual(tarefa.responsavel, self.criadora)

    def test_conta_inativa_nao_pode_ser_atribuida(self):
        inativo = User.objects.create_user(
            'usuario_inativo', password='senha', is_active=False,
        )

        resposta = self.client.post(
            reverse('criar_tarefa'),
            self.dados_ticket(responsavel=inativo.id),
        )

        self.assertEqual(resposta.status_code, 404)
        self.assertFalse(Task.objects.filter(titulo='Tarefa criada por operadora').exists())

    def test_busca_de_cliente_aceita_nome_parcial_unico(self):
        cliente = Cliente.objects.create(
            codigo='12345',
            nome_fantasia='Restaurante Sabor da Vila',
            razao_social='Sabor da Vila Alimentação Ltda.',
            cnpj='00.000.000/0001-00',
            proprietario='Responsável',
            telefone='11999999999',
        )
        formulario = self.client.get(reverse('criar_tarefa'))
        self.assertContains(formulario, 'id="listaClientes"')
        self.assertContains(formulario, 'class="cliente-opcao"')
        self.assertContains(formulario, cliente.nome_fantasia)

        resposta = self.client.post(
            reverse('criar_tarefa'),
            self.dados_ticket(cliente_busca='Sabor da Vila'),
        )

        self.assertRedirects(resposta, reverse('tarefas'))
        tarefa = Task.objects.get(titulo='Tarefa criada por operadora')
        self.assertEqual(tarefa.cliente, cliente)


class ModuloTicketTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            'usuario_modulo',
            password='senha',
        )
        self.client.force_login(self.usuario)

    def test_lista_de_modulos_espelha_erros_conhecidos(self):
        self.assertEqual(Task.MODULOS[1:], ErroConhecido.MODULOS)
        self.assertEqual(Task.MODULOS[0], ('', 'Sem Módulo Definido'))
        self.assertIn(('xtag', 'Xtag'), Task.MODULOS)
        self.assertIn(('concentrador', 'Concentrador'), Task.MODULOS)
        self.assertIn(('nfe', 'NFe'), Task.MODULOS)
        self.assertIn(
            ('solicitacao_geral_cliente', 'Solicitação Geral de Cliente'),
            Task.MODULOS,
        )

    def test_criacao_e_edicao_persistem_modulo(self):
        resposta = self.client.post(reverse('criar_tarefa'), {
            'area': 'tickets',
            'titulo': 'Ticket com módulo',
            'descricao': '',
            'modulo': 'pdv_pos',
            'fase': 'diversos',
            'status': 'pendente_netcamp',
            'prioridade': 'media',
            'prazo': '',
            'cliente': '',
        })

        self.assertRedirects(resposta, reverse('tarefas'))
        tarefa = Task.objects.get(titulo='Ticket com módulo')
        self.assertEqual(tarefa.modulo, 'pdv_pos')

        self.client.post(reverse('detalhes_tarefa', args=[tarefa.id]), {
            'editar_ticket': '1',
            'titulo': tarefa.titulo,
            'descricao': tarefa.descricao,
            'modulo': 'portal',
            'fase': tarefa.fase,
            'status': tarefa.status,
            'prioridade': tarefa.prioridade,
            'prazo': '',
            'cliente': '',
        })

        tarefa.refresh_from_db()
        self.assertEqual(tarefa.modulo, 'portal')

    def test_detalhes_exibem_texto_quando_modulo_nao_foi_definido(self):
        tarefa = Task.objects.create(
            titulo='Ticket sem módulo',
            responsavel=self.usuario,
        )

        resposta = self.client.get(
            reverse('detalhes_tarefa', args=[tarefa.id]),
        )

        self.assertContains(resposta, 'Sem Módulo Definido')


class ChecklistComercialTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            'usuario_comercial',
            password='senha',
        )
        self.client.force_login(self.usuario)

    def test_todas_as_fases_comerciais_recebem_checklist_padrao(self):
        for fase, _ in Task.FASES_COMERCIAL:
            with self.subTest(fase=fase):
                resposta = self.client.post(reverse('criar_tarefa'), {
                    'area': 'comercial',
                    'titulo': f'Comercial {fase}',
                    'descricao': '',
                    'fase': fase,
                    'status': 'pendente_netcamp',
                    'prioridade': 'media',
                    'prazo': '',
                    'cliente': '',
                })

                self.assertRedirects(resposta, reverse('comercial'))
                tarefa = Task.objects.get(titulo=f'Comercial {fase}')
                self.assertEqual(tarefa.checklists.count(), 10)


class RotinaTests(TestCase):
    def setUp(self):
        self.gerente = User.objects.create_user('gerente_rotina', password='senha')
        self.funcionario = User.objects.create_user('funcionario_rotina', password='senha')
        self.outro = User.objects.create_user('outro_rotina', password='senha')
        self.gerente.user_permissions.add(
            Permission.objects.get(codename='gerenciar_rotinas')
        )

    def test_gerente_cria_rotina_para_funcionario(self):
        self.client.force_login(self.gerente)

        resposta = self.client.post(reverse('rotina'), {
            'salvar_rotina': '1',
            'titulo': 'Conferir painel',
            'responsavel': self.funcionario.id,
            'periodicidade': 'diaria',
            'dia_mes': '',
            'descricao': 'Verificar pendências.',
        })

        self.assertRedirects(resposta, reverse('rotina'))
        item = Rotina.objects.get()
        self.assertEqual(item.responsavel, self.funcionario)
        self.assertEqual(item.criado_por, self.gerente)

    def test_rotina_diaria_aparece_no_popup_e_some_apos_check(self):
        item = Rotina.objects.create(
            titulo='Abrir operação',
            responsavel=self.funcionario,
            periodicidade='diaria',
            criado_por=self.gerente,
        )
        self.client.force_login(self.funcionario)

        dashboard = self.client.get(reverse('dashboard'))
        self.assertContains(dashboard, 'Rotina pendente')
        self.assertContains(dashboard, item.titulo)

        resposta = self.client.post(
            reverse('concluir_rotina', args=[item.id]),
            {'next': reverse('dashboard')},
        )
        self.assertRedirects(resposta, reverse('dashboard'))
        self.assertTrue(
            RotinaConclusao.objects.filter(
                rotina=item,
                periodo_referencia=date.today(),
            ).exists()
        )

        dashboard = self.client.get(reverse('dashboard'))
        self.assertNotContains(dashboard, item.titulo)

    def test_usuario_nao_conclui_rotina_de_outro(self):
        item = Rotina.objects.create(
            titulo='Rotina protegida',
            responsavel=self.funcionario,
            periodicidade='diaria',
            criado_por=self.gerente,
        )
        self.client.force_login(self.outro)

        resposta = self.client.post(reverse('concluir_rotina', args=[item.id]))

        self.assertEqual(resposta.status_code, 404)
        self.assertFalse(RotinaConclusao.objects.exists())

    def test_regras_de_disponibilidade_semanal_e_mensal(self):
        semanal = Rotina(
            titulo='Resumo semanal',
            responsavel=self.funcionario,
            periodicidade='semanal',
        )
        mensal = Rotina(
            titulo='Fechamento mensal',
            responsavel=self.funcionario,
            periodicidade='mensal',
            dia_mes=15,
        )

        self.assertEqual(
            periodo_referencia(semanal, date(2026, 7, 23)),
            date(2026, 7, 20),
        )
        self.assertIsNone(periodo_referencia(mensal, date(2026, 7, 14)))
        self.assertEqual(
            periodo_referencia(mensal, date(2026, 7, 15)),
            date(2026, 7, 15),
        )

    def test_conclusao_remove_apenas_periodo_atual(self):
        item = Rotina.objects.create(
            titulo='Rotina diária',
            responsavel=self.funcionario,
            periodicidade='diaria',
            criado_por=self.gerente,
        )
        ontem = date.today() - timedelta(days=1)
        RotinaConclusao.objects.create(
            rotina=item,
            concluido_por=self.funcionario,
            periodo_referencia=ontem,
        )

        pendentes = rotinas_pendentes_usuario(self.funcionario)

        self.assertEqual(pendentes, [item])


class SugestoesDesenvolvimentoTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.usuario = User.objects.create_user(
            'usuario_sugestao',
            password='senha',
        )
        self.cliente_cadastrado = Cliente.objects.create(
            codigo='90001',
            nome_fantasia='Cliente da Sugestão',
            razao_social='Cliente da Sugestão Ltda.',
            cnpj='90.001.000/0001-00',
            proprietario='Responsável',
            telefone='(11) 99999-9999',
        )
        self.sugestao = SugestaoDesenvolvimento.objects.create(
            titulo='Novo relatório gerencial',
            modulo='portal',
            cliente=self.cliente_cadastrado,
            descricao='Criar visão consolidada para os gestores.',
            criado_por=self.usuario,
        )
        self.client.force_login(self.usuario)

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_lista_pesquisa_e_abre_sugestao(self):
        lista = self.client.get(
            reverse('sugestoes_desenvolvimento'),
            {'busca': 'Cliente da Sugestão'},
        )
        detalhes = self.client.get(
            reverse('detalhes_sugestao_desenvolvimento', args=[self.sugestao.id]),
        )

        self.assertContains(lista, 'Novo relatório gerencial')
        self.assertContains(detalhes, 'Criar visão consolidada')
        self.assertContains(detalhes, 'Portal')

    def test_cria_e_edita_sugestao(self):
        resposta = self.client.post(
            reverse('criar_sugestao_desenvolvimento'),
            {
                'titulo': 'Melhoria no PDV',
                'modulo': 'pdv',
                'cliente': self.cliente_cadastrado.id,
                'descricao': 'Adicionar um novo atalho operacional.',
            },
        )
        criada = SugestaoDesenvolvimento.objects.get(titulo='Melhoria no PDV')
        self.assertRedirects(
            resposta,
            reverse('detalhes_sugestao_desenvolvimento', args=[criada.id]),
        )
        self.assertEqual(criada.criado_por, self.usuario)

        self.client.post(
            reverse('editar_sugestao_desenvolvimento', args=[criada.id]),
            {
                'titulo': 'Melhoria atualizada no PDV',
                'modulo': 'pdv_pos',
                'cliente': '',
                'descricao': 'Descrição atualizada.',
            },
        )
        criada.refresh_from_db()
        self.assertEqual(criada.modulo, 'pdv_pos')
        self.assertIsNone(criada.cliente)

    def test_envia_baixa_e_remove_anexo(self):
        self.client.post(
            reverse('detalhes_sugestao_desenvolvimento', args=[self.sugestao.id]),
            {
                'enviar_anexo': '1',
                'arquivo': SimpleUploadedFile('referencia.pdf', b'%PDF referencia'),
            },
        )
        anexo = AnexoSugestaoDesenvolvimento.objects.get(sugestao=self.sugestao)
        storage = anexo.arquivo.storage
        nome_arquivo = anexo.arquivo.name

        download = self.client.get(
            reverse('baixar_anexo_sugestao_desenvolvimento', args=[anexo.id]),
        )
        self.assertEqual(download.status_code, 200)
        b''.join(download.streaming_content)
        download.close()

        self.client.post(
            reverse('remover_anexo_sugestao_desenvolvimento', args=[anexo.id]),
        )
        self.assertFalse(
            AnexoSugestaoDesenvolvimento.objects.filter(id=anexo.id).exists()
        )
        self.assertFalse(storage.exists(nome_arquivo))

    def test_bloqueia_anexo_executavel(self):
        self.client.post(
            reverse('detalhes_sugestao_desenvolvimento', args=[self.sugestao.id]),
            {
                'enviar_anexo': '1',
                'arquivo': SimpleUploadedFile('programa.exe', b'MZ'),
            },
        )

        self.assertFalse(AnexoSugestaoDesenvolvimento.objects.exists())


class ProcedimentosInternosTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.usuario = User.objects.create_user(
            'usuario_procedimento',
            password='senha',
        )
        self.procedimento = ProcedimentoInterno.objects.create(
            titulo='Instalação do PDV',
            conteudo='Primeiro configure o servidor. Depois instale o PDV.',
            criado_por=self.usuario,
        )
        self.client.force_login(self.usuario)

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_lista_pesquisa_e_abre_procedimento(self):
        lista = self.client.get(
            reverse('procedimentos_internos'),
            {'busca': 'configure o servidor'},
        )
        detalhes = self.client.get(
            reverse('detalhes_procedimento', args=[self.procedimento.id]),
        )

        self.assertContains(lista, 'Instalação do PDV')
        self.assertContains(detalhes, 'Primeiro configure o servidor.')

    def test_usuario_cria_e_edita_procedimento(self):
        resposta = self.client.post(reverse('criar_procedimento'), {
            'titulo': 'Instalação do concentrador',
            'conteudo': 'Executar a instalação completa.',
        })
        criado = ProcedimentoInterno.objects.get(
            titulo='Instalação do concentrador',
        )
        self.assertRedirects(
            resposta,
            reverse('detalhes_procedimento', args=[criado.id]),
        )
        self.assertEqual(criado.criado_por, self.usuario)

        self.client.post(
            reverse('editar_procedimento', args=[criado.id]),
            {
                'titulo': 'Instalação atualizada do concentrador',
                'conteudo': 'Novo passo a passo.',
            },
        )
        criado.refresh_from_db()
        self.assertEqual(criado.titulo, 'Instalação atualizada do concentrador')
        self.assertEqual(criado.conteudo, 'Novo passo a passo.')

    def test_envia_baixa_e_remove_anexo(self):
        resposta = self.client.post(
            reverse('detalhes_procedimento', args=[self.procedimento.id]),
            {
                'enviar_anexo': '1',
                'arquivo': SimpleUploadedFile(
                    'manual.pdf',
                    b'%PDF-1.4 manual interno',
                    content_type='application/pdf',
                ),
            },
        )
        self.assertRedirects(
            resposta,
            reverse('detalhes_procedimento', args=[self.procedimento.id]),
        )
        anexo = AnexoProcedimento.objects.get(procedimento=self.procedimento)
        storage = anexo.arquivo.storage
        nome_arquivo = anexo.arquivo.name
        self.assertTrue(storage.exists(nome_arquivo))

        download = self.client.get(
            reverse('baixar_anexo_procedimento', args=[anexo.id]),
        )
        self.assertEqual(download.status_code, 200)
        self.assertIn('attachment;', download['Content-Disposition'])
        b''.join(download.streaming_content)
        download.close()

        self.client.post(
            reverse('remover_anexo_procedimento', args=[anexo.id]),
        )
        self.assertFalse(AnexoProcedimento.objects.filter(id=anexo.id).exists())
        self.assertFalse(storage.exists(nome_arquivo))

    def test_bloqueia_arquivo_executavel(self):
        self.client.post(
            reverse('detalhes_procedimento', args=[self.procedimento.id]),
            {
                'enviar_anexo': '1',
                'arquivo': SimpleUploadedFile('programa.exe', b'MZ'),
            },
        )

        self.assertFalse(AnexoProcedimento.objects.exists())


class AnexoTicketTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.admin = User.objects.create_superuser(
            'admin_anexo',
            'admin.anexo@example.com',
            'senha',
        )
        self.operador = User.objects.create_user('responsavel_anexo', password='senha')
        self.outro = User.objects.create_user('outro_anexo', password='senha')
        self.tarefa = Task.objects.create(
            titulo='Ticket com anexo',
            responsavel=self.operador,
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_responsavel_pode_enviar_e_baixar_anexo(self):
        self.client.force_login(self.operador)
        resposta = self.client.post(
            reverse('detalhes_tarefa', args=[self.tarefa.id]),
            {
                'enviar_anexo': '1',
                'arquivo': SimpleUploadedFile(
                    'manual.pdf',
                    b'%PDF-1.4 conteudo de teste',
                    content_type='application/pdf',
                ),
            },
        )

        self.assertRedirects(resposta, reverse('detalhes_tarefa', args=[self.tarefa.id]))
        anexo = AnexoTicket.objects.get(tarefa=self.tarefa)
        self.assertEqual(anexo.nome_original, 'manual.pdf')
        download = self.client.get(reverse('baixar_anexo_ticket', args=[anexo.id]))
        self.assertEqual(download.status_code, 200)
        self.assertIn('attachment;', download['Content-Disposition'])

    def test_usuario_que_nao_e_responsavel_nao_pode_enviar(self):
        self.client.force_login(self.outro)
        self.client.post(
            reverse('detalhes_tarefa', args=[self.tarefa.id]),
            {
                'enviar_anexo': '1',
                'arquivo': SimpleUploadedFile('nota.txt', b'teste'),
            },
        )

        self.assertFalse(AnexoTicket.objects.exists())

    def test_arquivo_executavel_e_bloqueado(self):
        self.client.force_login(self.operador)
        self.client.post(
            reverse('detalhes_tarefa', args=[self.tarefa.id]),
            {
                'enviar_anexo': '1',
                'arquivo': SimpleUploadedFile('programa.exe', b'MZ'),
            },
        )

        self.assertFalse(AnexoTicket.objects.exists())

    def test_responsavel_remove_registro_e_arquivo_fisico(self):
        anexo = AnexoTicket.objects.create(
            tarefa=self.tarefa,
            arquivo=SimpleUploadedFile('remover.txt', b'conteudo'),
            nome_original='remover.txt',
            tamanho=8,
            enviado_por=self.operador,
        )
        storage = anexo.arquivo.storage
        nome_arquivo = anexo.arquivo.name
        self.assertTrue(storage.exists(nome_arquivo))
        self.client.force_login(self.operador)

        resposta = self.client.post(
            reverse('remover_anexo_ticket', args=[anexo.id]),
        )

        self.assertRedirects(
            resposta,
            reverse('detalhes_tarefa', args=[self.tarefa.id]),
        )
        self.assertFalse(AnexoTicket.objects.filter(id=anexo.id).exists())
        self.assertFalse(storage.exists(nome_arquivo))

    def test_usuario_sem_permissao_nao_remove_anexo(self):
        anexo = AnexoTicket.objects.create(
            tarefa=self.tarefa,
            arquivo=SimpleUploadedFile('protegido.txt', b'conteudo'),
            nome_original='protegido.txt',
            tamanho=8,
            enviado_por=self.operador,
        )
        self.client.force_login(self.outro)

        self.client.post(reverse('remover_anexo_ticket', args=[anexo.id]))

        self.assertTrue(AnexoTicket.objects.filter(id=anexo.id).exists())


class AnexoErroConhecidoTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.usuario = User.objects.create_user(
            'usuario_anexo_erro',
            password='senha',
        )
        self.erro = ErroConhecido.objects.create(
            palavra_chave='Erro com evidência',
            modulo='pdv',
            descricao='Descrição do erro.',
            versao_observada='1.0',
            ticket_netcontroll='NC-456',
        )
        self.client.force_login(self.usuario)

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_envia_baixa_e_remove_anexo(self):
        resposta = self.client.post(
            reverse('detalhes_erro_conhecido', args=[self.erro.id]),
            {
                'enviar_anexo': '1',
                'arquivo': SimpleUploadedFile(
                    'evidencia.pdf',
                    b'%PDF-1.4 evidencia',
                    content_type='application/pdf',
                ),
            },
        )
        self.assertRedirects(
            resposta,
            reverse('detalhes_erro_conhecido', args=[self.erro.id]),
        )
        anexo = AnexoErroConhecido.objects.get(erro=self.erro)
        storage = anexo.arquivo.storage
        nome_arquivo = anexo.arquivo.name

        download = self.client.get(
            reverse('baixar_anexo_erro_conhecido', args=[anexo.id]),
        )
        self.assertEqual(download.status_code, 200)
        self.assertIn('attachment;', download['Content-Disposition'])
        b''.join(download.streaming_content)
        download.close()

        self.client.post(
            reverse('remover_anexo_erro_conhecido', args=[anexo.id]),
        )
        self.assertFalse(AnexoErroConhecido.objects.filter(id=anexo.id).exists())
        self.assertFalse(storage.exists(nome_arquivo))

    def test_bloqueia_anexo_executavel(self):
        self.client.post(
            reverse('detalhes_erro_conhecido', args=[self.erro.id]),
            {
                'enviar_anexo': '1',
                'arquivo': SimpleUploadedFile('programa.exe', b'MZ'),
            },
        )

        self.assertFalse(AnexoErroConhecido.objects.exists())


class ErroConhecidoCorrecaoTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            'usuario_erros',
            password='senha',
        )
        self.cliente_cadastrado = Cliente.objects.create(
            codigo='00001',
            nome_fantasia='Cliente Teste',
            razao_social='Cliente Teste Ltda.',
            cnpj='00.000.000/0001-00',
            proprietario='Responsável',
            telefone='(11) 99999-9999',
        )
        self.erro = ErroConhecido.objects.create(
            palavra_chave='Falha na emissão',
            modulo='nfce',
            descricao='Documento não é emitido.',
            versao_observada='1.0',
            ticket_netcontroll='NC-123',
        )
        self.erro.clientes.add(self.cliente_cadastrado)

    def test_edicao_adiciona_flag_e_medida_corretiva(self):
        self.client.force_login(self.usuario)

        resposta = self.client.post(
            reverse('editar_erro_conhecido', args=[self.erro.id]),
            {
                'palavra_chave': self.erro.palavra_chave,
                'modulo': self.erro.modulo,
                'descricao': self.erro.descricao,
                'corrigido': 'on',
                'medida_corretiva': 'Reiniciar o concentrador e reenviar.',
                'versao_observada': self.erro.versao_observada,
                'clientes': [self.cliente_cadastrado.id],
                'ticket_netcontroll': self.erro.ticket_netcontroll,
            },
        )

        self.assertRedirects(
            resposta,
            reverse('detalhes_erro_conhecido', args=[self.erro.id]),
        )
        self.erro.refresh_from_db()
        self.assertTrue(self.erro.corrigido)
        self.assertEqual(
            self.erro.medida_corretiva,
            'Reiniciar o concentrador e reenviar.',
        )

        detalhes = self.client.get(
            reverse('detalhes_erro_conhecido', args=[self.erro.id]),
        )
        self.assertContains(detalhes, 'Corrigido: Sim')
        self.assertContains(detalhes, 'Reiniciar o concentrador e reenviar.')

    def test_medida_corretiva_participa_da_busca(self):
        self.erro.medida_corretiva = 'Procedimento exclusivo concentrador'
        self.erro.save()
        self.client.force_login(self.usuario)

        resposta = self.client.get(
            reverse('erros_conhecidos'),
            {'busca': 'exclusivo concentrador'},
        )

        self.assertContains(resposta, self.erro.palavra_chave)


class GerarTicketImplantacaoTests(TestCase):
    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        self.operador = User.objects.create_user(
            'comercial_implantacao',
            password='senha',
        )
        self.tecnico = User.objects.create_user('tecnico_implantacao', password='senha')
        self.financeiro = User.objects.create_user('financeiro_implantacao', password='senha')
        self.fiscal = User.objects.create_user('fiscal_implantacao', password='senha')
        self.cliente = Cliente.objects.create(
            codigo='54321', nome_fantasia='Cliente da implantação',
            razao_social='Cliente da Implantação Ltda.',
            cnpj='00.000.000/0001-00', proprietario='Responsável',
            telefone='(11) 99999-9999',
        )
        self.comercial = Task.objects.create(
            titulo='Nova implantação',
            descricao='Dados da venda',
            modulo='nfce',
            area='comercial',
            fase='aprovado_aguardando_implantacao',
            responsavel=self.operador,
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def test_comentarios_e_anexos_sao_copiados_para_ticket_tecnico(self):
        comentario = Comment.objects.create(
            task=self.comercial,
            autor=self.operador,
            texto='Cliente enviou os dados necessários.',
        )
        anexo = AnexoTicket.objects.create(
            tarefa=self.comercial,
            arquivo=SimpleUploadedFile('contrato.pdf', b'conteudo do contrato'),
            nome_original='contrato.pdf',
            tamanho=20,
            enviado_por=self.operador,
        )
        self.client.force_login(self.operador)

        resposta = self.client.post(
            reverse('gerar_ticket_implantacao', args=[self.comercial.id]),
            {
                'cliente_id': self.cliente.id,
                'responsavel_tecnico': self.tecnico.id,
                'responsavel_cobranca': self.financeiro.id,
                'responsavel_fiscal': self.fiscal.id,
                'valor_mensalidade': '299,90',
                'valor_implantacao': '500,00',
                'data_primeira_cobranca': '2026-10-10',
                'previsao_implantacao': '2026-10-15',
                'detalhes_implantacao': 'Instalar os módulos contratados.',
            },
        )

        implantacao = Task.objects.get(origem_comercial=self.comercial)
        self.assertEqual(implantacao.modulo, 'nfce')
        self.assertEqual(implantacao.responsavel, self.tecnico)
        self.assertEqual(implantacao.cliente, self.cliente)
        self.assertIn(self.operador, implantacao.participantes.all())
        self.assertRedirects(
            resposta,
            reverse('detalhes_tarefa', args=[implantacao.id]),
        )
        comentario_copiado = implantacao.comentarios.get()
        self.assertEqual(comentario_copiado.texto, comentario.texto)
        self.assertEqual(comentario_copiado.autor, comentario.autor)
        self.assertEqual(comentario_copiado.criado_em, comentario.criado_em)

        anexo_copiado = implantacao.anexos.get()
        self.assertEqual(anexo_copiado.nome_original, anexo.nome_original)
        self.assertEqual(anexo_copiado.enviado_por, anexo.enviado_por)
        self.assertEqual(anexo_copiado.criado_em, anexo.criado_em)
        self.assertNotEqual(anexo_copiado.arquivo.name, anexo.arquivo.name)
        with anexo_copiado.arquivo.open('rb') as arquivo:
            self.assertEqual(arquivo.read(), b'conteudo do contrato')

        cobranca = self.comercial.tarefas_disparadas.get(tipo_disparo='cobranca')
        self.assertEqual(cobranca.fase, 'novas_cobrancas')
        self.assertEqual(cobranca.responsavel, self.financeiro)
        self.assertEqual(cobranca.valor_mensalidade, Decimal('299.90'))
        self.assertEqual(cobranca.valor_implantacao, Decimal('500.00'))
        self.assertTrue(cobranca.checklists.filter(descricao__icontains='implantação').exists())

        planilha = self.comercial.tarefas_disparadas.get(tipo_disparo='planilha_fiscal')
        self.assertEqual(planilha.fase, 'planilha_fiscal')
        self.assertEqual(planilha.responsavel, self.fiscal)
        self.assertEqual(planilha.checklists.count(), 4)

    def test_disparo_incompleto_nao_cria_tarefas_parciais(self):
        self.client.force_login(self.operador)

        resposta = self.client.post(
            reverse('gerar_ticket_implantacao', args=[self.comercial.id]),
            {'cliente_id': self.cliente.id},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(self.comercial.tarefas_disparadas.exists())
        self.assertFalse(hasattr(self.comercial, 'ticket_implantacao'))

    def test_disparo_permite_cadastrar_cliente_no_fluxo(self):
        self.client.force_login(self.operador)

        resposta = self.client.post(
            reverse('gerar_ticket_implantacao', args=[self.comercial.id]),
            {
                'novo_cliente': '1',
                'cliente-codigo': '98765',
                'cliente-nome_fantasia': 'Novo cliente disparado',
                'cliente-razao_social': 'Novo Cliente Disparado Ltda.',
                'cliente-cnpj': '11.111.111/0001-11',
                'cliente-proprietario': 'Novo responsável',
                'cliente-telefone': '(11) 98888-7777',
                'cliente-observacoes': '',
                'responsavel_tecnico': self.tecnico.id,
                'responsavel_cobranca': self.financeiro.id,
                'responsavel_fiscal': self.fiscal.id,
                'valor_mensalidade': '150,00',
                'valor_implantacao': '',
                'data_primeira_cobranca': '2026-10-20',
                'previsao_implantacao': '2026-10-22',
            },
        )

        novo_cliente = Cliente.objects.get(codigo='98765')
        implantacao = Task.objects.get(origem_comercial=self.comercial)
        self.assertRedirects(resposta, reverse('detalhes_tarefa', args=[implantacao.id]))
        self.assertEqual(implantacao.cliente, novo_cliente)
        cobranca = self.comercial.tarefas_disparadas.get(tipo_disparo='cobranca')
        self.assertIsNone(cobranca.valor_implantacao)


class TarefasRelacionadasTests(TestCase):
    def setUp(self):
        self.tecnico = User.objects.create_user('tecnico_relacionada', password='senha')
        self.financeiro = User.objects.create_user('financeiro_relacionada', password='senha')
        self.cliente = Cliente.objects.create(
            codigo='11223', nome_fantasia='Cliente Licenças',
            razao_social='Cliente Licenças Ltda.', cnpj='22.222.222/0001-22',
            proprietario='Responsável', telefone='11999999999',
        )
        self.ticket = Task.objects.create(
            titulo='Alteração de licenças', area='tickets',
            fase='tickets_abertos', responsavel=self.tecnico,
            cliente=self.cliente, prazo=date.today(),
        )
        self.client.force_login(self.tecnico)

    def test_cobranca_relacionada_bloqueia_ticket_e_aparece_no_popup(self):
        resposta = self.client.post(
            reverse('criar_tarefa_relacionada', args=[self.ticket.id]),
            {
                'tipo': 'cobranca',
                'titulo': 'Atualizar boleto das novas licenças',
                'responsavel': self.financeiro.id,
                'prazo': date.today().isoformat(),
                'prioridade': 'alta',
                'descricao': 'Cobrar as licenças adicionadas.',
                'valor_mensalidade': '450,00',
                'valor_mensal_anterior': '300,00',
                'valor_implantacao': '100,00',
                'data_primeira_cobranca': date.today().isoformat(),
                'motivo_alteracao': 'Aquisição de novas licenças',
                'bloqueia_encerramento': '1',
            },
        )

        self.assertRedirects(resposta, reverse('detalhes_tarefa', args=[self.ticket.id]))
        cobranca = self.ticket.tarefas_disparadas.get(tipo_disparo='cobranca')
        self.assertEqual(cobranca.area, 'relacionada')
        self.assertEqual(cobranca.responsavel, self.financeiro)
        self.assertEqual(cobranca.valor_mensalidade, Decimal('450.00'))
        self.assertTrue(cobranca.bloqueia_encerramento)

        bloqueio = self.client.get(reverse('encerrar_tarefa', args=[self.ticket.id]))
        self.assertRedirects(bloqueio, reverse('detalhes_tarefa', args=[self.ticket.id]))
        self.ticket.refresh_from_db()
        self.assertFalse(self.ticket.encerrada)

        self.client.force_login(self.financeiro)
        painel = self.client.get(reverse('dashboard'))
        self.assertContains(painel, cobranca.titulo)
        conclusao = self.client.get(reverse('encerrar_tarefa', args=[cobranca.id]))
        self.assertRedirects(conclusao, reverse('detalhes_tarefa', args=[self.ticket.id]))
        cobranca.refresh_from_db()
        self.assertTrue(cobranca.encerrada)

        self.client.force_login(self.tecnico)
        self.client.get(reverse('encerrar_tarefa', args=[self.ticket.id]))
        self.ticket.refresh_from_db()
        self.assertTrue(self.ticket.encerrada)


class AreaGabrielTests(TestCase):
    def setUp(self):
        self.gabriel = User.objects.create_superuser(
            'gabriel.porfirio',
            password='senha-segura',
        )
        self.outro = User.objects.create_superuser('outro.admin', password='senha')

    def test_somente_usuario_gabriel_porfirio_pode_acessar(self):
        self.client.force_login(self.outro)
        resposta = self.client.get(reverse('area_gabriel'))
        self.assertEqual(resposta.status_code, 403)

    def test_area_cadastra_pin_e_desbloqueia_por_duas_horas(self):
        self.client.force_login(self.gabriel)
        bloqueada = self.client.get(reverse('area_gabriel'))
        self.assertContains(bloqueada, 'Cadastrar PIN')

        resposta = self.client.post(reverse('area_gabriel'), {
            'cadastrar_pin': '1',
            'senha_atual': 'senha-segura',
            'pin': '4826',
            'confirmar_pin': '4826',
        })
        self.assertRedirects(resposta, reverse('area_gabriel'))
        configuracao = AcessoAreaGabriel.objects.get(usuario=self.gabriel)
        self.assertNotEqual(configuracao.pin_hash, '4826')
        self.assertGreater(
            self.client.session['area_gabriel_pin_ate'],
            timezone.now().timestamp() + 7100,
        )
        liberada = self.client.get(reverse('area_gabriel'))
        self.assertContains(liberada, 'Minha organização')

        sessao = self.client.session
        sessao['area_gabriel_pin_ate'] = 0
        sessao.save()
        resposta_pin = self.client.post(reverse('area_gabriel'), {
            'desbloquear_area': '1',
            'pin': '4826',
        })
        self.assertRedirects(resposta_pin, reverse('area_gabriel'))

    def test_pin_pode_ser_alterado_e_redefinido_com_a_senha(self):
        configuracao = AcessoAreaGabriel.objects.create(
            usuario=self.gabriel,
            pin_hash=make_password('1111'),
        )
        self.client.force_login(self.gabriel)
        sessao = self.client.session
        sessao['area_gabriel_pin_ate'] = timezone.now().timestamp() + 7200
        sessao.save()

        resposta = self.client.post(reverse('area_gabriel'), {
            'alterar_pin': '1',
            'pin_atual': '1111',
            'novo_pin': '2222',
            'confirmar_pin': '2222',
        })
        self.assertRedirects(resposta, reverse('area_gabriel'))
        configuracao.refresh_from_db()
        self.assertTrue(check_password('2222', configuracao.pin_hash))

        sessao = self.client.session
        sessao['area_gabriel_pin_ate'] = 0
        sessao.save()
        resposta = self.client.post(reverse('area_gabriel'), {
            'redefinir_pin': '1',
            'senha_atual': 'senha-segura',
            'novo_pin': '3333',
            'confirmar_pin': '3333',
        })
        self.assertRedirects(resposta, reverse('area_gabriel'))
        configuracao.refresh_from_db()
        self.assertTrue(check_password('3333', configuracao.pin_hash))

    def test_checklist_ordena_por_prioridade_e_permite_alterar(self):
        baixa = TarefaPessoal.objects.create(
            titulo='Tarefa baixa', area='gabriel',
            data_conclusao=date.today(), prioridade='baixa',
        )
        media = TarefaPessoal.objects.create(
            titulo='Tarefa média', area='gabriel',
            data_conclusao=date.today(), prioridade='media',
        )
        alta = TarefaPessoal.objects.create(
            titulo='Tarefa alta', area='gabriel',
            data_conclusao=date.today(), prioridade='alta',
        )
        self.client.force_login(self.gabriel)
        sessao = self.client.session
        sessao['area_gabriel_pin_ate'] = timezone.now().timestamp() + 7200
        sessao.save()

        pagina = self.client.get(reverse('area_gabriel'))
        self.assertEqual(
            list(pagina.context['tarefas_gabriel']),
            [alta, media, baixa],
        )

        self.client.post(
            reverse('alterar_prioridade_tarefa_pessoal', args=[baixa.id]),
            {'prioridade': 'alta'},
        )
        baixa.refresh_from_db()
        self.assertEqual(baixa.prioridade, 'alta')

    def test_tarefa_sem_data_recebe_prazo_de_tres_dias(self):
        self.client.force_login(self.gabriel)
        sessao = self.client.session
        sessao['area_gabriel_pin_ate'] = timezone.now().timestamp() + 7200
        sessao.save()

        resposta = self.client.post(reverse('area_gabriel'), {
            'criar_tarefa_pessoal': '1',
            'titulo': 'Tarefa sem data informada',
            'area': 'gabriel',
            'prioridade': 'alta',
            'data_conclusao': '',
        })

        self.assertRedirects(resposta, reverse('area_gabriel'))
        tarefa = TarefaPessoal.objects.get(titulo='Tarefa sem data informada')
        self.assertEqual(tarefa.data_conclusao, date.today() + timedelta(days=3))

    def test_kanban_exibe_somente_ticket_tecnico_atribuido_ao_gabriel(self):
        ticket_gabriel = Task.objects.create(
            titulo='Ticket técnico do Gabriel',
            area='tickets',
            responsavel=self.gabriel,
        )
        Task.objects.create(
            titulo='Ticket técnico de outro usuário',
            area='tickets',
            responsavel=self.outro,
        )
        Task.objects.create(
            titulo='Tarefa comercial do Gabriel',
            area='comercial',
            responsavel=self.gabriel,
        )
        self.client.force_login(self.gabriel)
        sessao = self.client.session
        sessao['area_gabriel_pin_ate'] = timezone.now().timestamp() + 7200
        sessao.save()

        resposta = self.client.get(reverse('area_gabriel'))

        self.assertContains(resposta, ticket_gabriel.titulo)
        self.assertNotContains(resposta, 'Ticket técnico de outro usuário')
        self.assertNotContains(resposta, 'Tarefa comercial do Gabriel')

    def test_coluna_netcamp_tambem_possui_checklist_simples(self):
        self.client.force_login(self.gabriel)
        sessao = self.client.session
        sessao['area_gabriel_pin_ate'] = timezone.now().timestamp() + 7200
        sessao.save()

        resposta = self.client.post(reverse('area_gabriel'), {
            'criar_tarefa_pessoal': '1',
            'titulo': 'Conferir equipamento da NetCamp',
            'area': 'netcamp',
            'prioridade': 'alta',
            'data_conclusao': date.today().isoformat(),
        })

        self.assertRedirects(resposta, reverse('area_gabriel'))
        tarefa = TarefaPessoal.objects.get(titulo='Conferir equipamento da NetCamp')
        self.assertEqual(tarefa.area, 'netcamp')
        pagina = self.client.get(reverse('area_gabriel'))
        self.assertIn(tarefa, pagina.context['tarefas_netcamp'])
        self.assertContains(pagina, 'Tarefas rápidas NetCamp')

        painel = self.client.get(reverse('dashboard'))
        self.assertContains(painel, tarefa.titulo)

    def test_lembrete_vencido_aparece_no_popup_e_pode_ser_concluido(self):
        lembrete = TarefaPessoal.objects.create(
            titulo='Comprar insumos do restaurante',
            area='casa_yakisoba',
            data_conclusao=date.today(),
        )
        futuro = TarefaPessoal.objects.create(
            titulo='Lembrete pessoal futuro',
            area='gabriel',
            data_conclusao=date.today() + timedelta(days=2),
        )
        self.client.force_login(self.gabriel)

        painel = self.client.get(reverse('dashboard'))
        self.assertContains(painel, lembrete.titulo)
        self.assertNotContains(painel, futuro.titulo)
        self.assertNotContains(painel, 'id="notificationBadge"')
        self.assertEqual(
            self.client.get(reverse('status_notificacoes')).json()['total'],
            0,
        )

        resposta = self.client.post(
            reverse('concluir_tarefa_pessoal', args=[lembrete.id]),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(resposta.status_code, 200)
        lembrete.refresh_from_db()
        self.assertTrue(lembrete.concluida)

        sessao = self.client.session
        sessao['area_gabriel_pin_ate'] = timezone.now().timestamp() + 7200
        sessao.save()
        pagina = self.client.get(reverse('area_gabriel'))
        self.assertNotIn(lembrete, pagina.context['tarefas_casa'])
        self.assertIn(lembrete, pagina.context['tarefas_arquivadas'])

        self.client.post(reverse('reabrir_tarefa_pessoal', args=[lembrete.id]))
        lembrete.refresh_from_db()
        self.assertFalse(lembrete.concluida)
        self.assertIsNone(lembrete.concluida_em)

    def test_comentarios_da_tarefa_pessoal_podem_ser_criados_editados_e_excluidos(self):
        tarefa = TarefaPessoal.objects.create(
            titulo='Organizar documentos',
            area='gabriel',
            data_conclusao=date.today(),
        )
        self.client.force_login(self.gabriel)
        sessao = self.client.session
        sessao['area_gabriel_pin_ate'] = timezone.now().timestamp() + 7200
        sessao.save()

        self.client.post(
            reverse('adicionar_comentario_tarefa_pessoal', args=[tarefa.id]),
            {'texto': 'Primeira observação'},
        )
        comentario = ComentarioTarefaPessoal.objects.get(tarefa=tarefa)
        self.client.post(
            reverse('editar_comentario_tarefa_pessoal', args=[comentario.id]),
            {'texto': 'Observação revisada'},
        )
        comentario.refresh_from_db()
        self.assertEqual(comentario.texto, 'Observação revisada')
        self.assertIsNotNone(comentario.editado_em)

        pagina = self.client.get(reverse('area_gabriel'))
        self.assertContains(pagina, 'Observação revisada')
        self.client.post(
            reverse('excluir_comentario_tarefa_pessoal', args=[comentario.id]),
        )
        self.assertFalse(ComentarioTarefaPessoal.objects.filter(id=comentario.id).exists())


class BuscaGlobalTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin_busca', password='senha')
        self.operador = User.objects.create_user('operador_busca', password='senha')
        self.outro = User.objects.create_user('outro_busca', password='senha')
        self.cliente = Cliente.objects.create(
            codigo='54321',
            nome_fantasia='Restaurante Horizonte',
            razao_social='Horizonte Alimentação Ltda.',
            cnpj='00.000.000/0001-00',
            proprietario='Proprietário',
            telefone='11999999999',
        )
        self.ticket = Task.objects.create(
            titulo='Configurar impressora cozinha',
            descricao='Configuração no terminal principal.',
            responsavel=self.operador,
            cliente=self.cliente,
        )
        self.procedimento = ProcedimentoInterno.objects.create(
            titulo='Instalação do terminal',
            conteudo='Configure a impressora da cozinha.',
            criado_por=self.admin,
        )
        self.erro = ErroConhecido.objects.create(
            palavra_chave='Impressora desconectada',
            modulo='pdv',
            descricao='Falha de comunicação com a impressora.',
            versao_observada='1.0',
            ticket_netcontroll='',
        )

    def test_busca_agrupa_e_exibe_todos_os_tipos(self):
        self.client.force_login(self.admin)
        resposta = self.client.get(reverse('busca_global'), {'q': 'impressora'})

        self.assertContains(resposta, self.ticket.titulo)
        self.assertContains(resposta, self.procedimento.titulo)
        self.assertContains(resposta, self.erro.palavra_chave)
        resposta_cliente = self.client.get(reverse('busca_global'), {'q': 'Horizonte'})
        self.assertContains(resposta_cliente, self.cliente.nome_fantasia)

    def test_operador_nao_encontra_ticket_atribuido_a_outro_usuario(self):
        ticket_alheio = Task.objects.create(
            titulo='Ticket confidencial alheio',
            responsavel=self.outro,
        )
        self.client.force_login(self.operador)

        resposta = self.client.get(
            reverse('busca_global'),
            {'q': 'confidencial alheio'},
        )

        self.assertNotContains(resposta, ticket_alheio.titulo)

    def test_ticket_pode_ser_encontrado_pelo_cliente_vinculado(self):
        cliente = Cliente.objects.create(
            codigo='67890',
            nome_fantasia='MADAME FENERICH',
            razao_social='Madame Fenerich Comércio Ltda.',
            cnpj='11.111.111/0001-11',
            proprietario='Responsável',
            telefone='11988887777',
        )
        ticket = Task.objects.create(
            titulo='Alteração de Pacote',
            descricao='Solicitação sem o nome do cliente no texto.',
            responsavel=self.operador,
            cliente=cliente,
        )
        self.client.force_login(self.admin)

        for termo in ('MADAME FENERICH', 'MADAME', 'FENERICH', '67890'):
            with self.subTest(termo=termo):
                resposta = self.client.get(reverse('busca_global'), {'q': termo})
                self.assertContains(resposta, ticket.titulo)


class CaixaEntradaTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser('admin', 'admin@example.com', 'senha')
        self.operador = User.objects.create_user('operador', password='senha')
        self.outro = User.objects.create_user('outro', password='senha')

    def test_admin_envia_comunicado_para_todos(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse('caixa_entrada'), {
            'categoria': 'aviso',
            'titulo': 'Aviso geral',
            'conteudo': 'Conteúdo do aviso.',
            'para_todos': '1',
        })

        self.assertRedirects(resposta, reverse('caixa_entrada'))
        comunicacao = Comunicacao.objects.get()
        self.assertEqual(comunicacao.entregas.count(), 3)

    def test_usuario_so_ve_comunicacao_destinada_a_ele(self):
        comunicacao = Comunicacao.objects.create(
            categoria='sistema',
            titulo='Somente operador',
            conteudo='Mensagem privada',
            autor=self.admin,
        )
        ComunicacaoDestinatario.objects.create(
            comunicacao=comunicacao,
            destinatario=self.operador,
        )
        self.client.force_login(self.outro)
        resposta = self.client.get(reverse('caixa_entrada'))

        self.assertNotContains(resposta, 'Somente operador')

    def test_usuario_marca_comunicacao_como_lida(self):
        comunicacao = Comunicacao.objects.create(
            categoria='aviso',
            titulo='Ler esta mensagem',
            conteudo='Teste',
            autor=self.admin,
        )
        entrega = ComunicacaoDestinatario.objects.create(
            comunicacao=comunicacao,
            destinatario=self.operador,
        )
        self.client.force_login(self.operador)
        self.client.post(
            reverse('alterar_leitura_comunicacao', args=[comunicacao.id]),
            {'lida': '1'},
        )

        entrega.refresh_from_db()
        self.assertTrue(entrega.lida)
        self.assertIsNotNone(entrega.lida_em)

    def test_abrir_comunicacao_marca_automaticamente_como_lida(self):
        comunicacao = Comunicacao.objects.create(
            categoria='aviso',
            titulo='Leitura automática',
            conteudo='Mensagem aberta pelo destinatário.',
            autor=self.admin,
        )
        entrega = ComunicacaoDestinatario.objects.create(
            comunicacao=comunicacao,
            destinatario=self.operador,
        )
        entrega_outro = ComunicacaoDestinatario.objects.create(
            comunicacao=comunicacao,
            destinatario=self.outro,
        )
        self.client.force_login(self.operador)

        resposta = self.client.get(
            f"{reverse('caixa_entrada')}?mensagem={comunicacao.id}",
        )

        self.assertEqual(resposta.status_code, 200)
        entrega.refresh_from_db()
        entrega_outro.refresh_from_db()
        self.assertTrue(entrega.lida)
        self.assertIsNotNone(entrega.lida_em)
        self.assertFalse(entrega_outro.lida)
        self.assertIsNone(entrega_outro.lida_em)

    def test_publicar_release_gera_comunicacao(self):
        self.client.force_login(self.admin)
        resposta = self.client.post(reverse('releases'), {
            'publicar_release': '1',
            'versao': '0.0.3',
            'titulo': 'Novidades',
            'conteudo': 'Melhorias da versão.',
        })

        self.assertEqual(resposta.status_code, 302)
        release = Release.objects.get()
        self.assertEqual(release.comunicacao.categoria, 'release')
        self.assertEqual(release.comunicacao.entregas.count(), 3)


class LogoutTests(TestCase):
    def test_sair_encerra_sessao_e_redireciona_para_login(self):
        usuario = User.objects.create_user('usuario', password='senha')
        self.client.force_login(usuario)

        resposta = self.client.get(reverse('logout'))

        self.assertRedirects(resposta, reverse('login'))
        dashboard = self.client.get(reverse('dashboard'))
        self.assertRedirects(
            dashboard,
            f"{reverse('login')}?next={reverse('dashboard')}",
        )

# Create your tests here.
