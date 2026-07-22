import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('app', '0011_task_area_comercial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Release',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('versao', models.CharField(max_length=30, verbose_name='Versão')),
                ('titulo', models.CharField(max_length=200, verbose_name='Título')),
                ('conteudo', models.TextField(verbose_name='Releases e correções')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('publicado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='releases_publicados', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-criado_em']},
        ),
        migrations.CreateModel(
            name='SolicitacaoRelease',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('feature', 'Nova feature'), ('correcao', 'Correção')], max_length=20)),
                ('titulo', models.CharField(max_length=200)),
                ('descricao', models.TextField(verbose_name='Descrição')),
                ('status', models.CharField(choices=[('pendente', 'Pendente'), ('feito', 'Feito')], default='pendente', max_length=20)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('concluido_em', models.DateTimeField(blank=True, null=True)),
                ('solicitante', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='solicitacoes_release', to=settings.AUTH_USER_MODEL)),
            ],
            options={'ordering': ['-status', '-criado_em']},
        ),
        migrations.CreateModel(
            name='ComentarioSolicitacao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texto', models.TextField()),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('autor', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
                ('solicitacao', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comentarios', to='app.solicitacaorelease')),
            ],
            options={'ordering': ['criado_em']},
        ),
    ]
