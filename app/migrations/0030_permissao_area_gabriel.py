from django.db import migrations


def atribuir_permissao(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')
    usuario = User.objects.filter(username='gabriel.porfirio').first()
    if not usuario:
        return
    content_type, _ = ContentType.objects.get_or_create(
        app_label='app',
        model='tarefapessoal',
    )
    permissao, _ = Permission.objects.get_or_create(
        content_type=content_type,
        codename='acessar_area_gabriel',
        defaults={'name': 'Pode acessar a área privada Gabriel'},
    )
    usuario.user_permissions.add(permissao)


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0029_tarefapessoal'),
    ]

    operations = [
        migrations.RunPython(atribuir_permissao, migrations.RunPython.noop),
    ]
