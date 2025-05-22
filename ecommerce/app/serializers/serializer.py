from rest_framework import serializers
from django.contrib.auth import authenticate
from app.models import Product, CartItem, Cart, OrderItem, Order, User, UserProfile, Category


class ProductSerializer(serializers.ModelSerializer):
    """
        Serializer for Product model.

        Fields:
        - Includes all product fields
        - Displays category names using SlugRelatedField (read-only)
    """
    categories = serializers.SlugRelatedField(
        many=True,
        read_only=True,
        slug_field='name'  # Visar bara kategorinamnen
    )

    class Meta:
        model = Product
        fields = ['product_id', 'product_name', 'price', 'product_info', 'categories']

    def get_fields(self):
        """ Stock is only for staff/superusers."""
        fields = super().get_fields()
        request = self.context.get('request')

        if request and request.user.is_authenticated and request.user.user_type in [1, 2]:
            fields['stock'] = serializers.IntegerField()

        return fields

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        request = self.context.get('request')

        if not (request and request.user.is_authenticated and request.user.user_type in [1, 2]):
            representation['status'] = 'In stock' if instance.stock > 0 else 'Out of stock'
            representation.pop('stock', None)

        return representation

class CategorySerializer(serializers.ModelSerializer):
    """
        Serializer for Category model.

        Fields:
        - id, name, and associated product IDs
        - products field is writable, allowing staff to assign products
    """
    products = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Product.objects.all(),
        required=False
    )
    class Meta:
        model = Category
        fields = ['id', 'name', 'products']

    def update(self, instance, validated_data):

        updated_products = validated_data.pop('products', [])

        existing_products = set(instance.products.all())

        for product in updated_products:
            if product in existing_products:
                instance.products.remove(product)
            else:
                instance.products.add(product)

        return super().update(instance, validated_data)
    def to_representation(self, instance):
        """Customize the output format of the category"""
        representation = super().to_representation(instance)
        # Ersätt "products": [id, id, ...] med detaljer
        representation['products'] = [
            {
                'id': product.product_id,
                'name': product.product_name
            } for product in instance.products.all()
        ]
        return representation

class CartItemSerializer(serializers.ModelSerializer):
    """
        Serializer for CartItem model.

        Fields:
        - Shows product name, price, available stock, and total price
        - Validates quantity does not exceed available stock
    """
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.CharField(source='product.price', read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name',
                  'product_price', 'quantity', 'price', 'total_price']
        extra_kwargs = {'product':{'required':True},
                        'quantity':{'min_value':1},
                        'price':{'read_only':True}
        }

    def get_available_stock(self, obj):
        return obj.product.stock

    def get_total_price(self, obj):
        return obj.price * obj.quantity

    def validate(self, data):
        product = data.get('product')
        quantity = data.get('quantity', 1)

        if product and quantity > product.stock:
            raise serializers.ValidationError(
                f"Only {product.stock} items available in stock"
            )
        return data

class CartSerializer(serializers.ModelSerializer):
    """
        Serializer for Cart model.

        Fields:
        - Includes cart metadata and list of items
        - Calculates total cart price
    """
    items = CartItemSerializer(many=True, read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = ['cart_id', 'user', 'created_at', 'updated_at',
                  'items', 'total_price']
        read_only_fields = ['user', 'created_at', 'updated_at']

    def get_total_price(self, obj):
        return sum(item.price * item.quantity for item in obj.items.all())

    def get_is_authenticated(self, obj):
        request = self.context.get('request')
        return request.user.is_authenticated if request else False


class OrderItemSerializer(serializers.ModelSerializer):
    """
        Serializer for OrderItem model.

        Fields:
        - Includes product name, quantity, individual price, and total price
    """
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'total_price']
        read_only_fields = ['price', 'total_price']

    def get_total_price(self, obj):
        return obj.price * obj.quantity

class OrderSerializer(serializers.ModelSerializer):
    """
        Serializer for Order model.

        Fields:
        - Includes user, order metadata, items, and calculated total price
    """
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['order_id', 'user', 'user_email','total_price', 'created_at', 'updated_at', 'items']
        read_only_fields = ['user','created_at', 'updated_at']

    def get_total_price(self, obj):
        return sum(item.total_price for item in obj.items.all())

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    email = serializers.EmailField(required=True)
    user_type_display = serializers.CharField(source='get_user_type_display', read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password',
            'user_type', 'user_type_display',
            'date_joined'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'user_type': {'read_only': True},
            'email': {'required': True},
        }

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("This email is already in use")
        return value

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            user_type=validated_data.get('user_type', 3),
        )
        return user

class UserProfileSerializer(serializers.ModelSerializer):
    """
        Serializer for User model (registration and detail).

        Fields:
        - Includes username, email, names, user_type (read-only), and password (write-only)
        - Validates unique email
    """
    email = serializers.EmailField(source='user.email', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = UserProfile
        fields = ['phone_number', 'address', 'date_of_birth', 'loyalty_points',
                  'email', 'username']
        read_only_fields = ['loyalty_points']

class LoginSerializer(serializers.Serializer):
    """
        Serializer for login credentials.

        Validates:
        - Username and password presence
        - User authentication status and activity
    """
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username=data.get('username')
        password=data.get('password')

        if not password:
            raise serializers.ValidationError("Password is required!")

        if username:
            user = authenticate(username=username, password=password)
        else:
            raise serializers.ValidationError("Username is required!")

        if not user:
            raise serializers.ValidationError("Invalid credentials")
        if not user.is_active:
            raise serializers.ValidationError("User is not active")
        return user
