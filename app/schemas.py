import datetime
import mimetypes
import uuid
from datetime import datetime as dt
from decimal import Decimal
from typing import Annotated, Any, Optional

from fastapi_users import schemas
from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints
from starlette_wtf import StarletteForm
from wtforms import (
    BooleanField,
    DecimalField,
    FileField,
    HiddenField,
    PasswordField,
    SelectField,
    StringField,
    ValidationError,
)
from wtforms.validators import (
    DataRequired,
    Email,
    InputRequired,
    Length,
    NumberRange,
    Regexp,
)
from wtforms.widgets import Input

from app.utils.classes import RoundedDecimal
from app.utils.fields import DateField, IdField

StringContr = Annotated[
    str, StringConstraints(min_length=3, max_length=36, strip_whitespace=True)
]


def serialize_rounded_decimal(value: Decimal) -> float:
    """
    Converts a Decimal value to a float by serializing it.

    Args:
        value: The Decimal value to be converted to a float.

    Returns:
        float: The serialized float value.
    """

    return float(value)


class EmailSchema(BaseModel):
    email: list[EmailStr]
    body: dict[str, Any]


class UserRead(schemas.BaseUser[uuid.UUID]):
    displayname: str


class UserCreate(schemas.BaseUserCreate):
    displayname: Optional[str]


class Base(BaseModel):
    model_config = ConfigDict(form_attributes=True)


class UserUpdate(schemas.BaseUserUpdate):
    displayname: Optional[str] = None
    password: Optional[str] = None
    email: Optional[EmailStr] = None


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    id: Optional[str]


class WalletUpdate(Base):
    label: Optional[StringContr]
    description: Optional[str]
    balance: Optional[RoundedDecimal] = Field(
        default=None,
        examples=[0.00],
        description="The wallet balance rounded to two decimal places.",
    )
    model_config = ConfigDict(json_encoders={Decimal: float})

    # TODO: Use field_serializer for response schemase
    # @field_serializer("balance")
    # def serialize_balance(self, balance: Decimal, _info):
    #     return serialize_rounded_decimal(balance)


class TransactionInformationBase(BaseModel):
    amount: RoundedDecimal = Field(
        ...,
        description="The transaction amount, rounded to two decimal places.",
        examples=[100.00],
    )
    reference: str
    category_id: IdField

    model_config = ConfigDict(json_encoders={Decimal: float})


class TransactionInformation(TransactionInformationBase):
    date: DateField


class MinimalResponse(Base):
    id: int
    label: str


class SectionData(MinimalResponse):
    pass


class FrequencyData(Base):
    id: int
    label: StringContr


class CategoryData(Base):
    id: int
    label: StringContr
    section: SectionData


class TransactionInformationCreate(TransactionInformation):
    wallet_id: IdField
    offset_wallet_id: Optional[IdField] = None


class TransactionData(TransactionInformationCreate):
    scheduled_transaction_id: Optional[IdField] = None


class TransactionInformtionUpdate(TransactionInformationCreate):
    pass


class ScheduledTransactionInformationCreate(TransactionInformationBase):
    date_start: DateField
    frequency_id: IdField
    date_end: DateField
    wallet_id: IdField
    offset_wallet_id: Optional[IdField] = None


class ScheduledTransactionInformtionUpdate(ScheduledTransactionInformationCreate):
    pass


class TransactionInformationData(TransactionInformation):
    category: CategoryData


class TransactionBase(Base):
    id: int
    wallet_id: IdField
    information: TransactionInformationData


class Transaction(TransactionBase):
    offset_transactions_id: Optional[IdField] = None


class TransactionResponse(Transaction):
    pass


class ScheduledTransaction(TransactionBase):
    date_start: DateField
    frequency: FrequencyData
    date_end: DateField
    wallet_id: IdField
    offset_wallet_id: Optional[IdField] = None


class Wallet(Base):
    label: StringContr
    description: Optional[str] = None
    balance: Optional[RoundedDecimal]

    model_config = ConfigDict(json_encoders={Decimal: float})


class WalletData(Wallet):
    id: IdField


class LoginForm(StarletteForm):
    username = StringField("E-Mail", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired()])


class CreateWalletForm(StarletteForm):
    label = StringField(
        "Name",
        validators=[
            DataRequired("Please enter your email address"),
            Length(max=36, min=3),
        ],
        render_kw={"placeholder": "e.g. 'Personal Savings'"},
    )

    description = StringField(
        "Description",
        validators=[
            Length(max=128),
        ],
        render_kw={"placeholder": "e.g. 'My primary savings wallet'"},
    )

    balance = DecimalField(
        "Balance",
        render_kw={"placeholder": "e.g. Current amount in savings"},
    )


class UpdateWalletForm(StarletteForm):
    label = StringField(
        "Name",
        validators=[
            DataRequired("Please enter your email address"),
            Length(max=36),
        ],
    )

    description = StringField(
        "Description",
        validators=[DataRequired("Please enter a description"), Length(max=128)],
    )


password_policy = Regexp(
    r"^(?=.*[A-Z])(?=.*\d)(?=.*[\@\#\$\%\^\&\*\(\)\-\_\=\+\{\}\[\]\|\:\;\,\.\<\>\?\/\!]).{8,}",
    message=(
        "Password should have at least "
        "8 characters,"
        "1 uppercase, "
        "1 digit and "
        "1 special character"
    ),
)


class RegisterForm(StarletteForm):
    email = StringField("Email", validators=[InputRequired(), Email(), Length(max=320)])
    password = PasswordField("Password", validators=[InputRequired(), password_policy])


