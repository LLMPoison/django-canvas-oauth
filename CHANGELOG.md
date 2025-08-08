# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Multi-environment Canvas OAuth support for LTI tools
- Automatic Canvas domain detection from LTI launch data
- New `CanvasEnvironment` model for managing multiple Canvas instances
- New `DomainBasedResolver` for automatic environment detection from LTI launches
- New `LegacyResolver` for backward compatibility with single-environment setups
- Enhanced resolver with automatic LTI domain extraction

### Changed

- `CanvasOAuth2Token.user` field changed from `OneToOneField` to `ForeignKey` to support multiple tokens per user (one per environment)
- Added `unique_together` constraint on `CanvasOAuth2Token` for `(user, environment)` pairs

### Migration Guide

#### For Existing Installations

1. Run migrations to upgrade database schema:

   ```bash
   python manage.py migrate canvas_oauth
   ```

2. **No code changes required** - existing single-environment setups continue to work unchanged
3. A default `CanvasEnvironment` record will be automatically created based on your existing `CANVAS_OAUTH_CANVAS_DOMAIN` setting
4. All existing tokens will be migrated to this default environment

#### For Multi-Environment Setup

1. Configure multiple environments in settings:

   ```python
   CANVAS_OAUTH_ENVIRONMENTS = {
       'production': {
           'client_id': 'your_prod_client_id',
           'client_secret': 'your_prod_secret',
           'canvas_domain': 'canvas.school.edu',
           'name': 'School Canvas',
       },
       'test': {
           'client_id': 'your_test_client_id',
           'client_secret': 'your_test_secret',
           'canvas_domain': 'canvas.test.school.edu',
           'name': 'School Canvas (Test)',
       },
   }
   CANVAS_OAUTH_ENVIRONMENT_RESOLVER = 'canvas_oauth.resolvers.DomainBasedResolver'
   ```

2. Create environment records:

   ```python
   from canvas_oauth.models import CanvasEnvironment

   CanvasEnvironment.objects.create(
       name='School Canvas',
       domain='canvas.school.edu',
       is_active=True
   )

   CanvasEnvironment.objects.create(
       name='School Canvas (Test)',
       domain='canvas.test.school.edu',
       is_active=True
   )
   ```

3. Add Canvas custom field to your LTI Developer Key:

   ```text
   api_domain=$Canvas.api.domain
   ```

### New Settings

- `CANVAS_OAUTH_ENVIRONMENTS` - Dictionary defining multiple Canvas instances with their OAuth credentials
- `CANVAS_OAUTH_ENVIRONMENT_RESOLVER` - Class path for environment resolution strategy

### Technical Details

- Migration `0001_initial` - Creates base `CanvasOAuth2Token` model
- Migration `0002_alter_canvasoauth2token_options` - No-op migration to handle missing migration file
- Migration `0003_add_multi_environment_support` - Adds `CanvasEnvironment` model and multi-environment support
