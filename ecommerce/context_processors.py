# shop/context_processors.py
from django.db.models import Count, Q
from .models import (
    Category, Brand, Cart, Customer, StoreSettings,
    Product, Tag
)


def ecommerce_context(request):
    """
    Global context processor for e-commerce data
    Available across all templates
    """
    
    # Get store settings
    store_settings = StoreSettings.get_settings()
    
    # Get main navigation categories (parent categories only)
    main_categories = Category.objects.filter(
        is_active=True,
        parent__isnull=True
    ).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).order_by('sort_order', 'name')[:8]
    
    # Get popular brands
    popular_brands = Brand.objects.filter(
        is_active=True
    ).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).filter(product_count__gt=0).order_by('sort_order', 'name')[:10]
    
    # Get popular tags
    popular_tags = Tag.objects.annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).filter(product_count__gt=0).order_by('-product_count')[:15]
    
    # Get customer and cart info
    customer = None
    cart = None
    cart_items_count = 0
    
    if request.user.is_authenticated:
        try:
            customer = Customer.objects.get(user_profile__user=request.user)
            cart = Cart.objects.filter(customer=customer).first()
        except Customer.DoesNotExist:
            pass
    else:
        # For anonymous users, get cart by session
        session_key = request.session.session_key
        if session_key:
            cart = Cart.objects.filter(session_key=session_key).first()
    
    # Get cart items count
    if cart:
        cart_items_count = cart.total_items
    
    # Currency and basic settings
    currency_symbol = 'BDT'
    if store_settings.currency == 'USD':
        currency_symbol = '$'
    elif store_settings.currency == 'EUR':
        currency_symbol = '€'
    
    return {
        # Store information
        'store_settings': store_settings,
        'store_name': store_settings.store_name,
        'currency': store_settings.currency,
        'currency_symbol': currency_symbol,
        
        # Navigation data
        'main_categories': main_categories,
        'popular_brands': popular_brands,
        'popular_tags': popular_tags,
        
        # User & cart data
        'current_customer': customer,
        'cart': cart,
        'cart_items_count': cart_items_count,
        
        # Contact info
        'contact_email': store_settings.contact_email,
        'contact_phone': store_settings.contact_phone,
        
        # Social links
        'facebook_url': store_settings.facebook_url,
        'twitter_url': store_settings.twitter_url,
        'instagram_url': store_settings.instagram_url,
        'youtube_url': store_settings.youtube_url,
        
        # Business settings
        'allow_guest_checkout': store_settings.allow_guest_checkout,
        'min_order_amount': store_settings.min_order_amount,
        'maintenance_mode': store_settings.maintenance_mode,
    }
