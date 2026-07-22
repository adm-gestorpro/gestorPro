import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from fcm_django.models import FCMDevice

@login_required
def registrar_dispositivo_fcm(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        registration_id = data.get('token')
        tipo_dispositivo = data.get('type', 'web') # 'web', 'android', 'ios'

        if not registration_id:
            return JsonResponse({'error': 'Token não informado'}, status=400)

        # Salva ou atualiza o dispositivo associado ao usuário logado
        device, created = FCMDevice.objects.update_or_create(
            registration_id=registration_id,
            defaults={
                'user': request.user,
                'type': tipo_dispositivo,
                'active': True
            }
        )

        return JsonResponse({'status': 'sucesso', 'device_id': device.id})
    return JsonResponse({'error': 'Método não permitido'}, status=405)