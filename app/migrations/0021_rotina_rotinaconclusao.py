import django.core.validators
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0020_despesafinanceira'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Rotina',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=180)),
                ('descricao', models.TextField(blank=True)),
                ('periodicidade', models.CharField(choices=[('diaria', 'Diária'), ('semanal', 'Semanal'), ('mensal', 'Mensal')], max_length=10)),
                ('dia_mes', models.PositiveSmallIntegerField(blank=True, null=True, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(31)], verbose_name='Dia do mês')),
                ('ativa', models.BooleanField(default=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
                ('criado_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rotinas_criadas', to=settings.AUTH_USER_MODEL)),
                ('responsavel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='rotinas', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['responsavel__username', 'periodicidade', 'titulo'],
                'permissions': [('gerenciar_rotinas', 'Pode gerenciar rotinas')],
            },
        ),
        migrations.CreateModel(
            name='RotinaConclusao',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('periodo_referencia', models.DateField()),
                ('concluido_em', models.DateTimeField(auto_now_add=True)),
                ('concluido_por', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='rotinas_concluidas', to=settings.AUTH_USER_MODEL)),
                ('rotina', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conclusoes', to='app.rotina')),
            ],
            options={
                'ordering': ['-concluido_em'],
            },
        ),
        migrations.AddConstraint(
            model_name='rotinaconclusao',
            constraint=models.UniqueConstraint(fields=('rotina', 'periodo_referencia'), name='rotina_conclusao_periodo_unico'),
        ),
    ]
