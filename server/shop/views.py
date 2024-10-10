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
    return render(request, 'checkout.html', {'cart': cart})

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

    return render(request, 'index.html', context)

@login_required
def profile(request):
    user = request.user
    user_profile, created = Profile.objects.get_or_create(user=user)


    if request.method == 'POST':
        user.first_name = request.POST['first_name']
        user.last_name = request.POST['last_name']
        user_profile.phone_number = request.POST['phone_number']
        user.save()
        user_profile.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('update_profile')
    
    context = {
        'user': user, 
        'user_profile': user_profile,
    }

    return render(request, 'update_profile.html', context)

@login_required
def checkout(request):
    return render(request, 'checkout.html', {})

def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        phone_number = request.POST['phone']
        if password1:
            user = User.objects.create_user(username, email, password1)
            user.save()
            
            user_profile, created = Profile.objects.get_or_create(user=user)
            user_profile.phone_number = phone_number
            user_profile.save()

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
    cart = Cart.objects.get(user=user)
    cart.items.clear()

def initialize_payment_view(request):
    if request.method == 'POST':
        location = request.POST.get('location')
        if not location:
            return render(request, 'payments/initialize.html', {'error': 'Location is required'})

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
                order_id=cart
            )
            order = Order.objects.create(
                user=request.user,
                cart=cart,
                payment=payment,
                status='completed',
                location=location
            )
            print(f"Order created: {order}")
            return redirect(payment_data['authorization_url'])
        else:
            return render(request, 'payments/initialize.html', {'error': 'Payment initialization failed'})

    cart = Cart.objects.get(user=request.user)
    cart_items = cart.items.all()
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
            
            cart = Cart.objects.get(user=request.user)
            cart_items = cart.items.all()
            for cart_item in cart_items:
                cart_item.quantity = 1
                cart_item.save()

            return redirect('payment_success')
        except Payment.DoesNotExist:
            return JsonResponse({'status': 'failed', 'message': 'Payment not found'})

    return JsonResponse({'status': 'failed', 'message': 'Payment verification failed'})

@login_required
def payment_success(request):
    print("Order is being created")

    cart = Cart.objects.get(user=request.user)
    cart_items = cart.items.all()

    total_price = sum(item.total for item in cart_items)

    payment = Payment.objects.filter(user=request.user).latest('date')
    
    order = Order.objects.filter(user=request.user).latest('created_at')

    order_history = OrderHistory.objects.create(
        user=request.user,
        total_price=total_price,
        location=order.location
    )
    order_history.items.set(cart_items)

    order_history.reference = payment.reference
    order_history.save()

    clear_user_cart(request.user)
    print("Order Created!")

    return redirect('order_history')

@login_required
def order_history(request):
    orders = OrderHistory.objects.filter(user=request.user).order_by('-payment_date')
    return render(request, 'order_history.html', {'orders': orders})
