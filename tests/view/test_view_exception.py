from bs4 import BeautifulSoup
from starlette.status import (
    HTTP_400_BAD_REQUEST,
    HTTP_403_FORBIDDEN,
    HTTP_404_NOT_FOUND,
    HTTP_405_METHOD_NOT_ALLOWED,
    HTTP_422_UNPROCESSABLE_ENTITY,
    HTTP_500_INTERNAL_SERVER_ERROR,
)

from app.utils.enums import RequestMethod
from tests.utils import make_http_request


async def test_view_not_found_error():
    """
    Tests the behavior of the view for handling a not found error.
    """
    res = await make_http_request(
        "/not-found", follow_redirects=True, method=RequestMethod.GET
    )

    assert res.status_code == HTTP_404_NOT_FOUND

    soup = BeautifulSoup(res.text, features="html.parser")

    assert soup.find("a", {"href": "/"}) is not None


async def test_view_internal_server_error():
    """
    Tests the behavior of the view for handling an internal server error.
    """

    status_code = HTTP_500_INTERNAL_SERVER_ERROR
    res = await make_http_request(
        f"/errors/raise/{status_code}", method=RequestMethod.GET
    )

    assert res.status_code == status_code

    soup = BeautifulSoup(res.text, features="html.parser")

    assert soup.find("h1").text == "✖⸑✖"


async def test_view_request_validation_error():
    """
    Tests the behavior of the view for handling a request validation error.
    """

    status_code = HTTP_422_UNPROCESSABLE_ENTITY
    res = await make_http_request(
        f"/errors/raise/{status_code}", method=RequestMethod.GET
    )

    assert res.status_code == status_code

    soup = BeautifulSoup(res.text, features="html.parser")

    assert soup.find("p") is not None
    assert soup.find("a", {"href": "/"}) is not None


async def test_view_forbidden_error():
    """
    Tests the behavior of the view for handling a forbidden error.
    """
    res = await make_http_request(
        f"/errors/raise/{HTTP_403_FORBIDDEN}", method=RequestMethod.GET
    )

    assert res.status_code == HTTP_404_NOT_FOUND
    soup = BeautifulSoup(res.text, features="html.parser")

    assert soup.find("a", {"href": "/"}) is not None


async def test_view_method_not_allowed():
    """
    Tests the behavior of the view for handling a method not allowed error.
    """
    status_code = HTTP_405_METHOD_NOT_ALLOWED
    res = await make_http_request(
        f"/errors/raise/{status_code}", method=RequestMethod.GET
    )

    assert res.status_code == status_code

    res_redirect = await make_http_request(
        f"/errors/raise/{status_code}", method=RequestMethod.GET, follow_redirects=True
    )

    soup = BeautifulSoup(res_redirect.text, features="html.parser")

    assert soup.find("a", {"href": "/"}) is not None


async def test_view_bad_request():
    """
    Tests the behavior of the view for handling a bad request error.
    """

    status_code = HTTP_400_BAD_REQUEST
    res = await make_http_request(
        f"/errors/raise/{status_code}", method=RequestMethod.GET
    )

    assert res.status_code == status_code

    soup = BeautifulSoup(res.text, features="html.parser")

    assert soup.find("a", {"href": "/"}) is not None
