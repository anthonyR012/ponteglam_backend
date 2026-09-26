import os
import sys
import argparse
import django

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ponteglam.settings")
django.setup()

from users.models import User
from fcm_django.models import FCMDevice
from notifications.tasks import (
    _send_push_to_user,
    _create_in_app_notification,
    send_fcm_notification_batch_task,
)

def send_notification():
    parser = argparse.ArgumentParser(
        description="Simular y enviar una notificación manual (Push y/o In-App) en PonteGlam."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--user-id",
        type=int,
        help="ID del usuario destinatario de la notificación.",
    )
    group.add_argument(
        "--email",
        type=str,
        help="Correo electrónico del usuario destinatario de la notificación.",
    )
    group.add_argument(
        "--multicast",
        action="store_true",
        help="Enviar notificación push a todos los dispositivos activos en la base de datos.",
    )

    parser.add_argument(
        "--title",
        type=str,
        default="Notificación de Prueba 🚀",
        help="Título de la notificación.",
    )
    parser.add_argument(
        "--body",
        type=str,
        default="Esta es una simulación manual de notificación enviada desde el backend.",
        help="Cuerpo o mensaje de la notificación.",
    )
    parser.add_argument(
        "--action",
        type=str,
        choices=["history", "supplier_appointments", "confirm_cash"],
        help="Acción/Destino para la redirección de la push notification.",
    )
    parser.add_argument(
        "--appointment-id",
        type=int,
        help="ID de la cita asociado para la redirección.",
    )
    parser.add_argument(
        "--in-app-only",
        action="store_true",
        help="Solo guardar la notificación en la base de datos (In-App) sin enviar Push FCM.",
    )
    parser.add_argument(
        "--push-only",
        action="store_true",
        help="Solo enviar la notificación Push FCM sin persistirla en la base de datos.",
    )

    args = parser.parse_args()

    # Resolver el usuario si se pasó correo
    user = None
    if args.user_id:
        try:
            user = User.objects.get(pk=args.user_id)
        except User.DoesNotExist:
            print(f"❌ Error: El usuario con ID {args.user_id} no existe.")
            sys.exit(1)
    elif args.email:
        try:
            user = User.objects.get(email=args.email)
        except User.DoesNotExist:
            print(f"❌ Error: El usuario con correo {args.email} no existe.")
            sys.exit(1)

    # Preparar payload de datos
    payload = {}
    if args.action:
        payload["action"] = args.action
    if args.appointment_id:
        payload["appointment_id"] = str(args.appointment_id)

    # Caso Multicast
    if args.multicast:
        tokens = list(
            FCMDevice.objects.filter(active=True).values_list(
                "registration_id", flat=True
            )
        )
        if not tokens:
            print("⚠️ No hay dispositivos activos registrados con tokens FCM.")
            return

        print(f"📡 Enviando notificación multicast a {len(tokens)} dispositivos activos...")
        send_fcm_notification_batch_task.delay(
            tokens, args.title, args.body, payload
        )
        print("✅ Tarea multicast enviada a Celery.")
        return

    # Si no es multicast, enviamos a un usuario específico
    print(f"👤 Destinatario: {user.full_name} (ID: {user.id}, Correo: {user.email})")

    # 1. Crear notificación In-App si no se especificó --push-only
    if not args.push_only:
        _create_in_app_notification(
            title=args.title,
            body=args.body,
            user_id=user.id,
            go_to=args.action,
            created_by_user_id=1,  # Sistema / Admin
            data=payload if payload else None,
        )
        print("💾 Notificación In-App guardada en base de datos.")

    # 2. Enviar notificación Push FCM si no se especificó --in-app-only
    if not args.in_app_only:
        devices = FCMDevice.objects.filter(user=user, active=True)
        if not devices.exists():
            print(
                f"⚠️ Advertencia: El usuario {user.full_name} no tiene dispositivos FCM activos."
            )
        else:
            print(f"📲 Enviando push notification a {devices.count()} dispositivo(s) activo(s)...")
            _send_push_to_user(
                user_id=user.id, title=args.title, body=args.body, data=payload
            )
            print("✅ Notificación push enviada a Celery.")

if __name__ == "__main__":
    send_notification()
