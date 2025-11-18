import logging
import requests
import os

from django.urls import reverse
from django.http.response import HttpResponse, HttpResponseRedirect
from django.shortcuts import redirect
from django.template import loader
from django.template.exceptions import TemplateDoesNotExist
from django.utils.crypto import get_random_string

import ipdb

from canvas_oauth import (canvas, settings)
from canvas_oauth.models import CanvasOAuth2Token
from canvas_oauth.exceptions import (
    MissingTokenError, InvalidOAuthStateError)
from django.core.cache import cache
from django.utils import timezone
from .models import CanvasUser
from urllib.parse import urlparse, parse_qsl, urlencode, urlunparse, parse_qs


logger = logging.getLogger(__name__)


def get_oauth_token(request):
    print("IN: get_oauth_token")
    """Retrieve a stored Canvas OAuth2 access token from Canvas for the
    currently logged in user.  If the token has expired (or has exceeded an
    expiration threshold as defined by the consuming project), a fresh token
    is generated via the saved refresh token.

    If the user does not have a stored token, the method raises a
    MissingTokenError exception.  If this happens inside a view, this exception
    will be handled by the middleware component of this library with a call to
    handle_missing_token.  If this happens outside of a view, then the user must
    be directed by other means to the Canvas site in order to authorize a token.
    """
    try:
        if request.session.has_key('user_id'):
            user_id_value = request.session['user_id']
        else:
            user_id_value = request.GET.get("user_id") or request.POST.get("user_id")
        canvas_user = CanvasUser.objects.get(canvas_user_id=user_id_value)
        oauth_token = canvas_user.canvas_oauth2_token
        logger.info("Token found for user %s" % request.user.pk)
    #except CanvasOAuth2Token.DoesNotExist:
    except Exception as e:
        """ If this exception is raised by a view function and not caught,
        it is probably because the oauth_middleware is not installed, since it
        is supposed to catch this error."""
        logger.info("No token found for user %s" % request.user.pk)
        print("No token found for user %s" % request.user.pk)
        raise MissingTokenError("No token found for user %s" % request.user.pk)

    # Check to see if we're within the expiration threshold of the access token
    if oauth_token.expires_within(settings.CANVAS_OAUTH_TOKEN_EXPIRATION_BUFFER):
        logger.info("Refreshing token for user %s" % request.user.pk)
        oauth_token = refresh_oauth_token(request, oauth_token)

    return oauth_token.access_token, user_id_value

def get_assignment(course_id, assignment_id, access_token):
    url = f"https://canvas.instructure.com/api/v1/courses/{course_id}/assignments/{assignment_id}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()
    return response.json()

def handle_missing_token(request):
    """
    Redirect user to canvas with a request for token.
    """
    # Store where the user came from so they can be redirected back there
    # at the end.  https://canvas.instructure.com/doc/api/file.oauth.html
    request.session["canvas_oauth_initial_uri"] = request.get_full_path()

    # The request state is a recommended security check on the callback, so
    # store in session for later
    oauth_request_state = get_random_string(12)
    request.session["canvas_oauth_request_state"] = oauth_request_state

    # The return URI is required to be the same when POSTing to generate
    # a token on callback, so also store it in session (although it could
    # be regenerated again via the same method call).
    oauth_redirect_uri = request.build_absolute_uri(reverse('canvas-oauth-callback'))
    request.session["canvas_oauth_redirect_uri"] = oauth_redirect_uri

    
    state_data = {
        "redirect_uri": oauth_redirect_uri,
        "initial_uri": request.get_full_path(),
        "timestamp": timezone.now().isoformat(),
        "user_id": request.POST.get("user_id"),
        "user": request.user,
        "course_id": request.POST.get("custom_canvas_course_id"),
    }


    # Store for 10 minutes (600 seconds)
    cache.set(f"oauth_state:{oauth_request_state}", state_data, timeout=600)


    authorize_url = canvas.get_oauth_login_url(
        settings.CANVAS_OAUTH_CLIENT_ID,
        redirect_uri=oauth_redirect_uri,
        state=oauth_request_state,
        scopes=settings.CANVAS_OAUTH_SCOPES)

    logger.info("Redirecting user to %s" % authorize_url)
    return HttpResponseRedirect(authorize_url)


