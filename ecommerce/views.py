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
from django.core.paginator import Paginator

from .models import (
    Product, Category, Brand, Banner, Review, ProductVariant,
    Cart, CartItem, Address, ShippingMethod, ShippingZone, Order, OrderItem,
    Customer, Coupon, Payment, StoreSettings
)

from Authentication.models import UserProfile

def get_cart_data(cart):
    """Helper function to serialize cart data."""
    if not cart:
        return {
            'success': True,
            'cart': {
                'items': [],
                'total_items': 0,
                'subtotal': '0.00'
            }
        }

    cart_items = cart.items.select_related('product', 'variant').all()
    items_data = []
    for item in cart_items:
        product_image = ''
        if item.product.images.exists():
            product_image = item.product.images.first().image.url

        items_data.append({
            'id': item.id,
            'product_id': item.product.id,
            'product_name': item.product.name,
            'variant_name': item.variant.name if item.variant else '',
            'quantity': item.quantity,
            'unit_price': str(item.unit_price),
            'total_price': str(item.total_price),
            'image_url': product_image
        })

    return {
        'success': True,
        'cart': {
            'items': items_data,
            'total_items': cart.total_items,
            'subtotal': str(cart.subtotal)
        }
    }

def cart_api(request):
    """Enhanced API endpoint to handle all cart operations."""
    cart, customer = get_or_create_cart(request)

    if request.method == 'GET':
        return JsonResponse(get_cart_data(cart))

    if request.method == 'POST':
        try:
            # Handle both JSON and form data
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
            
            action = data.get('action')

            if action == 'add':
                product_id = data.get('product_id')
                quantity = int(data.get('quantity', 1))
                variant_id = data.get('variant_id')

                if not product_id:
                    return JsonResponse({'success': False, 'message': 'Product ID required'})

                try:
                    product = Product.objects.get(id=product_id, is_active=True)
                except Product.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'Product not found'})

                # Check stock availability
                if product.is_track_stock and not product.allow_backorders:
                    if product.stock_quantity < quantity:
                        return JsonResponse({
                            'success': False, 
                            'message': f'Only {product.stock_quantity} items available in stock'
                        })

                unit_price = product.current_price
                cart_item_data = {'cart': cart, 'product': product}
                
                if variant_id:
                    try:
                        variant = ProductVariant.objects.get(id=variant_id, product=product)
                        cart_item_data['variant'] = variant
                        unit_price = variant.current_price
                        
                        # Check variant stock
                        if product.is_track_stock and not product.allow_backorders:
                            if variant.stock_quantity < quantity:
                                return JsonResponse({
                                    'success': False, 
                                    'message': f'Only {variant.stock_quantity} items available in stock'
                                })
                    except ProductVariant.DoesNotExist:
                        return JsonResponse({'success': False, 'message': 'Product variant not found'})

                cart_item, created = CartItem.objects.get_or_create(
                    **cart_item_data,
                    defaults={'quantity': quantity, 'unit_price': unit_price}
                )

                if not created:
                    new_quantity = cart_item.quantity + quantity
                    
                    # Check stock for updated quantity
                    available_stock = variant.stock_quantity if variant_id else product.stock_quantity
                    if product.is_track_stock and not product.allow_backorders:
                        if new_quantity > available_stock:
                            return JsonResponse({
                                'success': False, 
                                'message': f'Cannot add more items. Only {available_stock} available in stock'
                            })
                    
                    cart_item.quantity = new_quantity
                    cart_item.unit_price = unit_price  # Update price in case it changed
                    cart_item.save()
                
                response_data = get_cart_data(cart)
                message = f'{product.name}'
                if variant_id and 'variant' in locals():
                    message += f' ({variant.name})'
                message += f' (x{quantity}) added to cart'
                response_data['message'] = message
                return JsonResponse(response_data)

            elif action == 'update':
                item_id = data.get('item_id')
                quantity = int(data.get('quantity', 0))
                
                try:
                    cart_item = CartItem.objects.get(id=item_id, cart=cart)
                except CartItem.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'Cart item not found'})

                if quantity <= 0:
                    cart_item.delete()
                    response_data = get_cart_data(cart)
                    response_data['message'] = 'Item removed from cart'
                    return JsonResponse(response_data)
                else:
                    # Check stock availability
                    product = cart_item.product
                    variant = cart_item.variant
                    available_stock = variant.stock_quantity if variant else product.stock_quantity
                    
                    if product.is_track_stock and not product.allow_backorders:
                        if quantity > available_stock:
                            return JsonResponse({
                                'success': False, 
                                'message': f'Only {available_stock} items available in stock'
                            })
                    
                    cart_item.quantity = quantity
                    cart_item.save()
                
                return JsonResponse(get_cart_data(cart))

            elif action == 'remove':
                item_id = data.get('item_id')
                try:
                    cart_item = CartItem.objects.get(id=item_id, cart=cart)
                    cart_item.delete()
                    response_data = get_cart_data(cart)
                    response_data['message'] = 'Item removed from cart'
                    return JsonResponse(response_data)
                except CartItem.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'Cart item not found'})

            else:
                return JsonResponse({'success': False, 'message': 'Invalid action'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'})

    return JsonResponse({'success': False, 'message': 'Invalid request method'})


def home(request):
    """Home page view with product grids and categories"""
    
    # Get banners for hero section
    banners = Banner.objects.filter(
        is_active=True,
        show_on_homepage=True
    ).filter(
        Q(start_date__lte=timezone.now()) | Q(start_date__isnull=True)
    ).filter(
        Q(end_date__gte=timezone.now()) | Q(end_date__isnull=True)
    ).order_by('sort_order')[:5]
    
    # Get featured categories for display
    featured_categories = Category.objects.filter(
        is_active=True,
        parent__isnull=True
    ).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    ).prefetch_related('children').order_by('sort_order', 'name')[:8]
    
    # Featured Products Section
    featured_products = Product.objects.filter(
        is_active=True,
        is_featured=True
    ).select_related('brand', 'category').prefetch_related(
        'images', 'reviews', 'tags'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).order_by('-created_at')[:12]  # Show 12 products
    
    # Latest Products Section
    latest_products = Product.objects.filter(
        is_active=True
    ).select_related('brand', 'category').prefetch_related(
        'images', 'reviews', 'tags'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).order_by('-created_at')[:12]  # Show 12 latest products
    
    # Discounted Products Section
    discounted_products = Product.objects.filter(
        is_active=True,
        discount_price__isnull=False
    ).select_related('brand', 'category').prefetch_related(
        'images', 'reviews', 'tags'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).order_by('-created_at')[:12]  # Show 12 discounted products
    
    # Popular Products (based on reviews)
    popular_products = Product.objects.filter(
        is_active=True
    ).select_related('brand', 'category').prefetch_related(
        'images', 'reviews', 'tags'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).filter(
        review_count__gte=1
    ).order_by('-review_count', '-avg_rating')[:12]
    
    # Recent customer reviews for testimonials
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
def product_list(request):
    """Enhanced product list view with search and filtering"""
    products = Product.objects.filter(is_active=True).select_related(
        'brand', 'category'
    ).prefetch_related(
        'images', 'reviews'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    )
    
    # Search functionality
    search_query = request.GET.get('search', '').strip()
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(brand__name__icontains=search_query) |
            Q(category__name__icontains=search_query)
        )
    
    # Category filtering
    category_slug = request.GET.get('category', '').strip()
    if category_slug:
        try:
            category = Category.objects.get(slug=category_slug, is_active=True)
            products = products.filter(
                Q(category=category) | Q(category__parent=category)
            )
        except Category.DoesNotExist:
            pass
    
    # Brand filtering
    brand_slug = request.GET.get('brand', '').strip()
    if brand_slug:
        try:
            brand = Brand.objects.get(slug=brand_slug, is_active=True)
            products = products.filter(brand=brand)
        except Brand.DoesNotExist:
            pass
    
    # Price filtering
    min_price = request.GET.get('min_price', '').strip()
    max_price = request.GET.get('max_price', '').strip()
    
    if min_price:
        try:
            min_price = Decimal(min_price)
            products = products.filter(
                Q(discount_price__gte=min_price, discount_price__isnull=False) |
                Q(price__gte=min_price, discount_price__isnull=True)
            )
        except (ValueError, TypeError):
            pass
    
    if max_price:
        try:
            max_price = Decimal(max_price)
            products = products.filter(
                Q(discount_price__lte=max_price, discount_price__isnull=False) |
                Q(price__lte=max_price, discount_price__isnull=True)
            )
        except (ValueError, TypeError):
            pass
    
    # Sorting
    sort_by = request.GET.get('sort', 'newest')
    if sort_by == 'price_low':
        products = products.extra(
            select={
                'effective_price': 'COALESCE(discount_price, price)'
            }
        ).order_by('effective_price')
    elif sort_by == 'price_high':
        products = products.extra(
            select={
                'effective_price': 'COALESCE(discount_price, price)'
            }
        ).order_by('-effective_price')
    elif sort_by == 'name':
        products = products.order_by('name')
    elif sort_by == 'rating':
        products = products.order_by('-avg_rating', '-review_count')
    else:  # newest
        products = products.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'category_slug': category_slug,
        'brand_slug': brand_slug,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'total_products': paginator.count,
    }
    return render(request, 'ecommerce/product_list.html', context)

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
        if not request.session.session_key:
            request.session.create()
        session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    
    return cart, customer

