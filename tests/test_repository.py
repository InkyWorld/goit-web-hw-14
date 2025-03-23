import calendar
from datetime import date, datetime, timedelta
import json
import pytest
from unittest.mock import AsyncMock, Mock, patch

from app.repository.contacts import (
    create_contacts,
    delete_contact,
    get_all_contacts_from_cache,
    get_contact,
    get_contact_from_cache,
    get_contacts,
    get_upcoming_birthdays,
    search_by,
    set_contact_to_cache,
    update_contacts,
)
from app.repository.users import (
    confirmed_email,
    create_user,
    get_user_by_email,
    update_avatar_url,
    update_token,
)
from app.models.models import Contact
from app.schemas.contact import ContactSchema
from app.schemas.user import UserCreationSchema
from conftest import TestFixtures


@pytest.mark.asyncio
class TestUser(TestFixtures):
    async def test_get_user_by_email_existing(self, setup_user, setup_db):
        email = "email@example.com"
        mock_scalar = Mock(return_value=setup_user)
        setup_db.execute.return_value.scalar_one_or_none = mock_scalar

        user = await get_user_by_email(email=email, db=setup_db)

        assert user == setup_user
        setup_db.execute.assert_called_once()
        mock_scalar.assert_called_once()

    async def test_get_user_by_email_not_found(self, setup_db):
        email = "invalid_email@example.com"
        mock_scalar = Mock(return_value=None)
        setup_db.execute.return_value.scalar_one_or_none = mock_scalar
        user = await get_user_by_email(email=email, db=setup_db)
        assert user == None
        setup_db.execute.assert_called_once()
        mock_scalar.assert_called_once()

    async def test_create_user(self, setup_db):
        body = UserCreationSchema(
            username="username", email="email@example.com", password="password"
        )
        created_user = await create_user(body=body, db=setup_db)

        assert created_user.username == "username"
        assert created_user.email == "email@example.com"
        setup_db.add.assert_called_once_with(created_user)
        setup_db.commit.assert_called_once()
        setup_db.refresh.assert_called_once_with(created_user)

    async def test_update_token(self, setup_user, setup_db):
        new_token = "new_refresh_token_value"
        await update_token(setup_user, new_token, setup_db)
        assert setup_user.refresh_token == new_token
        setup_db.commit.assert_called_once()

    @patch("app.repository.users.get_user_by_email")
    async def test_confirmed_email(self, mock_get_user_by_email, setup_user, setup_db):
        mock_get_user_by_email.return_value = setup_user
        user = await confirmed_email("email@example.com", setup_db)
        assert setup_user.verified is True
        setup_db.commit.assert_called_once()
        assert user is setup_user
        mock_get_user_by_email.assert_called_once_with("email@example.com", setup_db)

    @patch("app.repository.users.get_user_by_email")
    async def test_confirmed_email_user_not_found(
        self, get_user_by_email_mock, setup_db
    ):
        get_user_by_email_mock.return_value = None
        email = "nonexistinguser@example.com"
        user = await confirmed_email(email, setup_db)
        assert user is None
        setup_db.commit.assert_not_called()

    @patch("app.repository.users.get_user_by_email")
    async def test_update_avatar_url(
        self, mock_get_user_by_email, setup_user, setup_db
    ):
        new_url = "https://example.com/image_example"
        setup_user.avatar = "old_url"
        mock_get_user_by_email.return_value = setup_user
        user = await update_avatar_url("email@example.com", new_url, setup_db)
        assert user.avatar == new_url
        setup_db.commit.assert_called_once()
        mock_get_user_by_email.assert_called_once_with("email@example.com", setup_db)


