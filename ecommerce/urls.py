# shop/urls.py
from django.urls import path
from . import views

app_name = 'ecommerce'

urlpatterns = [
    path('', views.home, name='home'),
    path('checkout/', views.checkout, name='checkout'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('update-cart-item/', views.update_cart_item, name='update_cart_item'),
    path('remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    path('calculate-shipping/', views.calculate_shipping, name='calculate_shipping'),
    path('place-order/', views.place_order, name='place_order'),
    path('order-success/<uuid:order_id>/', views.order_success, name='order_success'),
    path('save-address/', views.save_address, name='save_address'),
]
