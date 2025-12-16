from instagram.models import Post  # noqa: INP001


def run():
    post = Post.objects.get(id="3775940607441711666")
    post.handle_post_normal()
    post.handle_post_carousel()
    post.handle_post_video()
