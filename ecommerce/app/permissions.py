# permissions.py
from rest_framework import permissions

class ReadOnlyOrStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        # Tillåt alla GET, HEAD, OPTIONS requests
        if request.method in permissions.SAFE_METHODS:
            return True
        # Kräv staff/superuser för andra metoder
        return request.user.is_authenticated and request.user.user_type in [1, 2]

class IsStaffOrSuperuser(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)

class CartPermission(permissions.BasePermission):
    """
    Specialbehörighet för Cart:
    - Läs: Tillåt alla (inklusive anonyma)
    - Skriv: Kräver antingen inloggad användare ELLER session
    """

    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        # För POST/PUT/DELETE, kräv antingen inloggning eller session
        return request.user.is_authenticated or request.session.session_key


class OrderPermission(permissions.BasePermission):
    """
    Behörighet för Order:
    - Skapa: Endast inloggade användare
    - Lista: Visa endast användarens egna ordrar (alla för staff/superuser)
    - Läs: Endast ägaren eller staff/superuser
    - Ändra: Endast staff/superuser
    """

    def has_permission(self, request, view):
        # Tillåt alltid säkra metoder (GET, HEAD, OPTIONS)
        # Men filtrering av queryset hanterar vilka ordrar som visas
        if request.method in permissions.SAFE_METHODS:
            return True
        # För POST (skapande) krävs inloggning
        if request.method == 'POST':
            return request.user.is_authenticated
        # För PUT/PATCH/DELETE krävs staff/superuser
        return request.user.is_authenticated and request.user.user_type in [1, 2]

    def has_object_permission(self, request, view, obj):
        # Läsbehörighet: ägaren eller staff/superuser
        if request.method in permissions.SAFE_METHODS:
            return obj.user == request.user or request.user.user_type in [1, 2]

        # Skrivbehörighet: endast staff/superuser
        return request.user.user_type in [1, 2]