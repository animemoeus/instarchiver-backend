from rest_framework.pagination import CursorPagination


class InstagramUserCursorPagination(CursorPagination):
    """
    Cursor pagination for Instagram User list.
    Orders by created_at (descending) with username as tie-breaker for stability.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"  # Most recent users first
    cursor_query_param = "cursor"


class InstagramUserHistoryCursorPagination(CursorPagination):
    """
    Cursor pagination for Instagram User history records.
    Orders by history_date (descending) to show most recent changes first.
    """

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-history_date"  # Most recent history records first
    cursor_query_param = "cursor"
