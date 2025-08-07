# Generated migration for multi-environment support

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('canvas_oauth', '0001_initial'),
    ]

    operations = [
        # Create CanvasEnvironment model
        migrations.CreateModel(
            name='CanvasEnvironment',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(help_text='Human-readable name (e.g., "Harvard Canvas")', max_length=100, unique=True)),
                ('domain', models.CharField(help_text='Canvas domain (e.g., "canvas.harvard.edu")', max_length=255, unique=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Canvas Environment',
                'verbose_name_plural': 'Canvas Environments',
            },
        ),

        # Add environment field as nullable initially
        migrations.AddField(
            model_name='canvasoauth2token',
            name='environment',
            field=models.ForeignKey(
                null=True, blank=True,  # Allow null during migration
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tokens',
                to='canvas_oauth.CanvasEnvironment'
            ),
        ),

        # Change user field from OneToOneField to ForeignKey
        migrations.AlterField(
            model_name='canvasoauth2token',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='canvas_tokens', to='common.User'),
        ),

        # Data migration to create default environment and migrate existing tokens
        migrations.RunPython(
            code=lambda apps, schema_editor: create_default_environment_and_migrate_tokens(apps, schema_editor),
            reverse_code=lambda apps, schema_editor: reverse_migration(apps, schema_editor),
        ),

        # Now make environment field required
        migrations.AlterField(
            model_name='canvasoauth2token',
            name='environment',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='tokens',
                to='canvas_oauth.CanvasEnvironment'
            ),
        ),

        # Add unique constraint for user + environment
        migrations.AlterUniqueTogether(
            name='canvasoauth2token',
            unique_together={('user', 'environment')},
        ),
    ]


def create_default_environment_and_migrate_tokens(apps, schema_editor):
    CanvasEnvironment = apps.get_model('canvas_oauth', 'CanvasEnvironment')
    CanvasOAuth2Token = apps.get_model('canvas_oauth', 'CanvasOAuth2Token')

    # Only proceed if there are existing tokens to migrate
    if CanvasOAuth2Token.objects.exists():
        # Get domain from legacy settings
        domain = getattr(settings, 'CANVAS_OAUTH_CANVAS_DOMAIN', 'canvas.instructure.com')

        # Create default environment
        env, _ = CanvasEnvironment.objects.get_or_create(
            domain=domain,
            defaults={
                'name': 'Default Canvas',
                'is_active': True,
            }
        )

        # Migrate all existing tokens to this environment
        CanvasOAuth2Token.objects.filter(environment__isnull=True).update(environment=env)


def reverse_migration(apps, schema_editor):
    # Just clear the environment field on reverse
    CanvasOAuth2Token = apps.get_model('canvas_oauth', 'CanvasOAuth2Token')
    CanvasOAuth2Token.objects.update(environment=None)
