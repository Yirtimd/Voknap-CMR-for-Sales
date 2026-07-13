import hashlib
import json
import math
import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument, KnowledgeQuery
from app.modules.sales.models import Company, Deal


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
        self._validate_scope_context(tenant_id, visibility, company_id, deal_id)
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
                    scope=visibility,
                    company_id=company_id,
                    deal_id=deal_id,
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
        scope: str = "global",
        company_id: UUID | None = None,
        deal_id: UUID | None = None,
        include_global: bool = False,
    ) -> list[KnowledgeDocument]:
        self._validate_scope_context(tenant_id, scope, company_id, deal_id)
        query = self.db.query(KnowledgeDocument).filter(KnowledgeDocument.tenant_id == tenant_id)
        query = query.filter(self._document_scope_filter(scope, company_id, deal_id, include_global))
        return query.order_by(KnowledgeDocument.created_at.desc()).all()

    def search(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = 6,
        scope: str = "global",
        company_id: UUID | None = None,
        deal_id: UUID | None = None,
        include_global: bool = False,
    ) -> list[RankedChunk]:
        self._validate_scope_context(tenant_id, scope, company_id, deal_id)
        query_embedding = self.embedding_service.embed(query)
        rows_query = (
            self.db.query(KnowledgeChunk, KnowledgeDocument)
            .join(KnowledgeDocument, KnowledgeDocument.id == KnowledgeChunk.document_id)
            .filter(
                KnowledgeChunk.tenant_id == tenant_id,
                KnowledgeDocument.status == "ready",
                self._chunk_scope_filter(scope, company_id, deal_id, include_global),
            )
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
        scope: str = "global",
        company_id: UUID | None = None,
        deal_id: UUID | None = None,
        include_global: bool = False,
    ) -> tuple[str, list[RankedChunk]]:
        ranked_chunks = self.search(
            tenant_id=tenant_id,
            query=question,
            limit=limit,
            scope=scope,
            company_id=company_id,
            deal_id=deal_id,
            include_global=include_global,
        )
        if not ranked_chunks or ranked_chunks[0].score <= 0:
            answer = "Не нашел ответ в выбранной базе знаний."
            self._save_query(tenant_id, user_id, question, answer, scope, company_id, deal_id, include_global)
            return answer, []

        answer = self._grounded_answer(question, ranked_chunks, scope)
        self._save_query(tenant_id, user_id, question, answer, scope, company_id, deal_id, include_global)
        return answer, ranked_chunks

    def _grounded_answer(self, question: str, ranked_chunks: list[RankedChunk], scope: str) -> str:
        llm_api_key = settings.llm_api_key or settings.openai_api_key
        if llm_api_key:
            from openai import OpenAI

            context = "\n\n".join(
                f"[{index + 1}] {item.document.title}\n{item.chunk.text}"
                for index, item in enumerate(ranked_chunks)
            )
            prompt = (
                f"Режим базы знаний: {scope}. Ответь только по переданному контексту. "
                "Не используй знания о других компаниях. Если ответа нет, прямо скажи об этом.\n\n"
                f"Вопрос: {question}\n\nКонтекст:\n{context}"
            )
            try:
                client = OpenAI(
                    api_key=llm_api_key,
                    base_url=settings.llm_base_url,
                    timeout=12.0,
                    max_retries=0,
                )
                if settings.llm_base_url:
                    response = client.chat.completions.create(
                        model=settings.llm_model,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    return response.choices[0].message.content or self._extractive_answer(ranked_chunks[0])

                response = client.responses.create(
                    model=settings.llm_model,
                    input=prompt,
                )
                return response.output_text or self._extractive_answer(ranked_chunks[0])
            except Exception:
                return self._extractive_answer(ranked_chunks[0], llm_unavailable=True)

        return self._extractive_answer(ranked_chunks[0])

    def _extractive_answer(self, best: RankedChunk, llm_unavailable: bool = False) -> str:
        prefix = "LLM сейчас недоступна. " if llm_unavailable else ""
        return (
            f"{prefix}Нашел наиболее близкий фрагмент в базе знаний. "
            f"Источник: {best.document.title}. "
            f"Фрагмент: {best.chunk.text[:700]}"
        )

    def _save_query(
        self,
        tenant_id: UUID,
        user_id: UUID,
        question: str,
        answer: str,
        scope: str,
        company_id: UUID | None,
        deal_id: UUID | None,
        include_global: bool,
    ) -> None:
        self.db.add(
            KnowledgeQuery(
                tenant_id=tenant_id,
                user_id=user_id,
                scope=scope,
                company_id=company_id,
                deal_id=deal_id,
                include_global=include_global,
                question=question,
                answer=answer,
            )
        )
        self.db.commit()

    def _validate_scope_context(
        self,
        tenant_id: UUID,
        scope: str,
        company_id: UUID | None,
        deal_id: UUID | None,
    ) -> None:
        if scope not in {"global", "company", "deal"}:
            raise ValueError("Unknown knowledge scope")
        if scope == "global":
            if company_id is not None or deal_id is not None:
                raise ValueError("Global knowledge cannot receive company_id or deal_id")
            return
        if company_id is None:
            raise ValueError("Company knowledge requires company_id")
        company = (
            self.db.query(Company)
            .filter(Company.tenant_id == tenant_id, Company.id == company_id)
            .one_or_none()
        )
        if company is None:
            raise ValueError("Company does not belong to current workspace")
        if scope == "company":
            if deal_id is not None:
                raise ValueError("Company knowledge cannot receive deal_id; use deal scope")
            return
        if deal_id is None:
            raise ValueError("Deal knowledge requires deal_id")
        deal = (
            self.db.query(Deal)
            .filter(Deal.tenant_id == tenant_id, Deal.id == deal_id)
            .one_or_none()
        )
        if deal is None or deal.company_id != company_id:
            raise ValueError("Deal does not belong to selected company")

    def _document_scope_filter(
        self,
        scope: str,
        company_id: UUID | None,
        deal_id: UUID | None,
        include_global: bool,
    ):
        global_filter = KnowledgeDocument.visibility == "global"
        if scope == "global":
            return global_filter
        if scope == "company":
            scoped_filter = KnowledgeDocument.company_id == company_id
        else:
            scoped_filter = or_(
                KnowledgeDocument.deal_id == deal_id,
                and_(KnowledgeDocument.company_id == company_id, KnowledgeDocument.deal_id.is_(None)),
            )
        return or_(global_filter, scoped_filter) if include_global else scoped_filter

    def _chunk_scope_filter(
        self,
        scope: str,
        company_id: UUID | None,
        deal_id: UUID | None,
        include_global: bool,
    ):
        global_filter = KnowledgeChunk.scope == "global"
        if scope == "global":
            return global_filter
        if scope == "company":
            scoped_filter = and_(
                KnowledgeChunk.company_id == company_id,
                KnowledgeChunk.deal_id.is_(None),
            )
        else:
            scoped_filter = or_(
                KnowledgeChunk.deal_id == deal_id,
                and_(KnowledgeChunk.company_id == company_id, KnowledgeChunk.deal_id.is_(None)),
            )
        return or_(global_filter, scoped_filter) if include_global else scoped_filter

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
