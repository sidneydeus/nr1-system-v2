from nr1_agent.models import SessionState
from nr1_agent.risk_classifier import classify


def test_classifies_high_risk_from_immediate_mechanical_danger() -> None:
    session = SessionState(
        session_id="high-risk",
        answers=["Há uma máquina sem proteção, com risco de esmagamento."],
    )

    assessment = classify(session)

    assert assessment.classification == "Alto / Crítico"
    assert assessment.categories == ("Acidentes (mecânicos)",)


def test_classifies_low_risk_when_protections_are_confirmed() -> None:
    session = SessionState(
        session_id="low-risk",
        answers=["A empresa fornece EPI e treinamentos adequados. Não houve acidentes."],
    )

    assessment = classify(session)

    assert assessment.classification == "Baixo / Monitorado"
