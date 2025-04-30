from allauth.account.adapter import DefaultAccountAdapter
from django.shortcuts import resolve_url

class YourAccountAdapter(DefaultAccountAdapter):
    def get_login_redirect_url(self, request):
        user = request.user
        if user.is_superuser:
            return resolve_url('/admin/')
        return super().get_login_redirect_url(request)
