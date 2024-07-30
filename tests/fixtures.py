import asyncio
import datetime
import itertools
from typing import List

import pytest
from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.date_manager import get_day_delta, get_today, get_tomorrow, get_yesterday
from app.repository import Repository
from app.services.accounts import AccountService
from app.services.scheduled_transactions import ScheduledTransactionService
from app.services.transactions import TransactionService
from app.services.users import UserService
from app.utils.dataclasses_utils import CreateUserData
from app.utils.enums import DatabaseFilterOperator, Frequency

# Reference: https://github.com/EduardSchwarzkopf/pecuny/issues/88
# pylint: disable=unused-argument


@pytest.fixture(name="common_user_data", scope="session")
def fixture_common_user_data():
    """
    Fixture for common user data used in tests.

    Returns:
        UserCreate: A UserCreate instance with common user data.
    """

    return schemas.UserCreate(
        email="user123@example.com",
        password="mypassword",
        displayname="user",
    )


@pytest.fixture(name="user_service", scope="session")
async def fixture_user_service(session):
    """
    Create a session-scoped user service fixture.

    Args:
        session: The session object.

    Returns:
        UserService: The user service fixture.

    """
    yield UserService()


@pytest.fixture(name="create_test_users", scope="session")
async def fixture_create_test_users(user_service: UserService):
    """
    Fixture that creates test users.

    Args:
        None

    Yields:
        None
    """

    password = "password123"
    create_user_list = [
        ["user00@pytest.de", password, "User00"],
        ["user01@pytest.de", password, "User01"],
        ["hello123@pytest.de", password, "LoginUser"],
    ]

    user_list = []
    for user in create_user_list:
        user_list.append(
            await user_service.create_user(
                CreateUserData(
                    email=user[0],
                    password=user[1],
                    displayname=user[2],
                    is_verified=True,
                ),
            )
        )

    yield user_list


@pytest.fixture(name="test_users")
async def fixture_test_user_list(create_test_users, repository: Repository):
    """
    Fixture for retrieving a list of test users.

    Args:
        create_test_users (fixture): Fixture to create test users.

    Yields:
        list[models.User]: A list of test users.
    """
    yield await repository.get_all(models.User)


@pytest.fixture(name="test_user")
async def fixture_test_user(create_test_users, repository: Repository):
    """
    Fixture for retrieving a test user.

    Args:
        create_test_users (fixture): Fixture to create test users.

    Yields:
        models.User: The test user.

    """
    user_list = await repository.filter_by(
        models.User, models.User.is_verified, True, DatabaseFilterOperator.EQUAL
    )

    yield user_list[0]


async def create_and_yield_user(
    user_service: UserService, user_data: schemas.UserCreate
):
    """
    Creates a user using the provided user data and yields the user object.

    Args:
        user_service: The UserService instance for user management.
        user_data: The UserCreate schema containing user data.

    Yields:
        User: The created user object.

    Raises:
        None
    """

    user = await user_service.create_user(user_data)
    yield user

    if user:
        await user_service.delete_self(user)


@pytest.fixture(name="active_user")
async def fixture_active_user(
    user_service: UserService, common_user_data: schemas.UserCreate
):
    """
    Fixture for providing an active user for testing.

    Args:
        user_service: The UserService instance for user management.
        common_user_data: The common user data for creating the active user.

    Yields:
        User: The active user object for testing.
    """

    common_user_data.is_active = True
    async for user in create_and_yield_user(user_service, common_user_data):
        yield user


@pytest.fixture(name="active_verified_user")
async def fixture_active_verified_user(
    user_service: UserService, common_user_data: schemas.UserCreate
):
    """
    Fixture for providing an active and verified user for testing.

    Args:
        user_service: The UserService instance for user management.
        common_user_data: The common user data for creating the active and verified user.

    Yields:
        User: The active and verified user object for testing.
    """

    common_user_data.is_verified = True
    common_user_data.is_active = True
    async for user in create_and_yield_user(user_service, common_user_data):
        yield user


@pytest.fixture(name="inactive_user")
async def fixture_inactive_user(
    user_service: UserService, common_user_data: schemas.UserCreate
):
    """
    Fixture for providing an inactive user for testing.

    Args:
        user_service: The UserService instance for user management.
        common_user_data: The common user data for creating the inactive user.

    Yields:
        User: The inactive user object for testing.
    """

    common_user_data.is_active = False
    async for user in create_and_yield_user(user_service, common_user_data):
        yield user


