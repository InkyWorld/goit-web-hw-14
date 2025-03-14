import calendar
from datetime import date, datetime, timedelta
import json
from typing import Optional
from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy import and_, extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.redis import get_redis
from app.models.models import Contact, User
from app.schemas.contact import ContactSchema, ContactUpdateSchema


async def get_contacts(user: User, limit: int, offset: int, db: AsyncSession):
    """
    Retrieve a list of contacts for a given user.

    This function fetches contacts from the database, applying the provided 
    limit and offset for pagination.

    Args:
        user (User): The user whose contacts are being retrieved.
        limit (int): The maximum number of contacts to retrieve.
        offset (int): The starting point for pagination (number of contacts to skip).
        db (AsyncSession): The database session to execute the query.

    Returns:
        list[Contact]: A list of Contact objects belonging to the user.
    """
    stmt = select(Contact).where(Contact.user == user).offset(offset).limit(limit)
    contacts = await db.execute(stmt)
    return contacts.scalars().all()


async def get_contact(user: User, contact_id: int, db: AsyncSession):
    """
    Retrieve a specific contact for a given user by contact ID.

    Args:
        user (User): The user whose contact is being retrieved.
        contact_id (int): The ID of the contact to retrieve.
        db (AsyncSession): The database session to execute the query.

    Returns:
        Contact | None: The contact object if found, or None if no such contact exists.
    """
    stmt = select(Contact).where(Contact.user == user).filter_by(id=contact_id)
    contact = await db.execute(stmt)
    return contact.scalar_one_or_none()


async def create_contacts(user: User, body: ContactSchema, db: AsyncSession):
    """
    Create a new contact for a given user.

    Args:
        user (User): The user for whom the contact is being created.
        body (ContactSchema): The data for the new contact, including name, email, phone, etc.
        db (AsyncSession): The database session used for the operation.

    Returns:
        Contact: The newly created contact object.
    """
    contact = Contact(**body.model_dump(exclude_unset=True))
    contact.date_of_birth = datetime.strptime(contact.date_of_birth, '%Y-%m-%d').date()
    contact.user_id = user.id
    db.add(contact)
    await db.commit()
    await db.refresh(contact)
    return contact



async def update_contacts(user: User, contact_id: int, body: ContactUpdateSchema, db: AsyncSession):
    """
    Update an existing contact for a given user.

    Args:
        user (User): The user whose contact is being updated.
        contact_id (int): The ID of the contact to update.
        body (ContactUpdateSchema): The new data for the contact.
        db (AsyncSession): The database session to execute the update.

    Returns:
        Contact | None: The updated contact object if found and updated, or None if the contact doesn't exist.
    """
    
    stmt = select(Contact).where(Contact.user == user).filter_by(id=contact_id)
    result = await db.execute(stmt)
    contact = result.scalar_one_or_none()
    if contact:
        contact.name = body.name
        contact.surname = body.surname
        contact.email = body.email
        contact.phone = body.phone
        contact.date_of_birth = body.date_of_birth
        contact.additional_info = body.additional_info
        await db.commit()
        await db.refresh(contact)
    return contact


async def delete_contact(user: User, contact_id: int, db: AsyncSession):
    """
    Delete a contact for a given user.

    Args:
        user (User): The user whose contact is being deleted.
        contact_id (int): The ID of the contact to delete.
        db (AsyncSession): The database session to execute the delete.

    Returns:
        Contact | None: The deleted contact object if found and deleted, or None if the contact doesn't exist.
    """
    stmt = select(Contact).where(Contact.user == user).filter_by(id=contact_id)
    contact = await db.execute(stmt)
    contact = contact.scalar_one_or_none()
    if contact:
        await db.delete(contact)
        await db.commit()
    return contact

