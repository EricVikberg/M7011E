from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import ProductViewSet, CartViewSet, CartItemViewSet, OrderViewset, RegisterView, CustomAuthToken, \
    UserProfileViewSet, CategoryViewSet, LogoutView

router = DefaultRouter()
router.register(r'products', ProductViewSet, basename='products')
router.register(r'cart', CartViewSet, basename='cart')
router.register(r'cart-items', CartItemViewSet, basename='cart-items')
router.register(r'order', OrderViewset, basename='order')
router.register(r'user-profile', UserProfileViewSet, basename='userprofile')
router.register(r'categories', CategoryViewSet, basename='categories')

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', CustomAuthToken.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

] + router.urls

# Add custom views like CartView manually
