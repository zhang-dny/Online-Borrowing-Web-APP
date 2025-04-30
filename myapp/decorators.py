from django.shortcuts import redirect

def non_superuser_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if request.user.is_superuser:
            return redirect('/admin/')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def patron_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.groups.filter(name='Patron').exists():
            return redirect('catalog_view')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def librarian_required(view_func):
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.groups.filter(name='Librarian').exists():
            return redirect('catalog_view')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
