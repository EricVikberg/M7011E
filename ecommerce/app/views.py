from django.db import transaction
from django.shortcuts import render

from rest_framework import viewsets, status, permissions
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.views import APIView
from rest_framework.authentication import TokenAuthentication
from .models import Product, Cart, CartItem, Order, OrderItem, UserProfile, Category, User
from .permissions import ReadOnlyOrStaff, CartPermission, OrderPermission, IsStaffOrSuperuser, UserProfilePermission, \
    UserAccessPermission
from .serializers.serializer import (ProductSerializer, CartSerializer, CartItemSerializer,
                                     OrderSerializer, OrderItemSerializer, UserSerializer, LoginSerializer,
                                     UserProfileSerializer, CategorySerializer)


class UserViewSet(viewsets.ModelViewSet):
    """
    API endpoint for managing users.
    - Customers can view/update themselves
    - Staff/superusers have full access
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, UserAccessPermission]  # Använd vår nya permission
    lookup_field = 'username'

    def get_queryset(self):
        user = self.request.user
        if user.user_type == 1:  # SuperUser can see everyone
            return self.queryset.all()
        elif user.user_type == 2:  # Staff can see everyone except superusers
            return self.queryset.exclude(user_type=1)
        # Customers can only see themselves
        return self.queryset.filter(id=user.id)

    def partial_update(self, request, *args, **kwargs):
        user = self.get_object()

        # Spceical handling of changing password
        if 'password' in request.data:

            if not request.data['password']:
                return Response(
                    {"password": ["This field may not be blank."]},
                    status=status.HTTP_400_BAD_REQUEST
                )

            user.set_password(request.data['password'])
            user.save()

            if len(request.data) == 1:
                return Response({"status": "password changed"})

        return super().partial_update(request, *args, **kwargs)
class UserProfileViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows user profiles to be viewed or edited.

    Permissions:
    - GET: All authenticated users can view profiles
      - Users can only view their own profile unless staff/superuser
    - PATCH: Users can edit their own profile, staff/superusers can edit any
    - POST/PUT/DELETE: Disabled via permissions
    """
    serializer_class = UserProfileSerializer
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated, UserProfilePermission]  # Use custom permission
    lookup_field = 'user__username'
    queryset = UserProfile.objects.select_related('user').all()

    def get_queryset(self):
        """Filter queryset based on user permissions"""
        user = self.request.user
        if user.user_type in [1, 2]:  # SuperUser or Staff
            return self.queryset.all()
        return self.queryset.filter(user=user)


class ProductViewSet(viewsets.ModelViewSet):
    """
       API endpoint for managing products.

       Permissions:
       - Read operations allowed for all users
       - Write operations require staff/superuser status
    """
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [ReadOnlyOrStaff]

