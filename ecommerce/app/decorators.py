from functools import wraps
from rest_framework.exceptions import PermissionDenied, NotAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication


def auth_required(view_func):
    """Kräver autentisering men ingen specifik behörighet"""

    @wraps(view_func)
    def wrapped_view(self, request, *args, **kwargs):
        # Använd både Token och Session autentisering
        authenticators = [TokenAuthentication(), SessionAuthentication()]
        user_auth_tuple = None

        for authenticator in authenticators:
            try:
                user_auth_tuple = authenticator.authenticate(request)
            except:
                continue

            if user_auth_tuple is not None:
                request.user, request.auth = user_auth_tuple
                break

        if not request.user.is_authenticated:
            raise NotAuthenticated("Authentication required")

        return view_func(self, request, *args, **kwargs)

    return wrapped_view


def staff_or_superuser_required(view_func):
    """Kräver att användaren är staff eller superuser"""

    @wraps(view_func)
    def wrapped_view(self, request, *args, **kwargs):
        # Använd auth_required först
        response = auth_required(view_func)(self, request, *args, **kwargs)

        if request.user.user_type not in [1, 2]:  # 1=SuperUser, 2=Staff
            raise PermissionDenied("Staff or superuser required")

        return response

    return wrapped_view


def allow_any(view_func):
    """Tillåt alla, inklusive anonyma användare"""

    @wraps(view_func)
    def wrapped_view(self, request, *args, **kwargs):
        # Försök autentisera om möjligt, men kräv inte det
        print("allow_any decorator körs")
        authenticators = [TokenAuthentication(), SessionAuthentication()]

        for authenticator in authenticators:
            try:
                user_auth_tuple = authenticator.authenticate(request)
                if user_auth_tuple is not None:
                    request.user, request.auth = user_auth_tuple
                    break
            except:
                continue

        return view_func(self, request, *args, **kwargs)

    return wrapped_view