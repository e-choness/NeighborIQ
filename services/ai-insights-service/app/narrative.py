"""
Market narrative generation (Phase 5C).

Azure OpenAI is used ONLY for human-readable text summaries, not for numeric
predictions. One call per city per day keeps costs minimal (~99% reduction
compared to a per-house call).

Provider selection is controlled by the NARRATIVE_PROVIDER environment variable:
  "local"  — deterministic stub (default; used in dev and tests)
  "azure"  — Azure OpenAI GPT-3.5 (requires AZURE_OPENAI_KEY + AZURE_OPENAI_ENDPOINT)
"""
import logging
import os

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Adapters
# ---------------------------------------------------------------------------

class LocalNarrativeAdapter:
    """
    Deterministic stub for local development and testing.
    Returns a templated summary — no external API call required.
    """

    def generate(self, city: str, stats: dict) -> str:
        trend_pct = stats.get("price_trend_pct", 0)
        direction = "upward" if trend_pct >= 0 else "downward"
        top_region = stats.get("top_region", city)
        avg_yield = stats.get("avg_gross_yield_pct", 4.0)
        listing_count = stats.get("listing_count", 0)

        return (
            f"The {city.title()} real estate market is showing a {abs(trend_pct):.1f}% "
            f"{direction} price trend over the last six months. "
            f"The {top_region} area is generating the strongest investor interest, "
            f"with average gross rental yields of {avg_yield:.1f}%. "
            f"There are currently {listing_count} active listings across the city. "
            f"Buyers should note that market conditions continue to evolve — "
            f"consult a licensed real estate professional before making decisions."
        )


class AzureOpenAINarrativeAdapter:
    """
    Azure OpenAI adapter for production narrative generation.
    Requires:
      AZURE_OPENAI_KEY      — API key
      AZURE_OPENAI_ENDPOINT — Azure resource endpoint URL
      AZURE_OPENAI_DEPLOY   — Deployment name (default: gpt-35-turbo)
    """

    def __init__(
        self,
        api_key: str,
        endpoint: str,
        deployment: str = "gpt-35-turbo",
        api_version: str = "2024-02-01",
    ):
        self.api_key = api_key
        self.endpoint = endpoint
        self.deployment = deployment
        self.api_version = api_version

    def generate(self, city: str, stats: dict) -> str:
        try:
            from openai import AzureOpenAI
        except ImportError:
            logger.error("openai package not installed — falling back to local adapter.")
            return LocalNarrativeAdapter().generate(city, stats)

        client = AzureOpenAI(
            api_key=self.api_key,
            azure_endpoint=self.endpoint,
            api_version=self.api_version,
        )
        prompt = _build_prompt(city, stats)
        try:
            response = client.chat.completions.create(
                model=self.deployment,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=400,
                temperature=0.2,
            )
            return response.choices[0].message.content.strip()
        except Exception as exc:
            logger.error("Azure OpenAI call failed for city=%s: %s", city, exc)
            raise


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_adapter(provider: str | None = None) -> LocalNarrativeAdapter | AzureOpenAINarrativeAdapter:
    """
    Return a narrative adapter for the given provider.
    Defaults to NARRATIVE_PROVIDER env var, then "local".
    """
    provider = provider or os.getenv("NARRATIVE_PROVIDER", "local")

    if provider == "azure":
        api_key = os.getenv("AZURE_OPENAI_KEY", "")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        deployment = os.getenv("AZURE_OPENAI_DEPLOY", "gpt-35-turbo")
        if not api_key or not endpoint:
            logger.warning(
                "NARRATIVE_PROVIDER=azure but AZURE_OPENAI_KEY or AZURE_OPENAI_ENDPOINT "
                "is not set — falling back to local adapter."
            )
            return LocalNarrativeAdapter()
        return AzureOpenAINarrativeAdapter(api_key=api_key, endpoint=endpoint, deployment=deployment)

    return LocalNarrativeAdapter()


# ---------------------------------------------------------------------------
# Prompt builder (used by Azure adapter; exposed for testing)
# ---------------------------------------------------------------------------

def _build_prompt(city: str, stats: dict) -> str:
    return (
        f"You are a real estate market analyst. Based on the following pre-computed "
        f"market statistics for {city.title()}, write a 2-3 paragraph market summary "
        f"in English.\n\n"
        f"Market Statistics (computed from actual data):\n"
        f"- Top neighbourhoods by rental yield: {stats.get('top_neighborhoods', 'N/A')}\n"
        f"- Average price trend (last 6 months): {stats.get('price_trend_pct', 0):.1f}% "
        f"{('upward' if stats.get('price_trend_pct', 0) >= 0 else 'downward')}\n"
        f"- Total active listings: {stats.get('listing_count', 0)}\n"
        f"- Average gross rental yield: {stats.get('avg_gross_yield_pct', 0):.1f}%\n\n"
        f"Write a clear, factual market summary. Do not invent statistics — "
        f"use only the data provided above."
    )
