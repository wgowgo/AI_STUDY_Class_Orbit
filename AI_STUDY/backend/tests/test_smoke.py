from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get(/api/health)
    assert r.status_code == 200
    body = r.json()
    assert body.get(ok) is True
    assert integrations in body
    assert body[integrations].get(kess) == sample_only


def test_kess_sample_meta():
    r = client.post(/api/public/kess, json={region: 전국, year: 2026, grade: 1})
    assert r.status_code == 200
    data = r.json()
    assert data.get(source) == sample
    assert data.get(integration) == sample_only
    assert data.get(simulation) is True


def test_sklearn_simulation_flag():
    r = client.post(
        /api/models/risk/predict-sklearn,
        json={
            averageScore: 70,
            attendanceRate: 90,
            classQualityScore: 75,
            schoolEnvironmentScore: 65,
        },
    )
    assert r.status_code == 200
    assert r.json().get(simulation) is True
