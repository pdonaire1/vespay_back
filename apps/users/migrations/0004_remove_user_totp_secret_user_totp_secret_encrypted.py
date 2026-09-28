from django.db import migrations, models

from common.utils.crypto import encrypt_field


def encrypt_existing_secrets(apps, schema_editor):
    """Cifra los secretos TOTP existentes (antes guardados en texto plano)."""
    User = apps.get_model("users", "User")
    db_alias = schema_editor.connection.alias
    for user in User.objects.using(db_alias).all():
        if user.totp_secret:
            user.totp_secret_encrypted = encrypt_field(user.totp_secret)
            user.save(update_fields=["totp_secret_encrypted"])


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0003_user_backup_codes_user_is_2fa_enabled_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="totp_secret_encrypted",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.RunPython(encrypt_existing_secrets, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="user",
            name="totp_secret",
        ),
    ]
