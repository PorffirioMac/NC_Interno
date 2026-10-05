from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0035_alter_erroconhecido_modulo_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='origem_disparo',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='tarefas_disparadas', to='app.task'),
        ),
        migrations.AddField(
            model_name='task',
            name='tipo_disparo',
            field=models.CharField(blank=True, choices=[('', 'Não se aplica'), ('implantacao', 'Implantação'), ('cobranca', 'Cobrança'), ('planilha_fiscal', 'Planilha Fiscal')], default='', max_length=30),
        ),
        migrations.AddField(
            model_name='task',
            name='participantes',
            field=models.ManyToManyField(blank=True, related_name='tarefas_acompanhadas', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='task',
            name='valor_mensalidade',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='valor_implantacao',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='data_primeira_cobranca',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='task',
            name='fase',
            field=models.CharField(choices=[('implantacao', 'Implantação'), ('pendencias_pos_venda', 'Pendências Pós-Venda'), ('tickets_abertos', 'Tickets Abertos'), ('pendencias_plantao', 'Pendências Plantão'), ('tarefas_internas', 'Tarefas Internas'), ('diversos', 'Diversos'), ('aprovado_aguardando_implantacao', 'Aprovado, aguardando implantação'), ('lead_inicial', 'Lead inicial'), ('apresentacao', 'Apresentação'), ('enviar_proposta', 'Enviar proposta'), ('aguardando_retorno', 'Aguardando retorno'), ('cobrancas_avulsas', 'Cobranças avulsas de clientes'), ('novas_cobrancas', 'Novas Cobranças'), ('planilha_fiscal', 'Planilha Fiscal')], default='tickets_abertos', max_length=40),
        ),
    ]
