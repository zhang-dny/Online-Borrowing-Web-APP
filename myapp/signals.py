from django.contrib.auth.models import Group
from allauth.account.signals import user_logged_in
from django.dispatch import receiver
from .models import Profile

@receiver(user_logged_in)
def add_user_to_patron_group(request, user, **kwargs):
    patron_group, _ = Group.objects.get_or_create(name='Patron')
    if not user.groups.filter(name='Patron').exists() and not user.groups.filter(name='Librarian').exists():
        user.groups.add(patron_group)

@receiver(user_logged_in)
def populate_profile_on_login(request, user, **kwargs):
    social_account = user.socialaccount_set.first()
    if social_account and social_account.provider == 'google':
        email = social_account.extra_data.get('email')
        name = social_account.extra_data.get('name')

        profile, _ = Profile.objects.get_or_create(user=user)
        if not profile.google_email:
            profile.google_email = email
        if not profile.real_name:
            profile.real_name = name
        if not profile.date_joined:
            profile.date_joined = user.date_joined
        profile.save()
