"""
File for the API views of the companies application
"""
# Python Standard Library
from rest_framework import status, viewsets
from rest_framework.authentication import (
    BasicAuthentication, TokenAuthentication
)
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

# Local Modules
from core import models
from core.api import serializers


class ListTypes(viewsets.ViewSet):
    """
    ViewSet to list all the types.
    """
    serializer_class = serializers.TypeSerializer
    authentication_classes = [BasicAuthentication]
    permission_classes = [AllowAny]

    def list(self, request: Request):
        """
        Return a list of all the types.
        """

        types = models.Type.objects.all()
        serializer = self.serializer_class(types, many=True)
        return Response(
            {
                'success': serializer.data
            },
            status=status.HTTP_200_OK
        )


class ListCountries(viewsets.ViewSet):
    """
    ViewSet to list all the countries.
    """
    serializer_class = serializers.CountrySerializer
    authentication_classes = [BasicAuthentication]
    permission_classes = [AllowAny]

    def list(self, request: Request):
        """
        Return a list of all the countries.
        """
        from cities_light.models import Country

        countries = Country.objects.all()
        serializer = self.serializer_class(countries, many=True)
        return Response(
            {
                'success': serializer.data
            },
            status=status.HTTP_200_OK
        )


class ListCities(viewsets.ViewSet):
    """
    ViewSet to list all the cities supported by Ponteglam.
    """
    serializer_class = serializers.GeoReferenceCitySerializer
    authentication_classes = [BasicAuthentication]
    permission_classes = [AllowAny]

    def list(self, request: Request):
        """
        Return the list of GeoReferenceCity records managed by Ponteglam.
        """
        cities = models.GeoReferenceCity.objects.all().order_by('name')
        serializer = self.serializer_class(cities, many=True)
        return Response(
            {
                'success': serializer.data
            },
            status=status.HTTP_200_OK
        )


class CreateMobileAppLogView(viewsets.ViewSet):
    """
    ViewSet to register a mobile app log
    """
    serializer_class = serializers.MobileAppLogSerializer
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()

        for mobile_app_log in data:
            mobile_app_log['created_by_user_id'] = request.user.pk

        serializer = self.serializer_class(data=data, many=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "success": "Log registrado exitosamente"
            },
            status=status.HTTP_201_CREATED
        )


class ListAmenities(viewsets.ViewSet):
    """
    ViewSet to list all the amenities
    """
    serializer_class = serializers.AmenitySerializer
    authentication_classes = [BasicAuthentication]
    permission_classes = [AllowAny]

    def list(self, request: Request):
        """
        Return a list of all the amenities.
        """

        amenities = models.Amenity.objects.all()
        serializer = self.serializer_class(
            amenities, many=True, context={'request': request}
        )
        return Response(
            {
                'success': serializer.data
            },
            status=status.HTTP_200_OK
        )


class ListLegalContent(viewsets.ViewSet):
    """
    ViewSet to list legal content.
    Can be filtered by type code.
    """
    serializer_class = serializers.LegalContentSerializer
    permission_classes = [AllowAny]

    def list(self, request: Request):
        """
        Return a list of legal content, optionally filtered by type.
        """
        type_code = request.query_params.get('type')
        queryset = models.LegalContent.objects.filter(state__code='active')

        if type_code:
            queryset = queryset.filter(type__code=type_code)

        serializer = self.serializer_class(queryset, many=True)
        return Response(
            {
                'success': serializer.data
            },
            status=status.HTTP_200_OK
        )
