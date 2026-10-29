"""Conservative local grammar over retrieved text. No graph, registry, or gold labels."""

import re
from dataclasses import dataclass

from app.vector.models import Citation


def normal(value):
    return " ".join(value.casefold().split())


def product(value):
    return {"postgres": "postgresql"}.get(normal(value), normal(value))


@dataclass(frozen=True)
class Claim:
    subject: str
    predicate: str
    object: str
    display: str
    citation: Citation
    subject_display: str | None = None


NEGATIVE = re.compile(
    r"\b(not|never|may|might|could|would|if|allegedly|reportedly|ignore|instructions?|"
    r"example|denies|rumou?r|suppose)\b|^(system|assistant|user)\s*:",
    re.I,
)


def text_claims(chunks):
    claims = []
    for chunk in chunks:
        for start, end in zip(chunk.sentence_starts, chunk.sentence_ends, strict=True):
            # Only complete source sentences: chunk boundaries cannot remove a negation
            # prefix or turn a fenced example into an assertion.
            raw = chunk.text[start:end]
            if raw.startswith(('"', "'", ">")) or NEGATIVE.search(raw):
                continue
            text = raw.rstrip(".!? ")
            cite = Citation(
                document_id=chunk.document_id,
                chunk_id=chunk.chunk_id,
                quote=raw,
                start=chunk.start + start,
                end=chunk.start + end,
            )
            result = None
            if m := re.fullmatch(r"(.+?) (?:manages|leads) Project (.+?)(?: at .+)?", text):
                person, project = m.groups()
                result = (normal(person), "manages", normal(project), project)
            elif m := re.fullmatch(r"Project (.+?) is managed by (.+)", text):
                project, person = m.groups()
                result = (normal(person), "manages", normal(project), project)
            elif m := re.fullmatch(r"(.+?) (?:works for|is employed by) (.+)", text):
                person, org = m.groups()
                result = (normal(person), "employment", normal(org), org)
            elif m := re.fullmatch(r"Project (.+?) (?:belongs to|is owned by) (.+)", text):
                project, org = m.groups()
                result = (normal(project), "owner", normal(org), org)
            elif m := re.fullmatch(
                r"Project (.+?) (?:uses|utilizes) (?:its own |its |a |the )?"
                r"(.+?)(?: database)? instance",
                text,
            ):
                project, tech = m.groups()
                result = (normal(project), "uses", f"{product(tech)}@{normal(project)}", tech)
            elif m := re.fullmatch(
                r"The (.+?) instance for Project (.+?) (?:is hosted on|runs on) (.+)", text
            ):
                tech, project, platform = m.groups()
                canonical = {
                    "amazon web services": "AWS",
                    "microsoft azure": "Azure",
                    "google cloud": "GCP",
                }.get(normal(platform), platform)
                result = (
                    f"{product(tech)}@{normal(project)}",
                    "hosting",
                    normal(canonical),
                    canonical,
                )
            if result:
                claims.append(Claim(*result, cite, person if result[1] == "manages" else None))
    return claims


def question_plan(question):
    q = question.strip().rstrip("?.!")
    specs = [
        (r"Which project does (.+?) (?:manage|lead)", ["manages"]),
        (r"What project is (.+?) responsible for", ["manages"]),
        (r"Which project is (?:managed|led) by (.+)", ["manages"]),
        (
            r"(?:Where does (.+?) work|Which organization employs (.+?)|Who employs (.+?))",
            ["employment"],
        ),
        (r"Which organization does (.+?) work for", ["employment"]),
        (r"Which organization (?:owns|is responsible for) Project (.+)", ["owner"]),
        (r"Which organization does Project (.+?) belong to", ["owner"]),
        (r"(?:Which|What) (?:database|technology) does Project (.+?) (?:use|utilize)", ["uses"]),
        (r"What technology is used by Project (.+)", ["uses"]),
        (
            r"(?:Which|What) (?:database|technology) does the project (?:managed|led) by (.+?) use",
            ["manages", "uses"],
        ),
        (r"Name the technology used by the project under (.+?)'s management", ["manages", "uses"]),
        (r"Which organization owns the project (?:managed|led) by (.+)", ["manages", "owner"]),
        (r"Who owns the project under (.+?)'s management", ["manages", "owner"]),
        (
            r"(?:Which cloud platform|What platform) hosts the (?:database|technology) used by "
            r"Project (.+)",
            ["uses", "hosting"],
        ),
        (r"Where is the technology used by Project (.+?) hosted", ["uses", "hosting"]),
        (
            r"(?:Which cloud platform|What platform) hosts the (?:database|technology) used by the "
            r"project (?:managed|led) by (.+)",
            ["manages", "uses", "hosting"],
        ),
        (
            r"Where is the technology of the project under (.+?)'s management hosted",
            ["manages", "uses", "hosting"],
        ),
        (r"Who manages Project (.+)", ["manager_inverse"]),
    ]
    for pattern, predicates in specs:
        if match := re.fullmatch(pattern, q, re.I):
            return normal(next(g for g in match.groups() if g)), predicates
    if match := re.fullmatch(
        r"On which platform is the (.+?) instance for Project (.+?) hosted", q, re.I
    ):
        tech, project = match.groups()
        return f"{product(tech)}@{normal(project)}", ["hosting"]
    return None


class DeterministicAnswerer:
    version = "deterministic_text_v1"

    def answer(self, question, chunks):
        plan = question_plan(question)
        if plan is None:
            return None, [], "unsupported_question_form"
        initial, predicates = plan
        claims = text_claims(chunks)
        if predicates == ["manager_inverse"]:
            matches = [c for c in claims if c.predicate == "manages" and c.object == initial]
            if not matches:
                return None, [], "insufficient_evidence"
            answers = sorted({c.subject for c in matches})
            # Recover exact source subject casing from the supported quote.
            display = [next(c.subject_display for c in matches if c.subject == a) for a in answers]
            return "; ".join(display), [c.citation for c in matches], "supported"
        # Qualified homonyms cannot be inferred to be the unqualified person.
        if any(c.subject.startswith(initial + " (") for c in claims) and "(" not in initial:
            return None, [], "ambiguous_identity"
        frontier = [(initial, [])]
        for predicate in predicates:
            extended = []
            for subject, path in frontier:
                matches = [c for c in claims if c.subject == subject and c.predicate == predicate]
                if not matches:
                    return None, [], "insufficient_evidence"
                if (
                    predicate in {"owner", "hosting", "employment"}
                    and len({c.object for c in matches}) > 1
                ):
                    return None, [], "conflicting_evidence"
                extended.extend((c.object, [*path, c]) for c in matches)
            frontier = extended
        if not frontier:
            return None, [], "insufficient_evidence"
        answers, citations = {}, {}
        for final, path in frontier:
            answers[final] = path[-1].display
            for c in path:
                citations[(c.citation.chunk_id, c.citation.start, c.citation.end)] = c.citation
        return "; ".join(answers[k] for k in sorted(answers)), list(citations.values()), "supported"
