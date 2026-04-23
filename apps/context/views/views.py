from django.shortcuts import render
from apps.context.services.context_manager import ContextManager

def dashboard(request):
    # Supongamos que el usuario tiene una ciudad asignada o usamos una por defecto
    user_city = request.user.city 
    
    # Esto disparará la carga automática si los datos son viejos
    context_data = ContextManager.get_current_context(user_city)
    
    return render(request, 'dashboard.html', {
        'weather': context_data['weather'],
        'news': context_data['news']
    })