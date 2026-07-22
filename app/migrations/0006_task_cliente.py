import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('app', '0005_cliente')]

    operations = [
        migrations.AddField(
            model_name='task',
            name='cliente',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='tarefas',
                to='app.cliente',
            ),
        ),
    ]
