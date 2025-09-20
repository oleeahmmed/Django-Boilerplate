from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg, F
from django.utils import timezone
from decimal import Decimal
import json
from django.core.paginator import Paginator
from django import forms
from django.core.mail import send_mail
from django.conf import settings
from .models import (
    Product, Category, Brand, Banner, Review, ProductVariant,
    Cart, CartItem, Address, ShippingMethod, ShippingZone, Order, OrderItem,
    Customer, Coupon, Payment, StoreSettings, FAQ, Wishlist
)
from Authentication.models import UserProfile

# Helper Functions
def get_or_create_cart(request):
    """Get or create cart for the user or session."""
    customer = None
    session_key = None
    
    if request.user.is_authenticated:
        try:
            customer = Customer.objects.get(user_profile__user=request.user)
        except Customer.DoesNotExist:
            pass
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
    
    cart, created = Cart.objects.get_or_create(
        customer=customer,
        session_key=session_key,
        defaults={'created_at': timezone.now()}
    )
    return cart, customer

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

def get_next_order_number():
    """Generate next order number"""
    import time
    timestamp = int(time.time())
    return f"ORD-{timestamp}"

# Forms
class LoginForm(forms.Form):
    email = forms.EmailField(label='Email', max_length=254)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)

class RegistrationForm(forms.Form):
    first_name = forms.CharField(label='First Name', max_length=80)
    last_name = forms.CharField(label='Last Name', max_length=80)
    email = forms.EmailField(label='Email', max_length=254)
    phone = forms.CharField(label='Phone', max_length=30, required=False)
    password = forms.CharField(label='Password', widget=forms.PasswordInput)
    confirm_password = forms.CharField(label='Confirm Password', widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")
        return cleaned_data

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

class ProfileUpdateForm(forms.Form):
    first_name = forms.CharField(label='First Name', max_length=80)
    last_name = forms.CharField(label='Last Name', max_length=80)
    phone = forms.CharField(label='Phone', max_length=30, required=False)
    email = forms.EmailField(label='Email', max_length=254)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exclude(id=self.user.id).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={'min': 1, 'max': 5}),
            'comment': forms.Textarea(attrs={'rows': 4}),
        }

class ContactForm(forms.Form):
    name = forms.CharField(label='Name', max_length=100)
    email = forms.EmailField(label='Email', max_length=254)
    subject = forms.CharField(label='Subject', max_length=200)
    message = forms.CharField(label='Message', widget=forms.Textarea(attrs={'rows': 5}))

# Authentication Views
def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('ecommerce:dashboard')

    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            user = authenticate(request, username=email, password=password)
            if user:
                login(request, user)
                messages.success(request, 'Logged in successfully!')
                return redirect('ecommerce:dashboard')
            else:
                messages.error(request, 'Invalid email or password.')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = LoginForm()

    return render(request, 'ecommerce/login.html', {'form': form})

