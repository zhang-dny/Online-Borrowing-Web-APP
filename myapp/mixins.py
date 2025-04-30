from django.shortcuts import redirect

class NonSuperuserRequiredMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_superuser:
            return redirect('/admin/')
        return super().dispatch(request, *args, **kwargs)
