from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated

from addons.models import ServiceAddon, ServiceAddonLink, AppointmentAddon
from addons.api.serializers import ServiceAddonSerializer
from services.models import Service

class ListServiceAddons(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def list(self, request):
        service_id = request.query_params.get('service_id')
        if not service_id:
            all_addons = ServiceAddon.objects.filter(created_by_user=request.user)
            return Response({
                "success": {
                    "linked": [],
                    "available": ServiceAddonSerializer(all_addons, many=True).data
                }
            }, status=status.HTTP_200_OK)
        
        linked_addons = ServiceAddon.objects.filter(
            addon_services__service_id=service_id
        )
        available_addons = ServiceAddon.objects.filter(
            created_by_user=request.user
        ).exclude(
            addon_services__service_id=service_id
        )

        return Response({
            "success": {
                "linked": ServiceAddonSerializer(linked_addons, many=True).data,
                "available": ServiceAddonSerializer(available_addons, many=True).data
            }
        }, status=status.HTTP_200_OK)


class CreateServiceAddon(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request):
        serializer = ServiceAddonSerializer(data=request.data)
        if serializer.is_valid():
            addon = serializer.save(created_by_user=request.user)
            return Response(
                {"success": ServiceAddonSerializer(addon).data},
                status=status.HTTP_201_CREATED
            )
        return Response(
            {"error": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class UpdateServiceAddon(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def partial_update(self, request, pk=None):
        try:
            addon = ServiceAddon.objects.get(pk=pk, created_by_user=request.user)
        except ServiceAddon.DoesNotExist:
            return Response(
                {"error": "Adicional no encontrado o sin permisos."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = ServiceAddonSerializer(addon, data=request.data, partial=True)
        if serializer.is_valid():
            updated_addon = serializer.save()
            return Response(
                {"success": ServiceAddonSerializer(updated_addon).data},
                status=status.HTTP_200_OK
            )
        return Response(
            {"error": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )


class DeleteServiceAddon(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def destroy(self, request, pk=None):
        try:
            addon = ServiceAddon.objects.get(pk=pk, created_by_user=request.user)
        except ServiceAddon.DoesNotExist:
            return Response(
                {"error": "Adicional no encontrado o sin permisos."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        active_appointments = AppointmentAddon.objects.filter(
            addon=addon,
            appointment__status__in=['pending', 'active']
        ).exists()

        if active_appointments:
            return Response(
                {"error": "No puedes eliminar un adicional con citas activas."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        addon.delete()
        return Response(
            {"success": "Adicional eliminado correctamente."},
            status=status.HTTP_200_OK
        )


class LinkAddonToService(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request):
        addon_id = request.data.get('addon_id')
        service_id = request.data.get('service_id')

        if not addon_id or not service_id:
            return Response(
                {"error": "Se requieren addon_id y service_id."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            addon = ServiceAddon.objects.get(
                id=addon_id, created_by_user=request.user
            )
            service = Service.objects.get(
                id=service_id, created_by_user_id=request.user.pk
            )
        except (ServiceAddon.DoesNotExist, Service.DoesNotExist):
            return Response(
                {"error": "Adicional o servicio no encontrado o sin permisos."},
                status=status.HTTP_404_NOT_FOUND
            )

        if ServiceAddonLink.objects.filter(addon=addon, service=service).exists():
            return Response(
                {"success": "Adicional vinculado correctamente."},
                status=status.HTTP_200_OK
            )

        if ServiceAddonLink.objects.filter(service=service).count() >= 5:
            return Response(
                {"error": "No puedes vincular más de 5 adicionales a un servicio."},
                status=status.HTTP_400_BAD_REQUEST
            )

        ServiceAddonLink.objects.create(
            addon=addon,
            service=service,
            created_by_user_id=request.user.pk
        )
        return Response(
            {"success": "Adicional vinculado correctamente."},
            status=status.HTTP_200_OK
        )


class UnlinkAddonFromService(viewsets.ViewSet):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def create(self, request):
        addon_id = request.data.get('addon_id')
        service_id = request.data.get('service_id')

        if not addon_id or not service_id:
            return Response(
                {"error": "Se requieren addon_id y service_id."},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            addon = ServiceAddon.objects.get(
                id=addon_id, created_by_user=request.user
            )
            service = Service.objects.get(
                id=service_id, created_by_user_id=request.user.pk
            )
        except (ServiceAddon.DoesNotExist, Service.DoesNotExist):
            return Response(
                {"error": "Adicional o servicio no encontrado o sin permisos."},
                status=status.HTTP_404_NOT_FOUND
            )

        ServiceAddonLink.objects.filter(addon=addon, service=service).delete()
        
        return Response(
            {"success": "Adicional desvinculado correctamente."},
            status=status.HTTP_200_OK
        )