def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('ecommerce:dashboard')

    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.create_user(
                    username=form.cleaned_data['email'],
                    email=form.cleaned_data['email'],
                    password=form.cleaned_data['password'],
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name']
                )
                user_profile = UserProfile.objects.create(
                    user=user,
                    phone=form.cleaned_data.get('phone', '')
                )
                Customer.objects.create(
                    user_profile=user_profile,
                    email=form.cleaned_data['email'],
                    phone=form.cleaned_data.get('phone', ''),
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    is_guest=False
                )
                user = authenticate(request, username=form.cleaned_data['email'], password=form.cleaned_data['password'])
                login(request, user)
                messages.success(request, 'Registration successful! Welcome!')
                return redirect('ecommerce:dashboard')
            except Exception as e:
                messages.error(request, f'Registration failed: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = RegistrationForm()

    return render(request, 'ecommerce/register.html', {'form': form})

@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('ecommerce:home')

# User Dashboard Views
@login_required
def dashboard_view(request):
    """User dashboard view"""
    try:
        customer = Customer.objects.get(user_profile__user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('ecommerce:home')

    orders = Order.objects.filter(customer=customer).order_by('-created_at')[:5]
    wishlist = Wishlist.objects.filter(customer=customer).select_related('product')[:10]

    context = {
        'customer': customer,
        'orders': orders,
        'wishlist': wishlist,
    }
    return render(request, 'ecommerce/dashboard.html', context)

@login_required
def order_history_view(request):
    """User order history view"""
    try:
        customer = Customer.objects.get(user_profile__user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('ecommerce:home')

    orders = Order.objects.filter(customer=customer).order_by('-created_at')
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_orders': paginator.count,
    }
    return render(request, 'ecommerce/order_history.html', context)

@login_required
def profile_update_view(request):
    """User profile update view"""
    try:
        customer = Customer.objects.get(user_profile__user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('ecommerce:home')

    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                user = request.user
                user.first_name = form.cleaned_data['first_name']
                user.last_name = form.cleaned_data['last_name']
                user.email = form.cleaned_data['email']
                user.save()

                customer.first_name = form.cleaned_data['first_name']
                customer.last_name = form.cleaned_data['last_name']
                customer.email = form.cleaned_data['email']
                customer.phone = form.cleaned_data['phone']
                customer.save()

                user.userprofile.phone = form.cleaned_data['phone']
                user.userprofile.save()

                messages.success(request, 'Profile updated successfully!')
                return redirect('ecommerce:dashboard')
            except Exception as e:
                messages.error(request, f'Update failed: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ProfileUpdateForm(initial={
            'first_name': customer.first_name,
            'last_name': customer.last_name,
            'email': customer.email,
            'phone': customer.phone,
        }, user=request.user)

    return render(request, 'ecommerce/profile_update.html', {'form': form})

# Product Views
def home(request):
    """Homepage view with pagination support"""
    featured_page = int(request.GET.get('featured_page', 1))
    latest_page = int(request.GET.get('latest_page', 1))
    discounted_page = int(request.GET.get('discounted_page', 1))
    popular_page = int(request.GET.get('popular_page', 1))
    
    per_page = 8
    
    banners = Banner.objects.filter(is_active=True, show_on_homepage=True).order_by('sort_order')
    
    featured_products = Product.objects.filter(is_active=True, is_featured=True)[:per_page * featured_page]
    latest_products = Product.objects.filter(is_active=True).order_by('-created_at')[:per_page * latest_page]
    discounted_products = Product.objects.filter(is_active=True, discount_price__isnull=False)[:per_page * discounted_page]
    popular_products = Product.objects.annotate(review_count=Count('reviews')).filter(is_active=True, review_count__gt=0).order_by('-review_count')[:per_page * popular_page]
    
    context = {
        'banners': banners,
        'featured_products': featured_products,
        'latest_products': latest_products,
        'discounted_products': discounted_products,
        'popular_products': popular_products,
        'has_more_featured': Product.objects.filter(is_active=True, is_featured=True).count() > per_page * featured_page,
        'has_more_latest': Product.objects.filter(is_active=True).count() > per_page * latest_page,
        'has_more_discounted': Product.objects.filter(is_active=True, discount_price__isnull=False).count() > per_page * discounted_page,
        'has_more_popular': Product.objects.annotate(review_count=Count('reviews')).filter(is_active=True, review_count__gt=0).count() > per_page * popular_page,
    }
    return render(request, 'ecommerce/home.html', context)

def product_list(request):
    """Product list view with filters"""
    products = Product.objects.filter(is_active=True).select_related('brand', 'category').prefetch_related('images')
    products = products.annotate(avg_rating=Avg('reviews__rating'), review_count=Count('reviews')).order_by('-created_at')
    
    category_slug = request.GET.get('category')
    brand_slug = request.GET.get('brand')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    search_query = request.GET.get('q', '').strip()
    
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug, is_active=True)
        products = products.filter(Q(category=category) | Q(category__parent=category))
    
    if brand_slug:
        brand = get_object_or_404(Brand, slug=brand_slug, is_active=True)
        products = products.filter(brand=brand)
    
    if min_price:
        products = products.filter(current_price__gte=Decimal(min_price))
    if max_price:
        products = products.filter(current_price__lte=Decimal(max_price))
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(short_description__icontains=search_query)
        )
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'categories': Category.objects.filter(is_active=True, parent__isnull=True),
        'brands': Brand.objects.filter(is_active=True),
        'search_query': search_query,
        'total_products': paginator.count,
    }
    return render(request, 'ecommerce/product_list.html', context)

