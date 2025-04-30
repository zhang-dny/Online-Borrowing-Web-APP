from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.core.exceptions import ValidationError

from .models import Item, Profile, ItemReview, Collection, ExtraImage
from django.contrib.auth.models import User

class FirstAndLastNameSignupForm(SocialSignupForm):
    first_name = forms.CharField(max_length=30, required=True, label="First Name")
    last_name = forms.CharField(max_length=30, required=True, label="Last Name")

    def save(self, request):
        user = super().save(request)
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        return user

class ItemForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ['title', 'description', 'availability', 'image', 'location']
        widgets = {"availability": forms.Select(
            choices=Item.STATUS_CHOICES, attrs={"class": "availability-dropdown"}
        ), }

class ExtraImageForm(forms.ModelForm):
    extra_image = forms.ImageField(label="Extra Image", widget=forms.ClearableFileInput(attrs={'allow_multiple_selected': True}),required = False)
    class Meta:
        model = ExtraImage
        fields = ("extra_image",)

class ItemReviewForm(forms.ModelForm):
    class Meta:
        model = ItemReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.NumberInput(attrs={
                'min': 1.0,
                'max': 5.0,
                'step': 0.1,
                'class': 'form-control'
            }),
            'comment': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
        }

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['real_name', 'google_email', 'profile_pic']
        widgets = {
            'real_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Full Name',
                'id': 'real_name'
            }),
            'google_email': forms.EmailInput(attrs={
                'class': 'form-control-plaintext',
                'readonly': True,
                'placeholder': 'Google Email',
                'id': 'google_email'
            }),
            'profile_pic': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'id': 'profile_pic'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['google_email'].disabled = True

    def clean_google_email(self):
        return self.instance.google_email

class CollectionForm(forms.ModelForm):
    PUBLIC_CHOICES = [
        (True, 'Public (Anyone can see)'),
        (False, 'Private (Request access required)'),
    ]

    is_public = forms.ChoiceField(
        choices=PUBLIC_CHOICES,
        widget=forms.RadioSelect,
        label="Collection Visibility",
        initial=True,
    )

    class Meta:
        model = Collection
        fields = ['title', 'description', 'is_public', 'items', 'visible_to_users']
        widgets = {
            'items': forms.CheckboxSelectMultiple,
            'visible_to_users': forms.CheckboxSelectMultiple,
        }

    def __init__(self, *args, user=None, available_items=None, instance=None, **kwargs):
        super().__init__(*args, instance=instance, **kwargs)

        if available_items is not None:
            self.fields['items'].queryset = available_items
        else:
            if instance:
                if instance.is_public:
                    private_items = Item.objects.filter(collections__is_public=False).distinct()
                    self.fields['items'].queryset = Item.objects.filter(availability="Available").exclude(
                        identifier__in=private_items.values_list('identifier', flat=True))
                else:
                    self.fields['items'].queryset = Item.objects.filter(availability="Available")
            else:
                private_items = Item.objects.filter(collections__is_public=False).distinct()
                self.fields['items'].queryset = Item.objects.filter(availability="Available").exclude(
                    identifier__in=private_items.values_list('identifier', flat=True))

        if user and user.groups.filter(name='Patron').exists():
            self.fields.pop('is_public', None)
            self.fields.pop('visible_to_users', None)

            available_items = Item.objects.filter(availability="Available")
            private_items = Item.objects.filter(collections__is_public=False).exclude(collections=instance).distinct()
            self.fields['items'].queryset = available_items.exclude(identifier__in=private_items.values_list('identifier', flat=True))

        if user and user.groups.filter(name='Librarian').exists():
            self.fields.pop('is_public', None)

            if instance and not instance.is_public:
                patron_users = User.objects.filter(groups__name='Patron')
                self.fields['visible_to_users'].queryset = patron_users.exclude(id=user.id)
            else:
                self.fields.pop('visible_to_users', None)

    def clean_items(self):
        items = self.cleaned_data.get('items')
        if not items:
            raise ValidationError("A collection must have at least one item.")
        return items

    def clean_is_public(self):
        value = self.cleaned_data.get('is_public')
        return value == 'True'

class NotificationForm(forms.Form):
    message = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 3, 'placeholder': 'Enter custom notification...'}),
        label="Message"
    )