def get_user_data(access_token):
    # Fetch Canvas user info using access token
    try:
        #TODO: Remove hard-coded url
        user_response = requests.get(
            "https://canvas.docker/api/v1/users/self",
            #state_data.get("user_info_url", "https://canvas.local/api/v1/users/self"),
            headers={"Authorization": f"Bearer {access_token}"},
            verify=os.path.expanduser("~/.local/share/mkcert/rootCA.pem"),
            timeout=10,
        )
        user_response.raise_for_status()
    except requests.RequestException as e:
        return HttpResponseBadRequest(f"Failed to fetch Canvas user: {e}")

    return user_response.json()


def oauth_callback(request):
    """ Receives the callback from canvas and saves the token to the database.
        Redirects user to the page they came from at the start of the oauth
        procedure. """
    error = request.GET.get('error')
    if error:
        return render_oauth_error(error)
    code = request.GET.get('code')
    state = request.GET.get('state')

    state = request.GET.get("state")

    state_data = cache.get(f"oauth_state:{state}")
    if state_data is None:
        return HttpResponseBadRequest("Invalid or expired OAuth state")

    if request.session.has_key('canvas_oauth_request_state'):
        if (state != request.session['canvas_oauth_request_state']):
            logger.warning("OAuth state mismatch for request: %s" % request.get_full_path())
            raise InvalidOAuthStateError("OAuth state mismatch!")

    # Make the `authorization_code` grant type request to retrieve a
    access_token, expires, refresh_token = canvas.get_access_token(
        domain=settings.CANVAS_OAUTH_CANVAS_DOMAIN,
        grant_type='authorization_code',
        redirect_uri=state_data["redirect_uri"],
        #redirect_uri=request.session["canvas_oauth_redirect_uri"],
        #redirect_uri='https://localhost:8000/oauth/oauth-callback',
        code=code)


    user_data = get_user_data(access_token)

    canvas_user, _ = CanvasUser.objects.get_or_create(
        canvas_user_id=user_data["id"],
        defaults={
            "name": user_data.get("name", ""),
            "sortable_name": user_data.get("sortable_name", ""),
            "short_name": user_data.get("short_name", ""),
            "email": user_data.get("email", ""),
            "avatar_url": user_data.get("avatar_url", ""),
        },
    )

    obj, _ = CanvasOAuth2Token.objects.update_or_create(
        user=canvas_user,
        defaults={
        "access_token": access_token,
        "expires": expires,
        "refresh_token": refresh_token})
    logger.info("CanvasOAuth2Token instance created: %s" % obj.pk)

    initial_uri = state_data['initial_uri']
    #initial_uri = request.session['canvas_oauth_initial_uri']
    #initial_uri = '/canvas_plugin/'
    
    request.session['user_id'] = canvas_user.canvas_user_id
    
    logger.info("Redirecting user back to initial uri %s" % initial_uri)
    redirect_url = append_query_params(initial_uri, {
        "user_id": canvas_user.canvas_user_id,
        "custom_canvas_course_id": state_data.get("course_id", "default_course_id"),
    })


    return redirect(redirect_url)

def append_query_params(url, params):
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    query.update(params)
    encoded_query = urlencode(query, doseq=True)
    return urlunparse(parsed._replace(query=encoded_query))

def refresh_oauth_token(request, oauth_token):
    """ Makes refresh_token grant request with Canvas to get a fresh
    access token.  Update the oauth token model with the new token
    and new expiration date and return the saved model.
    """
    #oauth_token = request.user.canvas_oauth2_token

    # Get the new access token and expiration date via
    # a refresh token grant
    oauth_token.access_token, oauth_token.expires, _ = canvas.get_access_token(
        domain=settings.CANVAS_OAUTH_CANVAS_DOMAIN,
        grant_type='refresh_token',
        redirect_uri=request.build_absolute_uri(
            reverse('canvas-oauth-callback')),
        refresh_token=oauth_token.refresh_token)

    # Update the model with new token and expiration
    oauth_token.save()

    return oauth_token


def render_oauth_error(error_message):
    """ If there is an error in the oauth callback, attempts to render it in a
        template that can be styled; otherwise, if OAUTH_ERROR_TEMPLATE not
        found, this will return a HttpResponse with status 403 """
    logger.error("OAuth error %s" % error_message)
    try:
        template = loader.render_to_string(settings.CANVAS_OAUTH_ERROR_TEMPLATE,
                                           {"message": error_message})
    except TemplateDoesNotExist:
        return HttpResponse("Error: %s" % error_message, status=403)
    return HttpResponse(template, status=403)