def product_detail_view(request, slug):
    """Product detail page view"""
    product = get_object_or_404(
        Product.objects.select_related('brand', 'category').prefetch_related(
            'images', 'variants', 'reviews__customer', 'tags'
        ),
        slug=slug,
        is_active=True
    )

    related_products = Product.objects.filter(
        category=product.category, is_active=True
    ).exclude(id=product.id)[:4]

    is_wishlisted = False
    if request.user.is_authenticated:
        try:
            customer = Customer.objects.get(user_profile__user=request.user)
            is_wishlisted = Wishlist.objects.filter(customer=customer, product=product).exists()
        except Customer.DoesNotExist:
            pass

    context = {
        'product': product,
        'related_products': related_products,
        'is_wishlisted': is_wishlisted,
    }
    return render(request, 'ecommerce/product_detail.html', context)

@login_required
@require_POST
def submit_review_view(request, product_id):
    """Submit or update product review"""
    try:
        product = get_object_or_404(Product, id=product_id, is_active=True)
        customer = Customer.objects.get(user_profile__user=request.user)
    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Customer profile not found'}, status=400)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Product not found'}, status=404)

    form = ReviewForm(request.POST)
    if form.is_valid():
        review, created = Review.objects.update_or_create(
            customer=customer,
            product=product,
            defaults={
                'rating': form.cleaned_data['rating'],
                'comment': form.cleaned_data['comment'],
                'is_approved': False,
            }
        )
        messages.success(request, 'Review submitted successfully. It will appear after approval.')
        return JsonResponse({
            'success': True,
            'message': 'Review submitted successfully.'
        })
    else:
        return JsonResponse({
            'success': False,
            'message': 'Invalid review data',
            'errors': form.errors
        }, status=400)

# Wishlist Views
@login_required
@require_POST
def wishlist_add_remove(request):
    """Add or remove product from wishlist"""
    try:
        customer = Customer.objects.get(user_profile__user=request.user)
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id, is_active=True)
    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Customer profile not found'}, status=400)
    except Product.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Product not found'}, status=404)

    action = request.POST.get('action', 'add')
    if action == 'add':
        wishlist_item, created = Wishlist.objects.get_or_create(customer=customer, product=product)
        if created:
            return JsonResponse({'success': True, 'message': f'{product.name} added to wishlist'})
        else:
            return JsonResponse({'success': True, 'message': f'{product.name} already in wishlist'})
    elif action == 'remove':
        Wishlist.objects.filter(customer=customer, product=product).delete()
        return JsonResponse({'success': True, 'message': f'{product.name} removed from wishlist'})
    else:
        return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)

