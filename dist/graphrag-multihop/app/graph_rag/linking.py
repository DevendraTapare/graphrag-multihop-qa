from app.extraction.registry import EntityRegistry
from app.graph.schema import Label
from app.graph_rag.models import Resolution


class EntityLinker:
    def __init__(self, registry: EntityRegistry):
        self.registry = registry

    def resolve(self, plan):
        options = self.registry.candidates(plan.start_type, plan.mention)
        if not options:
            return Resolution(status="not_found", reason="alias_not_registered")
        for context in plan.contexts:
            choices = self.registry.candidates(context.entity_type, context.mention)
            if not choices:
                return Resolution(status="not_found", reason="context_not_registered")
            if len(choices) != 1:
                return Resolution(
                    status="ambiguous",
                    reason="context_ambiguous",
                    candidate_ids=tuple(sorted(e.entity.id for e in options)),
                )
            id = choices[0].entity.id
            if context.entity_type == Label.PROJECT:
                options = [e for e in options if id in e.project_ids]
            elif context.entity_type == Label.ORGANIZATION:
                options = [e for e in options if id in e.organization_ids]
            else:
                return Resolution(status="not_found", reason="unsupported_context_type")
        ids = tuple(sorted(e.entity.id for e in options))
        if len(ids) == 1:
            return Resolution(
                status="resolved",
                canonical_id=ids[0],
                candidate_ids=ids,
                reason="exact_typed_alias_and_context",
            )
        return Resolution(
            status="ambiguous" if ids else "not_found",
            candidate_ids=ids,
            reason="multiple_canonical_identities" if ids else "context_mismatch",
        )
