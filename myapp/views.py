from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User, Group
from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import Q
from django.utils.timezone import now
from django.views.generic import TemplateView
from django.shortcuts import render, redirect, get_object_or_404
from .models import Item, Profile, ItemReview, Collection, ExtraImage, CollectionAccessRequest, ItemRequest, Notification
from .forms import ItemForm, ProfileForm, ItemReviewForm, CollectionForm, ExtraImageForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .decorators import non_superuser_required, patron_required, librarian_required
from .mixins import NonSuperuserRequiredMixin
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Avg
from django.views.decorators.http import require_http_methods
from django.contrib.auth import logout
from django.conf import settings
from .forms import NotificationForm
from django.shortcuts import get_object_or_404


@login_required
def redirect_user(request):
    if request.user.is_authenticated and not request.user.is_superuser:
        try:
            profile = Profile.objects.get(user=request.user)
            if not profile.real_name:
                return redirect('setup_profile')
        except Profile.DoesNotExist:
            return redirect('setup_profile')
        
    if request.user.is_superuser:
        return redirect('/admin/')
    elif request.user.groups.filter(name='Librarian').exists():
        return redirect('librarian_homepage')
    elif request.user.groups.filter(name='Patron').exists():
        return redirect('patron_homepage')
    else:
        return redirect('catalog_view')

@login_required
@non_superuser_required
@patron_required
def patron_homepage(request):
    user = request.user
    profile = Profile.objects.filter(user=user).first()

    notifications = Notification.objects.filter(user=user).order_by('-timestamp')[:10]

    return render(request, 'account/patron_homepage.html', {
        'user': user,
        'profile': profile,
        'notifications': notifications,
    })

@login_required
def setup_profile(request):
    user = request.user
    try:
        profile = Profile.objects.get(user=user)
    except Profile.DoesNotExist:
        profile = Profile(user=user)
    if request.method == 'POST':
        real_name = request.POST.get('real_name')
        profile_pic = request.FILES.get('profile_pic')
        profile.real_name = real_name
        if profile_pic:
            profile.profile_pic = profile_pic
        profile.save()
        if user.is_superuser:
            return redirect('/admin/')
        elif request.user.groups.filter(name='Librarian').exists():
            return redirect('librarian_homepage')
        elif request.user.groups.filter(name='Patron').exists():
            return redirect('patron_homepage')
        else:
            return redirect('catalog_view')

    return render(request, 'setup_profile.html')

class LibrarianHomepageView(LoginRequiredMixin, NonSuperuserRequiredMixin, TemplateView):
    template_name = "account/librarian_homepage.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = Profile.objects.filter(user=self.request.user).first()
        return context

@login_required
@non_superuser_required
@librarian_required
def upgrade_patron(request):
    patrons = User.objects.filter(groups__name='Patron')

    if request.method == "POST":
        patron_id = request.POST.get("patron")
        if not patron_id:
            messages.error(request, "Please select a user.")
        else:
            try:
                patron = User.objects.get(id=patron_id)
                patron.groups.add(Group.objects.get(name='Librarian'))
                patron.groups.remove(Group.objects.get(name='Patron'))
                patron.save()
                messages.success(request, f"{patron.username} has been upgraded to Librarian.")
                return redirect('upgrade_patron')
            except User.DoesNotExist:
                messages.error(request, "User does not exist.")

    return render(request, 'account/upgrade_patron.html', {'patrons': patrons})

