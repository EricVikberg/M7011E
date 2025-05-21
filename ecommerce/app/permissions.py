# permissions.py
from rest_framework import permissions

class ReadOnlyOrStaff(permissions.BasePermission):
    """
        Permission class for read/write access to public resources.

        Permissions:
        - Allow all users to perform safe methods (GET, HEAD, OPTIONS)
        - Require staff or superuser status for write methods (POST, PUT, PATCH, DELETE)
    """
    def has_permission(self, request, view):
        # Tillåt alla GET, HEAD, OPTIONS requests
        if request.method in permissions.SAFE_METHODS:
            return True
        # Kräv staff/superuser för andra metoder
        return request.user.is_authenticated and request.user.user_type in [1, 2]

class IsStaffOrSuperuser(permissions.BasePermission):
    """
        Permission class for admin-only access.

        Permissions:
        - Require authenticated user with either is_staff or is_superuser = True
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser)

class CartPermission(permissions.BasePermission):
    """
    Permission class for cart-related operations.

    Permissions:
    - Read: Allow all users (including anonymous sessions)
    - Write: Require either authenticated user or active session
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True

        return request.user.is_authenticated or request.session.session_key


class OrderPermission(permissions.BasePermission):
    """
    Permission class for managing orders.

    Permissions:
    - Create (POST): Require authenticated user
    - Read (GET): Allow if user owns the order or is staff/superuser
    - Update/Delete (PUT/PATCH/DELETE): Only allowed for staff/superuser
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


class UserProfilePermission(permissions.BasePermission):
    """
    Custom permission for UserProfile:
    - Safe methods (GET, HEAD, OPTIONS) allowed for all authenticated users
    - PATCH allowed for profile owner or staff/superuser
    - All other methods (POST, PUT, DELETE) disabled
    """

    def has_permission(self, request, view):
        # Allow safe methods for authenticated users
        if request.method in permissions.SAFE_METHODS:
            return request.user.is_authenticated

        # Only allow PATCH for profile updates
        if request.method == 'PATCH':
            return request.user.is_authenticated

        # Block all other methods (POST, PUT, DELETE)
        return False

    def has_object_permission(self, request, view, obj):
        # For safe methods, check if user is owner or staff/superuser
        if request.method in permissions.SAFE_METHODS:
            return obj.user == request.user or request.user.user_type in [1, 2]

        # For PATCH, check if user is owner or staff/superuser
        if request.method == 'PATCH':
            return obj.user == request.user or request.user.user_type in [1, 2]

        return False


class UserAccessPermission(permissions.BasePermission):
    """
    Custom permission for User access:
    - Customers can view and update their own profile (including password)
    - Staff/superusers have full access
    """

    def has_permission(self, request, view):
        # Alla autentiserade användare kan komma åt vyer för att se/uppdatera sig själva
        return request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        # Staff/superusers har full åtkomst
        if request.user.user_type in [1, 2]:
            return True

        # Customers kan bara komma åt sin egen användare
        return obj == request.user