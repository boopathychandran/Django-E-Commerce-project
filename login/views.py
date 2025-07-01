from django.contrib.auth import logout
from django.contrib.auth.views import LogoutView
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from .models import Product 
from .models import Profile
from django import forms 
from django.contrib.auth.decorators import login_required
from .models import Wishlist
from django.http import JsonResponse
import razorpay
from django.conf import settings
from django.contrib import messages
# from .forms import ProfileForm
from .models import Profile

from django import forms
from django.contrib.auth.models import User

class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


class CustomLogoutView(LogoutView):
    http_method_names = ['post']

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

class ProfileEditForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['phone_number', 'address', 'city', 'pincode', 'profile_photo', 'date_of_birth', 'gender']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
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
#def edit_profile_view(request):
    #profile = request.user.profile  # Assuming you have a OneToOne relation
   # user = request.user  
   # return render(request, 'login/profile.html', {'profile': profile, 'user': user})
   

# ---------------- HOME / ECOMMERCE ----------------
@login_required
def ecommerce_view(request):
    wishlist_count = Wishlist.objects.filter(user=request.user).count() if request.user.is_authenticated else 0
    selected_category = request.GET.get('category', 'all')
    search_query = request.GET.get('query', '').strip().lower()

    # Get all unique categories from the database
    categories = Product.objects.values_list('category', flat=True).distinct().order_by('category')
    # Filter by category
    if selected_category != 'all':
        products = Product.objects.filter(category=selected_category)
    else:
        products = Product.objects.all()

    # Apply search filter
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

    # Coupon logic
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

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = [
            'phone_number', 'address', 'city', 'pincode',
            'profile_photo', 'date_of_birth', 'gender'
        ]

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




##   user_form = UserForm(instance=request.user)
  #  profile_form = ProfileForm(instance=request.user.profile)
   # if request.method == 'POST':
    #    user_form = UserForm(request.POST, instance=request.user)
     #   profile_form = ProfileForm(request.POST, request.FILES, instance=request.user.profile)
      #  if user_form.is_valid() and profile_form.is_valid():
       #     user_form.save()
        #    profile_form.save()
         #   messages.success(request, 'Profile updated successfully!')
          #  return redirect('profile')
    #return render(request, 'login/edit_profile.html', {
     #   'user_form': user_form,
      #  'profile_form': profile_form,
   # })#

@login_required
@csrf_exempt
def ajax_move_to_cart(request, product_id):
    if request.method == 'POST':
        # Add to cart
        cart = request.session.get('cart', {})
        if Product.objects.filter(id=product_id).exists():
            cart[str(product_id)] = cart.get(str(product_id), 0) + 1
            request.session['cart'] = cart
            request.session.modified = True
            # Remove from wishlist
            Wishlist.objects.filter(user=request.user, product_id=product_id).delete()
            cart_count = sum(cart.values())
            wishlist_count = Wishlist.objects.filter(user=request.user).count()
            return JsonResponse({'success': True, 'cart_count': cart_count, 'wishlist_count': wishlist_count})
        return JsonResponse({'success': False, 'error': 'Product not found'})
    return JsonResponse({'success': False, 'error': 'Invalid request method'})

 
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

    # Razorpay order creation
    import razorpay
    from django.conf import settings
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


@login_required
def profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)
    return render(request, 'login/profile.html', {
        'user': request.user,
        'profile': profile,
    })

def apply_coupon(request):
    if request.method == "POST":
        coupon = request.POST.get("coupon", "").strip().upper()
        if coupon == "SAVE10":
            request.session['coupon'] = 'SAVE10'
            request.session['discount'] = 10  # percent
            messages.success(request, "Coupon applied! You saved 10%.")
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

def address_view(request):
    if request.method == "POST":
        # Save address in session (or your model)
        request.session['address'] = {
            'name': request.POST['name'],
            'address': request.POST['address'],
            'city': request.POST['city'],
            'pincode': request.POST['pincode'],
            'phone': request.POST['phone'],
        }
        return redirect('payment')
    return render(request, 'login/address.html')