@require_POST
def add_to_cart(request):
    """Add product to cart - Legacy endpoint for backward compatibility"""
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
        
        return JsonResponse(get_cart_data(cart))
        
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
        else:
            cart_item.quantity = quantity
            cart_item.save()
        
        return JsonResponse(get_cart_data(cart))
        
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
        
        return JsonResponse(get_cart_data(cart))
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})

def checkout(request):
    """Checkout page view"""
    cart, customer = get_or_create_cart(request)
    
    if not cart or not cart.items.exists():
        messages.error(request, 'Your cart is empty.')
        return redirect('ecommerce:home')
    
    addresses = []
    if customer:
        addresses = customer.addresses.all().order_by('-is_default', '-created_at')
    
    shipping_methods = ShippingMethod.objects.filter(is_active=True).select_related('zone')
    
    subtotal = cart.subtotal
    discount_amount = cart.get_discount_amount()
    
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
    
    subtotal = cart.subtotal
    total_weight = cart.total_weight
    
    shipping_cost = shipping_method.calculate_cost(total_weight, subtotal)
    
    if cart.coupon and cart.coupon.discount_type == 'free_shipping' and cart.coupon.is_valid():
        shipping_cost = Decimal('0.00')
    
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
        
        required_fields = ['first_name', 'last_name', 'email', 'phone', 'address_line_1', 'city']
        for field in required_fields:
            if not billing_data.get(field):
                messages.error(request, f'Billing {field.replace("_", " ").title()} is required.')
                return redirect('ecommerce:checkout')
        
        shipping_method = None
        if shipping_method_id:
            try:
                shipping_method = ShippingMethod.objects.get(id=shipping_method_id, is_active=True)
            except ShippingMethod.DoesNotExist:
                messages.error(request, 'Invalid shipping method selected.')
                return redirect('ecommerce:checkout')
        
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
        
        class TempAddress:
            def __init__(self, data):
                for key, value in data.items():
                    setattr(self, key, value)
        
        billing_address = TempAddress(billing_data)
        shipping_address = TempAddress(shipping_data)
        
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
            
            payment = Payment.objects.create(
                method=payment_method,
                amount=order.total_amount,
                status=Payment.Status.PENDING if payment_method != 'cod' else Payment.Status.SUCCESS
            )
            order.payments.add(payment)
            
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
    
    required_fields = ['first_name', 'last_name', 'address_line_1', 'city']
    for field in required_fields:
        if not address_data.get(field):
            return JsonResponse({
                'success': False, 
                'message': f'{field.replace("_", " ").title()} is required.'
            })
    
    if address_data['is_default']:
        Address.objects.filter(customer=customer, type=address_data['type']).update(is_default=False)
    
    address = Address.objects.create(customer=customer, **address_data)
    
    return JsonResponse({
        'success': True,
        'message': 'Address saved successfully',
        'address_id': address.id,
        'address_html': f"{address.full_name}<br>{address.full_address}"
    })

