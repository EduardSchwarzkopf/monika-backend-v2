import pytest

from app import schemas

pytestmark = pytest.mark.anyio
ENDPOINT = "/api/accounts/"


async def test_create_account(session, authorized_client):
    async with session:
        res = await authorized_client.post(
            ENDPOINT,
            json={"label": "test_account", "description": "test", "balance": 500},
        )

    assert res.status_code == 201

    new_account = schemas.Account(**res.json())

    assert new_account.label == "test_account"
    assert new_account.balance == 500
    assert new_account.description == "test"


@pytest.mark.parametrize(
    "label, description, balance",
    [
        ("", None, None),
        ("test", "test", "aaaa"),
        ("test", "test", "0,3"),
    ],
)
async def test_invalid_create_account(
    session, authorized_client, label, description, balance
):
    async with session:
        res = await authorized_client.post(
            ENDPOINT,
            json={"label": label, "description": description, "balance": balance},
        )

    assert res.status_code == 422


@pytest.mark.usefixtures("test_account")
async def test_delete_account(authorized_client):
    res = await authorized_client.delete(f"{ENDPOINT}1")

    assert res.status_code == 204


@pytest.mark.parametrize(
    "account_id, status_code",
    [("2", 404), ("3", 404), ("4", 404), ("999999", 404)],
)
@pytest.mark.usefixtures("test_account")
async def test_invalid_delete_account(authorized_client, account_id, status_code):
    res = await authorized_client.delete(f"{ENDPOINT}{account_id}")

    assert res.status_code == status_code


@pytest.mark.parametrize(
    "values",
    [
        (
            {
                "label": "My new Label",
                "description": "very new description",
                "balance": 1111.3,
            }
        ),
        (
            {
                "label": "11113",
                "description": "cool story bro '",
                "balance": 2000,
            }
        ),
        (
            {
                "label": "My new Label",
                "description": "very new description",
                "balance": -0.333333334,
            }
        ),
        (
            {
                "label": "My new Label",
                "description": "very new description",
                "balance": -1000000.3,
            }
        ),
    ],
)
@pytest.mark.usefixtures("test_account")
async def test_update_account(session, authorized_client, values):
    async with session:
        res = await authorized_client.put(f"{ENDPOINT}1", json=values)

    assert res.status_code == 200
    account = schemas.AccountData(**res.json())

    for key, value in values.items():
        if key == "id":
            continue

        account_val = getattr(account, key)
        print(f"key: {key} | value: {value} | account_val: {account_val}")
        if isinstance(value, str):
            assert account_val == value
        else:
            assert account_val == round(value, 2)
