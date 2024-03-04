import asyncio
import datetime
from typing import List

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app import repository as repo
from app import schemas
from app import transaction_manager as tm
from app.services.accounts import AccountService
from app.services.transactions import TransactionService
from app.services.users import UserService
from app.utils.dataclasses_utils import CreateUserData
from tests.utils import get_date_range


@pytest.fixture(name="test_user")
async def fixture_test_user(test_users):
    yield test_users[0]


@pytest.fixture(scope="session")
async def fixture_create_test_users():
    """
    Fixture that creates test users.

    Args:
        user_service: The user service fixture.

    Returns:
        List[User]: A list of test users.
    """

    password = "password123"
    create_user_list = [
        ["user00@pytest.de", password, "User00"],
        ["user01@pytest.de", password, "User01"],
        ["user02@pytest.de", password, "User02"],
        ["user03@pytest.de", password, "User03"],
        ["hello123@pytest.de", password, "LoginUser"],
    ]

    user_service = UserService()
    for user in create_user_list:
        await user_service.create_user(
            CreateUserData(
                email=user[0],
                password=user[1],
                displayname=user[2],
                is_verified=True,
            ),
        )

    yield


@pytest.fixture(name="test_users")
async def fixture_test_user_list(fixture_create_test_users):
    yield await repo.get_all(models.User)


@pytest.fixture(name="test_account")
async def fixture_test_account(test_user: models.User, fixture_create_test_accounts):
    account = await repo.filter_by(models.Account, "user_id", test_user.id)
    yield account[0]


@pytest.fixture
async def fixture_create_test_accounts(
    session: AsyncSession, test_user, test_users: List[models.User]
):
    """
    Fixture that creates test accounts.

    Args:
        test_users: A list of test users.
        session: The session fixture.

    Returns:
        List[Account]: A list of test accounts.
    """

    account_data_list = [
        {
            "user": test_user,
            "label": "account_00",
            "description": "description_00",
            "balance": 100,
        },
        {
            "user": test_users[0],
            "label": "account_01",
            "description": "description_01",
            "balance": 200,
        },
        {
            "user": test_users[1],
            "label": "account_02",
            "description": "description_02",
            "balance": 500,
        },
        {
            "user": test_users[2],
            "label": "account_03",
            "description": "description_03",
            "balance": 1000,
        },
        {
            "user": test_user,
            "label": "account_04",
            "description": "description_04",
            "balance": 2000,
        },
    ]

    service = AccountService()

    # TODO: Make this async?
    for account_data in account_data_list:
        await service.create_account(
            account_data["user"],
            schemas.Account(
                label=account_data["label"],
                description=account_data["description"],
                balance=account_data["balance"],
            ),
        )

    yield


@pytest.fixture(name="test_accounts")
async def get_test_account_list(fixture_create_test_accounts):
    yield await repo.get_all(models.Account)


@pytest.fixture(name="test_account_transaction_list")
async def fixture_test_account_transaction_list(
    fixture_create_transactions, test_account
):

    yield await repo.filter_by(models.Transaction, "account_id", test_account.id)


@pytest.fixture(name="transaction_list")
async def fixture_get_all_transactions(fixture_create_transactions, test_account):

    yield await repo.get_all(models.Transaction)


@pytest.fixture
async def fixture_create_transactions(
    test_accounts: List[models.Account],
    test_account: models.Account,
    session: AsyncSession,
):
    """
    Fixture that creates test transactions.

    Args:
        test_accounts: The test accounts fixture.
        session: The session fixture.

    Returns:
        List[Transaction]: A list of test transactions.
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
    transaction_list = []

    async with session:
        for account in test_accounts:
            user = await repo.get(models.User, account.user_id)
            transaction_list.extend(
                [
                    await tm.transaction(
                        service.create_transaction,
                        user,
                        schemas.TransactionInformationCreate(
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

    yield
