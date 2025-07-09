from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LoginView
from . import views
from django.shortcuts import redirect
from .views import CustomLogoutView
from django.contrib import admin

urlpatterns = [
    path('', lambda request: redirect('login'), name='home'),  # Redirect root to login
    path('login/', LoginView.as_view(template_name='login/login.html'), name='login'),
    path('logout/', CustomLogoutView.as_view(), name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile_view, name='edit_profile'),
    path('ecommerce/', views.ecommerce_view, name='ecommerce'),
    path('product/<int:product_id>/', views.product_detail_view, name='product_detail'),
    path('cart/', views.cart_view, name='cart'),
    path('add/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove/<int:product_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add/<int:product_id>/', views.add_to_wishlist, name='add_to_wishlist'),
    path('wishlist/remove/<int:item_id>/', views.remove_from_wishlist, name='remove_from_wishlist'),
    path('ajax/add_to_cart/<int:product_id>/', views.ajax_add_to_cart, name='ajax_add_to_cart'),
    path('ajax/add_to_wishlist/<int:product_id>/', views.ajax_add_to_wishlist, name='ajax_add_to_wishlist'),
    path('ajax/move_to_cart/<int:product_id>/', views.ajax_move_to_cart, name='ajax_move_to_cart'),
    path('payment/', views.payment_view, name='payment'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    path('address/', views.address_view, name='address'),
    path('admin/', admin.site.urls),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='login/password_change.html'), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='login/password_change_done.html'), name='password_change_done'),
    path('accounts/password_change/', auth_views.PasswordChangeView.as_view(template_name='login/password_change.html'), name='password_change'),
    path('accounts/password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='login/password_change_done.html'), name='password_change_done'),
]