"""Request schemas for E-10 and E-12 (docs/07 §4; validation in docs/09 §4).

Only ``display_name`` is required. Patch: any subset; ``display_name: null`` is
``not_null``; ``null`` clears any other field (docs/07 §1.4).
"""

from __future__ import annotations

from typing import Any

from pydantic import ValidationInfo, field_validator

from app.core import validation as rules
from app.core.schemas import StrictModel

TEXT_LIMITS = {
    "display_name": (200, True),
    "contact_name": (120, False),
    "address_line1": (200, False),
    "address_line2": (200, False),
    "city": (100, False),
}
FIELDS = (
    "display_name",
    "contact_name",
    "email",
    "phone",
    "address_line1",
    "address_line2",
    "city",
    "state_code",
    "postal_code",
    "country_code",
    "gstin",
)


class _CustomerRules(StrictModel):
    @field_validator(*TEXT_LIMITS, check_fields=False)
    @classmethod
    def _text(cls, value: str | None, info: ValidationInfo) -> str | None:
        max_length, required = TEXT_LIMITS[str(info.field_name)]
        return rules.text_value(value, max_length=max_length, required=required)

    @field_validator("state_code", check_fields=False)
    @classmethod
    def _state(cls, value: str | None) -> str | None:
        return rules.state_code_value(value, required=False)

    @field_validator("postal_code", check_fields=False)
    @classmethod
    def _postal(cls, value: str | None) -> str | None:
        return rules.postal_code_value(value, required=False)

    @field_validator("country_code", check_fields=False)
    @classmethod
    def _country(cls, value: str | None) -> str:
        return rules.country_code_value(value)

    @field_validator("phone", check_fields=False)
    @classmethod
    def _phone(cls, value: str | None) -> str | None:
        return rules.phone_value(value)

    @field_validator("email", check_fields=False)
    @classmethod
    def _email(cls, value: str | None) -> str | None:
        return rules.email_value(value)

    @field_validator("gstin", check_fields=False)
    @classmethod
    def _gstin(cls, value: str | None) -> str | None:
        return rules.gstin_value(value)

    def provided(self) -> dict[str, Any]:
        return {name: getattr(self, name) for name in self.model_fields_set}


class CustomerCreate(_CustomerRules):
    display_name: str | None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state_code: str | None = None
    postal_code: str | None = None
    country_code: str | None = "IN"
    gstin: str | None = None


class CustomerPatch(_CustomerRules):
    display_name: str | None = None
    contact_name: str | None = None
    email: str | None = None
    phone: str | None = None
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state_code: str | None = None
    postal_code: str | None = None
    country_code: str | None = None
    gstin: str | None = None