@pytest.fixture(name="create_test_accounts", scope="session")
async def fixture_create_test_accounts(
    session: AsyncSession, create_test_users: list[models.User]
):
    """
    Fixture that creates test accounts.

    Args:
        session (fixture): The session fixture.
        test_users (fixture): Fixture to get a test user.
        test_users (fixuter): Fixture to get a list of test users.

    Returns:
        list[Account]: A list of test accounts.
    """

    account_data_list: list[dict[str, str | int]] = [
        {
            "label": "account_00",
            "description": "description_00",
            "balance": 100,
        },
        {
            "label": "account_01",
            "description": "description_01",
            "balance": 200,
        },
    ]

    service = AccountService()

    create_task_list = []

    for user, account_data in itertools.product(create_test_users, account_data_list):
        task = service.create_account(
            user,
            schemas.Account(
                label=account_data["label"],
                description=account_data["description"],
                balance=account_data["balance"],
            ),
        )
        create_task_list.append(task)

    account_list = await asyncio.gather(*create_task_list)
    await session.commit()

    yield account_list


@pytest.fixture(name="test_account")
async def fixture_test_account(
    test_user: models.User, create_test_accounts, repository: Repository
):
    """
    Fixture for retrieving a test account.

    Args:
        test_user (fixture): The test user.
        create_test_accounts (fixture): The fixture for creating test accounts.

    Yields:
        models.Account: The test account.

    """

    account = await repository.filter_by(
        models.Account,
        models.Account.user_id,
        test_user.id,
        load_relationships_list=[models.Account.user],
    )
    yield account[0]


@pytest.fixture(name="test_accounts")
async def fixture_get_test_account_list(create_test_accounts, repository: Repository):
    """
    Fixture for retrieving a list of test accounts.

    Args:
        create_test_accounts (fixuter): The fixture for creating test accounts.

    Yields:
        list[models.Account]: A list of test accounts.

    """

    yield await repository.get_all(
        models.Account, load_relationships_list=[models.Account.user]
    )


def get_date_range(date_start, days=5):
    """
    Returns a list of dates in a range starting from a given date.

    Args:
        date_start: The starting date.
        days: The number of days in the range (default is 5).

    Returns:
        list[datetime.date]: A list of dates in the range.
    """

    return [(date_start - datetime.timedelta(days=idx)) for idx in range(days)]


@pytest.fixture(name="create_transactions")
async def fixture_create_transactions(
    test_accounts: list[models.Account],
    session: AsyncSession,
):
    """
    Fixture that creates test transactions.

    Args:
        test_accounts (fixture): The test accounts fixture.
        session (fixture): The session fixture.

    Returns:
        list[Transaction]: A list of test transactions.
    """

    dates = get_date_range(datetime.datetime.now(datetime.timezone.utc))

    transaction_data = [
        {
            "amount": 200,
            "reference": "transaction_001",
            "date": dates[0],
            "category_id": 1,
        },
        {
            "amount": 100,
            "reference": "transaction_002",
            "date": dates[1],
            "category_id": 1,
        },
        {
            "amount": 50,
            "reference": "transaction_003",
            "date": dates[3],
            "category_id": 4,
        },
        {
            "amount": 100,
            "reference": "transaction_004",
            "date": dates[4],
            "category_id": 8,
        },
        {
            "amount": 500,
            "reference": "transaction_005",
            "date": dates[3],
            "category_id": 7,
        },
        {
            "amount": 200,
            "reference": "transaction_006",
            "date": dates[2],
            "category_id": 7,
        },
    ]

    service = TransactionService()
    create_task = []

    for account in test_accounts:
        create_task.extend(
            [
                service.create_transaction(
                    account.user,
                    schemas.TransactionData(
                        account_id=account.id,
                        amount=transaction["amount"],
                        reference=transaction["reference"],
                        date=transaction["date"],
                        category_id=transaction["category_id"],
                    ),
                )
                for transaction in transaction_data
            ]
        )

    transaction_list = await asyncio.gather(*create_task)
    await session.commit()

    yield transaction_list


