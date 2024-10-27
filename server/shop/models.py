# models.py
import random
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_rider = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            Profile.objects.create(user=instance)

    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        instance.profile.save()

class Category(models.Model):
    name = models.CharField(max_length=55)

    def __str__(self):
        return self.name

class Product(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=55)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    description = models.TextField()
    image = models.ImageField(upload_to="Product_Image")
    price = models.FloatField()
    sales = models.IntegerField(default=0)
    is_available = models.BooleanField(null=True, blank=True)

    def __str__(self):
        return self.name

class CartItem(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    @property
    def total(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

class Cart(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    items = models.ManyToManyField(CartItem, blank=True)
    delivery = models.IntegerField(default=400, null=True, blank=True)
    service_fee = models.IntegerField(default=50, null=True, blank=True)
    status = models.CharField(max_length=50, default="pending", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    @property
    def item_count(self):
        return self.items.count()
    @property
    def amount(self):
        return sum(item.total for item in self.items.all())
    @property
    def subtotal(self):
        return self.amount + self.delivery + self.service_fee

    def __str__(self):
        return f"{self.user.username}'s Cart"


class Payment(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('paystack', 'Paystack'),
        ('cash', 'Cash on Delivery'),
    ]

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.IntegerField()
    delivery = models.IntegerField(default=400, null=True, blank=True)
    service_fee = models.IntegerField(default=50, null=True, blank=True)
    total_amount = models.IntegerField(null=True, blank=True)
    email = models.EmailField()
    reference = models.CharField(max_length=255, blank=True, null=True)
    status = models.CharField(max_length=15, default="processing")
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='paystack')
    items = models.ManyToManyField(CartItem, blank=True)
    order_id = models.ForeignKey(Cart, on_delete=models.CASCADE, blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}' payment of {self.amount}"
    
class Order(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    cart = models.CharField(max_length=255, blank=True, null=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, blank=True, null=True)
    PAYMENT_METHOD_CHOICES = [
        ('paystack', 'Paystack'),
        ('cash', 'Cash on Delivery'),
    ]
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='paystack')
    location = models.CharField(max_length=255, null=True)
    delivered = models.BooleanField(default=None, blank=True, null=True)
    status = models.CharField(max_length=50, default="completed")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"
    

class OrderHistory(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    user_order = models.CharField(max_length=255, blank=True, null=True)
    reference = models.CharField(max_length=255, null=True, blank=True)
    location = models.CharField(max_length=255, null=True)
    delivery = models.IntegerField(default=400, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    PAYMENT_METHOD_CHOICES = [
        ('paystack', 'Paystack'),
        ('cash', 'Cash on Delivery'),
    ]
    payment_method = models.CharField(max_length=10, choices=PAYMENT_METHOD_CHOICES, default='paystack')
    status = models.CharField(
        max_length=50,
        choices=[
            ('Sent', 'Order Sent'),
            ('Received', 'Order Received'),
            ('Ready', 'Order Ready'),
            ('Delivered', 'Order Delivered'),
        ],
        default='Sent',
    )
    rider = models.CharField(
        max_length=50,
        choices=[
            ('LCU Errands', 'lcu_errands'),
            ('Green Baba Delivery', 'greenbaba'),
        ],
        default='Not Picked',
    )
    delivered = models.BooleanField(default=None, blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"

    @property
    def phone_number(self):
        try:
            return self.user.profile.phone_number
        except Profile.DoesNotExist:
            return None