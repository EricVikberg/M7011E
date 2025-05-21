from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Product, UserProfile, Category

admin.site.register(UserProfile)


class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ('username', 'email', 'user_type', 'is_staff', 'is_superuser')
    search_fields = ('email', 'username')
    ordering = ('email',)

    list_filter = ('user_type', 'is_active', 'date_joined')

    fieldsets = (
        (None, {'fields': ('username', 'email', 'password')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Custom fields', {'fields': ('user_type',)}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'user_type', 'password1', 'password2', 'is_staff', 'is_superuser'),
        }),
    )

    def is_staff(self, obj):
        return obj.user_type == 2  # Staff

    is_staff.boolean = True
    is_staff.short_description = 'Staff status'

    def is_superuser(self, obj):
        return obj.user_type == 1  # SuperUser

    def save_model(self, request, obj, form, change):
        # Uppdatera user_type baserat på is_staff och is_superuser
        if obj.is_superuser:
            obj.user_type = 1  # SuperUser
        elif obj.is_staff:
            obj.user_type = 2  # Staff
        else:
            obj.user_type = 3  # Customer
        super().save_model(request, obj, form, change)

    is_superuser.boolean = True
    is_superuser.short_description = 'Superuser status'


class ProductAdmin(admin.ModelAdmin):
    list_display = ('product_name', 'price', 'stock', 'display_categories')
    search_fields = ('product_name',)
    list_filter = ('price', 'stock')


    def display_categories(self, obj):
        return ", ".join([category.name for category in obj.categories.all()])

    display_categories.short_description = 'Categories'


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_products')  # Visa produktnamn istället för "Product object (1)"

    def display_products(self, obj):
        return ", ".join([product.product_name for product in obj.products.all()])

    display_products.short_description = 'Products'



admin.site.register(Category, CategoryAdmin)

admin.site.register(Product, ProductAdmin)

admin.site.register(User, UserAdmin)
