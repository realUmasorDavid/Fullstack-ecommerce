# views.py
import os
import json
import hmac
import hashlib
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.utils import timezone
from datetime import timedelta
from decouple import config
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
import logging
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Sum, Count
from django.contrib import auth, messages
from django.conf import settings
from .models import *
import json
from django.http import JsonResponse, HttpResponseForbidden, HttpResponseServerError, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views import View
from .paystack import initialize_payment, verify_payment

# Create your views here.
@method_decorator(csrf_exempt, name='dispatch')
class UpdateCartQuantitiesView(View):
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        user = request.user
        for cart_item_id, quantity in data.items():
            cart_item = CartItem.objects.get(id=cart_item_id, user=user)
            cart_item.quantity = quantity
            cart_item.save()
        return JsonResponse({'success': True})

@login_required
@require_POST
def add_to_cart(request, pk):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        product = get_object_or_404(Product, pk=pk)
        user = request.user

        # Get or create the user's cart
        cart, created = Cart.objects.get_or_create(user=user)

        # Check if the product is already in the user's cart
        cart_item, created = CartItem.objects.get_or_create(user=user, product=product)

        if not created:
            # If the item already exists, increase the quantity
            cart_item.quantity += 1
            cart_item.save()

        # Add the cart_item to the cart
        cart.items.add(cart_item)

        # Check if the added product is under 'Main Meal' category
        if product.category.name == 'Main Meal':
            try:
                pack_product = Product.objects.get(name='Pack')
                pack_in_cart = CartItem.objects.filter(user=user, product=pack_product).exists()

                if not pack_in_cart:
                    cart_item_pack, created = CartItem.objects.get_or_create(user=user, product=pack_product, defaults={'quantity': 1})
                    if created:
                        cart.items.add(cart_item_pack)
                        cart.save()
            except Product.DoesNotExist:
                pass  # Handle a case where 'Pack' product does not exist

        # Fetch the newly added cart item data
        cart_item_data = {
            'id': cart_item.id,
            'name': cart_item.product.name,
            'price': cart_item.product.price,
            'quantity': cart_item.quantity,
            'total': cart_item.total,
            'image': cart_item.product.image.url
        }

        return JsonResponse({'success': True, 'message': f'{cart_item} added to cart!', 'cart_item': cart_item_data})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

@login_required
def delete_item(request, pk):
    product = get_object_or_404(Product, pk=pk)
    user = request.user
    cart = Cart.objects.get(user=user)
    cart_item = get_object_or_404(CartItem, product=product, user=user)

    # Check if the item being deleted is the 'Pack' product
    if product.name == 'Pack':
        main_meal_items = CartItem.objects.filter(user=user, product__category__name='Main Meal')
        if main_meal_items.exists():
            messages.error(request, 'A Pack is required for your order.')
            return redirect('initialize_payment')

    cart.items.remove(cart_item)
    cart_item.delete()

    # Check if the removed product is a 'Main Meal'
    if product.category.name == 'Main Meal':
        main_meal_items = CartItem.objects.filter(user=user, product__category__name='Main Meal')
        if not main_meal_items.exists():
            try:
                pack_product = Product.objects.get(name='Pack')
                pack_cart_item = get_object_or_404(CartItem, product=pack_product, user=user)
                cart.items.remove(pack_cart_item)
                pack_cart_item.delete()
                cart.save()
            except Product.DoesNotExist:
                pass  # Handle the case where 'Pack' product does not exist

    messages.error(request, f'{cart_item} removed from cart!')
    return redirect('initialize_payment')

@require_GET
def get_cart(request):
    # Fetch the cart of the current user
    user = request.user
    try:
        cart = Cart.objects.get(user=user)
        cart_data = {
            'item_count': cart.item_count,
        }
        response = {
            'success': True,
            'cart': cart_data
        }
    except Cart.DoesNotExist:
        response = {
            'success': False,
            'message': 'Cart not found'
        }

    return JsonResponse(response)

@login_required
def home(request):
    return render(request, 'home.html')

