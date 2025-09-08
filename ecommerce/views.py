# ecommerce/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count, Avg
from django.utils import timezone
from decimal import Decimal
import json

from .models import (
    Product, Category, Brand, Banner, Review, ProductVariant,
    Cart, CartItem, Address, ShippingMethod, ShippingZone, Order, OrderItem,
    Customer, Coupon, Payment, StoreSettings
)

from Authentication.models import UserProfile

def home(request):
    """Home page view with products and categories"""
    
    # Get active banners for homepage
    banners = Banner.objects.filter(
        is_active=True,
        show_on_homepage=True
    ).filter(
        Q(start_date__lte=timezone.now()) | Q(start_date__isnull=True)
    ).filter(
        Q(end_date__gte=timezone.now()) | Q(end_date__isnull=True)
    ).order_by('sort_order')[:5]
    
    # Get featured categories with product counts (top-level categories only)
    featured_categories = Category.objects.filter(
        is_active=True,
        parent__isnull=True
    ).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).prefetch_related('children').order_by('sort_order', 'name')[:12]
    
    # Get featured products
    featured_products = Product.objects.filter(
        is_active=True,
        is_featured=True
    ).select_related('brand', 'category').prefetch_related(
        'images', 'reviews'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )[:8]
    
    # Get latest products
    latest_products = Product.objects.filter(
        is_active=True
    ).select_related('brand', 'category').prefetch_related(
        'images', 'reviews'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).order_by('-created_at')[:8]
    
    # Get discounted products
    discounted_products = Product.objects.filter(
        is_active=True,
        discount_price__isnull=False
    ).select_related('brand', 'category').prefetch_related(
        'images', 'reviews'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).order_by('-created_at')[:8]
    
    # Get popular products for daily shopping (most reviewed/highest rated)
    popular_products = Product.objects.filter(
        is_active=True
    ).select_related('brand', 'category').prefetch_related(
        'images', 'reviews'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).filter(
        review_count__gte=1
    ).order_by('-review_count', '-avg_rating')[:8]
    
    # Get recent reviews for social proof
    recent_reviews = Review.objects.filter(
        is_approved=True,
        product__is_active=True
    ).select_related('product', 'customer').order_by('-created_at')[:6]
    
    context = {
        'banners': banners,
        'featured_categories': featured_categories,
        'featured_products': featured_products,
        'latest_products': latest_products,
        'discounted_products': discounted_products,
        'popular_products': popular_products,
        'recent_reviews': recent_reviews,
    }
    
    return render(request, 'ecommerce/home.html', context)


def get_or_create_cart(request):
    """Get or create cart for current user/session"""
    cart = None
    customer = None
    
    if request.user.is_authenticated:
        try:
            customer = Customer.objects.get(user_profile__user=request.user)
            cart, created = Cart.objects.get_or_create(customer=customer)
        except Customer.DoesNotExist:
            user_profile, created = UserProfile.objects.get_or_create(user=request.user)
            customer = Customer.objects.create(
                user_profile=user_profile,
                email=request.user.email,
                first_name=request.user.first_name,
                last_name=request.user.last_name,
                is_guest=False
            )
            cart, created = Cart.objects.get_or_create(customer=customer)
    else:
        # For anonymous users, use session
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    
    return cart, customer


