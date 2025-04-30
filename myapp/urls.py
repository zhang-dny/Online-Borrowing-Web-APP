from django.urls import path, include
from django.views.generic import TemplateView
from django.contrib.auth.views import LogoutView
from django.contrib import admin
from . import views
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
                  path('admin/', admin.site.urls),
                  path('', lambda request: redirect('/accounts/login/')),
                  path("accounts/logout/", views.logout_view, name="account_logout"),
                  path('catalog/', views.catalog_view, name="catalog"),
                  path('accounts/', include('allauth.urls')),
                  path('setup_profile/', views.setup_profile, name='setup_profile'),
                  path('librarian_homepage/', views.LibrarianHomepageView.as_view(), name="librarian_homepage"),
                  path('patron_homepage/', views.patron_homepage, name="patron_homepage"),
                  path('redirect_user/', views.redirect_user, name='redirect_user'),
                  path('catalog/', views.catalog_view, name='catalog_view'),
                  path('browse/', views.catalog_view, name='browse_as_guest'),
                  path('upgrade/', views.upgrade_patron, name='upgrade_patron'),
                  path('librarian/add-item/', views.add_item, name="add-item"),
                  path('librarian/delete/<uuid:pk>/', views.delete_item, name='delete-item'),
                  path('librarian/edit/<uuid:pk>/', views.edit_item, name='edit-item'),
                  path('profile/update/', views.profile_update, name='profile_update'),
                  path('review/<uuid:pk>/', views.submit_review, name='submit-review'),
                  path('review/edit/<int:review_id>/', views.edit_review, name='edit-review'),
                  path('review/delete/<int:review_id>/', views.delete_review, name='delete-review'),
                  path('add-collection/', views.create_collection, name='add-collection'),
                  path('create-patron-collection/', views.create_patron_collection, name='create-patron-collection'),
                  path('request-access/<int:collection_id>/', views.request_access, name='request-access'),
                  path('librarian_request_approval', views.view_requests, name='librarian_request_approval'),
                  path('approve_request/<int:request_id>/', views.approve_request, name='approve_request'),
                  path('deny_request/<int:request_id>/', views.deny_request, name='deny_request'),
                  path('borrow-request/<uuid:item_id>/', views.request_borrow_item, name='request_borrow_item'),
                  path('borrow-request-collection/<uuid:item_id>/', views.request_borrow_item_collection, name='request_borrow_item_collection'),
                  path('borrow-requests/', views.view_borrow_requests, name='view_borrow_requests'),
                  path('approve-borrow/<int:request_id>/', views.approve_borrow_request, name='approve_borrow_request'),
                  path('deny-borrow/<int:request_id>/', views.deny_borrow_request, name='deny_borrow_request'),
                  path('current-items/', views.current_items_in_possession, name='current_items'),
                  path('collection/<int:collection_id>/edit/', views.edit_collection, name='edit_collection'),
                  path('collection/<int:collection_id>/delete/', views.delete_collection, name='delete_collection'),
                  path('librarian/edit-collection/<int:pk>/', views.edit_collection_librarian, name='edit_collection_librarian'),
                  path('librarian/delete-collection/<int:pk>/', views.delete_collection_librarian, name='delete_collection_librarian'),
                  path('collections/', views.collections, name='collections'),
                  path('collections/<int:collection_id>/items/', views.search_collection_items, name='collection_items'),
                  path('item/<uuid:pk>/', views.item_detail, name='item-detail'),
                  path('return-borrow-item/<int:request_id>/', views.return_borrow_item, name='return-borrow-item'),
                  path('notifications/mark-read/<int:notification_id>/', views.mark_notification_as_read, name='mark_notification_as_read'),
                  path('remove-profile-picture/', views.remove_profile_picture, name='remove_profile_picture'),
              ] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
