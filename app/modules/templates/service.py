import json
from uuid import UUID

from sqlalchemy.orm import Session

from app.modules.knowledge.service import KnowledgeService
from app.modules.sales.models import Pipeline, PipelineStage
from app.modules.templates.definitions import TEMPLATES, CompanyTemplate, get_template
from app.modules.templates.models import AppliedTemplate


class TemplateService:
    def __init__(self, db: Session):
        self.db = db

    def list_templates(self) -> list[CompanyTemplate]:
        return TEMPLATES

    def list_applied(self, tenant_id: UUID) -> list[AppliedTemplate]:
        return (
            self.db.query(AppliedTemplate)
            .filter(AppliedTemplate.tenant_id == tenant_id)
            .order_by(AppliedTemplate.created_at.desc())
            .all()
        )

    def apply_template(
        self,
        tenant_id: UUID,
        template_code: str,
        include_pipeline: bool = True,
        include_knowledge: bool = True,
    ) -> AppliedTemplate:
        template = get_template(template_code)
        if template is None:
            raise ValueError("Template not found")

        result: dict = {"pipeline_id": None, "knowledge_document_id": None}

        if include_pipeline:
            pipeline = self._create_pipeline(tenant_id, template)
            result["pipeline_id"] = str(pipeline.id)

        if include_knowledge:
            document = KnowledgeService(self.db).create_document(
                tenant_id=tenant_id,
                title=template.knowledge_title,
                text=template.knowledge_text,
                source_type="template",
            )
            result["knowledge_document_id"] = str(document.id)

        applied = AppliedTemplate(
            tenant_id=tenant_id,
            template_code=template.code,
            template_title=template.title,
            result_json=json.dumps(result),
        )
        self.db.add(applied)
        self.db.commit()
        self.db.refresh(applied)
        return applied

    def _create_pipeline(self, tenant_id: UUID, template: CompanyTemplate) -> Pipeline:
        pipeline = Pipeline(tenant_id=tenant_id, name=template.pipeline_name)
        self.db.add(pipeline)
        self.db.flush()

        for index, stage_name in enumerate(template.stages):
            self.db.add(
                PipelineStage(
                    tenant_id=tenant_id,
                    pipeline_id=pipeline.id,
                    name=stage_name,
                    sort_order=index,
                )
            )

        self.db.flush()
        return pipeline

