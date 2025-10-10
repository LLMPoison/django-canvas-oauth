

from django.db import models
from django.conf import settings
from django.utils import timezone
#from canvas_oauth.models import CanvasUser


# Create your models here.
class CanvasUser(models.Model):
    canvas_user_id = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    sortable_name = models.CharField(max_length=255, blank=True)
    short_name = models.CharField(max_length=255, blank=True)
    email = models.EmailField(blank=True, null=True)
    avatar_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} (Canvas ID: {self.canvas_user_id})"

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
    * :attr:`access_token` Access token
    * :attr:`refresh_token` Refresh token
    * :attr:`expires` Date and time of token expiration, in DateTime format
    * :attr:`created_on` When the initial access token was granted,
        in DateTime format
    * :attr:`updated_on` When the token was refreshed (or first created), in
        DateTime format
    """
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='canvas_oauth2_token',
    )
    """

    user = models.OneToOneField(CanvasUser, on_delete=models.CASCADE, related_name="canvas_oauth2_token")

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

    def __str__(self):
        return "CanvasOAuth2Token:%s" % self.user

    class Meta:
        verbose_name = "Canvas OAuth2 Token"
        verbose_name_plural = "Canvas OAuth2 Tokens"
