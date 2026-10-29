"""Stage 4 grammar plus an explicitly documented possessive project question."""

import re

from app.graph_rag.interpretation import interpret as original_interpret


def interpret(question):
    if match := re.fullmatch(
        r"Which cloud platform hosts the database used by (.+?)'s project[?.!]?",
        " ".join(question.split()),
        re.I,
    ):
        question = (
            "Which cloud platform hosts the database used by the project managed by "
            + match.group(1)
            + "?"
        )
    return original_interpret(question)
