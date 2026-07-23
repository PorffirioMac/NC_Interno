from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .models import (
    Comunicacao, ComunicacaoDestinatario, Notificacao, Release, Task,
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
