from types import SimpleNamespace

import pytest

from app.modules.knowledge.service import EmbeddingService


def test_openai_compatible_embeddings_reuse_llm_credentials(monkeypatch):
    captured = {}

    class FakeEmbeddings:
        def create(self, *, model, input):
            captured["model"] = model
            captured["input"] = input
            return SimpleNamespace(data=[SimpleNamespace(index=0, embedding=[0.1, 0.2, 0.3])])

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.embeddings = FakeEmbeddings()

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    monkeypatch.setattr("app.modules.knowledge.service.settings.embedding_provider", "openai_compatible")
    monkeypatch.setattr("app.modules.knowledge.service.settings.embedding_api_key", None)
    monkeypatch.setattr("app.modules.knowledge.service.settings.embedding_base_url", None)
    monkeypatch.setattr("app.modules.knowledge.service.settings.llm_api_key", "provider-key")
    monkeypatch.setattr("app.modules.knowledge.service.settings.llm_base_url", "https://provider.test/v1")
    monkeypatch.setattr("app.modules.knowledge.service.settings.embedding_model", "multilingual-model")

    vector = EmbeddingService().embed("русский multilingual текст")

    assert vector == [0.1, 0.2, 0.3]
    assert captured["api_key"] == "provider-key"
    assert captured["base_url"] == "https://provider.test/v1"
    assert captured["model"] == "multilingual-model"


def test_remote_embeddings_require_api_key(monkeypatch):
    monkeypatch.setattr("app.modules.knowledge.service.settings.embedding_provider", "openai_compatible")
    monkeypatch.setattr("app.modules.knowledge.service.settings.embedding_api_key", None)
    monkeypatch.setattr("app.modules.knowledge.service.settings.llm_api_key", None)

    with pytest.raises(RuntimeError, match="Embedding API key"):
        EmbeddingService().embed("knowledge")


def test_full_embeddings_endpoint_is_normalized_to_sdk_base_url(monkeypatch):
    captured = {}

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.embeddings = SimpleNamespace(
                create=lambda **_kwargs: SimpleNamespace(
                    data=[SimpleNamespace(index=0, embedding=[0.1, 0.2])]
                )
            )

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    monkeypatch.setattr("app.modules.knowledge.service.settings.embedding_provider", "openai_compatible")
    monkeypatch.setattr("app.modules.knowledge.service.settings.embedding_api_key", "provider-key")
    monkeypatch.setattr(
        "app.modules.knowledge.service.settings.embedding_base_url",
        "https://provider.test/v1/embeddings/",
    )

    EmbeddingService().embed("knowledge")

    assert captured["base_url"] == "https://provider.test/v1"


def test_unknown_embedding_provider_is_rejected(monkeypatch):
    monkeypatch.setattr("app.modules.knowledge.service.settings.embedding_provider", "unknown")

    with pytest.raises(RuntimeError, match="Unsupported embedding provider"):
        EmbeddingService().embed("knowledge")
