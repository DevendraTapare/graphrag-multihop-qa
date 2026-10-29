from enum import StrEnum


class Label(StrEnum):
    PERSON = "Person"
    ORGANIZATION = "Organization"
    PROJECT = "Project"
    TECHNOLOGY = "Technology"
    PLATFORM = "Platform"


class FactType(StrEnum):
    MANAGES = "MANAGES"
    WORKS_FOR = "WORKS_FOR"
    USES = "USES"
    HOSTED_ON = "HOSTED_ON"
    BELONGS_TO = "BELONGS_TO"


DIRECTIONS = {
    FactType.MANAGES: (Label.PERSON, Label.PROJECT),
    FactType.WORKS_FOR: (Label.PERSON, Label.ORGANIZATION),
    FactType.USES: (Label.PROJECT, Label.TECHNOLOGY),
    FactType.HOSTED_ON: (Label.TECHNOLOGY, Label.PLATFORM),
    FactType.BELONGS_TO: (Label.PROJECT, Label.ORGANIZATION),
}