@non_superuser_required
def catalog_view(request):
    search_query = request.GET.get('q', '')

    is_librarian = False
    is_patron = False

    if request.user.is_authenticated:
        is_librarian = request.user.groups.filter(name='Librarian').exists()
        is_patron = request.user.groups.filter(name='Patron').exists()

    private_item_ids = Item.objects.filter(
        collections__is_public=False
    ).values_list('identifier', flat=True).distinct()

    if is_librarian:
        items = Item.objects.all()
    else:
        items = Item.objects.exclude(identifier__in=private_item_ids).filter(
            Q(collections__is_public=True) | Q(collections__isnull=True)
        ).distinct()

    if request.user.is_authenticated:
        collections = Collection.objects.filter(
            Q(is_public=True) | Q(visible_to_users=request.user)
        ).distinct()
    else:
        collections = Collection.objects.filter(is_public=True)

    restricted_collections = Collection.objects.filter(is_public=False).distinct()

    if search_query:
        items = items.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(collections__title__icontains=search_query)
        ).distinct()
        collections = collections.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    if request.user.is_authenticated:
        requests = ItemRequest.objects.filter(user=request.user)
        request_map = {r.item.identifier: r.status for r in requests}
        for item in items:
            item.request_status = request_map.get(item.identifier, None)
    else:
        for item in items:
            item.request_status = None

    form = None
    if request.user.is_authenticated:
        if request.method == "POST":
            form = CollectionForm(request.POST)
            if not is_librarian:
                form.fields.pop('is_public', None)
            form.fields['items'].queryset = items

            if form.is_valid():
                collection = form.save(commit=False)
                collection.created_by = request.user
                if not is_librarian:
                    collection.is_public = True
                collection.save()
                form.save_m2m()
                messages.success(request, "Collection created successfully.")
                return redirect('catalog_view')
        else:
            form = CollectionForm()
            if not is_librarian:
                form.fields.pop('is_public', None)
            form.fields['items'].queryset = items

    return render(request, 'catalog.html', {
        'catalog_items': items,
        'collections': collections,
        'restricted_collections': restricted_collections,
        'form': form,
        'search_query': search_query,
        'is_librarian': is_librarian,
        'is_patron': is_patron,
    })



@login_required
@non_superuser_required
def item_detail(request, pk):
    item = get_object_or_404(Item, identifier=pk)
    reviews = ItemReview.objects.filter(item=item).order_by('-timestamp')

    is_librarian = (
        request.user.is_authenticated
        and request.user.groups.filter(name="Librarian").exists()
    )
    is_patron = (
        request.user.is_authenticated
        and request.user.groups.filter(name="Patron").exists()
    )

    average_rating = reviews.aggregate(avg=Avg('rating'))['avg']
    if average_rating is not None:
        average_rating = round(average_rating, 2)

    existing_review = None
    review_form = None

    if request.user.is_authenticated:
        existing_review = ItemReview.objects.filter(
            item=item,
            user=request.user
        ).first()
    if not existing_review:
        if request.method == "POST":
            review_form = ItemReviewForm(request.POST)
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.item = item
                review.user = request.user
                review.save()
                messages.success(request, "Review submitted!", extra_tags='item-detail')
                return redirect('item-detail', pk=pk)
        else:
            review_form = ItemReviewForm()

    image_list = []
    if item.image:
        image_list.append({
            'url': item.image.url,
            'is_main': True,
        })

    for extra_image in item.extra_images.all():
        image_list.append({
            'url': extra_image.extra_image.url,
            'is_main': False,
        })

    collection = item.collections.first() if item.collections.exists() else None

    borrower_request = ItemRequest.objects.filter(item=item, status='Approved').first()
    borrower = borrower_request.user if borrower_request else None

    notification_form = NotificationForm()
    if request.method == "POST" and 'notification_submit' in request.POST:
        notification_form = NotificationForm(request.POST)
        if notification_form.is_valid() and borrower:
            Notification.objects.create(
                user=borrower,
                message=notification_form.cleaned_data['message'],
                is_read=False
            )

            messages.success(request, "Notification sent!", extra_tags='item-detail')
            return redirect('item-detail', pk=pk)

    is_librarian = request.user.groups.filter(name='Librarian').exists()
    is_patron = request.user.groups.filter(name='Patron').exists()

    patron_group = Group.objects.get(name='Patron')
    all_users = User.objects.filter(groups=patron_group)

    return render(request, 'item_detail.html', {
        'item': item,
        'reviews': reviews,
        'review_form': review_form,
        'existing_review': existing_review,
        'image_list': image_list,
        'collection': collection,
        'average_rating': average_rating,
        'borrower': borrower,
        'notification_form': notification_form,
        'is_librarian': is_librarian,
        'is_patron': is_patron,
    })