@login_required
def wishlist_view(request):
    """Wishlist page view"""
    try:
        customer = Customer.objects.get(user_profile__user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('ecommerce:home')

    wishlist_items = Wishlist.objects.filter(customer=customer).select_related('product').prefetch_related('product__images')
    paginator = Paginator(wishlist_items, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'total_items': paginator.count,
    }
    return render(request, 'ecommerce/wishlist.html', context)

# Contact Form View
def contact_form_submit(request):
    """Handle contact form submission"""
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            try:
                send_mail(
                    subject=form.cleaned_data['subject'],
                    message=f"From: {form.cleaned_data['name']} <{form.cleaned_data['email']}>\n\n{form.cleaned_data['message']}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[settings.CONTACT_EMAIL],
                    fail_silently=False,
                )
                messages.success(request, 'Your message has been sent successfully!')
                return redirect('ecommerce:contact_us')
            except Exception as e:
                messages.error(request, f'Failed to send message: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ContactForm()

    return render(request, 'ecommerce/contact_us.html', {'form': form})

# Abandoned Cart Email (Stub for Celery Task)
def send_abandoned_cart_email(customer, cart):
    """Send abandoned cart email (to be called via Celery)"""
    if not cart or cart.total_items == 0:
        return

    items = [f"{item.product.name} (x{item.quantity})" for item in cart.items.all()]
    message = f"Hi {customer.full_name},\n\nYou left some items in your cart:\n{', '.join(items)}\n\nComplete your purchase now: {settings.SITE_URL}/cart/"
    try:
        send_mail(
            subject="Your Cart is Waiting!",
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[customer.email],
            fail_silently=True,
        )
    except Exception as e:
        print(f"Failed to send abandoned cart email: {str(e)}")

# Cart Views
def cart_page(request):
    """Cart page view"""
    cart, _ = get_or_create_cart(request)
    context = {
        'cart': cart,
    }
    return render(request, 'ecommerce/cart_page.html', context)

# API Views
def cart_api(request):
    """Enhanced API endpoint to handle all cart operations."""
    cart, customer = get_or_create_cart(request)

    if request.method == 'GET':
        return JsonResponse(get_cart_data(cart))

    if request.method == 'POST':
        try:
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
                    available_stock = variant.stock_quantity if 'variant' in locals() else product.stock_quantity
                    if product.is_track_stock and not product.allow_backorders:
                        if new_quantity > available_stock:
                            return JsonResponse({
                                'success': False, 
                                'message': f'Cannot add more items. Only {available_stock} available in stock'
                            })
                    
                    cart_item.quantity = new_quantity
                    cart_item.unit_price = unit_price
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
                except CartItem.DoesNotExist:
                    return JsonResponse({'success': False, 'message': 'Cart item not found'})
                
                return JsonResponse(get_cart_data(cart))

            else:
                return JsonResponse({'success': False, 'message': 'Invalid action'})
                
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

def product_detail_api(request, product_id):
    """API for product details (for modals)"""
    try:
        product = Product.objects.select_related('brand', 'category').prefetch_related(
            'images', 'variants', 'tags', 'reviews'
        ).get(
            id=product_id,
            is_active=True
        )
        
        images = []
        for img in product.images.all():
            images.append({
                'url': img.image.url,
                'alt': img.alt_text or product.name,
                'is_primary': img.is_primary
            })
        
        if not images:
            images.append({
                'url': '/static/images/placeholder-product.jpg',
                'alt': product.name,
                'is_primary': True
            })
        
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
        
        reviews = []
        for review in product.reviews.filter(is_approved=True)[:10]:
            reviews.append({
                'customer_name': review.customer.full_name or 'Anonymous',
                'rating': review.rating,
                'comment': review.comment,
                'created_at': review.created_at.strftime('%Y-%m-%d'),
                'is_verified_purchase': review.is_verified_purchase
            })
        
        tags = []
        for tag in product.tags.all():
            tags.append({
                'name': tag.name,
                'color': tag.color
            })
        
        specifications = {}
        if product.meta and isinstance(product.meta, dict):
            specifications = product.meta
        
        if product.weight:
            specifications['Weight'] = f"{product.weight} kg"
        if product.length and product.width and product.height:
            specifications['Dimensions'] = f"{product.length} x {product.width} x {product.height} cm"
        
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
            'review_count': product.reviews.filter(is_approved=True).count(),
            'avg_rating': product.reviews.filter(is_approved=True).aggregate(avg=Avg('rating'))['avg'] or 0,
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

# Legacy Cart Views
def add_to_cart(request):
    """Legacy add to cart view"""
    return redirect('ecommerce:cart_api')

def update_cart_item(request):
    """Legacy update cart item"""
    return redirect('ecommerce:cart_api')

def remove_from_cart(request):
    """Legacy remove from cart"""
    return redirect('ecommerce:cart_api')

# Checkout and Order Views
@transaction.atomic
@login_required
def checkout(request):
    """Checkout view"""
    try:
        customer = Customer.objects.get(user_profile__user=request.user)
    except Customer.DoesNotExist:
        messages.error(request, 'Customer profile not found.')
        return redirect('ecommerce:dashboard')

    cart, _ = get_or_create_cart(request)
    if not cart or cart.total_items == 0:
        messages.error(request, 'Your cart is empty.')
        return redirect('ecommerce:cart_page')

    addresses = Address.objects.filter(customer=customer)
    shipping_zones = ShippingZone.objects.all()
    shipping_methods = []
    for zone in shipping_zones:
        methods = ShippingMethod.objects.filter(zone=zone)
        shipping_methods.extend(methods)

    coupon = None
    if request.session.get('coupon_code'):
        try:
            coupon = Coupon.objects.get(code=request.session['coupon_code'], is_active=True)
        except Coupon.DoesNotExist:
            pass

    context = {
        'cart': cart,
        'addresses': addresses,
        'shipping_methods': shipping_methods,
        'coupon': coupon,
    }
    return render(request, 'ecommerce/checkout.html', context)

@csrf_exempt
@require_POST
@transaction.atomic
@login_required
def place_order(request):
    """Place order view"""
    try:
        customer = Customer.objects.get(user_profile__user=request.user)
    except Customer.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Customer not found'}, status=400)

    cart, _ = get_or_create_cart(request)
    if not cart or cart.total_items == 0:
        return JsonResponse({'success': False, 'message': 'Cart is empty'}, status=400)

    data = json.loads(request.body) if request.content_type == 'application/json' else request.POST

    order = Order.objects.create(
        customer=customer,
        subtotal=cart.subtotal,
        tax_amount=Decimal('0.00'),
        shipping_amount=Decimal(data.get('shipping_amount', '0.00')),
        discount_amount=Decimal(data.get('discount_amount', '0.00')),
        total_amount=cart.subtotal + Decimal(data.get('shipping_amount', '0.00')) - Decimal(data.get('discount_amount', '0.00')),
        shipping_method_id=data.get('shipping_method_id'),
        coupon_id=data.get('coupon_id'),
        status='pending',
        order_number=get_next_order_number()
    )

    for item in cart.items.all():
        OrderItem.objects.create(
            order=order,
            product=item.product,
            variant=item.variant,
            quantity=item.quantity,
            unit_price=item.unit_price,
            total_price=item.total_price
        )

        if item.product.is_track_stock:
            if item.variant:
                item.variant.stock_quantity -= item.quantity
                item.variant.save()
            else:
                item.product.stock_quantity -= item.quantity
                item.product.save()

    cart.items.all().delete()

    if request.session.get('coupon_code'):
        del request.session['coupon_code']

    return JsonResponse({
        'success': True,
        'order_id': order.id,
        'order_number': order.order_number
    })

def order_success(request, order_id):
    """Order success page"""
    order = get_object_or_404(Order, id=order_id, customer__user_profile__user=request.user)
    context = {'order': order}
    return render(request, 'ecommerce/order_success.html', context)

# Coupon and Shipping Views
def apply_coupon(request):
    """Apply coupon"""
    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            coupon = Coupon.objects.get(code=code, is_active=True)
            subtotal = Decimal(request.POST.get('subtotal', '0'))
            if coupon.is_valid(subtotal):
                request.session['coupon_code'] = code
                discount = coupon.get_discount_amount(subtotal)
                return JsonResponse({'success': True, 'discount': str(discount)})
            else:
                return JsonResponse({'success': False, 'message': 'Coupon not valid'})
        except Coupon.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Coupon not found'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def remove_coupon(request):
    """Remove coupon"""
    if request.method == 'POST':
        if request.session.get('coupon_code'):
            del request.session['coupon_code']
            return JsonResponse({'success': True})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def calculate_shipping(request):
    """Calculate shipping"""
    if request.method == 'POST':
        data = request.POST
        weight = Decimal(data.get('weight', '0'))
        subtotal = Decimal(data.get('subtotal', '0'))
        zip_code = data.get('zip_code', '')
        
        shipping_method = ShippingMethod.objects.filter(
            zone__countries__contains=[request.session.get('country', 'BD')],
            min_weight__lte=weight,
            max_weight__gte=weight
        ).first()
        
        if shipping_method:
            cost = shipping_method.calculate_cost(weight, subtotal)
            return JsonResponse({'success': True, 'cost': str(cost)})
        return JsonResponse({'success': False, 'message': 'Shipping not available'})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

def save_address(request):
    """Save address"""
    if request.method == 'POST':
        data = request.POST
        customer = Customer.objects.get(user_profile__user=request.user)
        address, created = Address.objects.update_or_create(
            customer=customer,
            defaults={
                'first_name': data.get('first_name'),
                'last_name': data.get('last_name'),
                'address_line_1': data.get('address_line_1'),
                'address_line_2': data.get('address_line_2'),
                'city': data.get('city'),
                'state': data.get('state'),
                'postal_code': data.get('postal_code'),
                'country': data.get('country'),
                'phone': data.get('phone'),
                'is_default': data.get('is_default', False),
            }
        )
        return JsonResponse({'success': True, 'address_id': address.id})
    return JsonResponse({'success': False, 'message': 'Invalid request'})

# Static Pages
def about_us(request):
    """About Us page view"""
    return render(request, 'ecommerce/about_us.html')

def contact_us(request):
    """Contact Us page view"""
    return render(request, 'ecommerce/contact_us.html')

def faq(request):
    """FAQ page view"""
    faqs = FAQ.objects.filter(is_active=True).order_by('sort_order')
    context = {'faqs': faqs}
    return render(request, 'ecommerce/faq.html', context)

def privacy_policy(request):
    """Privacy Policy page view"""
    return render(request, 'ecommerce/privacy_policy.html')

def terms_conditions(request):
    """Terms and Conditions page view"""
    return render(request, 'ecommerce/terms_conditions.html')

# Search and Category
def search_page(request):
    """Dedicated search results page for SEO"""
    search_query = request.GET.get('q', '').strip()
    products = Product.objects.none()
    
    if search_query:
        products = Product.objects.filter(
            is_active=True
        ).filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(brand__name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).select_related('brand', 'category').prefetch_related(
            'images', 'reviews'
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        ).distinct().order_by('-created_at')
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'search_query': search_query,
        'page_obj': page_obj,
        'total_results': paginator.count,
    }
    
    return render(request, 'ecommerce/search_page.html', context)

def category_page(request, category_slug):
    """Dedicated category page for SEO"""
    try:
        category = Category.objects.get(slug=category_slug, is_active=True)
    except Category.DoesNotExist:
        raise Http404("Category not found")
    
    products = Product.objects.filter(
        is_active=True
    ).filter(
        Q(category=category) | Q(category__parent=category)
    ).select_related('brand', 'category').prefetch_related(
        'images', 'reviews'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).order_by('-created_at')
    
    subcategories = category.children.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    )
    
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'subcategories': subcategories,
        'page_obj': page_obj,
        'total_products': paginator.count,
    }
    
    return render(request, 'ecommerce/category_page.html', context)


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
    """Enhanced checkout page view with better error handling"""
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
        'cart_items': cart.items.select_related('product', 'variant').prefetch_related('product__images').all(),
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
    """Enhanced apply coupon with better validation and error messages"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return redirect('ecommerce:checkout')
    
    coupon_code = request.POST.get('coupon_code', '').strip().upper()
    cart, customer = get_or_create_cart(request)
    
    if not cart:
        return JsonResponse({
            'success': False, 
            'message': 'Cart not found. Please refresh the page and try again.'
        })
    
    if not coupon_code:
        return JsonResponse({
            'success': False, 
            'message': 'Please enter a coupon code.'
        })
    
    try:
        coupon = Coupon.objects.get(code=coupon_code, is_active=True)
        
        # Check if coupon is valid for current time
        now = timezone.now()
        if coupon.valid_from and coupon.valid_from > now:
            return JsonResponse({
                'success': False,
                'message': f'This coupon is not yet valid. Valid from {coupon.valid_from.strftime("%Y-%m-%d")}.'
            })
        
        if coupon.valid_to and coupon.valid_to < now:
            return JsonResponse({
                'success': False,
                'message': 'This coupon has expired.'
            })
        
        # Check usage limits
        if coupon.usage_limit and coupon.used_count >= coupon.usage_limit:
            return JsonResponse({
                'success': False,
                'message': 'This coupon has reached its usage limit.'
            })
        
        # Check minimum amount requirement
        if coupon.minimum_amount and cart.subtotal < coupon.minimum_amount:
            return JsonResponse({
                'success': False,
                'message': f'Minimum order amount of {cart.subtotal.currency_symbol}{coupon.minimum_amount} required for this coupon.'
            })
        
        # Check if coupon is for first-time customers only
        if coupon.first_time_customers_only and customer:
            if customer.orders.filter(status__in=['completed', 'processing']).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'This coupon is only valid for first-time customers.'
                })
        
        # Apply coupon to cart
        success, message = cart.apply_coupon(coupon_code)
        
        if success:
            discount_amount = cart.get_discount_amount()
            subtotal = cart.subtotal
            
            return JsonResponse({
                'success': True,
                'message': message,
                'discount_amount': str(discount_amount),
                'subtotal': str(subtotal),
                'coupon_code': coupon_code,
                'coupon_name': coupon.name
            })
        else:
            return JsonResponse({'success': False, 'message': message})
            
    except Coupon.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Invalid coupon code. Please check and try again.'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while applying the coupon. Please try again.'
        })

@require_POST
def remove_coupon(request):
    """Enhanced remove coupon with better feedback"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return redirect('ecommerce:checkout')
    
    cart, customer = get_or_create_cart(request)
    
    if not cart:
        return JsonResponse({
            'success': False, 
            'message': 'Cart not found. Please refresh the page and try again.'
        })
    
    try:
        if cart.coupon:
            coupon_name = cart.coupon.name
            cart.remove_coupon()
            
            return JsonResponse({
                'success': True,
                'message': f'Coupon "{coupon_name}" removed successfully.',
                'discount_amount': '0.00',
                'subtotal': str(cart.subtotal)
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'No coupon applied to remove.'
            })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while removing the coupon. Please try again.'
        })

