from django.conf import settings
from django.db import models
from django.utils import timezone

from canvas_oauth import settings as oauth_settings


class CanvasEnvironment(models.Model):
    """Represents a Canvas environment configuration"""
    name = models.CharField(max_length=100, unique=True, help_text="Human-readable name (e.g., 'Harvard Canvas')")
    domain = models.CharField(max_length=255, unique=True, help_text="Canvas domain (e.g., 'canvas.harvard.edu')")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def base_url(self):
        """Return the base Canvas URL for this environment"""
        return f"https://{self.domain}"

    @property
    def client_id(self):
        """Get client ID from CANVAS_OAUTH_ENVIRONMENTS config or legacy settings"""

        # First check for a multi-environment config
        environments_config = getattr(settings, 'CANVAS_OAUTH_ENVIRONMENTS', {})
        for env_key, env_config in environments_config.items():
            if env_config.get('domain') == self.domain:
                return env_config.get('client_id')

        # Fall back to domain-based lookup
        return oauth_settings.get_client_id_for_domain(self.domain)

    @property
    def client_secret(self):
        """Get client secret from CANVAS_OAUTH_ENVIRONMENTS config or legacy settings"""

        # First check for a multi-environment config
        environments_config = getattr(settings, 'CANVAS_OAUTH_ENVIRONMENTS', {})
        for env_key, env_config in environments_config.items():
            if env_config.get('domain') == self.domain:
                return env_config.get('client_secret')

        # Fall back to domain-based lookup
        return oauth_settings.get_client_secret_for_domain(self.domain)

    class Meta:
        verbose_name = "Canvas Environment"
        verbose_name_plural = "Canvas Environments"

    def __str__(self):
        return f"{self.name} ({self.domain})"


class CanvasOAuth2Token(models.Model):
    """
    A CanvasOAuth2Token instance represents the access token
    response from Canvas when the user requests an authorization
    grant as in :rfc:`6749`.  Canvas tokens are short-lived, and
    so they issue refresh tokens as part of the grant response.
    The refresh tokens are used to retrieve new access tokens once
    they expire.
    Fields:
    * :attr:`user` The Django user representing resources' owner
    * :attr:`environment` The Canvas environment this token is for
    * :attr:`access_token` Access token
    * :attr:`refresh_token` Refresh token
    * :attr:`expires` Date and time of token expiration, in DateTime format
    * :attr:`created_on` When the initial access token was granted,
        in DateTime format
    * :attr:`updated_on` When the token was refreshed (or first created), in
        DateTime format
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='canvas_tokens',
    )
    environment = models.ForeignKey(
        CanvasEnvironment,
        on_delete=models.CASCADE,
        related_name='tokens'
    )
    access_token = models.TextField()
    refresh_token = models.TextField()
    expires = models.DateTimeField()
    created_on = models.DateTimeField(auto_now_add=True)
    updated_on = models.DateTimeField(auto_now=True)

    def expires_within(self, delta):
        """
        Check token expiration with timezone awareness within
        the given amount of time, expressed as a timedelta.

        :param delta: The timedelta to check expiration against
        """
        if not self.expires:
            return False

        return self.expires - timezone.now() <= delta

    def is_expired(self):
        """
        Check if the token is expired (past expiration time)
        """
        if not self.expires:
            return False

        return timezone.now() >= self.expires

    def __str__(self):
        return f"{self.user.username} - {self.environment.name}"

    class Meta:
        unique_together = ('user', 'environment')
        verbose_name = "Canvas OAuth2 Token"
        verbose_name_plural = "Canvas OAuth2 Tokens"
