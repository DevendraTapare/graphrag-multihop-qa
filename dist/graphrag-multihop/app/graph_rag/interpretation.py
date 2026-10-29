"""A closed deterministic question grammar, independent of vector runtime and gold."""

import re

from app.graph.schema import FactType as F
from app.graph.schema import Label as L
from app.graph_rag.models import Context, Plan, Step

VERSION = "graph-grammar-v1"


def interpret(question):
    q = " ".join(question.split()).strip().rstrip("?.!")
    # Specific inverse composition must precede the generic employment production.
    if match := re.fullmatch(r"Which organization employs the manager of Project (.+)", q, re.I):
        if len(match.group(1)) <= 200:
            return Plan(
                mention=match.group(1),
                start_type=L.PROJECT,
                steps=(Step(relation=F.MANAGES, direction="incoming"), Step(relation=F.WORKS_FOR)),
                answer_type=L.ORGANIZATION,
                rule_id="manager_employer",
            )
    # Each production defines types/steps explicitly. Captures are entity values only.
    productions = [
        ("person_project", r"Which projects? does (.+?) (?:manage|lead)", L.PERSON, (F.MANAGES,)),
        (
            "managed_project",
            r"Which projects? (?:is|are) (?:managed|led) by (.+)",
            L.PERSON,
            (F.MANAGES,),
        ),
        ("responsibility", r"What projects? is (.+?) responsible for", L.PERSON, (F.MANAGES,)),
        ("employment", r"Which organizations? employs? (.+)", L.PERSON, (F.WORKS_FOR,)),
        ("employer", r"Who employs (.+)", L.PERSON, (F.WORKS_FOR,)),
        ("workplace", r"Where does (.+?) work", L.PERSON, (F.WORKS_FOR,)),
        ("works_for", r"Which organizations? does (.+?) work for", L.PERSON, (F.WORKS_FOR,)),
        (
            "project_owner",
            r"Which organizations? (?:owns?|is responsible for) Project (.+)",
            L.PROJECT,
            (F.BELONGS_TO,),
        ),
        (
            "belongs_to",
            r"Which organizations? does Project (.+?) belong to",
            L.PROJECT,
            (F.BELONGS_TO,),
        ),
        (
            "technology",
            r"(?:Which|What) (?:databases?|technolog(?:y|ies)) does Project (.+?) (?:use|utilize)",
            L.PROJECT,
            (F.USES,),
        ),
        (
            "used_technology",
            r"What technolog(?:y|ies) (?:is|are) used by Project (.+)",
            L.PROJECT,
            (F.USES,),
        ),
        (
            "person_technology",
            r"(?:Which|What) (?:databases?|technolog(?:y|ies)) does the projects? "
            r"(?:managed|led) by (.+?) use",
            L.PERSON,
            (F.MANAGES, F.USES),
        ),
        (
            "under_management",
            r"Name the technolog(?:y|ies) used by the projects? under (.+?)'s management",
            L.PERSON,
            (F.MANAGES, F.USES),
        ),
        (
            "managed_owner",
            r"Which organizations? owns? the projects? (?:managed|led) by (.+)",
            L.PERSON,
            (F.MANAGES, F.BELONGS_TO),
        ),
        (
            "owner_under_management",
            r"Who owns the projects? under (.+?)'s management",
            L.PERSON,
            (F.MANAGES, F.BELONGS_TO),
        ),
        (
            "project_platform",
            r"(?:Which cloud platforms?|What platforms?) hosts? the "
            r"(?:databases?|technolog(?:y|ies)) used by Project (.+)",
            L.PROJECT,
            (F.USES, F.HOSTED_ON),
        ),
        (
            "technology_hosting",
            r"Where (?:is|are) the technolog(?:y|ies) used by Project (.+?) hosted",
            L.PROJECT,
            (F.USES, F.HOSTED_ON),
        ),
        (
            "person_platform",
            r"(?:Which cloud platforms?|What platforms?) hosts? the "
            r"(?:databases?|technolog(?:y|ies)) used by the projects? (?:managed|led) by (.+)",
            L.PERSON,
            (F.MANAGES, F.USES, F.HOSTED_ON),
        ),
        (
            "platform_under_management",
            r"Where (?:is|are) the technolog(?:y|ies) of the projects? "
            r"under (.+?)'s management hosted",
            L.PERSON,
            (F.MANAGES, F.USES, F.HOSTED_ON),
        ),
    ]
    for rule, pattern, label, predicates in productions:
        if match := re.fullmatch(pattern, q, re.I):
            mention = match.group(1)
            contexts = ()
            if context := re.fullmatch(
                r"(.+?) (?:at|in|from) (?:organization )?(.+)", mention, re.I
            ):
                mention, org = context.groups()
                if max(len(mention), len(org)) > 200:
                    return None
                contexts = (Context(entity_type=L.ORGANIZATION, mention=org),)
            if len(mention) > 200 or any(len(c.mention) > 200 for c in contexts):
                return None
            steps = tuple(Step(relation=p) for p in predicates)
            multiple = bool(
                re.search(
                    r"^(?:Which|What)(?: cloud)? "
                    r"(?:projects|databases|technologies|organizations|platforms)\b"
                    r"|^Name the technologies\b",
                    q,
                    re.I,
                )
            )
            return Plan(
                mention=mention,
                start_type=label,
                steps=steps,
                answer_type=steps[-1].types[1],
                contexts=contexts,
                multiple=multiple,
                rule_id=rule,
            )
    if match := re.fullmatch(r"Who manages Project (.+)", q, re.I):
        if len(match.group(1)) <= 200:
            return Plan(
                mention=match.group(1),
                start_type=L.PROJECT,
                steps=(Step(relation=F.MANAGES, direction="incoming"),),
                answer_type=L.PERSON,
                rule_id="manager_inverse",
            )
    if match := re.fullmatch(
        r"On which platforms? is the (.+?) instance for Project (.+?) hosted", q, re.I
    ):
        tech, project = match.groups()
        if max(len(tech), len(project)) <= 200:
            return Plan(
                mention=tech,
                start_type=L.TECHNOLOGY,
                steps=(Step(relation=F.HOSTED_ON),),
                answer_type=L.PLATFORM,
                contexts=(Context(entity_type=L.PROJECT, mention=project),),
                multiple=bool(re.search(r"\bplatforms\b", q, re.I)),
                rule_id="scoped_hosting",
            )
    return None
