from factory import Faker
from factory.django import DjangoModelFactory

from api_logs.models import APIRequestLog


class APIRequestLogFactory(DjangoModelFactory):
    method = Faker(
        "random_element",
        elements=("GET", "POST", "PUT", "DELETE", "PATCH"),
    )
    url = Faker("url")
    request_headers = Faker(
        "pydict",
        nb_elements=3,
        variable_nb_elements=True,
        value_types=[str],
    )
    request_params = Faker(
        "pydict",
        nb_elements=2,
        variable_nb_elements=True,
        value_types=[str],
    )
    request_body = Faker(
        "pydict",
        nb_elements=5,
        variable_nb_elements=True,
        value_types=[str, int],
    )

    response_status_code = Faker("random_int", min=200, max=599)
    response_headers = Faker(
        "pydict",
        nb_elements=3,
        variable_nb_elements=True,
        value_types=[str],
    )
    response_body = Faker(
        "pydict",
        nb_elements=5,
        variable_nb_elements=True,
        value_types=[str, int],
    )

    status = Faker(
        "random_element",
        elements=(
            APIRequestLog.STATUS_PENDING,
            APIRequestLog.STATUS_SUCCESS,
            APIRequestLog.STATUS_ERROR,
            APIRequestLog.STATUS_TIMEOUT,
        ),
    )
    duration_ms = Faker("random_int", min=10, max=5000)
    error_message = Faker("text", max_nb_chars=200)

    class Meta:
        model = APIRequestLog
