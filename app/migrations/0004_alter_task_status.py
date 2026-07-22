from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('app', '0003_deadlinehistory')]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='status',
            field=models.CharField(
                choices=[
                    ('pendente_cliente', 'Pendente Cliente'),
                    ('pendente_netcamp', 'Pendente NetCamp'),
                    ('pendente_netcontroll', 'Pendente Netcontroll'),
                ],
                default='pendente_cliente',
                max_length=30,
            ),
        ),
    ]
