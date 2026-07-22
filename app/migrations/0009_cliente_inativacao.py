from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('app', '0008_erroconhecido')]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='ativo',
            field=models.BooleanField(default=True, verbose_name='Ativo'),
        ),
        migrations.AddField(
            model_name='cliente',
            name='motivo_inativacao',
            field=models.TextField(blank=True, verbose_name='Motivo da inativação'),
        ),
        migrations.AddField(
            model_name='cliente',
            name='inativado_em',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Inativado em'),
        ),
    ]
