from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('app', '0006_task_cliente')]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='codigo',
            field=models.CharField(
                blank=True,
                max_length=5,
                null=True,
                unique=True,
                verbose_name='ID',
            ),
        ),
    ]