@require_POST
def add_to_cart(request):
    """Add product to cart"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    
    try:
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        variant_id = request.POST.get('variant_id')
        
        if not product_id:
            return JsonResponse({'success': False, 'message': 'Product ID required'})
        
        product = get_object_or_404(Product, id=product_id, is_active=True)
        cart, customer = get_or_create_cart(request)
        
        unit_price = product.current_price
        
        # Get or create cart item
        cart_item_data = {'cart': cart, 'product': product}
        if variant_id:
            variant = get_object_or_404(ProductVariant, id=variant_id)
            cart_item_data['variant'] = variant
            unit_price = variant.current_price
        
        cart_item, created = CartItem.objects.get_or_create(
            **cart_item_data,
            defaults={'quantity': quantity, 'unit_price': unit_price}
        )
        
        if not created:
            cart_item.quantity += quantity
            cart_item.save()
        
        return JsonResponse({
            'success': True,
            'message': f'{product.name} added to cart',
            'cart_count': cart.total_items,
            'cart_total': str(cart.subtotal)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_POST
def update_cart_item(request):
    """Update cart item quantity"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    
    try:
        item_id = request.POST.get('item_id')
        quantity = int(request.POST.get('quantity', 1))
        
        cart, customer = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        if quantity <= 0:
            cart_item.delete()
            message = 'Item removed from cart'
        else:
            cart_item.quantity = quantity
            cart_item.save()
            message = 'Cart updated'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'cart_count': cart.total_items,
            'cart_total': str(cart.subtotal)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_POST
def remove_from_cart(request):
    """Remove item from cart"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Invalid request'})
    
    try:
        item_id = request.POST.get('item_id')
        cart, customer = get_or_create_cart(request)
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        
        cart_item.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Item removed from cart',
            'cart_count': cart.total_items,
            'cart_total': str(cart.subtotal)
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


def checkout(request):
    """Checkout page view"""
    cart, customer = get_or_create_cart(request)
    
    if not cart or not cart.items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('ecommerce:home')
    
    # Get customer addresses if logged in
    addresses = []
    if customer:
        addresses = customer.addresses.all().order_by('-is_default', '-created_at')
    
    # Get available shipping methods
    shipping_methods = ShippingMethod.objects.filter(is_active=True).select_related('zone')
    
    # Calculate cart totals
    subtotal = cart.subtotal
    discount_amount = cart.get_discount_amount()
    
    # Get store settings
    store_settings = StoreSettings.get_settings()
    
    context = {
        'cart': cart,
        'cart_items': cart.items.select_related('product', 'variant').all(),
        'addresses': addresses,
        'customer': customer,
        'shipping_methods': shipping_methods,
        'subtotal': subtotal,
        'discount_amount': discount_amount,
        'store_settings': store_settings,
        'payment_methods': Payment.Method.choices,
    }
    
    return render(request, 'ecommerce/checkout.html', context)


@require_POST
def apply_coupon(request):
    """Apply coupon code to cart"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return redirect('ecommerce:checkout')
    
    coupon_code = request.POST.get('coupon_code', '').strip().upper()
    cart, customer = get_or_create_cart(request)
    
    if not cart:
        return JsonResponse({'success': False, 'message': 'Cart not found'})
    
    if not coupon_code:
        return JsonResponse({'success': False, 'message': 'Please enter a coupon code'})
    
    # Apply coupon
    success, message = cart.apply_coupon(coupon_code)
    
    if success:
        discount_amount = cart.get_discount_amount()
        subtotal = cart.subtotal
        
        return JsonResponse({
            'success': True,
            'message': message,
            'discount_amount': str(discount_amount),
            'subtotal': str(subtotal),
            'coupon_code': coupon_code
        })
    else:
        return JsonResponse({'success': False, 'message': message})


