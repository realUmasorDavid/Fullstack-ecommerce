from django.urls import path
from . import views
from .views import UpdateCartQuantitiesView

urlpatterns = [
    path('', views.home, name='home'),
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
    path('order', views.order_history, name='order_history'),
    path('order/<int:order_id>/', views.order_details, name='order_details'),
    path('staff_admin', views.admin_dashboard, name='admin_dashboard'),
    path('toggle_availability/<int:product_id>/', views.toggle_availability, name='toggle_availability'),
    path('rider_admin', views.rider_dashboard, name='order_admin'),
    path('accept_order/<int:order_id>/', views.accept_order, name='accept_order'),
    path('complete_order/<int:order_id>/', views.complete_order, name='complete_order'),
]