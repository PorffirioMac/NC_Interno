import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('app', '0012_releases_solicitacoes')]

    operations = [
        migrations.AddField(
            model_name='task',
            name='origem_comercial',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='ticket_implantacao',
                to='app.task',
            ),
        ),
    ]