@require_POST
def remove_coupon(request):
    """Remove coupon from cart"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return redirect('ecommerce:checkout')
    
    cart, customer = get_or_create_cart(request)
    
    if not cart:
        return JsonResponse({'success': False, 'message': 'Cart not found'})
    
    cart.remove_coupon()
    
    return JsonResponse({
        'success': True,
        'message': 'Coupon removed',
        'discount_amount': '0.00',
        'subtotal': str(cart.subtotal)
    })


@require_POST
def calculate_shipping(request):
    """Calculate shipping cost for selected method"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return redirect('ecommerce:checkout')
    
    shipping_method_id = request.POST.get('shipping_method_id')
    
    if not shipping_method_id:
        return JsonResponse({'success': False, 'message': 'No shipping method selected'})
    
    try:
        shipping_method = ShippingMethod.objects.get(id=shipping_method_id, is_active=True)
    except ShippingMethod.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Invalid shipping method'})
    
    cart, customer = get_or_create_cart(request)
    
    if not cart:
        return JsonResponse({'success': False, 'message': 'Cart not found'})
    
    # Calculate shipping cost
    subtotal = cart.subtotal
    total_weight = cart.total_weight
    
    shipping_cost = shipping_method.calculate_cost(total_weight, subtotal)
    
    # Check if coupon provides free shipping
    if cart.coupon and cart.coupon.discount_type == 'free_shipping' and cart.coupon.is_valid():
        shipping_cost = Decimal('0.00')
    
    # Calculate total
    discount_amount = cart.get_discount_amount()
    total = subtotal + shipping_cost - discount_amount
    
    return JsonResponse({
        'success': True,
        'shipping_cost': str(shipping_cost),
        'total': str(total),
        'method_name': shipping_method.name,
        'delivery_days': f"{shipping_method.min_delivery_days}-{shipping_method.max_delivery_days}"
    })


@require_POST
def place_order(request):
    """Place the order"""
    try:
        cart, customer = get_or_create_cart(request)
        
        if not cart or not cart.items.exists():
            messages.error(request, 'Your cart is empty.')
            return redirect('ecommerce:checkout')
        
        # Get form data
        billing_data = {
            'first_name': request.POST.get('billing_first_name', '').strip(),
            'last_name': request.POST.get('billing_last_name', '').strip(),
            'email': request.POST.get('billing_email', '').strip(),
            'phone': request.POST.get('billing_phone', '').strip(),
            'company': request.POST.get('billing_company', '').strip(),
            'address_line_1': request.POST.get('billing_address_line_1', '').strip(),
            'address_line_2': request.POST.get('billing_address_line_2', '').strip(),
            'city': request.POST.get('billing_city', '').strip(),
            'state': request.POST.get('billing_state', '').strip(),
            'postal_code': request.POST.get('billing_postal_code', '').strip(),
            'country': request.POST.get('billing_country', 'Bangladesh').strip(),
        }
        
        # Check if shipping is same as billing
        same_as_billing = request.POST.get('same_as_billing') == 'on'
        
        if same_as_billing:
            shipping_data = billing_data.copy()
        else:
            shipping_data = {
                'first_name': request.POST.get('shipping_first_name', '').strip(),
                'last_name': request.POST.get('shipping_last_name', '').strip(),
                'company': request.POST.get('shipping_company', '').strip(),
                'address_line_1': request.POST.get('shipping_address_line_1', '').strip(),
                'address_line_2': request.POST.get('shipping_address_line_2', '').strip(),
                'city': request.POST.get('shipping_city', '').strip(),
                'state': request.POST.get('shipping_state', '').strip(),
                'postal_code': request.POST.get('shipping_postal_code', '').strip(),
                'country': request.POST.get('shipping_country', 'Bangladesh').strip(),
                'phone': billing_data['phone'],
            }
        
        payment_method = request.POST.get('payment_method', 'cod')
        shipping_method_id = request.POST.get('shipping_method_id')
        customer_notes = request.POST.get('customer_notes', '').strip()
        
        # Validation
        required_fields = ['first_name', 'last_name', 'email', 'phone', 'address_line_1', 'city']
        for field in required_fields:
            if not billing_data.get(field):
                messages.error(request, f'Billing {field.replace("_", " ").title()} is required.')
                return redirect('ecommerce:checkout')
        
        # Validate shipping method
        shipping_method = None
        if shipping_method_id:
            try:
                shipping_method = ShippingMethod.objects.get(id=shipping_method_id, is_active=True)
            except ShippingMethod.DoesNotExist:
                messages.error(request, 'Invalid shipping method selected.')
                return redirect('ecommerce:checkout')
        
        # Create guest customer if needed
        if not customer:
            customer = Customer.get_or_create_guest_customer(
                email=billing_data['email'],
                session_key=request.session.session_key,
                first_name=billing_data['first_name'],
                last_name=billing_data['last_name'],
                phone=billing_data['phone']
            )
            cart.customer = customer
            cart.save()
        
        # Create temporary address objects for order creation
        class TempAddress:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        billing_address = TempAddress(billing_data)
        shipping_address = TempAddress(shipping_data)
        
        # Create order within transaction
        with transaction.atomic():
            order = Order()
            order.create_from_cart(
                cart=cart,
                billing_address=billing_address,
                shipping_address=shipping_address,
                payment_method=payment_method,
                shipping_method=shipping_method,
                customer_notes=customer_notes
            )
            
            # Create payment record
            payment = Payment.objects.create(
                method=payment_method,
                amount=order.total_amount,
                status=Payment.Status.PENDING if payment_method != 'cod' else Payment.Status.SUCCESS
            )
            order.payments.add(payment)
            
            # Update payment status on order
            if payment_method == 'cod':
                order.payment_status = Order.PaymentStatus.PENDING
            
            order.save()
        
        messages.success(request, f'Order placed successfully! Order ID: {order.order_number}')
        return redirect('ecommerce:order_success', order_id=order.order_id)
        
    except Exception as e:
        messages.error(request, f'An error occurred while placing your order: {str(e)}')
        return redirect('ecommerce:checkout')