@require_POST
def calculate_shipping(request):
    """Enhanced calculate shipping with better error handling"""
    if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
        return redirect('ecommerce:checkout')
    
    shipping_method_id = request.POST.get('shipping_method_id')
    
    if not shipping_method_id:
        return JsonResponse({
            'success': False, 
            'message': 'No shipping method selected.'
        })
    
    try:
        shipping_method = ShippingMethod.objects.get(id=shipping_method_id, is_active=True)
    except ShippingMethod.DoesNotExist:
        return JsonResponse({
            'success': False, 
            'message': 'Invalid shipping method selected.'
        })
    
    cart, customer = get_or_create_cart(request)
    
    if not cart:
        return JsonResponse({
            'success': False, 
            'message': 'Cart not found. Please refresh the page and try again.'
        })
    
    try:
        subtotal = cart.subtotal
        total_weight = cart.total_weight
        
        shipping_cost = shipping_method.calculate_cost(total_weight, subtotal)
        
        # Check for free shipping coupon
        if cart.coupon and cart.coupon.discount_type == 'free_shipping' and cart.coupon.is_valid():
            shipping_cost = Decimal('0.00')
        
        discount_amount = cart.get_discount_amount()
        total = subtotal + shipping_cost - discount_amount
        
        return JsonResponse({
            'success': True,
            'shipping_cost': str(shipping_cost),
            'total': str(total),
            'method_name': shipping_method.name,
            'delivery_days': f"{shipping_method.min_delivery_days}-{shipping_method.max_delivery_days}",
            'subtotal': str(subtotal),
            'discount_amount': str(discount_amount)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': 'An error occurred while calculating shipping. Please try again.'
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
            'review_count': len(reviews),
            'avg_rating': round(sum(review['rating'] for review in reviews) / len(reviews), 1) if reviews else 0,
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
    

def about_us(request):
    """About Us page view"""
    return render(request, 'ecommerce/about_us.html')

def contact_us(request):
    """Contact Us page view"""
    return render(request, 'ecommerce/contact_us.html')

def faq(request):
    """FAQ page view"""
    return render(request, 'ecommerce/faq.html')

def privacy_policy(request):
    """Privacy Policy page view"""
    return render(request, 'ecommerce/privacy_policy.html')

def terms_conditions(request):
    """Terms and Conditions page view"""
    return render(request, 'ecommerce/terms_conditions.html')

def search_page(request):
    """Dedicated search results page for SEO"""
    search_query = request.GET.get('q', '').strip()
    products = Product.objects.none()
    
    if search_query:
        products = Product.objects.filter(
            is_active=True
        ).filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(brand__name__icontains=search_query) |
            Q(category__name__icontains=search_query) |
            Q(tags__name__icontains=search_query)
        ).select_related('brand', 'category').prefetch_related(
            'images', 'reviews'
        ).annotate(
            avg_rating=Avg('reviews__rating'),
            review_count=Count('reviews')
        ).distinct().order_by('-created_at')
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'search_query': search_query,
        'page_obj': page_obj,
        'total_results': paginator.count,
    }
    
    return render(request, 'ecommerce/search_page.html', context)

def category_page(request, category_slug):
    """Dedicated category page for SEO"""
    try:
        category = Category.objects.get(slug=category_slug, is_active=True)
    except Category.DoesNotExist:
        raise Http404("Category not found")
    
    products = Product.objects.filter(
        is_active=True
    ).filter(
        Q(category=category) | Q(category__parent=category)
    ).select_related('brand', 'category').prefetch_related(
        'images', 'reviews'
    ).annotate(
        avg_rating=Avg('reviews__rating'),
        review_count=Count('reviews')
    ).order_by('-created_at')
    
    # Get subcategories
    subcategories = category.children.filter(is_active=True).annotate(
        product_count=Count('products', filter=Q(products__is_active=True))
    )
    
    # Pagination
    paginator = Paginator(products, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'category': category,
        'subcategories': subcategories,
        'page_obj': page_obj,
        'total_products': paginator.count,
    }
    
    return render(request, 'ecommerce/category_page.html', context)
