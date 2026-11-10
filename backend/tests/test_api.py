import os
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient
from backend.app.main import app


def test_demo_api_flow():
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        demo = client.post("/api/demo")
        assert demo.status_code == 200
        payload = demo.json()
        assert payload["name"] == "Recommendation Ranking Experiment"
        assert payload["result"]["primary"]["test"] == "two-proportion z-test"
        exp_id = payload["id"]
        detail = client.get(f"/api/experiments/{exp_id}")
        assert detail.status_code == 200
        history = client.get("/api/experiments")
        assert any(item["id"] == exp_id for item in history.json())


def test_bad_csv_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/api/experiments/analyze",
            data={"name": "Bad", "metric_column": "converted", "metric_type": "binary"},
            files={"file": ("bad.csv", b"x,y\n1,2\n", "text/csv")},
        )
        assert response.status_code == 422


def test_frontend_is_served():
    with TestClient(app) as client:
        index = client.get("/")
        assert index.status_code == 200
        assert "ExperimentForge" in index.text
        script = client.get("/app.js")
        assert script.status_code == 200
        assert "loadHistory" in script.text


def test_valid_csv_upload():
    csv = b"user_id,variant,converted,device\n" + b"".join(
        [f"c{i},control,{1 if i < 8 else 0},desktop\n".encode() for i in range(40)] +
        [f"t{i},treatment,{1 if i < 16 else 0},desktop\n".encode() for i in range(40)]
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/experiments/analyze",
            data={"name": "Upload Test", "metric_column": "converted", "metric_type": "binary"},
            files={"file": ("experiment.csv", csv, "text/csv")},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sample_size"] == 80
        assert data["result"]["primary"]["treatment_value"] > data["result"]["primary"]["control_value"]


def test_static_path_traversal_is_blocked():
    with TestClient(app) as client:
        response = client.get("/%2e%2e/README.md")
        assert response.status_code == 404
