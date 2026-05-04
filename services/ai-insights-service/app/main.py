from typing import Any, Dict, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import os

# Provider-agnostic request model


class AIProviderRequest(BaseModel):
    provider: str = Field(
        ..., description="Provider identifier, e.g., 'azure', 'openai', 'local'", example="local")
    model: Optional[str] = Field(
        None, description="Optional model name", example="gpt-4o-mini")
    input: Dict[str, Any] = Field(..., description="Domain-specific input (features or city descriptor)",
                                  example={"city": "Austin", "median_income": 80000})
    parameters: Optional[Dict[str, Any]] = Field(
        None, description="Provider-specific options", example={"max_tokens": 200, "temperature": 0.2})
    async_callback_url: Optional[str] = Field(
        None, description="Optional callback URL for async results", example=None)


class AIProviderPredictionResponse(BaseModel):
    provider: str
    model: Optional[str]
    predictions: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


class AIProviderTextResponse(BaseModel):
    provider: str
    model: Optional[str]
    text: str
    tokens_used: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None


app = FastAPI(title="AI Insights Service (provider-agnostic)", version="0.1.0")


# Simple adapter registry
class ProviderAdapter:
    def predict(self, input: Dict[str, Any], parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        raise NotImplementedError()

    def narrative(self, input: Dict[str, Any], parameters: Optional[Dict[str, Any]] = None) -> str:
        raise NotImplementedError()


class LocalAdapter(ProviderAdapter):
    # Returns deterministic stubbed responses for local development
    def predict(self, input: Dict[str, Any], parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        # Example: return price prediction and rental yield
        city = input.get("city", "unknown")
        base = 300000 if city.lower() != "unknown" else 100000
        price = base + int(input.get("median_income", 50000) / 10)
        rental_yield = 0.05
        return {"price": price, "rental_yield": rental_yield}

    def narrative(self, input: Dict[str, Any], parameters: Optional[Dict[str, Any]] = None) -> str:
        city = input.get("city", "your area")
        return f"Market narrative for {city}: stable demand with moderate price growth."


ADAPTERS = {
    "local": LocalAdapter(),
    # 'azure': AzureAdapter(),
    # 'openai': OpenAIAdapter(),
}


def get_adapter(provider: str) -> ProviderAdapter:
    adapter = ADAPTERS.get(provider)
    if not adapter:
        raise HTTPException(
            status_code=400, detail=f"Unknown provider: {provider}")
    return adapter


@app.post("/api/v1/ai/predict", response_model=AIProviderPredictionResponse)
async def ai_predict(req: AIProviderRequest):
    adapter = get_adapter(req.provider)
    predictions = adapter.predict(req.input, req.parameters)
    return AIProviderPredictionResponse(provider=req.provider, model=req.model, predictions=predictions, metadata={"source": "local-stub"})


@app.post("/api/v1/ai/narrative", response_model=AIProviderTextResponse)
async def ai_narrative(req: AIProviderRequest):
    adapter = get_adapter(req.provider)
    text = adapter.narrative(req.input, req.parameters)
    return AIProviderTextResponse(provider=req.provider, model=req.model, text=text, tokens_used=0, metadata={"source": "local-stub"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8003)
