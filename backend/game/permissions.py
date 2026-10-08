from rest_framework.permissions import BasePermission


class IsGameSessionAuthenticated(BasePermission):

    def has_permission(self, request, view):
        return (
            request.user is not None
            and getattr(request, "auth", None) is not None
        )