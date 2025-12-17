from instagram.models import Post  # noqa: INP001


def run():
    post = Post.objects.get(id="2401234233537846611")
    post.generate_thumbnail_insight()
