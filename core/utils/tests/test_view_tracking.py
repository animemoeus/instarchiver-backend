from django.core.cache import cache
from django.test import RequestFactory
from django.test import TestCase

from core.utils.view_tracking import get_client_ip
from core.utils.view_tracking import should_count_view


class TestGetClientIp(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_uses_first_entry_of_x_forwarded_for(self):
        request = self.factory.get(
            "/",
            HTTP_X_FORWARDED_FOR="1.2.3.4, 10.0.0.1",
            REMOTE_ADDR="10.0.0.1",
        )
        assert get_client_ip(request) == "1.2.3.4"

    def test_falls_back_to_remote_addr(self):
        request = self.factory.get("/", REMOTE_ADDR="9.9.9.9")
        assert get_client_ip(request) == "9.9.9.9"

    def test_unknown_when_neither_present(self):
        request = self.factory.get("/")
        del request.META["REMOTE_ADDR"]
        assert get_client_ip(request) == "unknown"


class TestShouldCountView(TestCase):
    def setUp(self):
        cache.clear()

    def test_first_view_is_counted(self):
        assert should_count_view("post", "123", "1.1.1.1") is True

    def test_repeat_view_same_ip_is_not_counted(self):
        should_count_view("post", "123", "1.1.1.1")
        assert should_count_view("post", "123", "1.1.1.1") is False

    def test_different_ip_is_counted_again(self):
        should_count_view("post", "123", "1.1.1.1")
        assert should_count_view("post", "123", "2.2.2.2") is True

    def test_different_object_is_counted_independently(self):
        should_count_view("post", "123", "1.1.1.1")
        assert should_count_view("post", "456", "1.1.1.1") is True

    def test_different_prefix_is_counted_independently(self):
        should_count_view("post", "123", "1.1.1.1")
        assert should_count_view("story", "123", "1.1.1.1") is True
