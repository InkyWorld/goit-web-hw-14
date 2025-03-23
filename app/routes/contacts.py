from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status, Path, Query
from redis import Redis
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi_limiter.depends import RateLimiter

from app.database.db import get_db
from app.database.redis import get_redis
from app.repository import contacts as repositories_contacts
from app.schemas.contact import (
    ContactSchema,
    ContactResponseSchema,
    ContactUpdateSchema,
)
from app.routes.auth import auth_service

router_crud = APIRouter(prefix="/contacts", tags=["main crud contacts"])
router_additional = APIRouter(
    prefix="/contacts", tags=["contacts additional operations"]
)

@router_crud.get("/contact/",
    dependencies=[Depends(RateLimiter(times=3, seconds=20))], response_model=list[ContactResponseSchema])
async def get_contacts(
    limit: int = Query(10, ge=2, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user=Depends(auth_service.authenticate_user),
    redis_client: Redis = Depends(get_redis)
):
    """
    Get a list of contacts with optional pagination and caching.

    This endpoint retrieves a list of contacts for the authenticated user. If contacts are 
    already cached, they are returned from the cache. Otherwise, the contacts are fetched from 
    the database and stored in the cache for future use.

    Args:
        limit (int): The maximum number of contacts to return. Defaults to 10, with a minimum of 2 
                     and a maximum of 500.
        offset (int): The number of contacts to skip. Defaults to 0.
        db (AsyncSession): The database session to interact with the database.
        user (User): The authenticated user (automatically injected by `authenticate_user`).
        redis_client (Redis): The Redis client used for caching.

    Returns:
        list[ContactResponseSchema]: A list of contact records.
    """
    cache_key = f"contacts:limit={limit}_offset={offset}"
    cached_contacts = await repositories_contacts.get_all_contacts_from_cache(cache_key, redis_client)
    if cached_contacts:
        return cached_contacts
    contacts = await repositories_contacts.get_contacts(user, limit, offset, db)
    await repositories_contacts.set_contact_to_cache(cache_key, contacts, redis_client)
    return contacts


@router_additional.get("/search_by/",
    dependencies=[Depends(RateLimiter(times=3, seconds=20))], response_model=list[ContactResponseSchema])
async def search_by(
    db: AsyncSession = Depends(get_db),
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    email: Optional[str] = None,
    user=Depends(auth_service.authenticate_user),
):
    """
    Search contacts by first name, last name, or email.

    This endpoint allows searching for contacts based on first name, last name, or email.
    If no contact is found, a 404 error is returned.

    Args:
        db (AsyncSession): The database session to interact with the database.
        first_name (Optional[str]): The first name of the contact to search for.
        last_name (Optional[str]): The last name of the contact to search for.
        email (Optional[str]): The email address of the contact to search for.
        user (User): The authenticated user (automatically injected by `authenticate_user`).

    Returns:
        list[ContactResponseSchema]: A list of contacts matching the search criteria.

    Raises:
        HTTPException: If no contacts are found, a 404 error is raised with a "NOT FOUND" message.
    """

    contact = await repositories_contacts.search_by(user, db, first_name, last_name, email)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")
    return contact


@router_crud.get("/contact/{contact_id}",
    dependencies=[Depends(RateLimiter(times=3, seconds=20))], response_model=ContactResponseSchema)
async def get_contact(
    contact_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
    user=Depends(auth_service.authenticate_user),
    redis_client: Redis = Depends(get_redis)
):
    """
    Get a specific contact by ID.

    This endpoint retrieves a contact by its unique ID. If the contact is cached, it is returned 
    from the cache. Otherwise, the contact is fetched from the database and stored in the cache 
    for future use.

    Args:
        contact_id (int): The ID of the contact to retrieve.
        db (AsyncSession): The database session to interact with the database.
        user (User): The authenticated user (automatically injected by `authenticate_user`).
        redis_client (Redis): The Redis client used for caching.

    Returns:
        ContactResponseSchema: The contact with the given ID.

    Raises:
        HTTPException: If the contact is not found, a 404 error is raised with a "NOT FOUND" message.
    """
    cache_key = f"contact:pk={contact_id}"
    cached_contacts = await repositories_contacts.get_contact_from_cache(cache_key, redis_client)
    if cached_contacts:
        return cached_contacts
    contact = await repositories_contacts.get_contact(user, contact_id, db)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")
    await repositories_contacts.set_contact_to_cache(cache_key, contact, redis_client)
    return contact


@router_crud.post(
    "/contact/",
    response_model=ContactResponseSchema,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RateLimiter(times=3, seconds=20))]
)
async def create_contact(
    body: ContactSchema,
    db: AsyncSession = Depends(get_db),
    user=Depends(auth_service.authenticate_user),
):
    """
    Create a new contact.

    This endpoint allows creating a new contact for the authenticated user.

    Args:
        body (ContactSchema): The data to create the contact, provided in the request body.
        db (AsyncSession): The database session to interact with the database.
        user (User): The authenticated user (automatically injected by `authenticate_user`).

    Returns:
        ContactResponseSchema: The newly created contact.
    """
    contact = await repositories_contacts.create_contacts(user, body, db)

    return contact