class ForgotPasswordForm(StarletteForm):
    email = StringField("Email", validators=[InputRequired(), Email(), Length(max=320)])


class GetNewTokenForm(StarletteForm):
    email = StringField("Email", validators=[InputRequired(), Email(), Length(max=320)])


class ResetPasswordForm(StarletteForm):
    token = HiddenField("Token", validators=[InputRequired()])
    password = PasswordField("Password", validators=[InputRequired(), password_policy])


class DatetimeLocalFieldWithoutTime(StringField):
    widget = Input(input_type="date")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = None

    def process_formdata(self, valuelist):
        if valuelist:
            date_str = " ".join(valuelist)
            try:
                naive_date_object = dt.strptime(date_str, "%Y-%m-%d")
                utc_date_object = naive_date_object.replace(
                    tzinfo=datetime.timezone.utc
                )
                self.data = utc_date_object
            except ValueError as e:
                self.data = None
                raise ValueError(
                    self.gettext(f"Not a valid date value: {valuelist}")
                ) from e


class CreateTransactionForm(StarletteForm):
    reference = StringField(
        "Reference",
        validators=[InputRequired(), Length(max=128)],
        render_kw={"placeholder": "e.g. 'Rent payment for March'"},
    )
    amount = DecimalField(
        "Amount",
        validators=[InputRequired(), NumberRange(min=0)],
        render_kw={"placeholder": "500"},
    )
    is_expense = BooleanField("Is this an expense?", default=True)
    category_id = SelectField(
        "Category",
        validators=[InputRequired()],
        coerce=int,
        render_kw={"placeholder": "Select the appropriate category"},
    )
    date = DatetimeLocalFieldWithoutTime(
        "Date",
        validators=[InputRequired()],
    )
    offset_wallet_id = SelectField(
        "Linked Wallet",
        coerce=int,
        render_kw={
            "placeholder": (
                "Select an wallet if this transaction is "
                "transferring funds between wallets"
            ),
        },
    )


class UpdateTransactionForm(StarletteForm):
    reference = StringField("Reference", validators=[InputRequired(), Length(max=128)])
    amount = DecimalField(
        "Amount",
        validators=[InputRequired(), NumberRange(min=0)],
    )
    is_expense = BooleanField("Is this an expense?")
    category_id = SelectField("Category", validators=[InputRequired()], coerce=int)
    date = DatetimeLocalFieldWithoutTime("Date", validators=[InputRequired()])
    offset_wallet_id = SelectField(
        "Linked Wallet", coerce=int, render_kw={"disabled": "disabled"}, default=0
    )


class CreateScheduledTransactionForm(StarletteForm):
    reference = StringField(
        "Reference",
        validators=[InputRequired(), Length(max=128)],
        render_kw={"placeholder": "e.g. 'Rent payment for March'"},
    )
    amount = DecimalField(
        "Amount",
        validators=[InputRequired(), NumberRange(min=0)],
        render_kw={"placeholder": "500"},
    )
    is_expense = BooleanField("Is this an expense?", default=True)
    category_id = SelectField(
        "Category",
        validators=[InputRequired()],
        coerce=int,
        render_kw={"placeholder": "Select the appropriate category"},
    )
    frequency_id = SelectField(
        "Frequency",
        validators=[InputRequired()],
        coerce=int,
        render_kw={"placeholder": "Select the appropriate frequency"},
    )
    date_start = DatetimeLocalFieldWithoutTime(
        "Date Start",
        validators=[InputRequired()],
    )
    date_end = DatetimeLocalFieldWithoutTime(
        "Date End",
        validators=[InputRequired()],
    )
    offset_wallet_id = SelectField(
        "Linked Wallet",
        coerce=int,
        render_kw={
            "placeholder": (
                "Select an wallet if this transaction is "
                "transferring funds between wallets"
            ),
        },
    )


class UpdateScheduledTransactionForm(StarletteForm):
    reference = StringField("Reference", validators=[InputRequired(), Length(max=128)])
    amount = DecimalField(
        "Amount",
        validators=[InputRequired(), NumberRange(min=0)],
    )
    is_expense = BooleanField("Is this an expense?")
    category_id = SelectField("Category", validators=[InputRequired()], coerce=int)
    date_start = DatetimeLocalFieldWithoutTime(
        "Date Start", validators=[InputRequired()]
    )
    date_end = DatetimeLocalFieldWithoutTime("Date End", validators=[InputRequired()])
    offset_wallet_id = SelectField("Linked Wallet", coerce=int, default=0)
    frequency_id = SelectField("Frequency", coerce=int, default=0)


class DatePickerForm(StarletteForm):
    date_start = DatetimeLocalFieldWithoutTime(
        "Start Date", validators=[InputRequired()]
    )
    date_end = DatetimeLocalFieldWithoutTime("End Date", validators=[InputRequired()])


class UpdateUserForm(StarletteForm):
    email = StringField("Email", validators=[Email(), InputRequired(), Length(max=320)])
    displayname = StringField("Displayname", validators=[Length(max=50)])


def validate_csv_file(_form, field):
    """
    Validates that the uploaded file is a CSV file.
    """
    if field.data and field.data.filename:
        mimetype, _encoding = mimetypes.guess_type(field.data.filename)
        if mimetype not in ["text/csv", "application/vnd.ms-excel"]:
            raise ValidationError("File must be a CSV file.")


class ImportTransactionsForm(StarletteForm):
    file = FileField(
        "File",
        validators=[InputRequired(), validate_csv_file],
    )