@non_superuser_required
def collections(request):
    query = request.GET.get('q', '')
    collections = Collection.objects.all()

    private_item_ids = Item.objects.filter(
        collections__is_public=False
    ).values_list('identifier', flat=True).distinct()

    for collection in collections:
        if collection.is_public:
            items = collection.items.exclude(identifier__in=private_item_ids)
        else:
            items = collection.items.all()

        collection.item_count = items.count()

    catalog_items = Item.objects.exclude(
        identifier__in=private_item_ids
    ).filter(
        Q(collections__is_public=True) | Q(collections__isnull=True)
    ).distinct()


    is_librarian = request.user.groups.filter(name='Librarian').exists()
    is_patron = request.user.groups.filter(name='Patron').exists()

    patron_group = Group.objects.get(name='Patron')
    all_users = User.objects.filter(groups=patron_group)

    if query:
        collections = collections.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )

    if request.user.is_authenticated:
        for collection in collections:
            if collection.visible_to_users.filter(id=request.user.id).exists():
                collection.access_granted = True
                collection.existing_request = None
            else:
                collection.access_granted = False
                collection.existing_request = CollectionAccessRequest.objects.filter(
                    user=request.user, collection=collection
                ).first()
    else:
        for collection in collections:
            collection.existing_request = None

    return render(request, 'collections.html', {
        'collections': collections,
        'query': query,
        'catalog_items': catalog_items,
        'is_librarian': is_librarian,
        'is_patron': is_patron,
        'all_users': all_users,
        })

@login_required
@non_superuser_required
def submit_review(request, pk):
    item = get_object_or_404(Item, identifier=pk)
    if request.method == "POST":
        form = ItemReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.item = item
            review.user = request.user
            review.save()
    return redirect('catalog_view')

@login_required
@non_superuser_required
def edit_review(request, review_id):
    review = get_object_or_404(ItemReview, id=review_id, user=request.user)
    if request.method == 'POST':
        form = ItemReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, "Review updated!", extra_tags='item-detail')
            return redirect('item-detail', pk=review.item.identifier)
    else:
        form = ItemReviewForm(instance=review)
    return render(request, 'edit_review.html', {'form': form, 'review': review})


@login_required
@non_superuser_required
def delete_review(request, review_id):
    review = get_object_or_404(ItemReview, id=review_id, user=request.user)
    item_identifier = review.item.identifier
    review.delete()
    messages.success(request, "Review deleted.", extra_tags='item-detail')
    return redirect('item-detail', pk=item_identifier)


@login_required
@non_superuser_required
def profile_update(request):

    is_librarian = (
        request.user.is_authenticated
        and request.user.groups.filter(name="Librarian").exists()
    )
    is_patron = (
        request.user.is_authenticated
        and request.user.groups.filter(name="Patron").exists()
    )

    is_librarian = request.user.groups.filter(name='Librarian').exists()
    is_patron = request.user.groups.filter(name='Patron').exists()


    profile, created = Profile.objects.get_or_create(user=request.user)
    current_image = profile.profile_pic.name if profile.profile_pic else None
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        clear_button_clicked = 'profile_pic-clear' in request.POST
        if form.is_valid():
            if clear_button_clicked and current_image:
                default_storage.delete(current_image)
                profile.profile_pic = None
            if 'profile_pic' in request.FILES:
                if current_image:
                    default_storage.delete(current_image)
            if created:
                profile.date_joined = now()
            form.save()
            return redirect("profile_update")

    else:
        form = ProfileForm(instance=profile)

    return render(request, "profile_update.html", 
                  {"form": form, 
                   "profile": profile, 
                   "is_librarian": is_librarian, 
                   "is_patron": is_patron})


@non_superuser_required
def search_collection_items(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)
    search_query = request.GET.get('q', '')

    if collection.is_public:
        private_item_ids = Item.objects.filter(
            collections__is_public=False
        ).values_list('identifier', flat=True).distinct()

        items = collection.items.exclude(identifier__in=private_item_ids)
    else:
        items = collection.items.all()

    item_count = items.count()

    is_librarian = False
    is_patron = False

    if request.user.is_authenticated:
        requests = ItemRequest.objects.filter(user=request.user)
        request_map = {r.item.identifier: r.status for r in requests}

        for item in items:
            item.request_status = request_map.get(item.identifier, None)

        is_librarian = request.user.groups.filter(name='Librarian').exists()
        is_patron = request.user.groups.filter(name='Patron').exists()

    if search_query:
        items = items.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )

    return render(request, 'collection_items.html', {
        'collection': collection,
        'items': items,
        'search_query': search_query,
        'is_librarian': is_librarian,
        'is_patron': is_patron,
        'item_count': item_count,
    })

