import hashlib
import json
import math
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument, KnowledgeQuery


@dataclass
class RankedChunk:
    chunk: KnowledgeChunk
    document: KnowledgeDocument
    score: float


class EmbeddingService:
    dimensions = 256

    def embed(self, text: str) -> list[float]:
        if settings.embedding_provider == "openai" and settings.openai_api_key:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            response = client.embeddings.create(model=settings.embedding_model, input=text)
            return response.data[0].embedding

        return self._local_embed(text)

    def _local_embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        words = re.findall(r"[\wа-яА-ЯёЁ]+", text.lower())
        for word in words:
            digest = hashlib.sha256(word.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class KnowledgeService:
    def __init__(self, db: Session):
        self.db = db
        self.embedding_service = EmbeddingService()

    def create_document(
        self,
        tenant_id: UUID,
        title: str,
        text: str,
        source_type: str = "text",
        company_id: UUID | None = None,
        deal_id: UUID | None = None,
        file_id: UUID | None = None,
        visibility: str = "global",
    ) -> KnowledgeDocument:
        document = KnowledgeDocument(
            tenant_id=tenant_id,
            company_id=company_id,
            deal_id=deal_id,
            file_id=file_id,
            title=title,
            source_type=source_type,
            visibility=visibility,
        )
        self.db.add(document)
        self.db.flush()

        chunks = self._split_text(text)
        for index, chunk_text in enumerate(chunks):
            embedding = self.embedding_service.embed(chunk_text)
            self.db.add(
                KnowledgeChunk(
                    tenant_id=tenant_id,
                    document_id=document.id,
                    chunk_index=index,
                    text=chunk_text,
                    embedding_json=json.dumps(embedding),
                    token_estimate=max(1, len(chunk_text) // 4),
                )
            )

        self.db.commit()
        self.db.refresh(document)
        return document

    def list_documents(
        self,
        tenant_id: UUID,
        company_id: UUID | None = None,
        deal_id: UUID | None = None,
    ) -> list[KnowledgeDocument]:
        query = self.db.query(KnowledgeDocument).filter(KnowledgeDocument.tenant_id == tenant_id)
        if company_id is not None:
            query = query.filter(KnowledgeDocument.company_id == company_id)
        if deal_id is not None:
            query = query.filter(KnowledgeDocument.deal_id == deal_id)
        return query.order_by(KnowledgeDocument.created_at.desc()).all()

    def search(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = 6,
        company_id: UUID | None = None,
        deal_id: UUID | None = None,
    ) -> list[RankedChunk]:
        query_embedding = self.embedding_service.embed(query)
        rows_query = (
            self.db.query(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .filter(KnowledgeChunk.tenant_id == tenant_id)
        )
        if company_id is not None:
            rows_query = rows_query.filter(
                (KnowledgeDocument.visibility == "global") |
                (KnowledgeDocument.company_id == company_id)
            )
        if deal_id is not None:
            rows_query = rows_query.filter(
                (KnowledgeDocument.visibility == "global") |
                (KnowledgeDocument.deal_id == deal_id) |
                (KnowledgeDocument.company_id == company_id)
            )
        rows = rows_query.all()

        ranked: list[RankedChunk] = []
        for chunk, document in rows:
            chunk_embedding = json.loads(chunk.embedding_json)
            score = self._cosine_similarity(query_embedding, chunk_embedding)
            ranked.append(RankedChunk(chunk=chunk, document=document, score=score))

        return sorted(ranked, key=lambda item: item.score, reverse=True)[:limit]

    def answer(
        self,
        tenant_id: UUID,
        user_id: UUID,
        question: str,
        limit: int = 6,
        company_id: UUID | None = None,
        deal_id: UUID | None = None,
    ) -> tuple[str, list[RankedChunk]]:
        ranked_chunks = self.search(tenant_id=tenant_id, query=question, limit=limit, company_id=company_id, deal_id=deal_id)
        if not ranked_chunks or ranked_chunks[0].score <= 0:
            answer = "Не нашел ответ в базе знаний компании."
            self._save_query(tenant_id, user_id, question, answer)
            return answer, []

        answer = self._grounded_answer(question, ranked_chunks)
        self._save_query(tenant_id, user_id, question, answer)
        return answer, ranked_chunks

    def _grounded_answer(self, question: str, ranked_chunks: list[RankedChunk]) -> str:
        llm_api_key = settings.llm_api_key or settings.openai_api_key
        if llm_api_key:
            from openai import OpenAI

            client = OpenAI(api_key=llm_api_key, base_url=settings.llm_base_url)
            context = "\n\n".join(
                f"[{index + 1}] {item.document.title}\n{item.chunk.text}"
                for index, item in enumerate(ranked_chunks)
            )
            prompt = (
                    "Ответь только по контексту компании. Если ответа нет, скажи, что не нашел в базе знаний.\n\n"
                    f"Вопрос: {question}\n\nКонтекст:\n{context}"
            )
            if settings.llm_base_url:
                response = client.chat.completions.create(
                    model=settings.llm_model,
                    messages=[{"role": "user", "content": prompt}],
                )
                return response.choices[0].message.content or ""

            response = client.responses.create(
                model=settings.llm_model,
                input=prompt,
            )
            return response.output_text

        best = ranked_chunks[0]
        return (
            "Нашел наиболее близкий фрагмент в базе знаний. "
            f"Источник: {best.document.title}. "
            f"Фрагмент: {best.chunk.text[:700]}"
        )

    def _save_query(self, tenant_id: UUID, user_id: UUID, question: str, answer: str) -> None:
        self.db.add(
            KnowledgeQuery(
                tenant_id=tenant_id,
                user_id=user_id,
                question=question,
                answer=answer,
            )
        )
        self.db.commit()

    def _split_text(self, text: str) -> list[str]:
        clean_text = re.sub(r"\s+", " ", text).strip()
        size = settings.rag_chunk_size
        overlap = settings.rag_chunk_overlap
        chunks: list[str] = []
        start = 0
        while start < len(clean_text):
            end = min(start + size, len(clean_text))
            chunk = clean_text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end == len(clean_text):
                break
            start = max(0, end - overlap)
        return chunks

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0 or right_norm == 0:
            return 0.0
        dot = sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True))
        return dot / (left_norm * right_norm)
