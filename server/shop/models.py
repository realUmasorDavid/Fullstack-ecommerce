# models.py
from django.db import models
from django.contrib.auth.models import User, AbstractUser, Group, Permission

class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    # Add unique related_name for groups and user_permissions
    groups = models.ManyToManyField(
        Group,
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name='customuser_set',  # Unique related_name
        related_query_name='customuser'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name='customuser_set',  # Unique related_name
        related_query_name='customuser'
    )

    def __str__(self):
        return self.username


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
    quantity = models.IntegerField()

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
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    items = models.ManyToManyField(CartItem, blank=True)
    status = models.CharField(max_length=50, default="pending", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    @property
    def item_count(self):
        return self.items.count()
    @property
    def amount(self):
        return sum(item.total for item in self.items.all())

    def __str__(self):
        return f"{self.user.username}'s Cart"


class Payment(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    amount = models.IntegerField()
    email = models.EmailField()
    reference = models.CharField(max_length=255)
    status = models.CharField(max_length=15, default="processing")
    items = models.ManyToManyField(CartItem, blank=True)
    order_id = models.ForeignKey(Cart, on_delete=models.CASCADE, blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username}' payment of {self.amount}"
    
class Order(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, blank=True, null=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, blank=True, null=True)
    delivered = models.BooleanField(default=None, blank=True, null=True)
    status = models.CharField(max_length=50, default="completed")
    created_at = models.DateTimeField(auto_now_add=True, blank=True, null=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"
    

class OrderHistory(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    items = models.ManyToManyField(CartItem)
    reference = models.CharField(max_length=255, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=50, default="not ready", null=True, blank=True)
    delivered = models.BooleanField(default=None, blank=True, null=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Order {self.id} by {self.user.username}"