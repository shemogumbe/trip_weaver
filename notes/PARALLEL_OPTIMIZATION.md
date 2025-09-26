Deprecated: The async parallel pipeline is now the default and consolidated in code.

- Unified agents live in `backend/app/graph/agents.py`
- Orchestration wrapper lives in `backend/app/graph/async_processor.py`
- Legacy LangGraph builder is shimmed in `backend/app/graph/build_graph.py`

See inline comments and `backend/README_API.md` for up-to-date usage and architecture.