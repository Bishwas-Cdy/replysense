from app.models import InboundReply, ReplyAnalysis
from app.schemas import Classification

SUPPORTED = {
    Classification.INTERESTED,
    Classification.QUESTION,
    Classification.MEETING_REQUEST,
    Classification.NOT_NOW,
}


def build_suggested_reply(reply: InboundReply, analysis: ReplyAnalysis) -> tuple[str, str] | None:
    classification = Classification(analysis.classification)
    if classification not in SUPPORTED:
        return None
    subject = reply.subject or "Your reply"
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"
    bodies = {
        Classification.INTERESTED: (
            "Thanks for your interest. I'd be happy to share more context and discuss whether this "
            "could be useful for your team. What would be the best next step?"
        ),
        Classification.QUESTION: (
            "Thanks for the question. I want to make sure I give you an accurate answer, so I'll "
            "follow up shortly with the relevant details."
        ),
        Classification.MEETING_REQUEST: (
            "Thanks — I'd be glad to connect. I'll review the timing you mentioned and send a few "
            "options for you to confirm."
        ),
        Classification.NOT_NOW: (
            "Understood, and thanks for letting me know. I'll make a note of the timing you "
            "mentioned "
            "and check back then."
        ),
    }
    return subject, bodies[classification]