@login_required
@non_superuser_required
@librarian_required
def add_item(request):
    """Handles item addition from the modal form."""
    if request.method == "POST":
        form = ItemForm(request.POST, request.FILES)
        extraimageform = ExtraImageForm(request.POST, request.FILES)
        files = request.FILES.getlist("extra_image")

        if form.is_valid():
            item = form.save(commit=False)
            item.created_by = request.user
            item.save()

            for f in files:
                ExtraImage.objects.create(identifier=item, extra_image=f)

            return redirect('catalog')
        else:
            return render(request, "catalog.html", {
                "form": form,
                "extraimageform": extraimageform,
            })

    else:
        form = ItemForm()
        extraimageform = ExtraImageForm()

    return render(request, "catalog.html", {
        "form": form,
        "extraimageform": extraimageform,
    })

@login_required
@non_superuser_required
@librarian_required
def delete_item(request, pk):
    item = get_object_or_404(Item, pk=pk)

    for extra_image in item.extra_images.all():
        extra_image.delete()

    item.delete()
    return redirect('catalog')


@login_required
@non_superuser_required
@librarian_required
def edit_item(request, pk):
    item = get_object_or_404(Item, pk=pk)
    current_image = item.image.name if item.image else None
    existing_extra_images = list(item.extra_images.all())

    if request.method == 'POST':
        form = ItemForm(request.POST, request.FILES, instance=item)
        extra_image_files = request.FILES.getlist("extra_image")
        removed_image_ids = request.POST.getlist("remove_extra_image")

        if form.is_valid():
            if 'image' in request.FILES and current_image:
                default_storage.delete(current_image)

            form.save()

            for img_id in removed_image_ids:
                try:
                    extra_img = ExtraImage.objects.get(id=img_id, identifier=item)
                    extra_img.delete()
                except ExtraImage.DoesNotExist:
                    pass

            for img_file in extra_image_files:
                ExtraImage.objects.create(identifier=item, extra_image=img_file)

            return redirect('catalog')

    else:
        form = ItemForm(instance=item)

    return render(request, 'edit_item.html', {
        'form': form,
        'item': item,
        'extra_images': item.extra_images.all()
    })


@login_required
@non_superuser_required
@librarian_required
def create_collection(request):
    if request.method == "POST":
        form = CollectionForm(request.POST, user=request.user)
        if form.is_valid():
            collection = form.save(commit=False)
            collection.created_by = request.user

            selected_items = form.cleaned_data.get("items")
            is_public = form.cleaned_data.get("is_public")

            if not is_public:
                for item in selected_items:
                    other_private = item.collections.filter(is_public=False)
                    if other_private.exists():
                        form.add_error(
                            "items",
                            f"'{item.title}' is already in a private collection."
                        )
                        return render(request, "collections.html", {
                            'form': form,
                            'collections': Collection.objects.all(),
                        })

            collection.save()
            form.instance = collection
            form.save_m2m()

            messages.success(request, "Collection created successfully.")
            return redirect('collections')

    else:
        form = CollectionForm(user=request.user)

    return render(request, "collections.html", {
        'form': form,
        'collections': Collection.objects.all(),
    })



@login_required
@non_superuser_required
@patron_required
def create_patron_collection(request):
    if request.method == "POST":
        form = CollectionForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    collection = form.save(commit=False)
                    collection.created_by = request.user
                    collection.is_public = True
                    collection.save()

                    item_identifiers = filter(None, request.POST.getlist('items'))
                    item_identifiers = list(item_identifiers)

                    items_to_add = Item.objects.filter(identifier__in=item_identifiers)
                    collection.items.set(items_to_add)
                    collection.save()

                    messages.success(request, "Collection created successfully.")
                    return redirect('collections')

            except Exception as e:
                messages.error(request, f"Error creating collection: {str(e)}")
                return redirect('collections')

        else:
            messages.error(request, "Invalid form submission.")
            return redirect('collections')

    else:
        form = CollectionForm()

    return redirect('collections')

@login_required
@non_superuser_required
@patron_required
def request_access(request, collection_id):
    collection = get_object_or_404(Collection, id=collection_id)

    exisiting_request = CollectionAccessRequest.objects.filter(
        Q(user=request.user) & Q(collection=collection)
    ).first()

    if exisiting_request:
        if exisiting_request.approved:
            messages.info(request, "You already have access to this collection.")
            return redirect('collections')
        else:
            messages.info(request, "Your access request is pending approval.")
            return redirect('collections')
    else:
        access_request = CollectionAccessRequest.objects.create(
            user=request.user,
            collection=collection
        )
        access_request.save()

    return redirect('collections')

