from django.db import migrations, models


def migrar_fases(apps, schema_editor):
    Task = apps.get_model('app', 'Task')
    Task.objects.filter(fase='suporte').update(fase='tickets_abertos')
    Task.objects.filter(fase='comercial').update(fase='diversos')


def reverter_fases(apps, schema_editor):
    Task = apps.get_model('app', 'Task')
    Task.objects.filter(fase='tickets_abertos').update(fase='suporte')
    Task.objects.filter(fase__in=['pendencias_pos_venda', 'tarefas_internas', 'diversos']).update(fase='comercial')


class Migration(migrations.Migration):
    dependencies = [('app', '0009_cliente_inativacao')]

    operations = [
        migrations.RunPython(migrar_fases, reverter_fases),
        migrations.AlterField(
            model_name='task',
            name='fase',
            field=models.CharField(
                choices=[
                    ('implantacao', 'Implantação'),
                    ('pendencias_pos_venda', 'Pendências Pós-Venda'),
                    ('tickets_abertos', 'Tickets Abertos'),
                    ('tarefas_internas', 'Tarefas Internas'),
                    ('diversos', 'Diversos'),
                ],
                default='tickets_abertos',
                max_length=30,
            ),
        ),
    ]
