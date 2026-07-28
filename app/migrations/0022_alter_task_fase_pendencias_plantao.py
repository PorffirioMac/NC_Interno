from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0021_rotina_rotinaconclusao'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='fase',
            field=models.CharField(
                choices=[
                    ('implantacao', 'Implantação'),
                    ('pendencias_pos_venda', 'Pendências Pós-Venda'),
                    ('tickets_abertos', 'Tickets Abertos'),
                    ('pendencias_plantao', 'Pendências Plantão'),
                    ('tarefas_internas', 'Tarefas Internas'),
                    ('diversos', 'Diversos'),
                    ('aprovado_aguardando_implantacao', 'Aprovado, aguardando implantação'),
                    ('lead_inicial', 'Lead inicial'),
                    ('apresentacao', 'Apresentação'),
                    ('enviar_proposta', 'Enviar proposta'),
                    ('aguardando_retorno', 'Aguardando retorno'),
                    ('cobrancas_avulsas', 'Cobranças avulsas de clientes'),
                ],
                default='tickets_abertos',
                max_length=40,
            ),
        ),
    ]
