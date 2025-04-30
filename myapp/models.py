from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.contrib.auth.models import User, AbstractUser
from django.core.files.storage import default_storage
from django.utils.timezone import now
import uuid
from datetime import timedelta
from decimal import Decimal


class Item(models.Model):
    STATUS_CHOICES = [
        ("Available", "Available"),
        ("Checked Out", "Checked Out")
    ]
    title = models.CharField(max_length = 200)
    description = models.TextField()
    availability = models.CharField(max_length = 20, choices = STATUS_CHOICES, default = 'Available')
    image = models.ImageField(upload_to ='item_images/', blank=True, null=True)
    identifier = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    location = models.CharField(max_length=50, null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        if self.image:
            default_storage.delete(self.image.name)
        super(Item, self).delete(*args, **kwargs)

class ExtraImage(models.Model):
    identifier = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='extra_images')
    extra_image = models.ImageField(upload_to = 'extra_images/', blank=True, null=True)

    def __str__(self):
        return f"Extra image for {self.identifier.title}"

    def delete(self, *args, **kwargs):
        if self.extra_image:
            default_storage.delete(self.extra_image.name)
        super(ExtraImage, self).delete(*args, **kwargs)

class Profile(models.Model):
    profile_pic = models.ImageField(upload_to ='profile_pictures/', null = True, blank = True)
    real_name = models.CharField(max_length=100, blank=True, null=True)
    google_email = models.EmailField(blank=True, null=True)
    user = models.OneToOneField(User, max_length=10, on_delete=models.CASCADE, null = True)
    date_joined = models.DateTimeField(default=now)

    def delete(self, *args, **kwargs):
        if self.profile_pic:
            default_storage.delete(self.profile_pic.name)
        super(Profile, self).delete(*args, **kwargs)

    def __str__(self):
        return self.user.username

class ItemReview(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.DecimalField(
        max_digits=2,
        decimal_places=1,
        validators=[MinValueValidator(Decimal('1.0')), MaxValueValidator(Decimal('5.0'))]
    )
    comment = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Review by {self.user.username} for {self.item.title}"

class Collection(models.Model):
    title = models.CharField(max_length=100)
    description = models.TextField()
    is_public = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='collections')
    items = models.ManyToManyField('Item', related_name='collections', blank=True)
    visible_to_users = models.ManyToManyField(User, blank=True, related_name='visible_collections')

    def __str__(self):
        return self.title
    
class CollectionAccessRequest(models.Model):
    collection = models.ForeignKey(Collection, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)

    def __str__(self):
        return f"Access request by {self.user.username} for {self.collection.title}"
    
class ItemRequest(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    request_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[('Pending', 'Pending'), ('Approved', 'Approved'), ('Denied', 'Denied')], default='Pending')

    @property
    def return_date(self):
        return self.request_date + timedelta(days=14)

    def __str__(self):
        return f"Request by {self.user.username} for {self.item.title}"
    
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    def __str__(self):
        return f"Notification for {self.user.username}"