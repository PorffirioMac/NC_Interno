from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('app', '0004_alter_task_status')]

    operations = [
        migrations.CreateModel(
            name='Cliente',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome_fantasia', models.CharField(max_length=200, verbose_name='Nome Fantasia')),
                ('razao_social', models.CharField(max_length=200, verbose_name='Razão Social')),
                ('cnpj', models.CharField(max_length=18, verbose_name='CNPJ')),
                ('proprietario', models.CharField(max_length=150, verbose_name='Proprietário')),
                ('telefone', models.CharField(max_length=30, verbose_name='Telefone')),
                ('observacoes', models.TextField(blank=True, verbose_name='Observações')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('atualizado_em', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['nome_fantasia']},
        ),
    ]
