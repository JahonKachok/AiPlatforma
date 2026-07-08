"""Role-based access control helpers shared by every app.

The app's authorization axis is the ``User.role`` field (7 fixed values),
independent of Django's built-in is_staff/is_superuser/Group/Permission
machinery, which is reserved for /django-admin/ access only.
"""
from functools import wraps

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied


def role_required(*roles):
    """Decorator for function-based views: 403s unless the user's role is
    in ``roles`` (or the user is a superuser)."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if request.user.is_superuser or request.user.role in roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return wrapped
    return decorator


class RoleRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Class-based-view equivalent of ``role_required``."""

    allowed_roles: tuple[str, ...] = ()

    def test_func(self):
        user = self.request.user
        return user.is_superuser or user.role in self.allowed_roles
