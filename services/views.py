# Python Standard Library
import json

# Third-party Libraries
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import IntegrityError, transaction
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

# Local Modules
from services import models
from services.permissions import ServicePermissions
from utils.functions import audit_log_create, audit_log_update, validate_json_with_pandas


class ServiceViewSet(ModelViewSet):

    permission_classes = [ServicePermissions]
    queryset = models.Service.objects.all().select_related(
        'headquarter', 'headquarter__company'
    ).order_by('code')
    serializer_class = None

    def create(self, request):
        try:
            payload = validate_json_with_pandas(request.data)

            if payload == 0:
                raise APIException('Json format is not correct.')

            with transaction.atomic():
                # create or update service
                service = models.Service.objects.update_or_create(
                    code=payload['code'],
                    defaults={
                        **payload,
                        'modified_at': timezone.now(),
                        'created_by_user_id': request.user.pk
                    }
                )

                # write log
                audit_log_create(request, models.Service, service, payload)

                # return response
                return Response({
                    'message': 'Service created successfully.'
                }, status=status.HTTP_200_OK)

        except APIException as e:
            raise APIException(f'Error: {e}')

        except IntegrityError as e:
            raise APIException(f'Error: {e}')

        except ValidationError as e:
            raise APIException(f'Error: {e}')

        except ValueError as e:
            raise APIException(f'Error: {e}')

        except json.JSONDecodeError as e:
            raise APIException(f'Error when decoding JSON: {e}')

        except Exception as e:
            raise APIException(f'Error: {e}')

    def update(self, request, pk=None):
        try:
            payload = validate_json_with_pandas(request.data)

            if payload == 0:
                raise APIException('Json format is not correct.')

            with transaction.atomic():
                # get service
                service = models.Service.objects.get(pk=pk)

                # update service
                service.modified_at = timezone.now()
                service.created_by_user_id = request.user.pk
                service.save(update_fields=['code', 'name', 'price', 'duration', 'is_active'])

                # write log
                audit_log_update(request, models.Service, service, payload)

                # return response
                return Response({
                    'message': 'Service updated successfully.'
                }, status=status.HTTP_200_OK)

        except ObjectDoesNotExist as e:
            raise APIException(f'Error: {e}')

        except APIException as e:
            raise APIException(f'Error: {e}')

        except IntegrityError as e:
            raise APIException(f'Error: {e}')

        except ValidationError as e:
            raise APIException(f'Error: {e}')

        except ValueError as e:
            raise APIException(f'Error: {e}')

        except json.JSONDecodeError as e:
            raise APIException(f'Error when decoding JSON: {e}')

        except Exception as e:
            raise APIException(f'Error: {e}')
