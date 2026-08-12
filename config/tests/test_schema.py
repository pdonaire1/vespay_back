import pytest
from rest_framework.test import APIClient


@pytest.mark.django_db
def test_schema_endpoint_serves_openapi(superuser):
    client = APIClient()
    client.force_authenticate(user=superuser)

    response = client.get("/api/schema/")

    assert response.status_code == 200
    assert response.data["openapi"].startswith("3.")
    assert response.data["info"]["title"] == "VesPay API"


@pytest.mark.django_db
def test_docs_require_authentication():
    client = APIClient()

    response = client.get("/api/docs/")

    assert response.status_code in (401, 403)


@pytest.mark.django_db
def test_docs_available_when_authenticated(superuser):
    client = APIClient()
    client.force_authenticate(user=superuser)

    response = client.get("/api/docs/")

    assert response.status_code == 200
