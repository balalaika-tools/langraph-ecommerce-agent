from typing import List, Optional, AsyncIterator
from langgraph.graph import StateGraph, START, END
from langsmith import traceable
from langchain_core.messages import AnyMessage, HumanMessage, AIMessage
from analyst_9000.backend.ai_core.graph.states import AgentState
from analyst_9000.backend.core.constants import ANALYST_LOGGER
from analyst_9000.backend.core.logger import get_logger
from analyst_9000.backend.ai_core.graph.nodes import (
    router_node,
    qa_node,
    sql_generator_node,
    response_synthesizer_node,
    error_handler_node,
    route_by_intent,
    should_retry_sql,
)

logger = get_logger(ANALYST_LOGGER)


class AnalystGraph:
    """
    Encapsulates the Graph construction and execution logic for Analyst-9000.
    
    Flow:
    1. Router: Classify intent and reform query
    2. If qa_bot → QA Node (streaming)
    3. If sql_agent → SQL Generator → (retry loop) → Response Synthesizer (streaming)
    """

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """Builds and returns the compiled StateGraph for Analyst-9000."""
        graph = StateGraph(AgentState)

        # --- Add Nodes ---
        graph.add_node("router", router_node)
        graph.add_node("qa_node", qa_node)
        graph.add_node("sql_generator_node", sql_generator_node)
        graph.add_node("response_synthesizer_node", response_synthesizer_node)
        graph.add_node("error_handler_node", error_handler_node)

        # --- Add Edges ---
        
        # Start → Router
        graph.add_edge(START, "router")

        # Router → Conditional routing based on intent
        graph.add_conditional_edges(
            "router",
            route_by_intent,
            {
                "qa_node": "qa_node",
                "sql_generator_node": "sql_generator_node",
            },
        )

        # QA Node → End (final response)
        graph.add_edge("qa_node", END)

        # SQL Generator → Conditional (retry, synthesize, or error)
        graph.add_conditional_edges(
            "sql_generator_node",
            should_retry_sql,
            {
                "sql_generator_node": "sql_generator_node",
                "response_synthesizer_node": "response_synthesizer_node",
                "error_handler_node": "error_handler_node",
            },
        )

        # Response Synthesizer → End
        graph.add_edge("response_synthesizer_node", END)

        # Error Handler → End
        graph.add_edge("error_handler_node", END)

        return graph.compile()

    def create_initial_state(
        self,
        query: str,
        session_id: str,
        messages: List[AnyMessage],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        reasoning_budget: Optional[str] = None,
    ) -> AgentState:
        """Creates the initial state for graph execution."""
        return AgentState(
            session_id=session_id,
            query=query,
            reformed_query=None,
            messages=messages,
            intent=None,
            title=None,
            response=None,
            attempt_history=[],
            n_iterations=0,
            sql_result=None,
            generated_sql=None,
            model_name=model_name,
            temperature=temperature,
            reasoning_budget=reasoning_budget,
        )


    @traceable(name="AnalystGraphStreamer", run_type="chain")
    async def stream(
        self,
        query: str,
        session_id: str,
        messages: List[AnyMessage],
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        reasoning_budget: Optional[str] = None,
    ) -> AsyncIterator[dict]:
        """
        Stream the graph execution, yielding events as they occur.
        
        This method yields dictionaries with the following structure:
        - {"type": "router", "intent": ..., "title": ..., "reformed_query": ...}
        - {"type": "token", "content": ...} for streaming response tokens
        - {"type": "sql", "query": ..., "success": ..., "error": ...}
        - {"type": "final", "response": ..., "title": ...}
        
        Args:
            query: The user's query
            session_id: The session ID  
            messages: The conversation messages
            model_name: Optional model name override
            temperature: Optional temperature override
            reasoning_budget: Optional reasoning budget
            
        Yields:
            Event dictionaries as the graph executes
        """
        logger.info(
            f"🚀 Starting AnalystGraph streaming execution",
            extra={
                "component": "AnalystGraph",
                "session_id": session_id,
                "model_name": model_name,
                "event": "graph_stream_start",
            }
        )

        initial_state = self.create_initial_state(
            query=query,
            session_id=session_id,
            messages=messages,
            model_name=model_name,
            temperature=temperature,
            reasoning_budget=reasoning_budget,
        )

        title = None
        final_response = None
        
        try:
            # Use astream_events for granular streaming
            async for event in self.graph.astream(initial_state, stream_mode="updates"):
                for node_name, node_output in event.items():
                    if node_name == "router":
                        title = node_output.get("title")
                        yield {
                            "type": "router",
                            "intent": node_output.get("intent"),
                            "title": title,
                            "reformed_query": node_output.get("reformed_query"),
                        }
                    
                    elif node_name in ("qa_node", "response_synthesizer_node", "error_handler_node"):
                        # These are the final response nodes
                        response = node_output.get("response", "")
                        final_response = response
                        
                        # Stream the response character by character for better UX
                        for char in response:
                            yield {"type": "token", "content": char}
                    
                    elif node_name == "sql_generator_node":
                        sql = node_output.get("generated_sql")
                        sql_result = node_output.get("sql_result")
                        attempt_history = node_output.get("attempt_history", [])
                        
                        yield {
                            "type": "sql",
                            "query": sql,
                            "success": sql_result is not None,
                            "error": attempt_history[-1].get("error") if attempt_history else None,
                        }

            # Yield final event
            yield {
                "type": "final",
                "response": final_response,
                "title": title,
            }

            logger.info(
                "🏁 Graph streaming completed successfully",
                extra={
                    "component": "AnalystGraph",
                    "session_id": session_id,
                    "event": "graph_stream_end",
                }
            )

        except Exception as e:
            logger.error(
                "❌ AnalystGraph streaming failed",
                extra={
                    "component": "AnalystGraph",
                    "session_id": session_id,
                    "error": str(e),
                    "event": "graph_stream_error",
                },
                exc_info=True,
            )
            yield {
                "type": "error",
                "error": str(e),
            }
            raise

