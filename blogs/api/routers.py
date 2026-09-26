# Third-party Libraries
from rest_framework import routers

# Local Modules
from blogs.api import views

router = routers.SimpleRouter()

router.register(r'create-post', views.CreatePost, basename='create-post')
router.register(r'create-post-comment', views.CreatePostComment,
                basename='create-post-comment')
router.register(r'create-post-interaction', views.CreatePostInteraction,
                basename='create-post-interaction')
router.register(r'create-comment-interaction', views.CreateCommentInteraction,
                basename='create-comment-interaction')
router.register(r'list-posts', views.ListPosts, basename='list-posts')
router.register(r'list-posts-comments', views.ListPostComments,
                basename='list-posts-comments')
