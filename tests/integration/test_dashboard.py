import re

from fastapi.testclient import TestClient


def test_dashboard_page_is_served_at_the_root(api_client: TestClient) -> None:
    response = api_client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Astronaut Health Monitor" in response.text


def test_dashboard_contains_every_main_feature(api_client: TestClient) -> None:
    page = api_client.get("/").text
    for element_id in ("banner", "cards", "chart", "regionInfo", "demo", "record", "crew"):
        assert f'id="{element_id}"' in page
    for region in ("head", "chest", "abdomen", "legs"):
        assert f'id="r-{region}"' in page


def test_dashboard_works_offline_without_external_resources(api_client: TestClient) -> None:
    page = api_client.get("/").text
    external_links = re.findall(r'(?:src|href)\s*=\s*["\']https?://', page)
    assert external_links == []
    assert "@import" not in page
    assert "cdn" not in page.lower()


def test_dashboard_only_calls_endpoints_that_exist(api_client: TestClient) -> None:
    page = api_client.get("/").text
    paths = set(api_client.get("/openapi.json").json()["paths"])
    for called in (
        "/health-indicators",
        "/health-status-rules",
        "/astronauts",
        "/measurements",
        "/demo/sample-crew",
        "/auth/login",
        "/auth/logout",
        "/auth/me",
        "/audit-log",
    ):
        assert f"'{called}" in page
        assert called in paths
    assert "/health-summary" in page and "/assessment" in page


def test_dashboard_uses_plain_language_for_beginners(api_client: TestClient) -> None:
    page = api_client.get("/").text
    for element_id in ("welcome", "demoBig", "todo", "actions", "bannerTitle"):
        assert f'id="{element_id}"' in page
    for plain_phrase in ("What to do now", "Why, and what to do", "Get medical help now", "Everything looks good"):
        assert plain_phrase in page
    assert "\\u25B2 Watch" not in page.split("<script>")[0]  # symbols in the page body are real characters


def test_dashboard_has_safety_panel_tour_and_offline_notices(api_client: TestClient) -> None:
    page = api_client.get("/").text
    for element_id in ("safety", "regionData", "notices", "tour", "helpBtn"):
        assert f'id="{element_id}"' in page
    for phrase in (
        "Precautions and safety",
        "Spaceflight considerations",
        "Suggested actions and when to get help",
        "Simulated sample data",
        "You are offline",
        "dosimeters",
    ):
        assert phrase in page
    for region_name in ("Head", "Chest", "Abdomen", "Legs"):
        assert f"{region_name}" in page


def test_body_map_image_is_served_locally_and_used_by_the_page(api_client: TestClient) -> None:
    image = api_client.get("/body-map.png")
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(b"\x89PNG")
    page = api_client.get("/").text
    assert 'href="/body-map.png"' in page
    for region in ("head", "chest", "abdomen", "arms", "legs"):
        assert f'id="r-{region}"' in page


def test_dashboard_reveals_information_in_stages_and_respects_reduced_motion(api_client: TestClient) -> None:
    page = api_client.get("/").text
    assert "Show full context" in page
    assert "aria-expanded" in page
    assert "prefers-reduced-motion" in page


def test_dashboard_is_split_into_focused_tabs(api_client: TestClient) -> None:
    page = api_client.get("/").text
    assert 'role="tablist"' in page
    for view in ("today", "body", "history", "add"):
        assert f'data-go="{view}"' in page
        assert f'data-view="{view}"' in page


def test_dashboard_has_a_sign_in_screen_and_sign_out(api_client: TestClient) -> None:
    page = api_client.get("/").text
    for element_id in ("login", "loginUser", "loginPassword", "loginBtn", "logout", "who", "auditTab", "auditTable"):
        assert f'id="{element_id}"' in page
    assert 'type="password"' in page
    assert 'autocomplete="current-password"' in page


def test_empty_dashboard_points_to_the_add_reading_tab(api_client: TestClient) -> None:
    page = api_client.get("/").text
    assert 'id="firstReading"' in page
    assert "Add my first reading" in page


def test_revamped_dashboard_has_sidebar_hazards_and_readiness_ring(api_client: TestClient) -> None:
    page = api_client.get("/").text
    assert 'data-go="hazards"' in page and 'data-view="hazards"' in page
    for hazard in (
        "Space radiation",
        "Isolation and confinement",
        "Distance from Earth",
        "Altered gravity",
        "Closed environment",
    ):
        assert hazard in page
    assert 'id="ringFg"' in page and 'id="printBtn"' in page and 'id="linkState"' in page
    assert "https://" not in page.replace("http://127.0.0.1", "")  # still fully offline: no external resources
