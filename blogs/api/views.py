# Third-party Libraries
from django.core.cache import cache
from rest_framework import status, viewsets
from rest_framework.authentication import TokenAuthentication
from rest_framework.request import Request
from rest_framework.response import Response

# Local Modules
from blogs import models
from blogs.api import serializers
from core import utils


class CreatePost(viewsets.ModelViewSet):
    serializer_class = serializers.PostSerializer
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


class CreatePostComment(viewsets.ModelViewSet):
    serializer_class = serializers.PostCommentSerializer
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


class CreatePostInteraction(viewsets.ModelViewSet):
    serializer_class = serializers.PostInteractionSerializer
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


class CreateCommentInteraction(viewsets.ModelViewSet):
    serializer_class = serializers.InteractionToPostCommentSerializer
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


class ListPosts(viewsets.ModelViewSet):
    queryset = models.Post.objects.all().order_by('-created_at')
    serializer_class = serializers.PostSerializer
    pagination_class = utils.CustomPagination
    authentication_classes = [TokenAuthentication]
    queryset = models.Post.objects.all().order_by('-created_at')

    def list(self, request: Request, *args, **kwargs):
        from blogs.tasks import add_five

        add_five.delay(10)

        query_page = request.query_params.get('page')
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            # Si hay resultados en la caché, devolverlos
            cache_key = f'posts_list_page_{query_page}'
            cached_data = cache.get(cache_key)

            if cached_data is not None:
                return self.get_paginated_response(cached_data)

            serializer = self.get_serializer(page, many=True)
            # Guardar resultados en la caché
            cache.set(cache_key, serializer.data, timeout=30)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(
            {
                'success': serializer.data
            }
        )


class ListPostComments(viewsets.ModelViewSet):
    serializer_class = serializers.PostCommentSerializer
    authentication_classes = [TokenAuthentication]

    def list(self, request: Request, *args, **kwargs):
        post_id = request.query_params.get('post_id')
        comments = models.PostComment.objects.filter(post_id=post_id)
        serializer = self.serializer_class(comments, many=True)

        return Response(serializer.data)
