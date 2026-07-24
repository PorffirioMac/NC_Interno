from django.db import migrations, models


def preencher_datas_de_encerramento(apps, schema_editor):
    Task = apps.get_model('app', 'Task')
    Task.objects.filter(encerrada=True, encerrado_em__isnull=True).update(
        encerrado_em=models.F('atualizado_em')
    )


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0018_anexoticket'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='encerrado_em',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Encerrado em',
            ),
        ),
        migrations.RunPython(
            preencher_datas_de_encerramento,
            migrations.RunPython.noop,
        ),
    ]
