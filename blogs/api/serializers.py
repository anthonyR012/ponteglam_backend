# third-party Libraries
from rest_framework import serializers

# Local Modules
from blogs import models


class PostSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Post
        fields = '__all__'
        extra_kwargs = {
            'file': {'required': False}
        }


class PostCommentSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.PostComment
        fields = '__all__'
        extra_kwargs = {
            'file': {'required': False}
        }


class PostInteractionSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.PostInteraction
        fields = '__all__'


class InteractionToPostCommentSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.InteractionToPostComment
        fields = '__all__'
