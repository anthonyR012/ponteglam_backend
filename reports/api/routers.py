# Third-party Libraries
from rest_framework import routers

# Local Modules
from reports.api import views


router = routers.SimpleRouter()


router.register(
    r'create-post-report', views.CreatePostReport,
    basename='create-post-report'
)
router.register(
    r'create-comment-report', views.CreateCommentReport,
    basename='create-comment-report'
)
router.register(
    r'create-user-report', views.CreateUserReport,
    basename='create-user-report'
)
