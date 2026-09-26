from django.http import HttpResponse
from firebase_admin import messaging


def send_notification(request):
    # Obtén el token del dispositivo (d
    registration_token = 'cNIF62-ZTO2so5KB'

    # Crea un mensaje
    message = messaging.Message(
        token=registration_token,
        notification=messaging.Notification(
            title='¡Hola desde Django!',
            body='Esta es una notificación de prueba.'
        )
    )

    # Envía la notificación
    response = messaging.send(message)
    print('Successfully sent message:', response)

    return HttpResponse('Notificación enviada.')


def send_notification_to_all(request):
    # Obtén los tokens de los dispositivos
    from fcm_django.models import FCMDevice
    devices = FCMDevice.objects.all()
    tokens = [device.registration_id for device in devices]

    # Crea un mensaje multicast
    multicast_message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(
            title='¡Hola desde Django!',
            body='Esta es una notificación de prueba.'
        )
    )

    # Envía el mensaje multicast
    response = messaging.send_each_for_multicast(multicast_message)

    # Imprime la respuesta
    print('Successfully sent message:', response)

    return HttpResponse('Notificaciones enviadas.')
