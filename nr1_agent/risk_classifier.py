from __future__ import annotations

import unicodedata
from dataclasses import dataclass

from nr1_agent.models import SessionState


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    classification: str
    categories: tuple[str, ...]
    evidence: tuple[str, ...]
    action: str


CATEGORY_KEYWORDS = {
    "Físicos": ("barulho", "ruido", "calor", "vibracao", "frio", "radiacao", "umidade"),
    "Químicos": ("poeira", "fumaca", "cheiro forte", "solvente", "acido", "gas", "vapor", "tinta"),
    "Biológicos": ("bacteria", "virus", "fungo", "sangue", "lixo hospitalar", "esgoto", "contaminacao"),
    "Ergonômicos": (
        "dor nas costas",
        "postura ruim",
        "peso excessivo",
        "repetitivo",
        "meta abusiva",
        "estresse",
        "turno noturno",
        "dor",
        "fadiga",
        "pausas insuficientes",
    ),
    "Acidentes (mecânicos)": (
        "queda",
        "choque",
        "ferramenta quebrada",
        "iluminacao ruim",
        "maquina sem protecao",
        "incendio",
        "esmagamento",
        "corte",
        "faísca",
    ),
}

HIGH_RISK_SIGNALS = (
    "risco iminente",
    "iminente",
    "acidente grave",
    "grave",
    "sem qualquer protecao",
    "maquina sem protecao",
    "risco de esmagamento",
    "risco de amputacao",
    "ambiente toxico",
    "sem ventilacao",
    "incendio",
    "explosao",
)

MEDIUM_RISK_SIGNALS = (
    "frequente",
    "frequentemente",
    "quase acidente",
    "quase-acidente",
    "dor",
    "fadiga",
    "sem epi",
    "sem ep i",
    "sem epc",
    "protecao insuficiente",
    "protecao intermitente",
    "nao fornece",
    "não fornece",
    "nao recebo",
    "não recebo",
    "nao resolve",
    "não resolve",
    "nao funciona",
    "não funciona",
)

PROTECTION_SIGNALS = (
    "epi",
    "epc",
    "treinamento",
    "treinamentos",
    "protecao adequada",
    "proteção adequada",
    "protegido",
    "protegida",
    "sem acidentes",
    "nenhum acidente",
    "sem queixas",
)


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


def _contains_any(text: str, signals: tuple[str, ...]) -> bool:
    return any(_normalize(signal) in text for signal in signals)


def classify(session: SessionState) -> RiskAssessment:
    answer_text = " ".join(session.answers)
    normalized_answers = _normalize(answer_text)
    categories = tuple(
        category
        for category, keywords in CATEGORY_KEYWORDS.items()
        if _contains_any(normalized_answers, keywords)
    )

    if _contains_any(normalized_answers, HIGH_RISK_SIGNALS):
        classification = "Alto / Crítico"
        action = "Intervenção imediata; comunicar o SESMT/CIPA e paralisar a atividade se necessário."
    elif _contains_any(normalized_answers, MEDIUM_RISK_SIGNALS):
        classification = "Médio / Alerta"
        action = "Programar vistoria e revisar as medidas de prevenção."
    elif _contains_any(normalized_answers, PROTECTION_SIGNALS) and not categories:
        classification = "Baixo / Monitorado"
        action = "Registrar no PGR e manter monitoramento periódico."
    elif _contains_any(normalized_answers, PROTECTION_SIGNALS) and not _contains_any(
        normalized_answers, ("sem", "falta", "ausencia", "ausência", "insuficiente", "inadequado")
    ):
        classification = "Baixo / Monitorado"
        action = "Registrar no PGR e manter monitoramento periódico."
    else:
        classification = "Médio / Alerta"
        action = "Programar vistoria e revisar as medidas de prevenção."

    evidence = tuple(
        answer.strip() for answer in session.answers if answer.strip()
    )
    return RiskAssessment(
        classification=classification,
        categories=categories or ("Nenhuma categoria identificada",),
        evidence=evidence,
        action=action,
    )


def format_assessment(assessment: RiskAssessment) -> str:
    categories = ", ".join(assessment.categories)
    evidence = " | ".join(assessment.evidence)
    return (
        "\n\nClassificação de risco: {classification}"
        "\nCategorias identificadas: {categories}"
        "\nEvidências consideradas: {evidence}"
        "\nEncaminhamento: {action}"
    ).format(
        classification=assessment.classification,
        categories=categories,
        evidence=evidence,
        action=assessment.action,
    )
