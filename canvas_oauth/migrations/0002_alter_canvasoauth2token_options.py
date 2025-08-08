# Generated migration to resolve phantom migration issue

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('canvas_oauth', '0001_initial'),
    ]

    operations = [
        # No-op migration to handle phantom migration that some users encountered
    ]
