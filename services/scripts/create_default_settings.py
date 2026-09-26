# Python Standard Library
import json
import os

# Third-party Libraries
from distutils.util import strtobool
from django.core.exceptions import MultipleObjectsReturned
from django.db import transaction

# Local Modules
from companies import models as companies_models
from headquarters import models as headquarters_models
from core.models import Type, Amenity
from ponteglam.settings import BASE_DIR
from services import models
from users import models as users_models
from addons import models as addons_models

f = open('services/scripts/default_settings.json')
default_settings = json.load(f)

CATEGORIES_SERVICES = default_settings.get('categories_services', None)
SERVICES = default_settings.get('services', None)
CATEGORIES_SERVICES_IMAGES = os.path.join(
    BASE_DIR, 'static/default_settings/categories_services_images/'
)
SERVICES_IMAGES = os.path.join(
    BASE_DIR, 'static/default_settings/services_images/'
)


def create_categories_services():
    print('################# CREATING CATEGORIES SERVICES ################')
    with transaction.atomic():
        try:
            for service_category_data in CATEGORIES_SERVICES:
                description = service_category_data.get('description', None)
                color = service_category_data.get('color', None)
                picture_filename = service_category_data.get('picture', None)
                state = service_category_data.get('state', None)

                if not description:
                    raise ValueError(
                        'Field "description" in categories services is '
                        'mandatory'
                    )

                if not color:
                    raise ValueError(
                        'Field "color" in categories services is mandatory'
                    )

                if not picture_filename:
                    raise ValueError(
                        'Field "picture" in categories services is mandatory'
                    )

                if not state:
                    raise ValueError(
                        'Field "state" in categories services is mandatory'
                    )

                state = Type.objects.get_type(
                    code=state, category_type_code='status_service_category'
                )

                # Crear o actualizar el objeto ServiceCategory
                service_category, created = \
                    models.ServiceCategory.objects.get_or_create(
                        defaults={
                            'created_by_user_id': 1,
                            'description': description,
                            'color': color,
                            'state': state,
                            'created_by_user_id': 1
                        },
                        description=description
                    )

                # Construir la ruta completa de la imagen
                picture_path = os.path.join(
                    CATEGORIES_SERVICES_IMAGES, picture_filename
                )

                # Leer la imagen desde la ruta local
                with open(picture_path, 'rb') as picture_data:
                    service_category.picture.delete(save=True)

                    # Asignar la imagen a ServiceCategory
                    service_category.picture.save(
                        picture_filename, picture_data, save=True
                    )

                if created:
                    print(f'Category service {service_category} created.')
                else:
                    print(f'Category service {service_category} updated.')

        except ValueError as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)

        except MultipleObjectsReturned as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)

        except Exception as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)


