from langgraph.graph import StateGraph, END
from app.graph.state import RunState
from app.graph.agents import destination_research, flight_agent, stay_agent, budget_agent, itinerary_synthesizer, optimized_activities_agent_with_openai

def build_graph():
    g = StateGraph(RunState)

    g.add_node("destination_research", destination_research)
    g.add_node("flight_agent", flight_agent)
    g.add_node("stay_agent", stay_agent)
    g.add_node("activities_agent", optimized_activities_agent_with_openai)  # Uses OpenAI instead of 22 Tavily calls
    g.add_node("budget_agent", budget_agent)
    g.add_node("itinerary_synthesizer", itinerary_synthesizer)

    g.set_entry_point("destination_research")
    g.add_edge("destination_research", "flight_agent")
    g.add_edge("flight_agent", "stay_agent")
    g.add_edge("stay_agent", "activities_agent")
    g.add_edge("activities_agent", "budget_agent")
    g.add_edge("budget_agent", "itinerary_synthesizer")
    g.add_edge("itinerary_synthesizer", END)

    return g.compile()
