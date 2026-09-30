from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    cccd_numbers = ("001099012345", "079204012345")

    for cccd in cccd_numbers:
        out = scrub_text(f"CCCD của tôi: {cccd}")
        assert cccd not in out
        assert "REDACTED_CCCD" in out


def test_scrub_credit_card_formats() -> None:
    cards = (
        "4111 1111 1111 1111",
        "4111-1111-1111-1111",
        "4111111111111111",
    )

    for card in cards:
        out = scrub_text(f"Card: {card}")
        assert card not in out
        assert "REDACTED_CREDIT_CARD" in out


def test_scrub_mixed_pii_in_one_message() -> None:
    out = scrub_text("a@b.vn 0901234567 001099012345 4111 1111 1111 1111")

    assert "a@b.vn" not in out
    assert "0901234567" not in out
    assert "001099012345" not in out
    assert "4111" not in out
    for label in (
        "REDACTED_EMAIL",
        "REDACTED_PHONE_VN",
        "REDACTED_CCCD",
        "REDACTED_CREDIT_CARD",
    ):
        assert label in out


def test_scrub_keeps_normal_text() -> None:
    text = "Explain why metrics traces and logs work together"
    assert scrub_text(text) == text