def product_detail_api(request, product_id):
    """API endpoint to get detailed product information for modal"""
    try:
        product = get_object_or_404(
            Product.objects.select_related('brand', 'category').prefetch_related(
                'images', 'variants', 'reviews__customer', 'tags'
            ),
            id=product_id,
            is_active=True
        )
        
        # Serialize product images
        images = []
        for img in product.images.all():
            images.append({
                'url': img.image.url,
                'alt': img.alt_text or product.name,
                'is_primary': img.is_primary
            })
        
        # If no images, add placeholder
        if not images:
            images.append({
                'url': '/static/images/placeholder-product.jpg',
                'alt': product.name,
                'is_primary': True
            })
        
        # Serialize product variants
        variants = []
        for variant in product.variants.filter(is_active=True):
            variants.append({
                'id': variant.id,
                'name': variant.name,
                'sku': variant.sku,
                'price': str(variant.current_price),
                'stock_quantity': variant.stock_quantity,
                'is_in_stock': variant.is_in_stock,
                'attributes': variant.attributes or {}
            })
        
        # Serialize reviews
        reviews = []
        for review in product.reviews.filter(is_approved=True)[:10]:  # Limit to 10 reviews
            reviews.append({
                'customer_name': review.customer.full_name or 'Anonymous',
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.strftime('%Y-%m-%d'),
                'is_verified_purchase': review.is_verified_purchase
            })
        
        # Serialize tags
        tags = []
        for tag in product.tags.all():
            tags.append({
                'name': tag.name,
                'color': tag.color
            })
        
        # Build specifications from meta field
        specifications = {}
        if product.meta and isinstance(product.meta, dict):
            specifications = product.meta
        
        # Add basic specifications if not in meta
        if product.weight:
            specifications['Weight'] = f"{product.weight} kg"
        if product.length and product.width and product.height:
            specifications['Dimensions'] = f"{product.length} x {product.width} x {product.height} cm"
        
        # Calculate average rating
        avg_rating = 0
        review_count = product.reviews.filter(is_approved=True).count()
        if review_count > 0:
            from django.db.models import Avg
            avg_rating = product.reviews.filter(is_approved=True).aggregate(
                avg_rating=Avg('rating')
            )['avg_rating'] or 0
        
        product_data = {
            'id': product.id,
            'name': product.name,
            'slug': product.slug,
            'sku': product.sku,
            'current_price': str(product.current_price),
            'original_price': str(product.price) if product.discount_price else None,
            'discount_percentage': product.discount_percentage,
            'short_description': product.short_description,
            'description': product.description,
            'stock_quantity': product.get_available_stock(),
            'is_in_stock': product.is_in_stock,
            'is_track_stock': product.is_track_stock,
            'allow_backorders': product.allow_backorders,
            'brand': {
                'name': product.brand.name if product.brand else None,
                'slug': product.brand.slug if product.brand else None
            } if product.brand else None,
            'category': {
                'name': product.category.name if product.category else None,
                'slug': product.category.slug if product.category else None,
                'full_path': product.category.full_path if product.category else None
            } if product.category else None,
            'images': images,
            'variants': variants,
            'tags': tags,
            'specifications': specifications,
            'reviews': reviews,
            'review_count': review_count,
            'avg_rating': round(avg_rating, 1) if avg_rating else 0,
            'meta_title': product.meta_title,
            'meta_description': product.meta_description,
            'is_featured': product.is_featured,
            'is_digital': product.is_digital,
            'created_at': product.created_at.strftime('%Y-%m-%d'),
        }
        
        return JsonResponse({
            'success': True,
            'product': product_data
        })
        
    except Product.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Product not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'An error occurred: {str(e)}'
        }, status=500)