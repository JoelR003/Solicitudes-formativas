def brief_result(request: dict) -> dict:
    """Keep the terminal demo focused on the decision rather than raw extraction."""

    workers = request["worker_list"]
    return {
        "solicitud_id": request["solicitud_id"],
        "inputs": {
            "pdf": request["pdf"]["file"],
            "worker_list": workers["file"],
            "worker_count": len(workers["workers"]),
        },
        "validations": request["validations"],
        "decision": request["decision"],
        "response_draft": request["response_draft"],
        "registration": request.get("registration"),
    }
