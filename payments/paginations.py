from rest_framework.pagination import CursorPagination


class PaymentCursorPagination(CursorPagination):
    """
    Cursor pagination for Payment list.
    Orders by created_at (descending) for most recent payments first.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"  # Most recent payments first
    cursor_query_param = "cursor"
