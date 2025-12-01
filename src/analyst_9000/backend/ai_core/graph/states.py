from typing import TypedDict, Annotated, List, Optional
from langchain_core.messages import BaseMessage
import operator



from typing import TypedDict, List, Optional

# Define a structure for a single attempt
class Attempt(TypedDict):
    sql: str
    error: str

class AgentState(TypedDict):
    """
    The central state object for the Data Analysis Agent.
    """

    messages: Annotated[List[BaseMessage], operator.add]
    #Stores the full audit trail of failures
    attempt_history: List[Attempt]
    n_iterations: int = 0