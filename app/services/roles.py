from fastapi import Request, Depends, HTTPException, status

from app.models.models import Role, User
from app.services.auth import auth_service


class RoleAccess:
    """
    A class that checks if a user has the required role to access a resource.

    This class is used as a dependency in FastAPI routes to enforce role-based access control. 
    It checks whether the user has one of the allowed roles and raises a `HTTPException` with 
    a 403 Forbidden status if the user does not have the required role.

    Attributes:
        allowed_roles (list[Role]): A list of roles that are allowed to access the resource.

    Args:
        allowed_roles (list[Role]): A list of roles that are permitted to access the route or resource.

    Methods:
        __call__(request: Request, user: User): 
            Checks if the user's role is in the list of allowed roles and raises an exception if not.
    """

    def __init__(self, allowed_roles: list[Role]):
        """
        Initializes the RoleAccess object with the allowed roles.

        Args:
            allowed_roles (list[Role]): A list of roles allowed to access the resource.
        """
        self.allowed_roles = allowed_roles

    async def __call__(self, request: Request, user: User = Depends(auth_service.authenticate_user)):
        """
        Checks whether the authenticated user has an allowed role.

        This method is invoked as a dependency in FastAPI routes. If the user's role is not
        in the list of allowed roles, an HTTP 403 Forbidden error is raised.

        Args:
            request (Request): The HTTP request object.
            user (User, optional): The user object obtained from the authentication service. 
                                    Defaults to the user returned by `auth_service.authenticate_user`.

        Raises:
            HTTPException: If the user's role is not in the allowed roles list, an HTTP 403 error is raised.
        
        Example:
            ```python
            role_access = RoleAccess(allowed_roles=[Role.admin, Role.manager])
            await role_access(request, user)
            ```
        """
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="FORBIDDEN"
            )