@router_crud.put("/contact/{contact_id}",
    dependencies=[Depends(RateLimiter(times=3, seconds=20))])
async def update_contact(
    body: ContactUpdateSchema,
    contact_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
    user=Depends(auth_service.authenticate_user),
):
    """
    Update an existing contact.

    This endpoint allows updating the details of an existing contact for the authenticated user.

    Args:
        body (ContactUpdateSchema): The updated contact data.
        contact_id (int): The ID of the contact to update.
        db (AsyncSession): The database session to interact with the database.
        user (User): The authenticated user (automatically injected by `authenticate_user`).

    Returns:
        ContactResponseSchema: The updated contact.

    Raises:
        HTTPException: If the contact is not found, a 404 error is raised with a "NOT FOUND" message.
    """
    contact = await repositories_contacts.update_contacts(user, contact_id, body, db)
    if contact is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="NOT FOUND")
    return contact


@router_crud.delete("/contact/{contact_id}",
    dependencies=[Depends(RateLimiter(times=3, seconds=20))], status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(
    contact_id: int = Path(ge=1),
    db: AsyncSession = Depends(get_db),
    user=Depends(auth_service.authenticate_user),
):
    """
    Delete a contact.

    This endpoint allows deleting an existing contact by its ID for the authenticated user.

    Args:
        contact_id (int): The ID of the contact to delete.
        db (AsyncSession): The database session to interact with the database.
        user (User): The authenticated user (automatically injected by `authenticate_user`).

    Returns:
        None: Returns a 204 No Content status code on successful deletion.
    """
    contact = await repositories_contacts.delete_contact(user, contact_id, db)
    return contact


@router_additional.get("/birthdays",
    dependencies=[Depends(RateLimiter(times=3, seconds=20))], response_model=list[ContactResponseSchema])
async def get_birthdays(
    db: AsyncSession = Depends(get_db), user=Depends(auth_service.authenticate_user),
    redis_client: Redis = Depends(get_redis)
):
    """
    Get upcoming birthdays of contacts.

    This endpoint retrieves a list of contacts with upcoming birthdays for the authenticated user.
    If the data is cached, it will be returned from the cache; otherwise, it is fetched from the database.

    Args:
        db (AsyncSession): The database session to interact with the database.
        user (User): The authenticated user (automatically injected by `authenticate_user`).
        redis_client (Redis): The Redis client used for caching.

    Returns:
        list[ContactResponseSchema]: A list of contacts with upcoming birthdays.

    Raises:
        HTTPException: If no upcoming birthdays are found, a 404 error is raised with the detail "No upcoming birthdays found".
    """
    cache_key = f"birthdays"
    cached_contacts = await repositories_contacts.get_all_contacts_from_cache(cache_key, redis_client)
    if cached_contacts:
        return cached_contacts
    contacts = await repositories_contacts.get_upcoming_birthdays(user, db)
    if not contacts:
        raise HTTPException(status_code=404, detail="No upcoming birthdays found")
    await repositories_contacts.set_contact_to_cache(cache_key, contacts, redis_client)
    return contacts
