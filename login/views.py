from django.contrib.auth import logout
from django.contrib.auth.views import LogoutView
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django import forms
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Product, Profile, Wishlist
import razorpay
from django.conf import settings

# ---------------- FORMS ----------------
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'phone_number', 'address', 'city', 'pincode',
            'profile_photo', 'date_of_birth', 'gender'
        ]
        widgets = {
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }

class CustomLogoutView(LogoutView):
    http_method_names = ['post']

# ---------------- PROFILE EDIT ----------------
@login_required
def edit_profile_view(request):
    user = request.user
    profile, created = Profile.objects.get_or_create(user=user)
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = ProfileForm(request.POST, request.FILES, instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('profile')
    else:
        user_form = UserForm(instance=user)
        profile_form = ProfileForm(instance=profile)
    return render(request, 'login/edit_profile.html', {
        'user_form': user_form,
        'profile_form': profile_form,
    })

# ---------------- AJAX CART & WISHLIST ----------------
@login_required
@csrf_exempt
def ajax_add_to_cart(request, product_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        if Product.objects.filter(id=product_id).exists():
            cart[str(product_id)] = cart.get(str(product_id), 0) + 1
            request.session['cart'] = cart
            request.session.modified = True
            cart_count = sum(cart.values())
            return JsonResponse({'success': True, 'cart_count': cart_count})
        return JsonResponse({'success': False, 'error': 'Product not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@csrf_exempt
def ajax_add_to_wishlist(request, product_id):
    if request.method == 'POST':
        product = get_object_or_404(Product, id=product_id)
        Wishlist.objects.get_or_create(user=request.user, product=product)
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
        return JsonResponse({'success': True, 'wishlist_count': wishlist_count})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

@login_required
@csrf_exempt
def ajax_move_to_cart(request, product_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        if Product.objects.filter(id=product_id).exists():
            cart[str(product_id)] = cart.get(str(product_id), 0) + 1
            request.session['cart'] = cart
            request.session.modified = True
            Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
            cart_count = sum(cart.values())
            wishlist_count = Wishlist.objects.filter(user=request.user).count()
            return JsonResponse({'success': True, 'cart_count': cart_count, 'wishlist_count': wishlist_count})
        return JsonResponse({'success': False, 'error': 'Product not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

# ---------------- HOME / ECOMMERCE ----------------
@login_required
def ecommerce_view(request):
    wishlist_count = Wishlist.objects.filter(user=request.user).count()
    selected_category = request.GET.get('category', 'all')
    search_query = request.GET.get('query', '').strip().lower()
    categories = Product.objects.values_list('category', flat=True).distinct().order_by('category')
    products = Product.objects.filter(category=selected_category) if selected_category != 'all' else Product.objects.all()
    if search_query:
        products = products.filter(name__icontains=search_query)
        request.session['last_search'] = search_query
    else:
        request.session.pop('last_search', None)
    cart = request.session.get('cart', {})
    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'search_query': search_query,
        'cart_count': sum(cart.values()),
        'last_search': request.session.get('last_search', ''),
        'wishlist_count': wishlist_count,
    }
    return render(request, 'login/ecommerce.html', context)

# ---------------- PRODUCT DETAIL ----------------
def product_detail_view(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    return render(request, 'login/product_detail.html', {'product': product})

# ---------------- ADD TO CART ----------------
@csrf_exempt
def add_to_cart(request, product_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        if Product.objects.filter(id=product_id).exists():
            cart[str(product_id)] = cart.get(str(product_id), 0) + 1
            request.session['cart'] = cart
            request.session.modified = True
            return redirect('ecommerce')
        return HttpResponse("Product not found", status=404)
    return HttpResponse("Invalid request method", status=405)

# ---------------- REMOVE FROM CART ----------------
@csrf_exempt
def remove_from_cart(request, product_id):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        if str(product_id) in cart:
            del cart[str(product_id)]
            request.session['cart'] = cart
            request.session.modified = True
        return redirect('cart')
    return HttpResponse("Invalid request method", status=405)

# ---------------- VIEW CART ----------------
def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    for pid, qty in cart.items():
        try:
            product = Product.objects.get(id=pid)
            item = {
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'image': product.image.url if product.image else '',
                'quantity': qty,
                'total': qty * product.price,
            }
            total += item['total']
            cart_items.append(item)
        except Product.DoesNotExist:
            continue
    coupon = request.session.get('coupon', '')
    discount_percent = request.session.get('discount', 0)
    discount_amount = (total * discount_percent) // 100
    total_after_discount = total - discount_amount
    context = {
        'cart': cart_items,
        'total': total_after_discount,
        'discount_amount': discount_amount,
        'coupon': coupon,
        'original_total': total,
    }
    return render(request, 'login/cart.html', context)

# ---------------- REGISTER ----------------
def register_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if not username or not password1 or not password2:
            return render(request, 'login/register.html', {'error': 'All fields are required.'})
        if User.objects.filter(username=username).exists():
            return render(request, 'login/register.html', {'error': 'Username already exists.'})
        if password1 != password2:
            return render(request, 'login/register.html', {'error': 'Passwords do not match.'})
        User.objects.create(username=username, password=make_password(password1))
        return redirect('login')
    return render(request, 'login/register.html')

# ---------------- WISHLIST MANAGEMENT ----------------
@login_required
def add_to_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    Wishlist.objects.get_or_create(user=request.user, product=product)
    next_url = request.META.get('HTTP_REFERER', 'ecommerce')
    return redirect(next_url)

@login_required
def wishlist_view(request):
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('product')
    return render(request, 'login/wishlist.html', {'wishlist_items': wishlist_items})

@login_required
def remove_from_wishlist(request, item_id):
    item = get_object_or_404(Wishlist, id=item_id, user=request.user)
    if request.method == "POST":
        item.delete()
    return redirect('wishlist')

# ---------------- PAYMENT ----------------
def payment_view(request): 
    address = request.session.get('address')
    cart = request.session.get('cart', {})
    cart_items = []
    total_price = 0
    for pid, qty in cart.items():
        try:
            product = Product.objects.get(id=pid)
            item = {
                'id': product.id,
                'name': product.name,
                'price': product.price,
                'image': product.image.url if product.image else '',
                'quantity': qty,
                'total': qty * product.price,
            }
            total_price += item['total']
            cart_items.append(item)
        except Product.DoesNotExist:
            continue
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))
    order = client.order.create({
        "amount": int(total_price * 100),  # Amount in paise
        "currency": "INR",
        "payment_capture": 1
    })
    context = {
        'cart': cart_items,
        'total': total_price,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "order_id": order["id"],
        "amount": total_price,
    }
    return render(request, 'login/payment.html', context)

# ---------------- PROFILE VIEW ----------------
@login_required
def profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    return render(request, 'login/profile.html', {
        'user': request.user,
        'profile': profile,
    })

# ---------------- COUPON MANAGEMENT ----------------
def apply_coupon(request):
    if request.method == "POST":
        coupon = request.POST.get("coupon", "").strip().upper()
        if coupon == "SAVE10":
            request.session['coupon'] = 'SAVE10'
            request.session['discount'] = 10  # percent
            messages.success(request, "Coupon applied! You saved 10%.")
        elif coupon == "CHANDRAN75":
            request.session['coupon'] = 'CHANDRAN75'
            request.session['discount'] = 75  # percent
            messages.success(request, "Coupon applied! You saved 75%.")
        elif coupon == "FIRST50":
            request.session['coupon'] = 'FIRST50'
            request.session['discount'] = 50  # percent
            messages.success(request, "Coupon applied! You saved 50%.")
        else:
            request.session['coupon'] = ''
            request.session['discount'] = 0
            messages.error(request, "Invalid coupon code.")
    return redirect('cart')

def remove_coupon(request):
    if request.method == "POST":
        request.session['coupon'] = ''
        request.session['discount'] = 0
        messages.info(request, "Coupon removed.")
    return redirect('cart')

# ---------------- ADDRESS HANDLING ----------------
def address_view(request):
    if request.method == "POST":
        request.session['address'] = {
            'name': request.POST['name'],
            'address': request.POST['address'],
            'city': request.POST['city'],
            'pincode': request.POST['pincode'],
            'phone': request.POST['phone'],
        }
        return redirect('payment')
    return render(request, 'login/address.html')