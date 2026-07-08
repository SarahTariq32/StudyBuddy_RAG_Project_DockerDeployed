from fastapi import APIRouter, Request

router = APIRouter(prefix="/ops", tags=["ops"])


@router.get("/dashboard")
def dashboard(request: Request, hours: int = 24, limit: int = 100):
    ops = getattr(request.app.state, "ops", None)
    if ops is None:
        return {
            "enabled": False,
            "project": None,
            "metrics": {},
            "charts": {},
            "recent_requests": [],
        }
    return ops.get_dashboard_data(hours=hours, limit=limit)


@router.get("/traces")
def traces(request: Request, hours: int = 24, limit: int = 30):
    ops = getattr(request.app.state, "ops", None)
    if ops is None:
        return {
            "enabled": False,
            "project": None,
            "count": 0,
            "traces": [],
        }
    return ops.get_traces(hours=hours, limit=limit)


@router.get("/traces/{trace_id}")
def trace_detail(trace_id: str, request: Request):
    ops = getattr(request.app.state, "ops", None)
    if ops is None:
        return {
            "enabled": False,
            "project": None,
            "trace": None,
        }
    return ops.get_trace(trace_id)
