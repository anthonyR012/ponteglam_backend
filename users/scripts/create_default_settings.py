# Python Standard Library
import json
import os

# Third-party Libraries
from distutils.util import strtobool
from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction

# Local Modules
from core import models as core_models
from ponteglam.settings import BASE_DIR
from users import models

f = open('users/scripts/default_settings.json')
default_settings = json.load(f)

USERS = default_settings.get('users', None)
USERS_IMAGES = os.path.join(
    BASE_DIR, 'static/default_settings/users_images/'
)


def create_user_admin():

    print('################# CREATING ADMIN USER ################')
    with transaction.atomic():

        try:
            user, created = models.User.objects.get_or_create(
                username='admin',
                defaults={
                    'email': 'admin@gmail.com',
                    'first_name': 'adminfn',
                    'last_name': 'adminln',
                    'full_name': 'adminfn adminln',
                    'is_superuser': True,
                    'is_staff': True
                }
            )

            picture_filename = 'user_1.jpg'
            picture_path = os.path.join(
                USERS_IMAGES, picture_filename
            )

            # Leer la imagen desde la ruta local
            with open(picture_path, 'rb') as picture_data:
                user.picture.delete(save=True)

                # Asignar la imagen a ServiceCategory
                user.picture.save(
                    picture_filename, picture_data, save=True
                )

            user.set_password('admin')
            user.save()

            if created:
                print('Admin user created')
            else:
                print('Admin user already exists')

        except Exception as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)


def create_users():

    print('################# CREATING USERS ################')
    with transaction.atomic():

        try:

            for user_data in USERS:

                username = user_data.get('username', None)
                email = user_data.get('email', None)
                first_name = user_data.get('first_name', None)
                last_name = user_data.get('last_name', None)
                full_name = user_data.get('full_name', None)
                password = user_data.get('password', None)
                address = user_data.get('address', None)
                phone = user_data.get('phone', None)
                date_of_birth = user_data.get('date_of_birth', None)
                identification = user_data.get('identification', None)
                uuid_google = user_data.get('uuid_google', None)
                email_verified = user_data.get('email_verified', None)
                city = user_data.get('city', None)
                picture_filename = user_data.get('picture', None)
                gender = user_data.get('gender', None)
                type = user_data.get('type', None)
                state = user_data.get('state', None)
                login = user_data.get('login', None)

                city_name = user_data.get('city', None)
                city, _ = core_models.GeoReferenceCity.objects.get_or_create(
                    name=city_name,
                    defaults={'latitude': '0', 'longitude': '0', 'created_by_user_id': 1}
                )
                gender = core_models.Type.objects.get(
                    code=gender, category_type__code='gender_user'
                )
                type = core_models.Type.objects.get(
                    code=type, category_type__code='type_user'
                )
                state = core_models.Type.objects.get(
                    code=state, category_type__code='status_user'
                )
                login = core_models.Type.objects.get(
                    code=login, category_type__code='login_of'
                )

                user, created = models.User.objects.get_or_create(
                    defaults={
                        'username': username,
                        'email': email,
                        'first_name': first_name,
                        'last_name': last_name,
                        'full_name': full_name,
                        'address': address,
                        'phone': phone,
                        'date_of_birth': date_of_birth,
                        'identification': identification,
                        'uuid_google': uuid_google,
                        'email_verified': strtobool(email_verified),
                        'city': city,
                        'gender': gender,
                        'type': type,
                        'state': state,
                        'login': login
                    },
                    **{
                        'username': username,
                    }
                )

                picture_path = os.path.join(
                    USERS_IMAGES, picture_filename
                )

                # Leer la imagen desde la ruta local
                with open(picture_path, 'rb') as picture_data:
                    user.picture.delete(save=True)

                    # Asignar la imagen a ServiceCategory
                    user.picture.save(
                        picture_filename, picture_data, save=True
                    )

                user.set_password(password)
                user.save()

                if created:
                    print(f'User {user} created.')
                else:
                    print(f'User {user} updated.')

        except MultipleObjectsReturned as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)

        except Exception as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)


def run():
    create_users()
