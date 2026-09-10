from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0032_acessoareagabriel'),
    ]

    operations = [
        migrations.AddField(
            model_name='tarefapessoal',
            name='prioridade',
            field=models.CharField(choices=[('alta', 'Alta'), ('media', 'Média'), ('baixa', 'Baixa')], default='media', max_length=10),
        ),
    ]
