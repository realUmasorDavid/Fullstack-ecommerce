# views.py
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST, require_GET
from django.db.models import Sum, Count
from django.contrib import auth
from django.contrib import messages
from django.conf import settings
from .models import *
import json
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.core.exceptions import ObjectDoesNotExist
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
@require_POST
def add_to_cart(request, pk):
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        product = get_object_or_404(Product, pk=pk)
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item, created = CartItem.objects.get_or_create(product=product)
        cart.items.add(cart_item)

        # Check if the added product is a 'Main Meal'
        if product.category.name == 'Main Meals':
            try:
                pack_product = Product.objects.get(name='Pack')
                pack_in_cart = cart.items.filter(product=pack_product).exists()

                if not pack_in_cart:
                    cart_item_pack, created = CartItem.objects.get_or_create(product=pack_product, defaults={'quantity': 1})
                    if created:
                        cart.items.add(cart_item_pack)
                        cart.save()
            except Product.DoesNotExist:
                pass  # Handle the case where 'Pack' product does not exist

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
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item = get_object_or_404(CartItem, product=product)

    # Check if the item being deleted is the 'Pack' product
    if product.name == 'Pack':
        main_meal_items = cart.items.filter(product__category__name='Main Meals')
        if main_meal_items.exists():
            messages.error(request, 'A Pack is required for your order.')
            return redirect('initialize_payment')

    cart.items.remove(cart_item)

    # Check if the removed product is a 'Main Meal'
    if product.category.name == 'Main Meals':
        main_meal_items = cart.items.filter(product__category__name='Main Meals')
        if not main_meal_items.exists():
            try:
                pack_product = Product.objects.get(name='Pack')
                pack_cart_item = get_object_or_404(CartItem, product=pack_product)
                cart.items.remove(pack_cart_item)
                pack_cart_item.delete()  # Also delete the CartItem associated with the 'Pack' product
                cart.save()
            except Product.DoesNotExist:
                pass  # Handle the case where 'Pack' product does not exist

    messages.error(request, f'{cart_item} removed from cart!')
    return redirect('initialize_payment')

@require_GET
def get_cart(request):
    # Fetch the cart data for the current user
    user = request.user
    try:
        cart = Cart.objects.get(user=user)
        cart_data = {
            'item_count': cart.item_count,
            # Add other relevant cart data here
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

# @login_required
# def view_cart(request):
#     cart, created = Cart.objects.get_or_create(user=request.user)
#     cart_items = CartItem.objects.filter(cart=cart)

#     context = {
#         'cart_items': cart_items,
#         'cart': cart,
#     }
#     return render(request, 'cart.html', context)

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
    return JsonResponse({'is_available': product.is_available})

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
    cart = Cart.objects.get(user=user)

    # Delete all items in the cart
    cart.items.through.objects.filter(cart=cart).delete()

    # Additionally, delete the 'Pack' product if it exists in the cart
    try:
        pack_product = Product.objects.get(name='Pack')
        pack_cart_item = CartItem.objects.filter(product=pack_product, cart=cart)
        pack_cart_item.delete()
    except Product.DoesNotExist:
        pass  # Handle the case where 'Pack' product does not exist

def initialize_payment_view(request):
    if request.method == 'POST':
        location = request.POST.get('location')
        payment_method = request.POST.get('payment_method')

        if not location:
            return render(request, 'cart.html', {'error': 'Location is required'})

        if not payment_method:
            return render(request, 'cart.html', {'error': 'Payment method is required'})

        # Retrieve the user's cart
        cart = Cart.objects.get(user=request.user)
        cart_items = cart.items.all()
        cart_amount = cart.amount
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
                location=order.location,
                total_price=cart.subtotal,
                payment=payment
            )

            for cart_item in cart_items:
                product = cart_item.product
                product.sales += cart_item.quantity
                product.save()

                cart_item.quantity = 1
                cart_item.save()
                
            try:
                pack_product = Product.objects.get(name='Pack')
                pack_cart_item = get_object_or_404(CartItem, product=pack_product)
                pack_cart_item.delete()
            except Product.DoesNotExist:
                pass  # Handle the case where 'Pack' product does not exist

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

            order = Order.objects.filter(user=request.user).latest('created_at')
            order_history = OrderHistory.objects.create(
                user=request.user,
                user_order=", ".join([str(item) for item in cart_items]),
                reference=payment.reference,
                location=order.location,
                total_price=cart.subtotal,
                payment_method='paystack',
                payment=payment
            )

            for cart_item in cart_items:
                product = cart_item.product
                product.sales += cart_item.quantity
                product.save()

                cart_item.quantity = 1
                cart_item.save()
                
            try:
                pack_product = Product.objects.get(name='Pack')
                pack_cart_item = get_object_or_404(CartItem, product=pack_product)
                pack_cart_item.delete()
            except Product.DoesNotExist:
                pass  # Handle the case where 'Pack' product does not exist

            clear_user_cart(request.user)

            return redirect('payment_success')
        except Payment.DoesNotExist:
            return JsonResponse({'status': 'failed', 'message': 'Payment not found'})

    return JsonResponse({'status': 'failed', 'message': 'Payment verification failed'})

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
    return render(request, 'order_details.html', {'order': order})

def error_404(request, exception):
    data = {}
    return render(request,'errors/404.html', data)

def error_403(request, *args, **argv):
    return render(request, 'errors/403.html', status=403)

def error_500(request, *args, **argv):
    return render(request, 'errors/500.html', status=500)

def admin_dashboard(request):
    
    if not request.user.profile.is_staff:
        return HttpResponseForbidden("You do not have permission to access this page.")
    
    products = Product.objects.all()
    orders = OrderHistory.objects.all().order_by('-payment_date')[:10]
    total_sales = OrderHistory.objects.aggregate(total_sales=Sum('total_price'))['total_sales'] or 0

    # Calculate total sales for each product
    product_sales = OrderHistory.objects.values('user_order').annotate(total_sales=Sum('total_price'))

    context = {
        'user': request.user,  # Ensure the user object is passed to the template
        'products': products,
        'orders': orders,
        'total_sales': total_sales,
        'product_sales': product_sales,
    }

    return render(request, 'secondary_admin.html', context)

@login_required
def rider_dashboard(request):
    # Check if the user is a rider
    if not request.user.profile.is_rider:
        return HttpResponseForbidden("You do not have permission to access this page.")

    # Fetch new orders
    new_orders = OrderHistory.objects.filter(status='Sent')

    # Fetch ongoing deliveries for the current user
    ongoing_deliveries = OrderHistory.objects.filter(rider=request.user.username, delivered=None)

    context = {
        'user': request.user,  # Ensure the user object is passed to the template
        'profile': request.user.profile,  # Pass the user's profile to the template
        'new_orders': new_orders,
        'ongoing_deliveries': ongoing_deliveries,
    }

    return render(request, 'order_admin.html', context)

@require_POST
def accept_order(request, order_id):
    order = get_object_or_404(OrderHistory, id=order_id)
    if order.status == 'Sent':
        order.status = 'Ready'
        order.rider = request.user.username
        order.save()
        return JsonResponse({'status': 'success', 'message': 'Order accepted successfully.'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Order cannot be accepted.'}, status=400)

@require_POST
def complete_order(request, order_id):
    order = get_object_or_404(OrderHistory, id=order_id)
    if order.status == 'Ready':
        order.status = 'Delivered'
        order.delivered = True
        order.save()
        return JsonResponse({'status': 'success', 'message': 'Order delivered successfully.'})
    else:
        return JsonResponse({'status': 'error', 'message': 'Order not delivered.'}, status=400)