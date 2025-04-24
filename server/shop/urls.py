from django.urls import path
from . import views
from .views import UpdateCartQuantitiesView
from django.conf.urls import handler404, handler500
from django.contrib.auth import views as auth_views

handler403 = 'shop.views.error_403'
handler404 = 'shop.views.error_404'
handler500 = 'shop.views.error_500'

urlpatterns = [
    path('', views.home, name='home'),
    path('about', views.about, name='about'),
    path('store', views.store, name='store'),
    path('search/', views.search_products, name='search_products'),
    path('profile', views.profile, name='update_profile'),
    path('checkout', views.checkout, name='checkout'),
    path('signup', views.signup, name='signup'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('add_to_cart/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('delete_item/<int:pk>/', views.delete_item, name='delete_item'),
    path('update_cart_quantities/', UpdateCartQuantitiesView.as_view(), name='update_cart_quantities'),
    path('cart', views.initialize_payment_view, name='initialize_payment'),
    path('get-cart', views.get_cart, name='get-cart'),
    path('payments/verify/', views.verify_payment_view, name='verify_payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('paystack/webhook/', views.paystack_webhook, name='paystack_webhook'),
    path('order', views.order_history, name='order_history'),
    path('order/<int:order_id>/', views.order_details, name='order_details'),
    path('staff_admin', views.admin_dashboard, name='admin_dashboard'),
    path('toggle_availability/<int:product_id>/', views.toggle_availability, name='toggle_availability'),
    path('rider_admin', views.rider_dashboard, name='order_admin'),
    path('receive_order/<int:order_id>/', views.receive_order, name='receive_order'),
    path('cancel_order/<int:order_id>/', views.cancel_order, name='cancel_order'),
    path('accept_order/<int:order_id>/', views.accept_order, name='accept_order'),
    path('complete_order/<int:order_id>/', views.complete_order, name='complete_order'),
    # path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('test-error/', views.test_error),
    path('coming-soon/', views.coming_soon, name='coming_soon'),
    path('password_reset/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
]