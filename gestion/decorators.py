from functools import wraps
from django.shortcuts import redirect

def pasajero_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if hasattr(request.user, 'rol') and request.user.rol == 'PASAJERO':
            return view_func(request, *args, **kwargs)
        else:
            return redirect('vuelos')  # O a otra página con mensaje
    return _wrapped_view
