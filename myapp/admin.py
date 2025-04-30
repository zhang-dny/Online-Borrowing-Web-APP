from django.contrib import admin
from .models import Profile, Item, ItemReview, Collection

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'profile_pic')

class ItemAdmin(admin.ModelAdmin):
    list_display = ('title', 'identifier', 'location', 'availability')
    search_fields = ('title', 'identifier', 'location')

class ItemReviewAdmin(admin.ModelAdmin):
    list_display = ('item', 'user', 'rating', 'timestamp')
    search_fields = ('item__title', 'user__username')
    list_filter = ('rating', 'timestamp')

admin.site.register(Profile, ProfileAdmin)
admin.site.register(Item)
admin.site.register(ItemReview)
admin.site.register(Collection)