def order_success(request, order_id):
    """Order success page"""
    try:
        order = get_object_or_404(Order, order_id=order_id)
        
        # Verify order belongs to current user/session
        if request.user.is_authenticated:
            if not (order.customer and order.customer.user_profile and 
                   order.customer.user_profile.user == request.user):
                return redirect('ecommerce:home')
        else:
            session_key = request.session.session_key
            if not (order.customer and order.customer.session_key == session_key):
                return redirect('ecommerce:home')
        
        context = {
            'order': order,
            'order_items': order.items.select_related('product').all()
        }
        
        return render(request, 'ecommerce/order_success.html', context)
        
    except Exception:
        messages.error(request, 'Order not found.')
        return redirect('ecommerce:home')


@require_POST
def save_address(request):
    """Save address for logged in users"""
    if not request.user.is_authenticated:
        return JsonResponse({'success': False, 'message': 'Please login to save address'})
    
    try:
        customer = Customer.objects.get(user_profile__user=request.user)
    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Customer profile not found'})
    
    address_data = {
        'first_name': request.POST.get('first_name', '').strip(),
        'last_name': request.POST.get('last_name', '').strip(),
        'company': request.POST.get('company', '').strip(),
        'address_line_1': request.POST.get('address_line_1', '').strip(),
        'address_line_2': request.POST.get('address_line_2', '').strip(),
        'city': request.POST.get('city', '').strip(),
        'state': request.POST.get('state', '').strip(),
        'postal_code': request.POST.get('postal_code', '').strip(),
        'country': request.POST.get('country', 'Bangladesh').strip(),
        'phone': request.POST.get('phone', '').strip(),
        'type': request.POST.get('type', 'both'),
        'is_default': request.POST.get('is_default') == 'true'
    }
    
    # Validation
    required_fields = ['first_name', 'last_name', 'address_line_1', 'city']
    for field in required_fields:
        if not address_data.get(field):
            return JsonResponse({
                'success': False, 
                'message': f'{field.replace("_", " ").title()} is required.'
            })
    
    # If setting as default, unset other default addresses
    if address_data['is_default']:
        Address.objects.filter(customer=customer, type=address_data['type']).update(is_default=False)
    
    address = Address.objects.create(customer=customer, **address_data)
    
    return JsonResponse({
        'success': True,
        'message': 'Address saved successfully',
        'address_id': address.id,
        'address_html': f"{address.full_name}<br>{address.full_address}"
    })