@login_required
def store(request):
    categories = Category.objects.all()
    selected_category = request.GET.get('category')

    if selected_category:
        products = Product.objects.filter(category__name=selected_category, is_available=True).exclude(name='Packaging')
    else:
        products = Product.objects.filter(is_available=True).exclude(name='Pack')

    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = CartItem.objects.filter(cart=cart)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        products_data = list(products.values('id', 'name', 'price', 'image', 'is_available'))
        for product in products_data:
            product['image'] = request.build_absolute_uri(settings.MEDIA_URL + product['image'])
        return JsonResponse(products_data, safe=False)

    context = {
        'cart_items': cart_items,
        'cart': cart,
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
    }

    return render(request, 'index.html', context)

@require_POST
def toggle_availability(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_available = not product.is_available
    product.save()
    
    response_data = {
            'is_available': product.is_available,
            'name': product.name,
        }

    return JsonResponse(response_data)

@login_required
def search_products(request):
    query = request.GET.get('query', '')
    if query:
        products = Product.objects.filter(name__icontains=query, is_available=True)
    else:
        products = Product.objects.filter(is_available=True).exclude(name='Pack')

    products_data = [
        {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'image': product.image.url,
            'is_available': product.is_available
        }
        for product in products
    ]
    return JsonResponse(products_data, safe=False)

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

def normalize_phone_number(phone_number):
    # Removes any leading zeros and add the country code
    if phone_number.startswith('0'):
        phone_number = '+234' + phone_number[1:]
    elif not phone_number.startswith('+'):
        phone_number = '+234' + phone_number
    return phone_number

# Twilio credentials
# account_sid = config('TWILIO_SID')
# auth_token = config('TWILIO_AUTH_TOKEN')
# twilio_number = '+14847256777'

# client = Client(account_sid, auth_token)

# def generate_otp():
#     return random.randint(100000, 999999)

# def send_otp(phone_number, otp):
#     try:
#         message = client.messages.create(
#             body=f'Your OTP is {otp}',
#             from_=twilio_number,
#             to=phone_number
#         )
#         return message.sid
#     except TwilioRestException as e:
#         print(f"Twilio error: {e}")
#         return None

# def signup(request):
#     if request.method == 'POST':
#         username = request.POST['username']
#         email = request.POST['email']
#         password1 = request.POST['password1']
#         phone_number = request.POST['phone']

#         if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
#             return render(request, 'signup.html', {'error': 'Username or email is already in use'})

#         if password1:
#             phone_number = normalize_phone_number(phone_number)
#             otp = generate_otp()
#             message_sid = send_otp(phone_number, otp)

#             if message_sid is None:
#                 return render(request, 'signup.html', {'error': 'Failed to send OTP'})

#             # Store OTP in session
#             request.session['otp'] = str(otp)  # Ensure OTP is stored as a string
#             request.session['username'] = username
#             request.session['email'] = email
#             request.session['password1'] = password1
#             request.session['phone_number'] = phone_number

#             print(f"OTP stored in session: {request.session['otp']}")  # Debugging statement

#             return redirect('verify_otp')
#         else:
#             return render(request, 'signup.html', {'error': 'Unable to create account'})
#     return render(request, 'signup.html')

# def verify_otp(request):
#     if request.method == 'POST':
#         entered_otp = request.POST['otp']
#         stored_otp = request.session.get('otp')

#         print(f"Entered OTP: {entered_otp}")  # Debugging statement
#         print(f"Stored OTP: {stored_otp}")  # Debugging statement

#         if entered_otp == stored_otp:
#             username = request.session.get('username')
#             email = request.session.get('email')
#             password1 = request.session.get('password1')
#             phone_number = request.session.get('phone_number')

#             print(f"Username: {username}")  # Debugging statement
#             print(f"Email: {email}")  # Debugging statement
#             print(f"Password: {password1}")  # Debugging statement
#             print(f"Phone Number: {phone_number}")  # Debugging statement

#             user = User.objects.create_user(username, email, password1)
#             user.save()

#             user_profile, created = Profile.objects.get_or_create(user=user)
#             user_profile.phone_number = phone_number
#             user_profile.save()

#             # Clear session data
#             request.session.flush()

#             return redirect('store')
#         else:
#             print("OTP mismatch")  # Debugging statement
#             return render(request, 'verify_otp.html', {'error': 'Invalid OTP'})
#     return render(request, 'verify_otp.html')

def signup(request):
    if request.method == 'POST':
        username = request.POST['username']
        email = request.POST['email']
        password1 = request.POST['password1']
        phone_number = request.POST['phone']

        if User.objects.filter(username=username).exists() or User.objects.filter(email=email).exists():
            return render(request, 'signup.html', {'error': 'Username or email is already in use'})

        if password1:
            user = User.objects.create_user(username, email, password1)
            user.save()

            user_profile, created = Profile.objects.get_or_create(user=user)
            user_profile.phone_number = phone_number
            user_profile.save()

            return redirect('store')
        else:
            return render(request, 'signup.html', {'error': 'Unable to create account'})
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
            return render(request, 'login.html', {'error': 'Incorrect username or password'})
    return render(request, 'login.html')

def logout(request):
    auth.logout(request)
    return redirect('login')

def clear_user_cart(user):
    # Get the user's cart
    cart = get_object_or_404(Cart, user=user)

    # Clear all cart items
    cart.items.clear()

    # Delete all CartItem entries for the user's cart
    CartItem.objects.filter(user=user).delete()

    # Handle the specific case for the 'Pack' product
    try:
        pack_product = Product.objects.get(name='Pack')
        pack_cart_item = CartItem.objects.filter(product=pack_product, cart=cart)
        pack_cart_item.delete()
    except Product.DoesNotExist:
        pass  # Handle the case where 'Pack' product does not exist

    # Save the cart (if there are any additional fields that need to be updated)
    cart.save()

@login_required
def initialize_payment_view(request):
    if request.method == 'POST':
        location = request.POST.get('location')
        payment_method = request.POST.get('payment_method')

        if not location:
            return render(request, 'cart.html', {'error': 'Location is required'})

        if not payment_method:
            return render(request, 'cart.html', {'error': 'Payment method is required'})

        # Get the user's cart
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.all()
        cart_amount = sum(item.total for item in cart_items)
        delivery = cart.delivery
        service_fee = cart.service_fee
        amount = cart.subtotal
        email = request.user.email

        if payment_method == 'paystack':
            callback_url = request.build_absolute_uri('/payments/verify/')
            payment_data = initialize_payment(amount, email, callback_url)

            if payment_data and 'reference' in payment_data:
                payment = Payment.objects.create(
                    user=request.user,
                    amount=cart_amount,
                    delivery=delivery,
                    service_fee=service_fee,
                    total_amount=amount,
                    email=email,
                    reference=payment_data['reference'],
                    status='pending',
                    payment_method='paystack',
                    order_id=cart
                )
                order = Order.objects.create(
                    user=request.user,
                    cart=", ".join([str(item) for item in cart_items]),
                    payment=payment,
                    status='pending',
                    payment_method='paystack',
                    location=location
                )
                return redirect(payment_data['authorization_url'])
            else:
                return render(request, 'cart.html', {'error': 'Payment initialization failed'})
        elif payment_method == 'cash':
            payment = Payment.objects.create(
                user=request.user,
                amount=cart_amount,
                delivery=delivery,
                service_fee=service_fee,
                total_amount=amount,
                email=email,
                status='pending',
                payment_method='cash',
                order_id=cart
            )
            order = Order.objects.create(
                user=request.user,
                cart=", ".join([str(item) for item in cart_items]),
                payment=payment,
                payment_method='cash',
                status='pending',
                location=location
            )

            order_history = OrderHistory.objects.create(
                user=request.user,
                user_order=", ".join([str(item) for item in cart_items]),
                reference=payment.reference,
                payment_method='cash',
                delivery=delivery,
                location=order.location,
                total_price=amount,
                payment=payment
            )

            for cart_item in cart_items:
                product = cart_item.product
                product.sales += cart_item.quantity
                product.save()

            clear_user_cart(request.user)
            return redirect('payment_success')

    cart = Cart.objects.get(user=request.user)
    cart_items = cart.items.all()
    context = {
        'cart': cart,
        'cart_items': cart_items,
        'amount': cart.amount,
        'email': request.user.email,
    }
    return render(request, 'cart.html', context)

@login_required
def verify_payment_view(request):
    reference = request.GET.get('reference')

    if not reference:
        return JsonResponse({'status': 'failed', 'message': 'Reference not provided'})

    payment_data = verify_payment(reference)
    
    # Get the user's cart
    cart = Cart.objects.get(user=request.user)
    cart_items = cart.items.all()
    delivery = cart.delivery
    service_fee = cart.service_fee
    amount = cart.subtotal
    email = request.user.email

    if payment_data:
        try:
            payment = Payment.objects.get(reference=reference)
            payment.status = payment_data['status']
            payment.save()

            cart_items = CartItem.objects.filter(user=request.user)

            order = Order.objects.filter(user=request.user).latest('created_at')
            order_history = OrderHistory.objects.create(
                user=request.user,
                user_order=", ".join([str(item) for item in cart_items]),
                reference=payment.reference,
                location=order.location,
                delivery=delivery,
                total_price=amount,
                payment_method='paystack',
                payment=payment
            )

            for cart_item in cart_items:
                product = cart_item.product
                product.sales += cart_item.quantity
                product.save()

            clear_user_cart(request.user)

            return redirect('payment_success')
        except Payment.DoesNotExist:
            return JsonResponse({'status': 'failed', 'message': 'Payment not found'})

    return JsonResponse({'status': 'failed', 'message': 'Payment verification failed'})

@csrf_exempt
def paystack_webhook(request):
    # Only accept POST requests for security
    if request.method != 'POST':
        return HttpResponseBadRequest("Only POST requests allowed")

    # Get Paystack signature from headers
    paystack_signature = request.headers.get('x-paystack-signature')
    if not paystack_signature:
        return HttpResponseBadRequest("Missing signature")

    # Get the secret key from environment variables (ensure it's in bytes)
    secret = os.getenv('paystack')
    if not secret:
        return HttpResponseBadRequest("Missing secret key")

    # Ensure the secret key is in bytes
    secret = secret.encode('utf-8')

    # Verify the signature by comparing the generated HMAC with the Paystack signature
    body = request.body
    expected_signature = hmac.new(secret, body, hashlib.sha512).hexdigest()

    # Compare the signatures
    if not hmac.compare_digest(expected_signature, paystack_signature):
        return HttpResponseBadRequest("Invalid signature")

    # Process the webhook data
    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        return HttpResponseBadRequest("Invalid JSON")

    # Handle the 'charge.success' event
    if event['event'] == 'charge.success':
        data = event['data']
        reference = data.get('reference')
        amount_paid = data.get('amount', 0) // 100  # Convert from kobo to Naira

        # Process payment verification
        try:
            payment = Payment.objects.get(reference=reference)

            if payment.status != 'completed':
                payment.status = 'completed'
                payment.total_amount = amount_paid  # optional, you can adjust total if needed
                payment.save()

                # Optional: trigger order fulfillment or notification here
                print(f"✅ Payment verified for {payment.user.username} | Reference: {reference}")

        except Payment.DoesNotExist:
            # Handle case when the payment reference doesn't exist in the database
            print(f"⚠️ Webhook received for unknown reference: {reference}")

    return HttpResponse(status=200)

@login_required
def payment_success(request):
    print("Order is being created")

    clear_user_cart(request.user)
    print("Order Created!")

    return redirect('order_history')

@login_required
def order_history(request):
    orders = OrderHistory.objects.filter(user=request.user).order_by('-payment_date')
    return render(request, 'order_history.html', {'orders': orders})

def order_details(request, order_id):
    order = get_object_or_404(OrderHistory, id=order_id, user=request.user)
    rider_phone_number = None

    if order.rider:
        rider_profile = Profile.objects.get(user=order.rider)
        rider_phone_number = rider_profile.phone_number
        
    context = {
        'order': order, 
        'rider_phone_number': rider_phone_number,
    }

    return render(request, 'order_details.html', context)

def error_404(request, exception):
    data = {}
    return render(request,'errors/404.html', data)

def error_403(request, *args, **argv):
    return render(request, 'errors/403.html', status=403)

def error_500(request, exception=None):
    context = {
        'exception': str(exception) if exception else "An unknown error occurred."
    }
    return HttpResponseServerError(render(request, 'errors/500.html', context))

@login_required
def admin_dashboard(request):
    # Check if the user has staff permissions
    if not request.user.profile.is_staff:
        return HttpResponseForbidden("You do not have permission to access this page.")

    # Get all products
    products = Product.objects.all()

    # Get the latest 10 orders, ordered by payment date in descending order
    all_orders = OrderHistory.objects.all()
    orders = OrderHistory.objects.all().order_by('-payment_date')[:10]
    incoming_orders = OrderHistory.objects.filter(status='Sent').order_by('-payment_date')

    today = timezone.now().date()
    yesterday = timezone.now().date() - timedelta(1)

    # Calculate today's sales
    yesterday_sales = OrderHistory.objects.filter(payment_date__date=yesterday).aggregate(total=Sum('total_price'))['total'] or 0
    today_sales = OrderHistory.objects.filter(payment_date__date=today).aggregate(total=Sum('total_price'))['total'] or 0

    # Calculate all sales
    total_sales = OrderHistory.objects.aggregate(total_sales=Sum('total_price'))['total_sales'] or 0

    # Calculate total sales for each product
    product_sales = OrderHistory.objects.values('user_order').annotate(total_sales=Sum('total_price'))

    context = {
        'user': request.user,
        'products': products,
        'all_orders': all_orders,
        'orders': orders,
        'incoming_orders': incoming_orders,
        'yesterday_sales': yesterday_sales,
        'today_sales': today_sales,
        'total_sales': total_sales,
        'product_sales': product_sales,
    }

    # Render the template with the context data
    return render(request, 'secondary_admin.html', context)

@login_required
def rider_dashboard(request):
    # Check if the user is a rider
    if not request.user.profile.is_rider:
        return HttpResponseForbidden("You do not have permission to access this page.")

    # Fetch new orders
    new_orders = OrderHistory.objects.filter(status='Received', delivered=None).order_by('-payment_date')

    # Fetch ongoing deliveries for the current user
    ongoing_deliveries = OrderHistory.objects.filter(rider=request.user, delivered=None)

    today = timezone.now().date()
    yesterday = timezone.now().date() - timedelta(days=1)

    # Calculate yesterday's sales
    yesterday_sales = OrderHistory.objects.filter(payment_date__date=yesterday, rider=request.user).aggregate(total=Sum('delivery'))['total'] or 0

    # Calculate today's sales
    today_sales = OrderHistory.objects.filter(payment_date__date=today, rider=request.user).aggregate(total=Sum('delivery'))['total'] or 0

    context = {
        'user': request.user,
        'profile': request.user.profile,
        'yesterday_sales': yesterday_sales,
        'today_sales': today_sales,
        'new_orders': new_orders,
        'ongoing_deliveries': ongoing_deliveries,
    }

    return render(request, 'order_admin.html', context)

@require_POST
@login_required
def receive_order(request, order_id):
    order = get_object_or_404(OrderHistory, id=order_id)
    if order.status == 'Sent':
        order.status = 'Received'
        order.rider = request.user
        order.save()
        return JsonResponse({'status': 'success', 'message': 'Order Received successfully.'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Order cannot be received.'}, status=400)

@require_POST
@login_required
def cancel_order(request, order_id):
    order = get_object_or_404(OrderHistory, id=order_id)
    if order.status == 'Sent':
        order.status = 'Received'
        order.delivered = False
        order.save()
        return JsonResponse({'status': 'success', 'message': 'Order Received successfully.'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Order cannot be received.'}, status=400)

@require_POST
@login_required
def accept_order(request, order_id):
    order = get_object_or_404(OrderHistory, id=order_id)
    if order.status == 'Received':
        order.status = 'Ready'
        order.rider = request.user
        order.save()
        return JsonResponse({'status': 'success', 'message': 'Order accepted successfully.'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Order cannot be accepted.'}, status=400)

@require_POST
@login_required
def complete_order(request, order_id):
    order = get_object_or_404(OrderHistory, id=order_id)
    if order.status == 'Ready' and order.rider == request.user:
        order.status = 'Delivered'
        order.delivered = True
        order.save()
        return JsonResponse({'status': 'success', 'message': 'Order delivered successfully.'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Order cannot be completed.'}, status=400)
    
def test_error(request):
    raise Exception("This is a test error")

def coming_soon(request):
    return render(request, 'countdown.html')

def about(request):
    return render(request, 'about.html')