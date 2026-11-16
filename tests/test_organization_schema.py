import pytest
from pydantic import ValidationError

from engipilot_ai.modules.organizations.api.v1.schemas.organization import (
    OrganizationCreate,
)


def test_organization_code_is_normalized() -> None:
    payload = OrganizationCreate(
        name=" EngiPilot Technologies ",
        code=" ENGIPILOT ",
    )

    assert payload.name == "EngiPilot Technologies"
    assert payload.code == "engipilot"


def test_organization_name_must_have_two_characters() -> None:
    with pytest.raises(ValidationError):
        OrganizationCreate(
            name="X",
            code="engipilot",
        )
