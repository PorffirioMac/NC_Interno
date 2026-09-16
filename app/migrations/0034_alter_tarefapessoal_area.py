from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0033_tarefapessoal_prioridade'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tarefapessoal',
            name='area',
            field=models.CharField(
                choices=[
                    ('netcamp', 'NetCamp'),
                    ('casa_yakisoba', 'Casa do Yakisoba'),
                    ('gabriel', 'Gabriel'),
                ],
                max_length=30,
                verbose_name='Área',
            ),
        ),
    ]
