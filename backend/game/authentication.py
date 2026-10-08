from django.core.exceptions import ValidationError
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed

from .models import GameSession


class GameSessionAuthentication(BaseAuthentication):

    def authenticate(self, request):
        token = request.headers.get("X-Session-Token")

        # No token supplied.
        # Let the permission class reject the request.
        if not token:
            return None

        try:
            game_session = (
                GameSession.objects
                .select_related("registration")
                .get(session_token=token)
            )

        except GameSession.DoesNotExist:
            raise AuthenticationFailed(
                "Invalid session token."
            )

        except (ValidationError, ValueError, TypeError):
            raise AuthenticationFailed(
                "Invalid session token."
            )

        if game_session.status == GameSession.Status.COMPLETED:
            raise AuthenticationFailed(
                "Game session is already completed."
            )

        return (
            game_session.registration,
            game_session,
        )

    def authenticate_header(self, request):
        return 'Bearer realm="clueverse"'