import json
import os
import pytest


def load_spec(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


@pytest.mark.skipif(
    not os.path.exists(os.path.join(BASE, "api-gateway", "openapi.json")),
    reason="Contract tests require all service openapi.json files (run from project root)",
)
def test_openapi_specs_exist_and_basic_structure() -> None:
    services = [
        "api-gateway",
        "auth-service",
        "house-api-service",
        "ai-insights-service",
    ]

    for svc in services:
        spec_path = os.path.join(BASE, svc, "openapi.json")
        assert os.path.exists(
            spec_path), f"Missing openapi.json for {svc}: {spec_path}"
        spec = load_spec(spec_path)
        assert "openapi" in spec, f"Spec {svc} missing 'openapi'"
        assert isinstance(spec.get("paths"), dict) and spec.get(
            "paths"), f"Spec {svc} has no paths"


@pytest.mark.skipif(
    not os.path.exists(os.path.join(BASE, "ai-insights-service", "openapi.json")),
    reason="Contract tests require openapi.json",
)
def test_ai_insights_schema_examples() -> None:
    spec_path = os.path.join(BASE, "ai-insights-service", "openapi.json")
    spec = load_spec(spec_path)
    assert "/api/v1/ai/predict" in spec["paths"]
    req_schema = spec["components"]["schemas"].get("AIProviderRequest")
    assert req_schema is not None
    provider_prop = req_schema["properties"].get("provider")
    assert provider_prop is not None
    # Example must exist and be provider-agnostic
    assert provider_prop.get("example") == "local"


@pytest.mark.skipif(
    not os.path.exists(os.path.join(BASE, "house-api-service", "openapi.json")),
    reason="Contract tests require house-api-service openapi.json",
)
def test_house_api_contracts() -> None:
    spec_path = os.path.join(BASE, "house-api-service", "openapi.json")
    spec = load_spec(spec_path)
    assert "/api/v1/houses" in spec["paths"]
    get_op = spec["paths"]["/api/v1/houses"].get("get")
    assert get_op is not None
    # Ensure pagination query params are declared
    params = {p["name"] for p in get_op.get("parameters", [])}
    assert "page" in params and "page_size" in params