@login_required
@non_superuser_required
def edit_collection(request, collection_id):
    """Edit collection only if the current user is the creator."""
    collection = get_object_or_404(Collection, id=collection_id, created_by=request.user)

    if request.method == "POST":
        form = CollectionForm(request.POST, instance=collection, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Collection updated successfully.")
            return redirect('collections')
        else:
            messages.error(request, "Invalid form submission.")
    else:
        form = CollectionForm(instance=collection, user=request.user)

    return render(request, "edit_collection.html", {
        "form": form,
        "collection": collection
    })


@login_required
@non_superuser_required
def delete_collection(request, collection_id):
    """Delete collection only if the current user is the creator."""
    collection = get_object_or_404(Collection, id=collection_id, created_by=request.user)

    if request.method == "POST":
        collection.delete()
        messages.success(request, "Collection deleted successfully.")
        return redirect('catalog_view')

    return render(request, "confirm_delete_collection.html", {
        "collection": collection
    })

@login_required
@non_superuser_required
def edit_collection_librarian(request, pk):
    collection = get_object_or_404(Collection, pk=pk)

    if collection.created_by != request.user:
        messages.error(request, "You do not have permission to edit this collection.")
        return redirect('catalog')

    private_item_ids = Item.objects.filter(
        collections__is_public=False
    ).values_list('identifier', flat=True).distinct()

    if collection.is_public:
        available_items = Item.objects.exclude(identifier__in=private_item_ids).distinct()
    else:
        available_items = Item.objects.all()

    if request.method == "POST":
        form = CollectionForm(request.POST, instance=collection, user=request.user, available_items=available_items)
        if form.is_valid():
            form.save()
            messages.success(request, "Collection updated successfully.")
            return redirect('catalog')
    else:
        form = CollectionForm(instance=collection, user=request.user, available_items=available_items)

    return render(request, 'edit_collection_librarian.html', {'form': form, 'collection': collection})




@login_required
@non_superuser_required
def delete_collection_librarian(request, pk):
    collection = get_object_or_404(Collection, pk=pk)

    if collection.created_by != request.user:
        messages.error(request, "You do not have permission to delete this collection.")
        return redirect('catalog')

    if request.method == "POST":
        collection.delete()
        messages.success(request, "Collection deleted successfully.")
        return redirect('catalog')

    return render(request, 'confirm_delete_collection_librarian.html', {'collection': collection})

@login_required
@non_superuser_required
@librarian_required
def view_requests(request):
    access_requests = CollectionAccessRequest.objects.filter(approved=False)
    return render(request, 'librarian_request_approval.html', {'access_requests': access_requests})

@login_required
@non_superuser_required
@librarian_required
def approve_request(request, request_id):
    access_request = get_object_or_404(CollectionAccessRequest, id=request_id)
    access_request.approved = True
    access_request.save()
    collection = access_request.collection
    collection.visible_to_users.add(access_request.user)
    collection.save()

    Notification.objects.create(
        user=access_request.user,
        message=f"Your access request to '{collection.title}' has been approved and is visible to you.",
        is_read=False
    )

    messages.success(request, "Access request approved.")
    return redirect('librarian_request_approval')

@login_required
@non_superuser_required
@librarian_required
def deny_request(request, request_id):
    access_request = get_object_or_404(CollectionAccessRequest, id=request_id)
    access_request.delete()

    Notification.objects.create(
        user=access_request.user,
        message=f"Your access request to '{access_request.collection.title}' has been denied",
        is_read=False
    )

    messages.success(request, "Access request denied.")
    return redirect('librarian_request_approval')

@login_required
@non_superuser_required
def request_borrow_item(request, item_id):
    item = get_object_or_404(Item, identifier=item_id)

    existing_request = ItemRequest.objects.filter(
        item=item,
        user=request.user
    ).first()

    if existing_request:
        if existing_request.status == 'Approved':
            return JsonResponse({'status': 'error', 'message': 'Item is already approved.'})
        elif existing_request.status == 'Pending':
            return JsonResponse({'status': 'error', 'message': 'Item is pending.'})
        else:
            existing_request.status = 'Pending'
            existing_request.save()
            messages.info(request, "Your requested item was denied.")
        return redirect('catalog')

    ItemRequest.objects.create(item=item, user=request.user, status='Pending')
    messages.success(request, "Your borrow request has been submitted.")
    return redirect('catalog')

@login_required
def request_borrow_item_collection(request, item_id):
    item = get_object_or_404(Item, identifier=item_id)

    existing_request = ItemRequest.objects.filter(
        item=item,
        user=request.user
    ).first()

    if existing_request:
        if existing_request.status == 'Approved':
            messages.info(request, "Item is already approved.")
        elif existing_request.status == 'Pending':
            messages.info(request, "Item is pending.")
        else:
            existing_request.status = 'Pending'
            existing_request.save()
            messages.info(request, "Your requested item was denied.") 
        return redirect('collection_items', collection_id=item.collections.first().id)

    ItemRequest.objects.create(item=item, user=request.user, status='Pending')
    messages.success(request, "Your borrow request has been submitted.")
    return redirect('collection_items', collection_id=item.collections.first().id)

@login_required
@non_superuser_required
@librarian_required
def view_borrow_requests(request):
    borrow_requests = ItemRequest.objects.filter(status='Pending').order_by('-request_date')
    return render(request, 'borrow_requests.html', {'borrow_requests': borrow_requests})

@login_required
@non_superuser_required
def approve_borrow_request(request, request_id):
    borrow_request = get_object_or_404(ItemRequest, id=request_id)
    borrow_request.status = 'Approved'
    borrow_request.save()

    borrow_request.item.availability = "Checked Out"
    borrow_request.item.save()

    other_borrow_requests = ItemRequest.objects.filter(
        item=borrow_request.item,
        status='Pending'
    ).exclude(id=request_id)
    for other_request in other_borrow_requests:
        other_request.status = 'Denied'
        other_request.save()

        Notification.objects.create(
        user=other_request.user,
        message=f"Your borrow request for '{borrow_request.item.title}' has denied.",
        is_read=False
    )

    Notification.objects.create(
        user=borrow_request.user,
        message=f"Your borrow request for '{borrow_request.item.title}' has been approved and is in your possession.",
        is_read=False
    )

    messages.success(request, "Approved borrow request.")
    return redirect('view_borrow_requests')

@login_required
@non_superuser_required
def deny_borrow_request(request, request_id):
    borrow_request = get_object_or_404(ItemRequest, id=request_id)
    borrow_request.status = 'Denied'
    borrow_request.save()
    messages.success(request, "Denied borrow request.")

    Notification.objects.create(
        user=borrow_request.user,
        message=f"Your borrow request for '{borrow_request.item.title}' has been denied.",
        is_read=False
    )

    return redirect('view_borrow_requests')

@login_required
@non_superuser_required
def return_borrow_item(request, request_id):
    borrow_request = get_object_or_404(ItemRequest, id=request_id)
    if borrow_request.status == 'Approved':
        borrow_request.item.availability = "Available"
        borrow_request.item.save()
        borrow_request.status = 'Returned'
        borrow_request.save()

        Notification.objects.create(
            user=borrow_request.user,
            message=f"Your borrow request for '{borrow_request.item.title}' has been marked as returned.",
            is_read=False
        )

        messages.success(request, "Item returned successfully.")
    else:
        messages.error(request, "Only approved items can be returned.")

    return redirect('current_items')

@login_required
@non_superuser_required
def current_items_in_possession(request):
    approved_requests = ItemRequest.objects.filter(
        user=request.user,
        status='Approved'
    ).order_by('-request_date')
    return render(request, 'current_items.html', {'items': approved_requests})

@login_required
@non_superuser_required
def remove_profile_picture(request):
    if request.method == "POST":
        profile = request.user.profile
        profile.profile_pic.delete(save=False)
        profile.profile_pic = None
        profile.save()
    return redirect('profile_update')

@require_POST
@login_required
def mark_notification_as_read(request, notification_id):
    try:
        notification = Notification.objects.get(id=notification_id, user=request.user)
        notification.is_read = True
        notification.save()
        return redirect('patron_homepage')
    except Notification.DoesNotExist:
        return redirect('patron_homepage')

@require_http_methods(["GET", "POST"])
def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect(settings.LOGOUT_REDIRECT_URL or "/")
    return render(request, "account/logout.html")
