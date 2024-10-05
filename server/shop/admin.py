from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import *

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('username', 'email', 'phone_number', 'is_staff', 'is_active')
    list_filter = ('is_staff', 'is_active')
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'phone_number')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'phone_number', 'password1', 'password2', 'is_staff', 'is_active')}
        ),
    )
    search_fields = ('username', 'email', 'phone_number')
    ordering = ('username',)

class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'name')
    search_fields = ['name']

class ProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'description', 'price', 'quantity')
    search_fields = ('id', 'name', 'category', 'price')

class CartItemAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity')

class CartItemInline(admin.TabularInline):
    model = Cart.items.through  # This specifies the many-to-many relationship
    extra = 1  # Number of extra forms to display
    
class CartItemInline2(admin.TabularInline):
    model = Payment.items.through  # This specifies the many-to-many relationship
    extra = 1  # Number of extra forms to display
    
class CartItemInline3(admin.TabularInline):
    model = OrderHistory.items.through  # This specifies the many-to-many relationship
    extra = 1  # Number of extra forms to display

class CartAdmin(admin.ModelAdmin):
    inlines = [CartItemInline]
    list_display = ('user', 'items_display', 'amount', 'created_at')
    readonly_fields = ('user', 'amount', 'created_at')

    def items_display(self, obj):
        items = obj.items.all()
        return ', '.join([str(item) for item in items])
    items_display.short_description = 'Items'

    def amount(self, obj):
        return obj.amount
    amount.short_description = 'Total Amount'

class PaymentAdmin(admin.ModelAdmin):
    inlines = [CartItemInline2]
    list_display = ('user', 'amount', 'email', 'reference', 'items_display', 'status', 'date')
    search_fields = ('id', 'reference', 'user__username', 'email')
    readonly_fields = ('user', 'amount', 'email', 'reference', 'items_display', 'status', 'date')
    
    def items_display(self, obj):
        items = obj.items.all()
        return ', '.join([str(item) for item in items])
    items_display.short_description = 'Items'


class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'cart', 'payment', 'delivered', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user', 'cart__id', 'payment__id')
    
class OrderHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'items_display', 'total_price', 'status', 'delivered', 'payment_date')
    list_filter = ('status', 'delivered' ,'payment_date')
    search_fields = ('user__username', 'status', 'delivered')
    readonly_fields = ('id', 'user', 'total_price', 'payment_date')
    
    def items_display(self, obj):
        items = obj.items.all()
        return ', '.join([str(item) for item in items])
    items_display.short_description = 'Items'

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Category, CategoryAdmin)
admin.site.register(Product, ProductAdmin)
admin.site.register(CartItem, CartItemAdmin)
admin.site.register(Cart, CartAdmin)
admin.site.register(Payment, PaymentAdmin)
admin.site.register(Order, OrderAdmin)
admin.site.register(OrderHistory, OrderHistoryAdmin)
