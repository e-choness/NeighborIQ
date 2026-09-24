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
    Deterministic, template-based summary for development and for deployments
    without an LLM. Every sentence is conditional on a statistic actually being
    present, so missing data produces a shorter summary, never an invented one.
    """

    def generate(self, city: str, stats: dict) -> str:
        name = city.title()
        parts = []
        count = stats.get("listing_count")
        if count:
            parts.append(f"{name} has {count} active listings in NeighborIQ.")
        if stats.get("median_price"):
            ppsf = stats.get("median_price_per_sqft")
            ppsf_text = f" (${ppsf:,.0f} per sq ft)" if ppsf else ""
            parts.append(f"The median asking price is ${stats['median_price']:,.0f}{ppsf_text}.")
        trend = stats.get("price_trend_pct")
        if trend is not None:
            direction = "upward" if trend >= 0 else "downward"
            parts.append(f"Asking prices show a {abs(trend):.1f}% {direction} trend over the last six months.")
        if stats.get("avg_gross_yield_pct"):
            parts.append(f"Estimated gross rental yields average {stats['avg_gross_yield_pct']:.1f}%.")
        if stats.get("top_neighborhoods"):
            parts.append(f"The highest estimated yields are in {stats['top_neighborhoods']}.")
        if stats.get("price_cut_share_pct") is not None and count:
            parts.append(
                f"{stats['price_cut_share_pct']:.0f}% of listings have had a price reduction"
                + (f", and the median listing has been on the market {stats['median_days_on_market']} days."
                   if stats.get("median_days_on_market") is not None else ".")
            )
        if not parts:
            parts.append(f"There is not enough listing data for {name} to summarise yet.")
        parts.append(
            "These figures are estimates from asking prices, not sold prices — consult a "
            "licensed real estate professional before making decisions."
        )
        return " ".join(parts)


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

_PROMPT_FIELDS = (
    ("listing_count", "Active listings", "{:,}"),
    ("median_price", "Median asking price (CAD)", "${:,.0f}"),
    ("median_price_per_sqft", "Median asking price per sq ft (CAD)", "${:,.0f}"),
    ("price_trend_pct", "Asking-price trend, last 6 months (%)", "{:+.1f}"),
    ("avg_gross_yield_pct", "Average estimated gross rental yield (%)", "{:.1f}"),
    ("top_neighborhoods", "Neighbourhoods with the highest estimated yield", "{}"),
    ("price_cut_share_pct", "Listings with a price reduction (%)", "{:.0f}"),
    ("median_days_on_market", "Median days on market", "{}"),
)


def _build_prompt(city: str, stats: dict) -> str:
    """Only statistics that were actually computed are included in the prompt."""
    lines = [
        f"- {label}: {fmt.format(stats[key])}"
        for key, label, fmt in _PROMPT_FIELDS
        if stats.get(key) is not None
    ]
    return (
        f"You are a real estate market analyst writing for small residential investors. "
        f"Based ONLY on the following pre-computed statistics for {city.title()}, write a "
        f"2-paragraph market summary in English.\n\n"
        f"Market statistics (computed from active asking prices, not sold prices):\n"
        + "\n".join(lines or ["- (no statistics available)"])
        + "\n\nDo not invent statistics, trends or neighbourhoods that are not listed above. "
        "If a figure is missing, do not mention it."
    )
