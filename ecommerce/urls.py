# shop/urls.py
from django.urls import path
from . import views

app_name = 'ecommerce'

urlpatterns = [
    # Existing URLs (unchanged)
    path('', views.home, name='home'),
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail_view, name='product_detail'),
    path('checkout/', views.checkout, name='checkout'),
    path('api/cart/', views.cart_api, name='cart_api'),
    path('api/products/<int:product_id>/', views.product_detail_api, name='product_detail_api'),
    path('add-to-cart/', views.add_to_cart, name='add_to_cart'),
    path('update-cart-item/', views.update_cart_item, name='update_cart_item'),
    path('remove-from-cart/', views.remove_from_cart, name='remove_from_cart'),
    path('apply-coupon/', views.apply_coupon, name='apply_coupon'),
    path('remove-coupon/', views.remove_coupon, name='remove_coupon'),
    path('calculate-shipping/', views.calculate_shipping, name='calculate_shipping'),
    path('place-order/', views.place_order, name='place_order'),
    path('order-success/<uuid:order_id>/', views.order_success, name='order_success'),
    path('save-address/', views.save_address, name='save_address'),
    path('about-us/', views.about_us, name='about_us'),
    path('contact-us/', views.contact_us, name='contact_us'),
    path('faq/', views.faq, name='faq'),
    path('cart/', views.cart_page, name='cart_page'),
    path('search/', views.search_page, name='search_page'),
    path('category/<slug:category_slug>/', views.category_page, name='category_page'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-and-conditions/', views.terms_conditions, name='terms_conditions'),
    # New Wishlist URLs
    path('wishlist/', views.wishlist_view, name='wishlist'),
    path('wishlist/add-remove/', views.wishlist_add_remove, name='wishlist_add_remove'),
]
