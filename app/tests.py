from datetime import date, timedelta
import shutil
import tempfile

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.test import TestCase
from django.urls import reverse

from .models import (
    AnexoTicket, Cliente, Comunicacao, ComunicacaoDestinatario, Notificacao,
    Release, Task,
)


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
