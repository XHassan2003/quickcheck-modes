from playwright.sync_api import Page, expect


BASE_URL = "http://127.0.0.1:8080"


def test_homepage_loads(page: Page):
    response = page.goto(BASE_URL)

    assert response is not None
    assert response.status == 200

    expect(page.locator("body")).not_to_be_empty()


def test_practice_site_loads(page: Page):
    response = page.goto(f"{BASE_URL}/demo/")

    assert response is not None
    assert response.status == 200

    expect(page.locator("body")).not_to_be_empty()


def test_api_rejects_empty_url(page: Page):
    response = page.request.post(
        f"{BASE_URL}/api/test",
        data={"url": "", "mode": "both"}
    )

    assert response.status == 400

    data = response.json()
    assert data["error"] == "Enter a link first."


def test_api_rejects_invalid_mode(page: Page):
    response = page.request.post(
        f"{BASE_URL}/api/test",
        data={
            "url": "http://example.com",
            "mode": "invalid"
        }
    )

    assert response.status == 400


def test_history_api(page: Page):
    response = page.request.get(f"{BASE_URL}/api/tests")

    assert response.status == 200
    assert isinstance(response.json(), list)    