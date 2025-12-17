from instagram.models import Post  # noqa: INP001


def run():
    post = Post.objects.get(id="3543919140694604356")
    post.generate_thumbnail_insight()
