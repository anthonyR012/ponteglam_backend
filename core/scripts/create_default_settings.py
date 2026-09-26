"""
python manage.py shell < core/scripts/create_default_settings.py
"""

# Python Standard Library
import json

# Third-party Libraries
from cities_light.models import City
from django.apps import apps as django_apps
from django.core.exceptions import MultipleObjectsReturned
from django.core.management import call_command
from django.db import connection, transaction

# Local Modules
from companies.scripts import create_default_settings as cds_companies
from core import models
from services.scripts import create_default_settings as cds_services
from users import models as user_models
from users.scripts import create_default_settings as cds_users

f = open('core/scripts/default_settings.json')
default_settings = json.load(f)

CATEGORIES_TYPES = default_settings.get('categories_types', None)
WEEK_DAYS = default_settings.get('week_days', None)
AMENITIES = default_settings.get('amenities', None)
CANCELLATION_RULES = default_settings.get('cancellation_rules', None)


APPS_TO_CLEAN = ['companies', 'headquarters', 'ratings', 'services', 'core']


def clean_database():
    print('################# CLEANING DATABASE ################')

    app_models = []
    for app_label in APPS_TO_CLEAN:
        for model in django_apps.get_app_config(app_label).get_models():
            app_models.append(model)
            print(f'  Queued for deletion: {model.__name__}')

    tables = ', '.join(f'"{m._meta.db_table}"' for m in app_models)
    with connection.cursor() as cursor:
        cursor.execute(f'TRUNCATE TABLE {tables} RESTART IDENTITY CASCADE')

    print('################# DATABASE CLEANED ################')


def create_categories_types():

    print('################# CREATING TYPES ################')
    with transaction.atomic():

        try:

            created_by_user = user_models.User.objects.filter(
                username='admin'
            ).last()

            if not created_by_user:
                raise ValueError(
                    'Field "created_by_user" in categorys is mandatory'
                )

            for category_types in CATEGORIES_TYPES:

                code = category_types.get('code', None)
                description = category_types.get('description', None)

                types = category_types.get('types', None)

                category, created = models.Category.objects.update_or_create(
                    defaults={
                        'code': code,
                        'description': description,
                        'created_by_user_id': created_by_user.pk
                    },
                    **{
                        'code': code
                    }
                )

                if created:
                    print(f'Category {category} created.')
                else:
                    print(f'Category {category} updated.')

                for type in types:
                    code = type.get('code', None)
                    description = type.get('description', None)

                    type, created = models.Type.objects.update_or_create(
                        defaults={
                            'description': description,
                            'created_by_user_id': created_by_user.pk
                        },
                        **{'category_type': category, 'code': code}
                    )

                    if created:
                        print(f'Type {type} created.')
                    else:
                        print(f'Type {type} updated.')

        except ValueError as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)

        except MultipleObjectsReturned as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)

        except Exception as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)


def create_week_days():

    print('################# CREATING WEEK DAYS ################')
    with transaction.atomic():

        try:

            created_by_user = user_models.User.objects.filter(
                username='admin'
            ).last()

            if not created_by_user:
                raise ValueError(
                    'Field "created_by_user" in categorys is mandatory'
                )

            for week_day_data in WEEK_DAYS:

                code = week_day_data.get('code', None)
                description = week_day_data.get('description', None)

                week_day, created = models.WeekDay.objects.update_or_create(
                    defaults={
                        'code': code,
                        'description': description,
                        'created_by_user_id': created_by_user.pk
                    },
                    **{
                        'code': code
                    }
                )

                if created:
                    print(f'Week day {week_day} created.')
                else:
                    print(f'Week day {week_day} updated.')

        except ValueError as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)

        except MultipleObjectsReturned as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)

        except Exception as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)


