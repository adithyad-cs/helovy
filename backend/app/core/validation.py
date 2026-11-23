"""Field rules shared by the business and customer schemas (docs/09 §4.2, §4.4).

Every function returns the normalised value or raises a Pydantic error whose type is the
documented field error code (docs/07 §1.5).
"""

from __future__ import annotations

import re

from app.core.schemas import clean_text, field_error

# docs/09 §4.4: GST state codes offered for addresses (25, 28, 97 and 99 are not offered).
STATE_NAMES: dict[str, str] = {
    "01": "Jammu and Kashmir",
    "02": "Himachal Pradesh",
    "03": "Punjab",
    "04": "Chandigarh",
    "05": "Uttarakhand",
    "06": "Haryana",
    "07": "Delhi",
    "08": "Rajasthan",
    "09": "Uttar Pradesh",
    "10": "Bihar",
    "11": "Sikkim",
    "12": "Arunachal Pradesh",
    "13": "Nagaland",
    "14": "Manipur",
    "15": "Mizoram",
    "16": "Tripura",
    "17": "Meghalaya",
    "18": "Assam",
    "19": "West Bengal",
    "20": "Jharkhand",
    "21": "Odisha",
    "22": "Chhattisgarh",
    "23": "Madhya Pradesh",
    "24": "Gujarat",
    "26": "Dadra and Nagar Haveli and Daman and Diu",
    "27": "Maharashtra",
    "29": "Karnataka",
    "30": "Goa",
    "31": "Lakshadweep",
    "32": "Kerala",
    "33": "Tamil Nadu",
    "34": "Puducherry",
    "35": "Andaman and Nicobar Islands",
    "36": "Telangana",
    "37": "Andhra Pradesh",
    "38": "Ladakh",
}

POSTAL_CODE = re.compile(r"^[1-9][0-9]{5}$")
PHONE = re.compile(r"^[0-9+() -]{6,20}$")
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
GSTIN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")


def state_name(code: str | None) -> str | None:
    return STATE_NAMES.get(code) if code else None


def text_value(value: str | None, *, max_length: int, required: bool) -> str | None:
    """A single-line text field; ``None`` is ``not_null`` for required fields."""
    if value is None:
        if required:
            raise field_error("not_null", "This field can't be empty.")
        return None
    return clean_text(value, max_length=max_length, required=required)


def state_code_value(value: str | None, *, required: bool) -> str | None:
    code = text_value(value, max_length=2, required=required)
    if code is not None and code not in STATE_NAMES:
        raise field_error("invalid_choice", "Choose a state from the list.")
    return code


def postal_code_value(value: str | None, *, required: bool) -> str | None:
    code = text_value(value, max_length=6, required=required)
    if code is not None and not POSTAL_CODE.match(code):
        raise field_error("invalid_format", "Enter a 6-digit PIN code that does not start with 0.")
    return code


def phone_value(value: str | None) -> str | None:
    phone = text_value(value, max_length=20, required=False)
    if phone is not None and not PHONE.match(phone):
        raise field_error(
            "invalid_format", "Use 6-20 characters: digits, spaces, +, - and brackets."
        )
    return phone


def email_value(value: str | None) -> str | None:
    email = text_value(value, max_length=254, required=False)
    if email is not None and not EMAIL.match(email):
        raise field_error("invalid_format", "Enter an email address such as name@example.com.")
    return email


def gstin_value(value: str | None) -> str | None:
    """Upper-cased for entry convenience; the checksum is not validated (P1-05)."""
    gstin = text_value(value, max_length=15, required=False)
    if gstin is None:
        return None
    gstin = gstin.upper()
    if not GSTIN.match(gstin):
        raise field_error(
            "invalid_format", "Enter a 15-character GSTIN, for example 29ABCDE1234F1Z5."
        )
    return gstin


def country_code_value(value: str | None) -> str:
    if value is None:
        raise field_error("not_null", "This field can't be empty.")
    if value != "IN":
        raise field_error("invalid_choice", "Only India (IN) is supported.")
    return value
