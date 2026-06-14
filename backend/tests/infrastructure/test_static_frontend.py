from pathlib import Path

from fastapi.testclient import TestClient

from study_podcast.infrastructure.app import create_app
from study_podcast.infrastructure.config import Settings


def test_serves_frontend_index_when_dist_exists(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>StudyCast</h1>", encoding="utf-8")
    client = TestClient(
        create_app(Settings(database_path=tmp_path / "app.sqlite3", frontend_dist_path=dist))
    )

    response = client.get("/")

    assert response.status_code == 200
    assert "StudyCast" in response.text


def test_react_router_fallback_serves_index_for_non_api_route(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>StudyCast</h1>", encoding="utf-8")
    client = TestClient(
        create_app(Settings(database_path=tmp_path / "app.sqlite3", frontend_dist_path=dist))
    )

    response = client.get("/jobs")

    assert response.status_code == 200
    assert "StudyCast" in response.text


def test_api_routes_still_return_json_when_frontend_is_served(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>StudyCast</h1>", encoding="utf-8")
    client = TestClient(
        create_app(Settings(database_path=tmp_path / "app.sqlite3", frontend_dist_path=dist))
    )

    response = client.get("/api/v1/projects")

    assert response.status_code == 200
    assert response.json() == []


def test_missing_api_route_returns_json_not_frontend_html(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<h1>StudyCast</h1>", encoding="utf-8")
    client = TestClient(
        create_app(Settings(database_path=tmp_path / "app.sqlite3", frontend_dist_path=dist))
    )

    response = client.get("/api/v1/not-a-route")

    assert response.status_code == 404
    assert response.json() == {
        "code": "not_found",
        "message": "API route not found",
        "details": None,
    }
