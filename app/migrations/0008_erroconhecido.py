from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('app', '0007_cliente_codigo')]

    operations = [
        migrations.CreateModel(
            name='ErroConhecido',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('palavra_chave', models.CharField(max_length=200, verbose_name='Palavra-Chave')),
                ('modulo', models.CharField(choices=[('pdv', 'PDV'), ('pdv_pos', 'PDV/POS'), ('portal', 'Portal'), ('tablet_mesa', 'Tablet Mesa'), ('totem', 'Totem'), ('ecommerce', 'E-commerce'), ('nfce', 'NFCe'), ('outros', 'Outros')], max_length=30, verbose_name='Módulo')),
                ('descricao', models.TextField(verbose_name='Descrição')),
                ('versao_observada', models.CharField(max_length=100, verbose_name='Versão Observada')),
                ('ticket_netcontroll', models.CharField(max_length=100, verbose_name='Ticket Netcontroll')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('clientes', models.ManyToManyField(related_name='erros_conhecidos', to='app.cliente')),
            ],
            options={'ordering': ['-atualizado_em']},
        ),
    ]
