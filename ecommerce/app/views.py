from django.db import transaction
from django.shortcuts import render

from rest_framework import viewsets, status
from rest_framework.response import Response

from .models import Product, Cart, CartItem, Order, OrderItem
from .serializers.product_serializer import (ProductSerializer, CartSerializer, CartItemSerializer,
                                             OrderSerializer, OrderItemSerializer)


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer

class CartViewSet(viewsets.ModelViewSet):
    queryset = Cart.objects.all()
    serializer_class = CartSerializer

    # ccheck to see if user is logged in, or if in need of a session key-based cart
    def get_queryset(self):
        if self.request.user.is_authenticated:
            return self.queryset.filter(user=self.request.user)
        else:
            session_key = self.request.session.session_key
            if not session_key:
                self.request.session.create()
                session_key = self.request.session.session_key
            return self.queryset.filter(session_key=session_key)

class CartItemViewSet(viewsets.ModelViewSet):
    serializer_class = CartItemSerializer
    queryset = CartItem.objects.select_related('product')

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
    serializer_class = OrderSerializer
    queryset = Order.objects.prefetch_related('items__product')

    def get_queryset(self):
        if self.request.user.is_authenticated:
           return self.queryset.filter(user=self.request.user)
        return self.queryset.all()


    def create(self, request, *args, **kwargs):
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
