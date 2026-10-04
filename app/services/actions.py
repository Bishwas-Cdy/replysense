from dataclasses import dataclass

from app.schemas import Classification, RecommendedAction


@dataclass(frozen=True)
class ActionDecision:
    action: RecommendedAction
    requires_human_review: bool


ACTION_MAP: dict[Classification, ActionDecision] = {
    Classification.INTERESTED: ActionDecision(RecommendedAction.HUMAN_REVIEW, True),
    Classification.MEETING_REQUEST: ActionDecision(RecommendedAction.SCHEDULE_FOLLOW_UP, True),
    Classification.QUESTION: ActionDecision(RecommendedAction.ANSWER_QUESTION, True),
    Classification.NOT_NOW: ActionDecision(RecommendedAction.CREATE_FOLLOW_UP_TASK, False),
    Classification.NOT_INTERESTED: ActionDecision(RecommendedAction.CLOSE_OPPORTUNITY, False),
    Classification.WRONG_PERSON: ActionDecision(RecommendedAction.FIND_CORRECT_CONTACT, False),
    Classification.REFERRAL: ActionDecision(RecommendedAction.ROUTE_TO_REFERRAL, True),
    Classification.OUT_OF_OFFICE: ActionDecision(RecommendedAction.WAIT_UNTIL_RETURN, False),
    Classification.UNSUBSCRIBE: ActionDecision(RecommendedAction.SUPPRESS_CONTACT, False),
    Classification.BOUNCE: ActionDecision(RecommendedAction.MARK_EMAIL_INVALID, False),
    Classification.UNKNOWN: ActionDecision(RecommendedAction.MANUAL_TRIAGE, True),
}


def decide_action(classification: Classification) -> ActionDecision:
    return ACTION_MAP[classification]