@pytest.mark.asyncio
class TestContact(TestFixtures):
    async def test_get_contacts(self, setup_db, setup_user, setup_contacts):
        limit = 3
        offset = 0
        mock_execute = Mock()
        mock_execute.scalars.return_value.all.return_value = setup_contacts

        # Set the return value of the db.execute to this mock
        setup_db.execute.return_value = mock_execute

        # Call the function to test
        result = await get_contacts(
            user=setup_user, limit=limit, offset=offset, db=setup_db
        )

        # Assertions
        assert result == setup_contacts
        setup_db.execute.assert_called_once()

    async def test_get_contact(self, setup_db, setup_user, setup_contacts):
        mock_execute = Mock()
        mock_execute.scalar_one_or_none.return_value = setup_contacts[0]
        setup_db.execute.return_value = mock_execute

        # Call the function to test
        result = await get_contact(user=setup_user, contact_id=1, db=setup_db)

        # Assertions
        assert result == setup_contacts[0]
        setup_db.execute.assert_called_once()
        mock_execute.scalar_one_or_none.assert_called_once()

    async def test_create_contacts(self, setup_db, setup_user):
        body = ContactSchema(
            name="John",
            surname="Doe",
            email="johndoe@example.com",
            phone="+38 050 123 45 67",
            date_of_birth="1990-05-14",
            additional_info="Likes hiking and photography.",
        )
        contact = await create_contacts(user=setup_user, body=body, db=setup_db)
        setup_db.add.assert_called_once()
        setup_db.commit.assert_called_once()
        setup_db.refresh.assert_called_once_with(contact)

        assert contact.phone == "+38 050 123 45 67"
        assert contact.date_of_birth == datetime(1990, 5, 14).date()
        assert contact.user_id == setup_user.id

    async def test_update_contacts_existing(self, setup_db, setup_user, setup_contacts):
        mock_execute = Mock()
        mock_execute.scalar_one_or_none.return_value = setup_contacts[0]
        setup_db.execute.return_value = mock_execute

        body = ContactSchema(
            name="name",
            surname="surname",
            email="email@example.com",
            phone="+380961234567",
            date_of_birth="1910-10-10",
            additional_info="example",
            completed=True,
        )

        await update_contacts(setup_user, 1, body, setup_db)
        setup_db.commit.assert_called_once()
        assert setup_contacts[0].additional_info == body.additional_info

    async def test_update_contacts_not_found(
        self, setup_db, setup_user, setup_contacts
    ):
        mock_execute = Mock()
        mock_execute.scalar_one_or_none.return_value = None
        setup_db.execute.return_value = mock_execute

        body = ContactSchema(
            name="name",
            surname="surname",
            email="email@example.com",
            phone="+380961234567",
            date_of_birth="1910-10-10",
            additional_info="example",
            completed=True,
        )
        await update_contacts(setup_user, 1, body, setup_db)
        setup_db.commit.assert_not_called()
        assert setup_contacts[0].additional_info == "Friend from work"

    async def test_delete_contacts_existing(self, setup_db, setup_user, setup_contacts):
        scalar_mock = Mock()
        scalar_mock.scalar_one_or_none.return_value = setup_contacts[0]
        setup_db.execute.return_value = scalar_mock
        result = await delete_contact(setup_user, 1, setup_db)
        setup_db.commit.assert_called_once()
        assert result == setup_contacts[0]
        scalar_mock.scalar_one_or_none.assert_called_once()

    async def test_delete_contacts_not_found(
        self, setup_db, setup_user, setup_contacts
    ):
        scalar_mock = Mock()
        scalar_mock.scalar_one_or_none.return_value = None
        setup_db.execute.return_value = scalar_mock
        result = await delete_contact(setup_user, 1, setup_db)
        setup_db.commit.assert_not_called()
        assert result == None
        scalar_mock.scalar_one_or_none.assert_called_once()

    async def test_search_by_with_filters(self, setup_db, setup_user, setup_contacts):
        scalar_mock = Mock()
        scalar_mock.scalars.return_value.all.return_value = [setup_contacts[0]]

        setup_db.execute.return_value = scalar_mock

        result = await search_by(
            setup_user, setup_db, first_name="John", last_name="Doe", email="john.doe@example.com"
        )

        setup_db.execute.assert_called_once()
        assert result[0] == setup_contacts[0]
        assert result[0].name == "John"

    async def test_search_by_no_filters(self, setup_db, setup_user, setup_contacts):
        scalar_mock = Mock()
        scalar_mock.scalars.return_value.all.return_value = setup_contacts

        setup_db.execute.return_value = scalar_mock

        result = await search_by(
            setup_user, setup_db, first_name=None, last_name=None, email=None
        )

        setup_db.execute.assert_called_once()
        assert len(result) == len(setup_contacts)

    async def test_get_upcoming_birthdays_with_matches(
        self, setup_db, setup_user, setup_contacts
    ):
        today = date.today()
        next_week = today + timedelta(days=7)

        setup_contacts[0].date_of_birth = today.strftime("%Y-%m-%d")
        setup_contacts[1].date_of_birth = (today + timedelta(days=5)).strftime(
            "%Y-%m-%d"
        )

        scalar_mock = Mock()
        scalar_mock.scalars.return_value.all.return_value = [
            setup_contacts[0],
            setup_contacts[1],
        ]
        setup_db.execute.return_value = scalar_mock

        result = await get_upcoming_birthdays(setup_user, setup_db)

        setup_db.execute.assert_called_once()
        assert len(result) == 2
        assert all(
            contact.date_of_birth
            in [
                today.strftime("%Y-%m-%d"),
                (today + timedelta(days=5)).strftime("%Y-%m-%d"),
            ]
            for contact in result
        )

    async def test_get_upcoming_birthdays_no_matches(
        self, setup_db, setup_user, setup_contacts
    ):
        today = date.today()

        setup_contacts[0].date_of_birth = (today + timedelta(days=10)).strftime(
            "%Y-%m-%d"
        )
        setup_contacts[1].date_of_birth = (today - timedelta(days=5)).strftime(
            "%Y-%m-%d"
        )

        scalar_mock = Mock()
        scalar_mock.scalars.return_value.all.return_value = []
        setup_db.execute.return_value = scalar_mock

        result = await get_upcoming_birthdays(setup_user, setup_db)

        setup_db.execute.assert_called_once()
        assert result == []

    async def test_get_upcoming_birthdays_month_change(self, setup_db, setup_user, setup_contacts):
        today = date.today()
        last_day_of_month = calendar.monthrange(today.year, today.month)[1]

        # Handle the case where next_week crosses into the next month
        if today.day + 7 > last_day_of_month:
            next_month_day = (
                today + timedelta(days=7 - (last_day_of_month - today.day))
            ).day
            next_month = today.month + 1 if today.month < 12 else 1

            # Set up contacts' birthdays
            setup_contacts[0].date_of_birth = (
                f"{today.year}-{today.month:02d}-{last_day_of_month:02d}"
            )
            setup_contacts[1].date_of_birth = (
                f"{today.year}-{next_month:02d}-{next_month_day:02d}"
            )
            setup_contacts[1].date_of_birth = (
                f"{today.year}-{next_month:02d}-{next_month_day:02d}"
            )
            scalar_mock = Mock()
            scalar_mock.scalars.return_value.all.return_value = [
                setup_contacts[0],
                setup_contacts[1],
            ]
            setup_db.execute.return_value = scalar_mock

            result = await get_upcoming_birthdays(setup_user, setup_db)

            setup_db.execute.assert_called_once()
            assert len(result) == 2
            assert all(
                contact.date_of_birth
                in [setup_contacts[0].date_of_birth, setup_contacts[1].date_of_birth]
                for contact in result
            )

    async def test_get_all_contacts_from_cache_with_no_data(self):
        cache_key = "contacts:user_123"
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        result = await get_all_contacts_from_cache(cache_key, mock_redis)
        result == []
        mock_redis.get.assert_called_once_with(cache_key)

    async def test_get_all_contacts_from_cache_with_data(self):
        cache_key = "contacts:user_123"
        mock_redis = AsyncMock()

        # Fake cached contact data
        contacts_data = [
            {"id": 1, "name": "John Doe", "email": "john@example.com"},
            {"id": 2, "name": "Jane Smith", "email": "jane@example.com"},
        ]

        mock_redis.get.return_value = json.dumps(contacts_data)
        result = await get_all_contacts_from_cache(cache_key, mock_redis)
        assert len(result) == 2
        assert isinstance(result[0], Contact)
        assert result[0].name == "John Doe"
        assert result[1].email == "jane@example.com"
        mock_redis.get.assert_called_once_with(cache_key)

    async def test_get_all_contacts_from_cache_corrupted_data(self):
        cache_key = "contacts:user_123"
        mock_redis = AsyncMock()

        mock_redis.get.return_value = "invalid_json"

        with pytest.raises(json.JSONDecodeError):
            await get_all_contacts_from_cache(cache_key, mock_redis)

    async def test_get_contact_from_cache(self):
        cache_key = "contacts:user_123"
        contact_data = {
            "id": 1,
            "name": "John",
            "surname": "Doe",
            "email": "john@example.com",
            "phone": "380963487456",
            "date_of_birth": "1990-05-10",
            "additional_info": "Some additional info about John.",
            "user_id": 1,
        }

        contact_data_dumps = json.dumps(contact_data)
        mock_redis = AsyncMock()
        with patch.object(
            mock_redis, "get", AsyncMock(return_value=contact_data_dumps)
        ):
            result = await get_contact_from_cache(cache_key, mock_redis)

            assert isinstance(result, Contact)
            assert result.name == "John"
            assert result.email == "john@example.com"
            mock_redis.get.assert_called_once_with(cache_key)

    async def test_get_contact_from_cache_not_found(self):
        redis_client = AsyncMock()

        contact_cache_key = "contact:2"
        redis_client.get.return_value = None

        contact = await get_contact_from_cache(contact_cache_key, redis_client)

        # Assertions
        redis_client.get.assert_called_once_with(contact_cache_key)
        with patch("json.loads") as json_loads_mock:
            json_loads_mock.assert_not_called()
        assert contact is None

    async def test_set_to_cache(self):
        contacts = [
            Contact(
                id=1,
                name="John",
                surname="Doe",
                email="john.doe@example.com",
                phone="380963487456",
                date_of_birth=date.fromisoformat("1990-05-10"),
                additional_info="Some info",
            ),
            Contact(
                id=2,
                name="Jane",
                surname="Smith",
                email="jane.smith@example.com",
                phone="380963487457",
                date_of_birth=date.fromisoformat("1992-07-25"),
                additional_info="More info",
            ),
        ]
        mock_redis = AsyncMock()

        with patch.object(mock_redis, "setex", AsyncMock()) as mock_setex:
            key = "contacts:user_123"

            await set_contact_to_cache(key, contacts, mock_redis)

            mock_setex.assert_called_once_with(
                key, 60, json.dumps([contact.__getstate__() for contact in contacts])
            )