def create_services():
    print('################# CREATING SERVICES ################')
    with transaction.atomic():
        try:
            for service_data in SERVICES:
                company = service_data.get('company', None)
                headquarters = service_data.get('headquarters', None)
                name = service_data.get('name', None)
                description = service_data.get('description', None)
                confirmation_in = service_data.get('confirmation_in', None)
                remember_in = service_data.get('remember_in', None)
                only_home_service = service_data.get('only_home_service', None)
                price = service_data.get('price', None)
                state = service_data.get('state', None)
                gender = service_data.get('gender', None)
                service_category = service_data.get('service_category', None)
                amenities = service_data.get('amenities', None)
                pictures = service_data.get('pictures', None)
                addons = service_data.get('addons', [])

                company = companies_models.Company.objects.filter(
                    name=company
                ).last()

                state = Type.objects.get_type(
                    code=state, category_type_code='status_service'
                )
                gender = Type.objects.get_type(
                    code=gender, category_type_code='gender_service'
                )
                service_category = models.ServiceCategory.objects.filter(
                    description=service_category
                ).last()

                user = users_models.User.objects.filter(
                    pk=company.created_by_user_id
                ).last()

                # Crear o actualizar el objeto Service
                service, created = models.Service.objects.update_or_create(
                    defaults={
                        'name': name,
                        'description': description,
                        'confirmation_in': confirmation_in,
                        'remember_in': remember_in,
                        'only_home_service': strtobool(only_home_service),
                        'price': price,
                        'state': state,
                        'gender': gender,
                        'service_category': service_category,
                        'created_by_user_id': user.pk
                    },
                    **{'name': name, 'service_category': service_category}
                )

                type_service_file = Type.objects.get_type(
                    code='service_image', category_type_code='type_file'
                )
                for picture_filename in pictures:
                    picture_path = os.path.join(
                        SERVICES_IMAGES, picture_filename
                    )

                    with open(picture_path, 'rb') as picture_data:
                        service_files = models.ServiceFile.objects.filter(
                            service=service
                        )

                        for service_file in service_files:
                            service_file.delete()

                        service_file = models.ServiceFile.objects.create(
                            service=service,
                            type=type_service_file,
                            created_by_user_id=user.pk

                        )

                        service_file.file.save(
                            picture_filename, picture_data, save=True
                        )

                        service_file.save()

                for amenity in amenities:
                    amenity_obj = Amenity.objects.get(code=amenity)
                    service_amenities = models.ServiceAmenity.objects.filter(
                        service=service, amenity=amenity_obj
                    )

                    for service_amenity in service_amenities:
                        service_amenity.delete()

                    service_amenity = models.ServiceAmenity.objects.create(
                        service=service, amenity=amenity_obj,
                        created_by_user_id=user.pk
                    )

                    service_amenity.save()

                for headquarter in headquarters:
                    headquarter_obj = \
                        headquarters_models.Headquarter.objects.filter(
                            name=headquarter, company=company
                        ).last()

                    headquarter_service = \
                        headquarters_models.HeadquarterService.objects.filter(
                            headquarter=headquarter_obj, service=service

                        )

                    if not headquarter_service:
                        headquarter_service = \
                            headquarters_models.HeadquarterService.objects.create(
                                headquarter=headquarter_obj,
                                service=service,
                                created_by_user_id=user.pk
                            )

                        headquarter_service.save()

                    # Phase 2: Worker Dummy Mapping
                    from workers.models import Worker
                    worker, _ = Worker.objects.get_or_create(
                        user=user,
                        defaults={
                            'created_by_user_id': user.pk
                        }
                    )
                    
                    headquarter_worker = \
                        headquarters_models.HeadquarterWorker.objects.filter(
                            headquarter=headquarter_obj, worker=worker
                        ).last()

                    if not headquarter_worker:
                        headquarters_models.HeadquarterWorker.objects.create(
                            headquarter=headquarter_obj,
                            worker=worker,
                            created_by_user_id=user.pk
                        )
                        
                    worker_service = \
                        models.WorkerService.objects.filter(
                            worker=worker, service=service
                        ).last()

                    if not worker_service:
                        models.WorkerService.objects.create(
                            worker=worker,
                            service=service,
                            created_by_user_id=user.pk
                        )

                if created:
                    print(f'Service {service} created.')
                else:
                    print(f'Service {service} updated.')

                service.save()

                for addon_data in addons:
                    addon, _ = addons_models.ServiceAddon.objects.get_or_create(
                        name=addon_data['name'],
                        defaults={
                            'description': addon_data.get('description', ''),
                            'price': addon_data.get('price', 0),
                            'duration_minutes': addon_data.get('duration_minutes', 10),
                            'created_by_user': user,
                        }
                    )
                    addons_models.ServiceAddonLink.objects.get_or_create(
                        addon=addon,
                        service=service,
                        defaults={'created_by_user_id': user.pk}
                    )
                    print(f'  Addon "{addon.name}" linked to service "{service.name}".')

        except ValueError as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)

        except MultipleObjectsReturned as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)

        except Exception as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)


def run():
    create_categories_services()
    create_services()
