from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('items', '0005_guntransaction'),
    ]

    operations = [
        # Add is_equipped to UserHouse
        migrations.AddField(
            model_name='userhouse',
            name='is_equipped',
            field=models.BooleanField(default=False),
        ),
        # Add is_equipped to UserCar
        migrations.AddField(
            model_name='usercar',
            name='is_equipped',
            field=models.BooleanField(default=False),
        ),
        # Add is_equipped to UserGun
        migrations.AddField(
            model_name='usergun',
            name='is_equipped',
            field=models.BooleanField(default=False),
        ),
        # Remove city FK from UserGun (guns travel with the player)
        migrations.RemoveField(
            model_name='usergun',
            name='city',
        ),
        # Remove city FK from GunTransaction (historical record, no longer city-specific)
        migrations.RemoveField(
            model_name='guntransaction',
            name='city',
        ),
    ]
