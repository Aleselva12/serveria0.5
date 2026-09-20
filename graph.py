import os
from dotenv import load_dotenv

from llm_factory import ChatGroq
from langchain_core.messages import SystemMessage, AIMessage
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# Import the tools we wrapped in tools.py
from tools import supervisor_tools
from prompt import SUPERVISOR_PROMPT

# Load environment variables
load_dotenv()

# Initialize the local Ollama LLM
llm = ChatGroq(
    model=os.getenv("OLLAMA_MODEL", "gpt-oss:20b"),
    temperature=0.0
)

# Bind the supervisor tools to the LLM
model_with_tools = llm.bind_tools(supervisor_tools)

def call_model(state: MessagesState):
    """
    Calls the supervisor model with the local-first system prompt.
    """
    messages = list(state.get("messages", []))
    messages_for_llm = [SystemMessage(content=SUPERVISOR_PROMPT)] + messages

    response = model_with_tools.invoke(messages_for_llm)
    tool_calls = getattr(response, "tool_calls", None) or []

    # Prevent the model from dispatching multiple tool calls in a single response.
    # LangGraph will execute only the first one, then loop back and let the model decide.
    if len(tool_calls) > 1:
        response = AIMessage(
            content=getattr(response, "content", ""),
            additional_kwargs=getattr(response, "additional_kwargs", {}),
            response_metadata=getattr(response, "response_metadata", {}),
            tool_calls=[tool_calls[0]],
            id=getattr(response, "id", None),
        )

    return {"messages": [response]}

def should_continue(state: MessagesState):
    """
    Conditional edge: route to the tool node only when the latest message requests a tool call.
    """
    messages = list(state.get("messages", []))
    last_message = messages[-1] if messages else None

    if last_message is not None:
        tool_calls = getattr(last_message, "tool_calls", None) or []
        if len(tool_calls) > 0:
            return "tools"

    return END

# Set up the ToolNode with our supervisor tools
tool_node = ToolNode(supervisor_tools)

# Define the StateGraph using MessagesState (which tracks conversation history)
workflow = StateGraph(MessagesState)

# Add our two nodes: the LLM (agent) and the tools
workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

# Set the entry point to always start at the agent
workflow.add_edge(START, "agent")

# Add the conditional edges from the agent
workflow.add_conditional_edges(
    "agent",
    should_continue,
    {
        "tools": "tools",
        END: END
    }
)

# Once the tools finish running, always return to the agent to process the tool outputs
workflow.add_edge("tools", "agent")

# Set up a checkpointer to persist conversation memory
memory = MemorySaver()

# Compile the graph
graph = workflow.compile(checkpointer=memory)
