from fastapi import APIRouter, Depends

from app.auth.rbac import require_roles
from app.database import query


router = APIRouter(prefix="/api/v2/admin", tags=["admin"])


@router.get("/users")
def users(user=Depends(require_roles("ADMIN"))):
    rows = query(
        """
        SELECT u.user_id, u.username, UPPER(r.role_name) AS role_name, u.employee_id, u.active
        FROM users u
        JOIN roles r ON r.role_id = u.role_id
        ORDER BY u.user_id DESC
        """
    )
    return {"success": True, "data": rows, "message": "OK", "errors": []}
