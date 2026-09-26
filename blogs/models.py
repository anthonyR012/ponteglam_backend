# Third-party Libraries
from django.db import models
from django.utils import timezone

# Local Modules
from core.models import MixinAudit


# Create your models here.
class Post(MixinAudit):

    def generate_file_name(instance, filename):
        date = timezone.now()
        return f'post/{date.year}/{date.month}/{date.day}/{filename}'

    content = models.TextField()
    file = models.FileField(
        upload_to=generate_file_name, null=True, blank=True
    )
    type = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='type_post'
    )

    def __str__(self):
        return self.content


class PostComment(MixinAudit):

    def generate_file_name(instance, filename):
        date = timezone.now()
        return f'comments/{date.year}/{date.month}/{date.day}/{filename}'

    content = models.TextField()
    file = models.FileField(
        upload_to=generate_file_name, null=True, blank=True
    )
    type = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='type_post_comment'
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='post_comment'
    )
    head_comment = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self):
        return self.content


class PostInteraction(MixinAudit):

    type = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='type_post_interaction'
    )
    post = models.ForeignKey(
        Post, on_delete=models.CASCADE, related_name='post_interaction'
    )

    def __str__(self):
        return self.post


class InteractionToPostComment(MixinAudit):

    post_comment = models.ForeignKey(
        PostComment, on_delete=models.CASCADE,
        related_name='interaction_to_post_comment'
    )
    type = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='type_interaction_to_post_comment'
    )

    def __str__(self):
        return self.post_comment
