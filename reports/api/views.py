# Third-party Libraries
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.request import Request
from rest_framework.response import Response

# Local Modules
from reports.api import serializers


class CreateUserReport(viewsets.ModelViewSet):
    serializer_class = serializers.UserReportSerializer
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        data['created_by_user_id'] = request.user.pk

        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED
        )


class CreatePostReport(viewsets.ModelViewSet):
    serializer_class = serializers.PostReportSerializer
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        data['created_by_user_id'] = request.user.pk

        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED
        )


class CreateCommentReport(viewsets.ModelViewSet):
    serializer_class = serializers.CommentReportSerializer
    authentication_classes = [TokenAuthentication]

    def create(self, request: Request, *args, **kwargs):
        data = request.data.copy()
        data['created_by_user_id'] = request.user.pk

        serializer = self.serializer_class(data=data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            data=serializer.data,
            status=status.HTTP_201_CREATED
        )