@pytest.fixture(name="create_scheduled_transactions")
async def fixture_create_scheduled_transactions(
    test_accounts: list[models.Account],
    repository: Repository,
):
    """
    Fixture to create a list of scheduled transactions for testing purposes.

    Args:
        test_accounts: List of test accounts for which scheduled transactions will be created.
        repository: The repository for database operations.

    Yields:
        List[models.TransactionScheduled | None]: List of created scheduled transactions or None.

    Raises:
        ValueError: If no user is found for a scheduled transaction.
    """

    today = get_today()
    tomorrow = get_tomorrow(today)
    yesterday = get_yesterday(today)
    reference_prefix = "scheduled_transaction"

    transaction_data_list = [
        {
            "amount": 100,
            "reference": f"{reference_prefix}_daily",
            "category_id": 1,
            "date_start": today,
            "frequency_id": Frequency.DAILY.value,
            "date_end": tomorrow,
        },
        {
            "amount": 1000,
            "reference": f"{reference_prefix}_weekly",
            "category_id": 1,
            "date_start": today,
            "frequency_id": Frequency.WEEKLY.value,
            "date_end": (today + datetime.timedelta(weeks=2)),
        },
        {
            "amount": 10000,
            "reference": f"{reference_prefix}_yearly",
            "category_id": 1,
            "date_start": today,
            "frequency_id": Frequency.YEARLY.value,
            "date_end": (today + datetime.timedelta(weeks=52)),
        },
        {
            "amount": 100,
            "reference": f"{reference_prefix}_daily_not_started",
            "category_id": 1,
            "date_start": tomorrow,
            "frequency_id": Frequency.DAILY.value,
            "date_end": (tomorrow + datetime.timedelta(weeks=48)),
        },
        {
            "amount": 1000,
            "reference": f"{reference_prefix}_weekly_not_started",
            "category_id": 1,
            "date_start": tomorrow,
            "frequency_id": Frequency.WEEKLY.value,
            "date_end": (tomorrow + datetime.timedelta(weeks=1)),
        },
        {
            "amount": 10000,
            "reference": f"{reference_prefix}_yearly_not_started",
            "category_id": 1,
            "date_start": tomorrow,
            "frequency_id": Frequency.DAILY.value,
            "date_end": (tomorrow + datetime.timedelta(weeks=52)),
        },
        {
            "amount": 100,
            "reference": f"{reference_prefix}_daily_ended",
            "category_id": 1,
            "date_start": (today - datetime.timedelta(weeks=2)),
            "frequency_id": Frequency.DAILY.value,
            "date_end": yesterday,
        },
        {
            "amount": 1000,
            "reference": f"{reference_prefix}_weekly_ended",
            "category_id": 1,
            "date_start": get_day_delta(today, -7),
            "frequency_id": Frequency.WEEKLY.value,
            "date_end": yesterday,
        },
        {
            "amount": 10000,
            "reference": f"{reference_prefix}_yearly_ended",
            "category_id": 1,
            "date_start": get_day_delta(today, -365),
            "frequency_id": Frequency.YEARLY.value,
            "date_end": yesterday,
        },
    ]

    service = ScheduledTransactionService()
    create_task = []

    for account in test_accounts:

        create_task.extend(
            [
                service.create_scheduled_transaction(
                    account.user,
                    schemas.ScheduledTransactionInformationCreate(
                        account_id=account.id,
                        amount=transaction["amount"],
                        reference=transaction["reference"],
                        category_id=transaction["category_id"],
                        date_start=transaction["date_start"],
                        frequency_id=transaction["frequency_id"],
                        date_end=transaction["date_end"],
                    ),
                )
                for transaction in transaction_data_list
            ]
        )

    scheduled_transaction_list: List[models.TransactionScheduled | None] = (
        await asyncio.gather(*create_task)
    )
    await repository.session.commit()

    yield scheduled_transaction_list

    delete_task = []
    for scheduled_transaction in scheduled_transaction_list:

        if scheduled_transaction is None:
            continue

        user = await repository.get(models.User, scheduled_transaction.account.user_id)

        if user is None:
            raise ValueError("No user found")

        delete_task.extend(
            [service.delete_scheduled_transaction(user, scheduled_transaction.id)]
        )

    await asyncio.gather(*delete_task)
    await repository.session.commit()


@pytest.fixture(name="test_account_scheduled_transaction_list")
async def fixture_test_account_scheduled_transaction_list(
    create_scheduled_transactions, test_account, repository: Repository
):
    """
    Fixture for retrieving a list of scheduled transactions for a test account.

    Args:
        create_scheduled_transactions: A fixture for creating scheduled transactions.
        test_account: The test account for which transactions are retrieved.
        repository: The repository to filter transactions from.

    Returns:
        A list of scheduled transactions filtered by the test account.
    """

    today = get_today()
    model = models.TransactionScheduled

    result = await repository.session.execute(
        select(model).where(
            and_(
                model.date_start <= today,
                model.date_end >= today,
                model.is_active is True,
                model.account_id == test_account.id,
                ~exists().where(
                    and_(
                        models.Transaction.scheduled_transaction_id == model.id,
                        func.date(models.Transaction.created_at) == func.date(today),
                    )
                ),
            )
        )
    )

    scheduled_transaction_list = result.scalars().all()
    return scheduled_transaction_list


@pytest.fixture(name="test_account_transaction_list")
async def fixture_test_account_transaction_list(
    create_transactions, test_account, repository: Repository
):
    """
    Fixture for retrieving a list of transactions associated with a test account.

    Args:
        create_transactions (fixture): The fixture for creating transactions.
        test_account (fixture): The test account.

    Yields:
        list[models.Transaction]: A list of transactions associated with the test account.
    """

    yield await repository.filter_by(
        models.Transaction, models.Transaction.account_id, test_account.id
    )


@pytest.fixture(name="transaction_list")
async def fixture_get_all_transactions(create_transactions, repository: Repository):
    """
    Fixture for retrieving a list of transactions.

    Args:
        create_transactions (fixture): The fixture for creating transactions.

    Yields:
        list[models.Transaction]: A list of transactions.

    """

    yield await repository.get_all(models.Transaction)