class CategoryViewSet(viewsets.ModelViewSet):
    """
        API endpoint for managing product categories.

        Permissions:
        - Read operations allowed for all users
        - Write operations require staff/superuser status
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer  # You'll need to create this
    permission_classes = [ReadOnlyOrStaff]  # Only staff/superusers can access

class CartViewSet(viewsets.ModelViewSet):
    """
        API endpoint for managing shopping carts.

        Permissions:
        - Read operations allowed for all (including anonymous users)
        - Write operations require either authenticated user or valid session
    """
    queryset = Cart.objects.all()
    serializer_class = CartSerializer
    permission_classes = [CartPermission]

    def get_queryset(self):
        """Return carts based on user permissions"""
        user = self.request.user

        # Staff/SuperUser can see all carts
        if user.is_authenticated and user.user_type in [1, 2]:  # 1=SuperUser, 2=Staff
            return self.queryset.all()

        # Authenticated customers see only their own cart
        elif user.is_authenticated:
            return self.queryset.filter(user=user)

        # Anonymous users see only their session-based cart
        else:
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            return self.queryset.filter(session_key=session_key)

    def create(self, request, *args, **kwargs):
        """Allow POST only for staff/superusers with valid data"""
        if not request.user.is_staff:
            return Response({"detail": "Permission denied"}, status=403)


class CartItemViewSet(viewsets.ModelViewSet):
    """
        API endpoint for managing cart items.

        Permissions:
        - Same as CartViewSet (inherits CartPermission)
        - Validates stock availability before adding items
    """
    serializer_class = CartItemSerializer
    queryset = CartItem.objects.select_related('product')
    authentication_classes = []  # Allow anonymous access
    permission_classes = [CartPermission] # Remove all permission checks

    def get_queryset(self):
        # check if logged in
        if self.request.user.is_authenticated:
            return self.queryset.filter(cart__user=self.request.user)
        else:
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
                return self.queryset.none()
        return self.queryset.filter(cart__session_key=session_key)

    def perform_create(self, serializer):
        with transaction.atomic():
            product = serializer.validated_data['product']
            quantity = serializer.validated_data['quantity']

            # Check if logged in
            if self.request.user.is_authenticated:
                # For authenticated users
                cart,_ = Cart.objects.get_or_create(user=self.request.user)
            else:
                # For anonymous user s
                session_key = self.request.session.session_key
                if not session_key:
                    self.request.session.create()
                    session_key = self.request.session.session_key
                cart, _ = Cart.objects.get_or_create(session_key=session_key,defaults={'user': None})


            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={
                    'quantity': quantity,
                    'price' : product.price
                })

            if not created:
                cart_item.quantity += quantity
                cart_item.price = product.price
                cart_item.save()

            serializer.instance = cart_item

class OrderViewset(viewsets.ModelViewSet):
    """
       API endpoint for managing orders.

       Permissions:
       - Customers can create and view their own orders
       - Staff/superusers can view all orders
       - Only staff/superusers can modify/delete orders
    """
    serializer_class = OrderSerializer
    queryset = Order.objects.prefetch_related('items__product')
    permission_classes = [OrderPermission]

    def get_queryset(self):
        """Filter orders based on user permissions"""
        if self.request.user.is_authenticated:
            if self.request.user.user_type in [1, 2]:  # Staff/superuser can see all
                return self.queryset.all()
            return self.queryset.filter(user=self.request.user)
        return self.queryset.none()


    def create(self, request, *args, **kwargs):
        """
                Create an order from cart contents.
                Validates stock and processes order atomically.
        """
        with transaction.atomic():
            cart = Cart.objects.get(user=request.user)

            # Check if there even are any items in the cart
            if not cart.items.exists():
                return Response({'error': 'Cart is empty'}, status=status.HTTP_400_BAD_REQUEST)

            # Verify the stock and lock products
            products = {}
            for item in cart.items.select_related('product').select_for_update(): #Select_related for JOIN and select_for_update to lock the rows in the database,.
                if item.quantity > item.product.stock:
                    return Response({'error': 'Product quantity exceeds stock'}, status=status.HTTP_400_BAD_REQUEST)
                products[item.product.product_id] = item.product

            # Create an order
            order = Order.objects.create(
                user=request.user,
                total_price=sum(item.product.price * item.quantity for item in cart.items.all())
            )

            # Create order items and remove them from the stock
            order_items = []
            for item in cart.items.all():
                product = products[item.product.product_id]
                order_items.append(OrderItem(
                    order=order,
                    product=product,
                    quantity=item.quantity,
                    price=item.price
                ))
                product.stock -= item.quantity
                product.save()

            OrderItem.objects.bulk_create(order_items)
            cart.items.all().delete()

            return Response(
                self.get_serializer(order).data,
                status=status.HTTP_201_CREATED
            )
class CustomAuthToken(ObtainAuthToken):
    """
        Custom token authentication endpoint that:
        - Returns user details along with token
        - Merges anonymous cart with user cart on login
    """
    serializer_class = LoginSerializer

    def post(self, request, *args, **kwargs):
        """Authenticate user and return token with user data"""
        serializer = self.serializer_class(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        Token.objects.filter(user=user).delete()

        # Create new token
        token, created = Token.objects.get_or_create(user=user)

        # Merge session-based cart with user cart
        self.merge_carts(request, user)

        return Response({
            'token': token.key,
            'user_id': user.pk,
            'email': user.email,
            'user_type' : user.get_user_type_display(),
        })

    def merge_carts(self, request, user):
        """Merge anonymous session cart with authenticated user cart"""
        session_key = request.session.session_key
        if not session_key:
            return

        with transaction.atomic():
            try:
                # Get anonymous cart with prefetched items
                anonymous_cart = Cart.objects.prefetch_related('items').get(session_key=session_key)

                # Get or create user cart with prefetch
                user_cart, created = Cart.objects.prefetch_related('items').get_or_create(user=user)

                # Create a mapping of product IDs to items in user cart for quick lookup
                user_items_map = {item.product_id: item for item in user_cart.items.all()}

                # Process each anonymous cart item
                for anonymous_item in anonymous_cart.items.all():
                    if anonymous_item.product_id in user_items_map:
                        # Item exists in user cart - update quantity
                        user_item = user_items_map[anonymous_item.product_id]
                        user_item.quantity += anonymous_item.quantity
                        user_item.save()
                    else:
                        # Item doesn't exist - move to user cart
                        anonymous_item.cart = user_cart
                        anonymous_item.save()

                # Delete the anonymous cart (items are already transferred)
                anonymous_cart.delete()

                # Update session if needed
                if hasattr(request, 'session'):
                    request.session.pop('cart_id', None)

            except Cart.DoesNotExist:
                pass

class RegisterView(APIView):
    """
        API endpoint for user registration.
        Creates both User and UserProfile with optional profile data.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        """Register new user with optional profile data"""
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token = Token.objects.create(user=user)

            # data for auto-created profile
            profile_data = {
                'phone_number': request.data.get('phone_number'),
                'address': request.data.get('address'),
                'date_of_birth': request.data.get('date_of_birth')
            }
            if any(profile_data.values()):  # If any profile data provided
                profile_serializer = UserProfileSerializer(
                    instance=user.profile,
                    data=profile_data,
                    partial=True
                )
                if profile_serializer.is_valid():
                    profile_serializer.save()

            return Response({
                'token': token.key,
                'user' : UserSerializer(user).data,
            }, status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    """
        API endpoint for logging out users.

        - Requires authentication
        - Deletes the current user's token (logout)
    """
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        try:
            # Delete the user's current token
            token = Token.objects.get(user=user)
            token.delete()
            return Response({"message": "Successfully logged out."}, status=status.HTTP_200_OK)
        except Token.DoesNotExist:
            return Response({"error": "Token not found."}, status=status.HTTP_400_BAD_REQUEST)