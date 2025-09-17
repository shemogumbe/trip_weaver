from langgraph.graph import StateGraph, END
from app.graph.state import RunState
from app.graph.agents import flight_agent, stay_agent, activities_agent, budget_agent, itinerary_synthesizer

def build_graph():
    g = StateGraph(RunState)

    g.add_node("flight_agent", flight_agent)
    g.add_node("stay_agent", stay_agent)
    g.add_node("activities_agent", activities_agent)
    g.add_node("budget_agent", budget_agent)
    g.add_node("itinerary_synthesizer", itinerary_synthesizer)

    g.set_entry_point("flight_agent")
    g.add_edge("flight_agent", "stay_agent")
    g.add_edge("stay_agent", "activities_agent")
    g.add_edge("activities_agent", "budget_agent")
    g.add_edge("budget_agent", "itinerary_synthesizer")
    g.add_edge("itinerary_synthesizer", END)

    return g.compile()