async def search_by(user: User, db: AsyncSession,
        first_name: Optional[str],
        last_name: Optional[str],
        email: Optional[str]):
    """
    Search for contacts by first name, last name, or email.

    Args:
        user (User): The user whose contacts are being searched.
        db (AsyncSession): The database session to execute the search.
        first_name (Optional[str], optional): The first name to search for. Defaults to None.
        last_name (Optional[str], optional): The last name to search for. Defaults to None.
        email (Optional[str], optional): The email to search for. Defaults to None.

    Returns:
        list[Contact]: A list of contacts matching the search criteria.
    """

    filters = []

    if first_name:
        filters.append(Contact.name.ilike(f"%{first_name}%"))
    if last_name:
        filters.append(Contact.surname.ilike(f"%{last_name}%"))
    if email:
        filters.append(Contact.email.ilike(f"%{email}%"))

    stmt = select(Contact).where(Contact.user == user).where(and_(*filters)) if filters else select(Contact)
    contacts = await db.execute(stmt)
    return contacts.scalars().all()


async def get_upcoming_birthdays(user: User, db: AsyncSession):
    """
    Retrieve contacts with upcoming birthdays within the next 7 days.

    Args:
        user (User): The user whose contacts are being checked for upcoming birthdays.
        db (AsyncSession): The database session to execute the query.

    Returns:
        list[Contact]: A list of contacts whose birthdays are within the next 7 days.
    """
    today = date.today()
    next_week = today + timedelta(days=7)
    last_day_of_month = calendar.monthrange(today.year, today.month)[1]
    if today.day < next_week.day:
        query = (
            (extract('month', Contact.date_of_birth) == today.month) &
            (extract('day', Contact.date_of_birth) >= today.day) &
            (extract('day', Contact.date_of_birth) <= next_week.day)
        )
    else:
        query = (
            ((extract('month', Contact.date_of_birth) == today.month) &
            (extract('day', Contact.date_of_birth) <= last_day_of_month) &
            (extract('day', Contact.date_of_birth) >= today.day)) |
            ((extract('month', Contact.date_of_birth) == next_week.month) &
            (extract('day', Contact.date_of_birth) <= next_week.day))  
        )

    stmt = select(Contact).where(Contact.user == user).where(query)
    result = await db.execute(stmt)
    contacts = result.scalars().all()
    return contacts

async def get_all_contacts_from_cache(cache_key: str, redis_client: Redis):
    """
    Retrieve all contacts from Redis cache.

    Args:
        cache_key (str): The key under which contacts are cached.
        redis_client (Redis): The Redis client instance to query the cache.

    Returns:
        list[Contact]: A list of contacts retrieved from the cache, or an empty list if no data is cached.
    """
    cached_data = await redis_client.get(cache_key)
    if cached_data:
        data = json.loads(cached_data)
        contacts = []
        for item in data:
            contact = Contact()  
            contact.__setstate__(item)
            contacts.append(contact)
        return contacts
    return []

async def get_contact_from_cache(contact_cache_key: str, redis_client: Redis):
    """
    Retrieve a specific contact from Redis cache.

    Args:
        contact_cache_key (str): The key under which the contact is cached.
        redis_client (Redis): The Redis client instance to query the cache.

    Returns:
        Contact | None: The contact object if found in the cache, or None if no data is cached.
    """
    cached_data = await redis_client.get(contact_cache_key)
    if cached_data:
        data = json.loads(cached_data)
        contact = Contact()
        contact.__setstate__(data)
        return contact
    return None

async def set_to_cache(key: str, value: dict, redis_client: Redis, ttl: int = 60, ):
    """
    Store data in Redis cache.

    Args:
        key (str): The cache key under which the data will be stored.
        value (dict): The data to be cached.
        redis_client (Redis): The Redis client instance used to interact with the cache.
        ttl (int, optional): The time-to-live (TTL) for the cached data, in seconds. Defaults to 60.

    Returns:
        None: This function does not return any value.
    """
    await redis_client.setex(key, ttl, json.dumps(value))