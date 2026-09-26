# third-party Libraries
from rest_framework import serializers

# Local Modules
from reports import models


class UserReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.UserReport
        fields = '__all__'


class PostReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.PostReport
        fields = '__all__'


class CommentReportSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.CommentReport
        fields = '__all__'
