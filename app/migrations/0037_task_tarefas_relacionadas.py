from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0036_task_disparo_novo_cliente'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='bloqueia_encerramento',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='task',
            name='valor_mensal_anterior',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='motivo_alteracao',
            field=models.TextField(blank=True),
        ),
        migrations.AlterField(
            model_name='task',
            name='area',
            field=models.CharField(choices=[('tickets', 'Tickets'), ('comercial', 'Comercial'), ('relacionada', 'Tarefa Relacionada')], default='tickets', max_length=20),
        ),
        migrations.AlterField(
            model_name='task',
            name='tipo_disparo',
            field=models.CharField(blank=True, choices=[('', 'Não se aplica'), ('implantacao', 'Implantação'), ('cobranca', 'Cobrança'), ('planilha_fiscal', 'Planilha Fiscal'), ('tarefa_interna', 'Tarefa Interna'), ('retorno_cliente', 'Retorno ao Cliente'), ('outro', 'Outro')], default='', max_length=30),
        ),
    ]
