from django.urls import path
from . import views
from .views import UpdateCartQuantitiesView

urlpatterns = [
    path('', views.home, name='home'),
    path('store', views.store, name='store'),
    path('profile', views.profile, name='profile'),
    # path('order', views.order, name='order'),
    path('checkout', views.checkout, name='checkout'),
    path('signup', views.signup, name='signup'),
    path('login', views.login, name='login'),
    path('logout', views.logout, name='logout'),
    path('add_to_cart/<int:pk>/', views.add_to_cart, name='add_to_cart'),
    path('delete_item/<int:pk>/', views.delete_item, name='delete_item'),
    path('cart/', views.view_cart, name='view_cart'),
    path('update_cart_quantities/', UpdateCartQuantitiesView.as_view(), name='update_cart_quantities'),
    path('initialize/', views.initialize_payment_view, name='initialize_payment'),
    path('payments/verify/', views.verify_payment_view, name='verify_payment'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('order', views.order_history, name='order_history'),
    # path('deleteitem', views.delete_cart, name='deleteitem')
]