def create_geo_references_cities():

    print('################# CREATING GEO REFERENCES CITIES ################')
    with transaction.atomic():

        try:
            created_by_user = user_models.User.objects.filter(
                username='admin'
            ).last()

            if not created_by_user:
                raise ValueError(
                    'Field "created_by_user" in categorys is mandatory'
                )

            cities = City.objects.all()
            if not cities:
                print('############### CREATING CITIES LIGHT ###############')
                call_command('cities_light')
                print('################ CITIES LIGHT CREATED ################')
                cities = City.objects.all()

            for city in cities:

                geo_reference_city, created = \
                    models.GeoReferenceCity.objects.get_or_create(
                        name=f'{city.name}',
                        city=city,
                        created_by_user_id=created_by_user.pk,
                        defaults={
                            'latitude': city.latitude or '0',
                            'longitude': city.longitude or '0'
                        }
                    )

                if created:
                    print(f'Geo reference city {city.name} created')
                else:
                    print(f'Geo reference city {city.name} updated')

        except ValueError as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)

        except MultipleObjectsReturned as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)

        except Exception as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)


def create_amenities():

    print('################# CREATING AMENITIES ################')
    with transaction.atomic():

        try:

            created_by_user = user_models.User.objects.filter(
                username='admin'
            ).last()

            if not created_by_user:
                raise ValueError(
                    'Field "created_by_user" in categorys is mandatory'
                )

            for amenity_data in AMENITIES:

                code = amenity_data.get('code', None)
                description = amenity_data.get('description', None)
                color = amenity_data.get('color', None)
                icon_name = amenity_data.get('icon_name', None)

                amenity, created = models.Amenity.objects.update_or_create(
                    defaults={
                        'code': code,
                        'description': description,
                        'color': color,
                        'icon_name': icon_name,
                        'created_by_user_id': created_by_user.pk
                    },
                    **{
                        'code': code
                    }
                )

                if created:
                    print(f'Amenity {amenity} created.')
                else:
                    print(f'Amenity {amenity} updated.')

        except ValueError as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)

        except MultipleObjectsReturned as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)

        except Exception as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)


def create_cancellation_rules():
    from services.models import CancellationRule
    print('################# CREATING CANCELLATION RULES ################')
    with transaction.atomic():
        try:
            created_by_user = user_models.User.objects.filter(
                username='admin'
            ).last()

            if not created_by_user:
                raise ValueError(
                    'Field "created_by_user" is mandatory'
                )

            if CANCELLATION_RULES:
                for rule_data in CANCELLATION_RULES:
                    rule, created = CancellationRule.objects.update_or_create(
                        min_hours=rule_data['min_hours'],
                        defaults={
                            'penalty_pct': rule_data['penalty_pct'],
                            'fee_level': rule_data['fee_level'],
                            'description': rule_data['description'],
                            'created_by_user_id': created_by_user.pk
                        }
                    )
                    if created:
                        print(f'Rule {rule} created.')
                    else:
                        print(f'Rule {rule} updated.')

        except Exception as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)


def create_legal_contents():
    print('################# CREATING LEGAL CONTENTS ################')
    legal_contents = default_settings.get('legal_contents', None)
    if not legal_contents:
        print('No legal contents found in default_settings.json')
        return

    with transaction.atomic():
        try:
            created_by_user = user_models.User.objects.filter(
                username='admin'
            ).last()

            if not created_by_user:
                raise ValueError(
                    'Field "created_by_user" is mandatory'
                )

            for legal_data in legal_contents:
                title = legal_data.get('title')
                content = legal_data.get('content')
                version = legal_data.get('version')
                type_code = legal_data.get('type')
                state_code = legal_data.get('state')

                type_obj = models.Type.objects.get_type(
                    type_code, 'legal_content_category'
                )
                state_obj = models.Type.objects.get_type(
                    state_code, 'status_legal_content'
                )

                legal_content, created = models.LegalContent.objects.update_or_create(
                    defaults={
                        'title': title,
                        'content': content,
                        'version': version,
                        'state': state_obj,
                        'created_by_user_id': created_by_user.pk
                    },
                    **{'type': type_obj}
                )

                if created:
                    print(f'Legal content {legal_content} created.')
                else:
                    print(f'Legal content {legal_content} updated.')

        except Exception as e:
            print(f'Error: {e}')
            transaction.set_rollback(True)


clean_database()
cds_users.create_user_admin()
create_categories_types()
create_week_days()
create_geo_references_cities()
create_amenities()
create_cancellation_rules()
create_legal_contents()
cds_users.run()
cds_companies.run()
cds_services.run()
