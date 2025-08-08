# gestion/context_processors.py
from django.utils import timezone  # Mejor práctica en Django que usar datetime directamente

def aerolinea_context(request):
    return {
        'nombre_aerolinea': 'Tu Aerolínea',
        'year_actual': timezone.now().year,  # Usando timezone de Django
    }