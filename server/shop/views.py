# views.py
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import auth
from django.contrib import messages
from .models import *
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from .paystack import initialize_payment, verify_payment

# Create your views here.
@method_decorator(csrf_exempt, name='dispatch')
class UpdateCartQuantitiesView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        for cart_item_id, quantity in data.items():
            cart_item = CartItem.objects.get(id=cart_item_id)
            cart_item.quantity = quantity
            cart_item.save()
        return JsonResponse({'success': True})

@login_required
def add_to_cart(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item, created = CartItem.objects.get_or_create(product=product)
    cart.items.add(cart_item)
    messages.success(request, f'{cart_item} added to cart!')
    return redirect('store')

@login_required
def delete_item(request, pk):
    product = get_object_or_404(Product, pk=pk)
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item = get_object_or_404(CartItem, product=product)
    cart.items.remove(cart_item)
    messages.error(request, f'{cart_item} removed from cart!')
    return redirect('store')

@login_required
def view_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    return render(request, 'checkout.html', {'cart': cart})  # Ensure the template name matches

@login_required
def home(request):
    return render(request, 'home.html')

@login_required
def store(request):
    products = Product.objects.all()
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)
    context = {
        'cart_items': cart_items,
        'cart': cart,
        'products': products,
    }

    return render(request, 'index.html', context)  # Ensure the template name matches

@login_required
def profile(request):
    return render(request, 'profile.html', {})

@login_required
def checkout(request):
    return render(request, 'checkout.html', {})

def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        password2 = request.POST['password2']
        if password1 == password2:
            user = User.objects.create_user(username, email, password1)
            user.save()
            return redirect('login')
        return render(request, 'signup.html', {'success': 'Account created successfully'})
    return render(request, 'signup.html')

def login(request):
    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user:
            auth.login(request, user)
            return redirect('store')
        else:
            return render(request, 'login.html', {'error': 'Invalid credentials'})
    return render(request, 'login.html')

def logout(request):
    auth.logout(request)
    return redirect('login')

def clear_user_cart(user):
    # Assuming you have a Cart model that links to the user
    cart = Cart.objects.get(user=user)
    cart.items.clear()  # Clear all items in the cart

def initialize_payment_view(request):
    if request.method == 'POST':
        # Retrieve the user's cart
        cart = Cart.objects.get(user=request.user)
        items = cart.items.all()
        amount = cart.amount
        email = request.user.email
        callback_url = request.build_absolute_uri('/payments/verify/')

        payment_data = initialize_payment(amount, email, callback_url)

        if payment_data and 'reference' in payment_data:
            payment = Payment.objects.create(
                user=request.user,
                amount=amount,
                email=email,
                reference=payment_data['reference'],
                status='pending',
                order_id=cart  # Ensure this line is correct
            )
            order = Order.objects.create(
                user=request.user,
                cart=cart,  # Pass the actual Cart instance
                payment=payment,
                status='completed',
            )
            print(f"Order created: {order}")  # Add this line for debugging
            return redirect(payment_data['authorization_url'])
        else:
            # Handle the error case
            return render(request, 'payments/initialize.html', {'error': 'Payment initialization failed'})

    # If the request method is not POST, render the initialize.html page
    cart = Cart.objects.get(user=request.user)
    cart_items = cart.items.all()  # Retrieve the related CartItem instances
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'amount': cart.amount,
        'email': request.user.email,
    }
    return render(request, 'payments/initialize.html', context)

def verify_payment_view(request):
    reference = request.GET.get('reference')

    if not reference:
        return JsonResponse({'status': 'failed', 'message': 'Reference not provided'})

    payment_data = verify_payment(reference)

    if payment_data:
        try:
            payment = Payment.objects.get(reference=reference)
            payment.status = payment_data['status']
            payment.save()

            # Redirect to the payment_success view after successful verification
            return redirect('payment_success')
        except Payment.DoesNotExist:
            return JsonResponse({'status': 'failed', 'message': 'Payment not found'})

    return JsonResponse({'status': 'failed', 'message': 'Payment verification failed'})

# @login_required
# def order(request):
#     user = request.user
#     payments = Payment.objects.filter(user=user).order_by('-date')
#     orders = Order.objects.filter(user=user).order_by('-created_at')

#     context = {
#         'orders': orders,
#         'payments': payments,
#     }
#     return render(request, 'orders.html', context)

@login_required
def payment_success(request):
    print("Order is being created")

    # Assuming you have a way to get the user's cart items
    cart = Cart.objects.get(user=request.user)
    cart_items = cart.items.all()

    # Calculate the total price
    total_price = sum(item.total for item in cart_items)

    # Assuming you have a way to get the Payment instance
    # This could be from a session, a form submission, or any other method
    payment = Payment.objects.filter(user=request.user).latest('date')

    # Create a new order history entry
    order_history = OrderHistory.objects.create(
        user=request.user,
        total_price=total_price,
        payment=payment  # Link the Payment instance to the OrderHistory instance
    )
    order_history.items.set(cart_items)

    # Optionally, update the reference field in OrderHistory if needed
    order_history.reference = payment.reference
    order_history.save()

    # Clear the cart
    clear_user_cart(request.user)
    print("Order Created!")

    # Redirect to the order history page or any other page
    return redirect('order_history')

@login_required
def order_history(request):
    orders = OrderHistory.objects.filter(user=request.user).order_by('-payment_date')
    return render(request, 'order_history.html', {'orders': orders})
