import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://127.0.0.1:8080"


def test_homepage_loads(page: Page):
    """Check that the QuickCheck dashboard opens."""

    response = page.goto(BASE_URL)

    assert response is not None
    assert response.status == 200

    expect(page).to_have_title("QuickCheck Modes")
    expect(
        page.get_by_role("heading", name="QuickCheck Modes")
    ).to_be_visible()

    expect(page.locator("#u")).to_be_visible()
    expect(page.get_by_role("button", name="Next")).to_be_visible()


def test_practice_site_button(page: Page):
    """Check that Use the practice site fills the URL field."""

    page.goto(BASE_URL)

    page.locator("#demo").click()

    expect(page.locator("#u")).to_have_value(
        "http://127.0.0.1:8080/demo/"
    )


def test_navigation_to_mode_selection(page: Page):
    """Check that a user can move from Link to What to test."""

    page.goto(BASE_URL)

    page.locator("#demo").click()
    page.get_by_role("button", name="Next").click()

    expect(
        page.get_by_role("heading", name="What should we test?")
    ).to_be_visible()

    expect(page.locator("#s2")).to_be_visible()

    # Check all three testing modes
    expect(page.locator('input[value="functional"]')).to_be_visible()
    expect(page.locator('input[value="ui"]')).to_be_visible()
    expect(page.locator('input[value="both"]')).to_be_visible()

    expect(
        page.get_by_role("button", name="Start testing")
    ).to_be_visible()


def test_back_navigation(page: Page):
    """Check that Back returns to the URL entry screen."""

    page.goto(BASE_URL)

    page.locator("#demo").click()
    page.get_by_role("button", name="Next").click()

    page.get_by_role("button", name="Back").click()

    expect(
        page.get_by_role("heading", name="Which website should we test?")
    ).to_be_visible()

    expect(page.locator("#u")).to_be_visible()


def test_api_rejects_empty_url(page: Page):
    """Check backend validation for an empty URL."""

    response = page.request.post(
        f"{BASE_URL}/api/test",
        data={"url": "", "mode": "both"}
    )

    assert response.status == 400
    assert response.json()["error"] == "Enter a link first."


def test_api_rejects_invalid_mode(page: Page):
    """Check backend validation for an invalid testing mode."""

    response = page.request.post(
        f"{BASE_URL}/api/test",
        data={
            "url": "https://example.com",
            "mode": "invalid"
        }
    )

    assert response.status == 400
    assert response.json()["error"] == "Choose Functional, UI or Both."