import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0030_permissao_area_gabriel'),
    ]

    operations = [
        migrations.CreateModel(
            name='ComentarioTarefaPessoal',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texto', models.TextField(verbose_name='Comentário')),
                ('criado_em', models.DateTimeField(auto_now_add=True)),
                ('editado_em', models.DateTimeField(blank=True, null=True)),
                ('tarefa', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='comentarios', to='app.tarefapessoal')),
            ],
            options={'ordering': ['-criado_em']},
        ),
    ]
