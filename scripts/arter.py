from instagram.models import Post  # noqa: INP001


def run():
    post = Post.objects.get(id="3689148398131099643")
    post.generate_embedding_task()
