from fastapi import APIRouter, Depends
from langchain_core.messages import HumanMessage

from app.dependencies import require_roles
from app.graphs.role_chatbot import build_role_chat_graph
from app.models.user import User
from app.schemas.chat import CandidateChatRequest, CandidateChatResponse


router = APIRouter(prefix="/chat", tags=["candidate assistant"])


@router.post("/assistant", response_model=CandidateChatResponse)
def role_scoped_chat(
    request: CandidateChatRequest,
    current_user: User = Depends(require_roles("candidate", "interviewer", "hiring_manager")),
):
    """Invoke a chatbot whose database tools are scoped to the authenticated role and user."""
    graph = build_role_chat_graph(current_user.role, current_user.id)
    result = graph.invoke({
        "role": current_user.role,
        "messages": [HumanMessage(content=request.message.strip())],
    })
    return CandidateChatResponse(reply=str(result["messages"][-1].content))


@router.post("/candidate", response_model=CandidateChatResponse)
def candidate_chat(
    request: CandidateChatRequest,
    current_user: User = Depends(require_roles("candidate")),
):
    graph = build_role_chat_graph(current_user.role, current_user.id)
    result = graph.invoke({"role": current_user.role,
                           "messages": [HumanMessage(content=request.message.strip())]})
    return CandidateChatResponse(reply=str(result["messages"][-1].content))
