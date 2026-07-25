import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='CitadelStay',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('entered_at', models.DateTimeField()),
                ('scheduled_until', models.DateTimeField()),
                ('left_at', models.DateTimeField(blank=True, null=True)),
                ('cooldown_until', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='citadel_stays',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'db_table': 'ooe_citadel_stays',
                'ordering': ['-entered_at'],
            },
        ),
    ]
