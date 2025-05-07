from rest_framework import serializers
from app.models import Product, CartItem, Cart, OrderItem, Order


class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = '__all__'

class CartItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)
    product_price = serializers.CharField(source='product.price', read_only=True)
    available_stock = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = ['id', 'product', 'product_name',
                  'product_price', 'quantity', 'price', 'available_stock', 'total_price']
        extra_kwargs = {'product':{'required':True},
                        'quantity':{'min_value':1}
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
    product_name = serializers.CharField(source='product.product_name', read_only=True)
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'price', 'total_price']
        read_only_fields = ['price', 'total_price']

    def get_total_price(self, obj):
        return obj.price * obj.quantity

class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    total_price = serializers.SerializerMethodField()
    class Meta:
        model = Order
        fields = ['order_id', 'user', 'user_email','total_price', 'created_at', 'updated_at', 'items']
        read_only_fields = ['user','created_at', 'updated_at']

    def get_total_price(self, obj):
        return sum(item.total_price for item in obj.items.all())