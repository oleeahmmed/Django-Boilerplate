# shop/urls.py
from django.urls import path
from . import views

app_name = 'ecommerce'

urlpatterns = [
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('checkout/', views.checkout, name='checkout'),
    
    # Enhanced Cart API - handles all cart operations
    path('api/cart/', views.cart_api, name='cart_api'),
    
    # Product Detail API for modal
    path('api/products/<int:product_id>/', views.product_detail_api, name='product_detail_api'),
    
    # Legacy cart endpoints (for backward compatibility)
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('update-cart-item/', views.update_cart_item, name='update_cart_item'),
    path('remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    
    # Coupon management
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    
    # Shipping and order processing
    path('calculate-shipping/', views.calculate_shipping, name='calculate_shipping'),
    path('place-order/', views.place_order, name='place_order'),
    path('order-success/<uuid:order_id>/', views.order_success, name='order_success'),
    
    # Address management
    path('save-address/', views.save_address, name='save_address'),
]