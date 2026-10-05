from django.db import migrations, models


MODULOS = [
    ('pdv', 'PDV'),
    ('pdv_pos', 'PDV/POS'),
    ('portal', 'Portal'),
    ('tablet_mesa', 'Tablet Mesa'),
    ('totem', 'Totem'),
    ('ecommerce', 'E-commerce'),
    ('nfce', 'NFCe'),
    ('xtag', 'Xtag'),
    ('concentrador', 'Concentrador'),
    ('nfe', 'NFe'),
    ('solicitacao_geral_cliente', 'Solicitação Geral de Cliente'),
    ('outros', 'Outros'),
]


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0034_alter_tarefapessoal_area'),
    ]

    operations = [
        migrations.AlterField(
            model_name='erroconhecido',
            name='modulo',
            field=models.CharField(choices=MODULOS, max_length=30, verbose_name='Módulo'),
        ),
        migrations.AlterField(
            model_name='sugestaodesenvolvimento',
            name='modulo',
            field=models.CharField(choices=MODULOS, max_length=30, verbose_name='Módulo'),
        ),
        migrations.AlterField(
            model_name='task',
            name='modulo',
            field=models.CharField(
                blank=True,
                choices=[('', 'Sem Módulo Definido'), *MODULOS],
                default='',
                max_length=30,
                verbose_name='Módulo',
            ),
        ),
    ]
