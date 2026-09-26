# Third-party Libraries
from django.db import models

# Local Modules
from core.models import MixinAudit


# Create your models here.
class Report(MixinAudit):

    description = models.TextField()
    additional_information = models.TextField(null=True, blank=True)
    actions_taken = models.TextField(null=True, blank=True)
    reviewed_by_user_id = models.IntegerField(null=True, blank=True)
    type = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='type_%(class)s'
    )
    state = models.ForeignKey(
        'core.Type', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='state_%(class)s'
    )

    class Meta:
        abstract = True


class UserReport(Report):

    user = models.ForeignKey(
        'users.User', on_delete=models.CASCADE,
        related_name='user_report'
    )


class PostReport(Report):

    post = models.ForeignKey(
        'blogs.Post', on_delete=models.CASCADE, related_name='post_report'
    )


class CommentReport(Report):

    comment = models.ForeignKey(
        'blogs.PostComment', on_delete=models.CASCADE,
        related_name='comment_report'
    )


class CompanyReport(Report):

    company = models.ForeignKey(
        'companies.Company', on_delete=models.CASCADE,
        related_name='company_report'
    )


class AdReport(Report):
    pass
