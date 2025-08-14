from django.db import migrations

def set_default_superuser(apps, schema_editor):
    Usuario = apps.get_model('gestion', 'Usuario')
    # Todos los usuarios existentes pasarán a is_superuser=False
    for user in Usuario.objects.all():
        user.is_superuser = False
        user.save()

class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0005_alter_usuario_groups_alter_usuario_user_permissions'),  # reemplazá con tu última migración
    ]

    operations = [
        migrations.RunPython(set_default_superuser),
    ]

