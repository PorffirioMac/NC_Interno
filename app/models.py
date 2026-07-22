from django.db import models
from django.contrib.auth.models import User


class Cliente(models.Model):
    codigo = models.CharField('ID', max_length=5, unique=True, null=True, blank=True)
    nome_fantasia = models.CharField('Nome Fantasia', max_length=200)
    razao_social = models.CharField('Razão Social', max_length=200)
    cnpj = models.CharField('CNPJ', max_length=18)
    proprietario = models.CharField('Proprietário', max_length=150)
    telefone = models.CharField('Telefone', max_length=30)
    observacoes = models.TextField('Observações', blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    motivo_inativacao = models.TextField('Motivo da inativação', blank=True)
    inativado_em = models.DateTimeField('Inativado em', null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['nome_fantasia']

    def __str__(self):
        return self.nome_fantasia


class ErroConhecido(models.Model):
    MODULOS = [
        ('pdv', 'PDV'),
        ('pdv_pos', 'PDV/POS'),
        ('portal', 'Portal'),
        ('tablet_mesa', 'Tablet Mesa'),
        ('totem', 'Totem'),
        ('ecommerce', 'E-commerce'),
        ('nfce', 'NFCe'),
        ('outros', 'Outros'),
    ]

    palavra_chave = models.CharField('Palavra-Chave', max_length=200)
    modulo = models.CharField('Módulo', max_length=30, choices=MODULOS)
    descricao = models.TextField('Descrição')
    versao_observada = models.CharField('Versão Observada', max_length=100)
    clientes = models.ManyToManyField(Cliente, related_name='erros_conhecidos')
    ticket_netcontroll = models.CharField('Ticket Netcontroll', max_length=100)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-atualizado_em']

    def __str__(self):
        return f'{self.palavra_chave} - {self.get_modulo_display()}'


class Release(models.Model):
    versao = models.CharField('Versão', max_length=30)
    titulo = models.CharField('Título', max_length=200)
    conteudo = models.TextField('Releases e correções')
    publicado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='releases_publicados')
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-criado_em']

    def __str__(self):
        return f'Versão {self.versao} - {self.titulo}'


class SolicitacaoRelease(models.Model):
    TIPOS = [('feature', 'Nova feature'), ('correcao', 'Correção')]
    STATUS = [('pendente', 'Pendente'), ('feito', 'Feito')]

    tipo = models.CharField(max_length=20, choices=TIPOS)
    titulo = models.CharField(max_length=200)
    descricao = models.TextField('Descrição')
    solicitante = models.ForeignKey(User, on_delete=models.CASCADE, related_name='solicitacoes_release')
    status = models.CharField(max_length=20, choices=STATUS, default='pendente')
    criado_em = models.DateTimeField(auto_now_add=True)
    concluido_em = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-status', '-criado_em']

    def __str__(self):
        return self.titulo


class ComentarioSolicitacao(models.Model):
    solicitacao = models.ForeignKey(SolicitacaoRelease, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    texto = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em']

# ========== COMERCIAL ==========

class Lead(models.Model):
    STATUS_CHOICES = [
        ('contato_inicial', 'Contato Inicial'),
        ('proposta_enviada', 'Proposta Enviada'),
        ('negociacao', 'Negociação'),
        ('aprovado', 'Aprovado'),
        ('perdido', 'Perdido'),
    ]

    empresa = models.CharField(max_length=200)
    contato_nome = models.CharField(max_length=100)
    contato_telefone = models.CharField(max_length=20, blank=True)
    contato_email = models.EmailField(blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='contato_inicial')
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='leads_responsavel')
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.empresa} - {self.get_status_display()}"

# ========== TAREFAS (Cards do Kanban) ==========

class Task(models.Model):
    AREAS = [
        ('tickets', 'Tickets'),
        ('comercial', 'Comercial'),
    ]

    STATUS_CHOICES = [
        ('pendente_cliente', 'Pendente Cliente'),
        ('pendente_netcamp', 'Pendente NetCamp'),
        ('pendente_netcontroll', 'Pendente Netcontroll'),
    ]

    FASES_TICKETS = [
        ('implantacao', 'Implantação'),
        ('pendencias_pos_venda', 'Pendências Pós-Venda'),
        ('tickets_abertos', 'Tickets Abertos'),
        ('tarefas_internas', 'Tarefas Internas'),
        ('diversos', 'Diversos'),
    ]

    FASES_COMERCIAL = [
        ('aprovado_aguardando_implantacao', 'Aprovado, aguardando implantação'),
        ('lead_inicial', 'Lead inicial'),
        ('apresentacao', 'Apresentação'),
        ('enviar_proposta', 'Enviar proposta'),
        ('aguardando_retorno', 'Aguardando retorno'),
        ('cobrancas_avulsas', 'Cobranças avulsas de clientes'),
    ]

    FASES = FASES_TICKETS + FASES_COMERCIAL

    STATUS_COMERCIAL = [
        ('contato_inicial', 'Contato Inicial'),
        ('proposta_enviada', 'Proposta Enviada'),
        ('negociacao', 'Negociação'),
        ('aprovado', 'Aprovado'),
    ]

    STATUS_IMPLANTACAO = [
        ('pendente', 'Pendente'),
        ('em_andamento', 'Em Andamento'),
        ('concluido', 'Concluído'),
    ]

    STATUS_SUPORTE = [
        ('aberto', 'Aberto'),
        ('em_andamento', 'Em Andamento'),
        ('aguardando', 'Aguardando Cliente'),
        ('resolvido', 'Resolvido'),
        ('fechado', 'Fechado'),
    ]

    titulo = models.CharField(max_length=300)
    descricao = models.TextField(blank=True)
    area = models.CharField(max_length=20, choices=AREAS, default='tickets')
    fase = models.CharField(max_length=40, choices=FASES, default='tickets_abertos')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='pendente_cliente')
    prioridade = models.CharField(max_length=20, choices=[
        ('baixa', 'Baixa'),
        ('media', 'Média'),
        ('alta', 'Alta'),
        ('urgente', 'Urgente'),
    ], default='media')
    encerrada = models.BooleanField('Encerrada', default=False)
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tarefas')
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, null=True, blank=True, related_name='tarefas')
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tarefas',
    )
    prazo = models.DateField(null=True, blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"[{self.get_fase_display()}] {self.titulo}"

class ChecklistItem(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='checklists')
    descricao = models.CharField(max_length=500)
    concluido = models.BooleanField(default=False)
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{'✅' if self.concluido else '⬜'} {self.descricao}"

class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comentarios')
    autor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    texto = models.TextField()
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['criado_em']

    def __str__(self):
        return f"Comentário de {self.autor} em {self.criado_em.strftime('%d/%m/%Y %H:%M')}"
    
