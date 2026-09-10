from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0028_confirmacaodespesafinanceira'),
    ]

    operations = [
        migrations.CreateModel(
            name='TarefaPessoal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', models.CharField(max_length=300, verbose_name='Tarefa')),
                ('area', models.CharField(choices=[('casa_yakisoba', 'Casa do Yakisoba'), ('gabriel', 'Gabriel')], max_length=30, verbose_name='Área')),
                ('data_conclusao', models.DateField(verbose_name='Data de conclusão')),
                ('concluida', models.BooleanField(default=False)),
                ('concluida_em', models.DateTimeField(blank=True, null=True)),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['concluida', 'data_conclusao', 'titulo'],
                'permissions': [('acessar_area_gabriel', 'Pode acessar a área privada Gabriel')],
            },
        ),
    ]
