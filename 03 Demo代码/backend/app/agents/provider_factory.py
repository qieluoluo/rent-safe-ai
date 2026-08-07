from app.agents.mock_provider import MockAnalysisProvider
from app.agents.openai_compatible_provider import OpenAICompatibleAnalysisProvider
from app.core.config import Settings


def build_analysis_provider(settings: Settings) -> MockAnalysisProvider:
    provider = settings.ai_provider.lower()
    if provider == "mock":
        return MockAnalysisProvider()
    if provider in {"deepseek", "openai-compatible"}:
        return OpenAICompatibleAnalysisProvider(settings)
    raise ValueError(f"不支持的 AI_PROVIDER: {settings.ai_provider}")
