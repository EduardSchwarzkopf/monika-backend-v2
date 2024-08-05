from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple, Type, TypeVar, Union

from sqlalchemy import Select, and_, exists, func, text
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.orm.attributes import InstrumentedAttribute

from app import models
from app.database import db
from app.models import BaseModel
from app.utils.enums import DatabaseFilterOperator, Frequency
from app.utils.fields import IdField

ModelT = TypeVar("ModelT", bound=BaseModel)


class Repository:

    def __init__(self, session: Optional[AsyncSession] = None):

        self.session = session if session is not None else db.session

    def _load_relationships(
        self, query: Select, relationships: InstrumentedAttribute = None
    ) -> Select:
        """Apply loading options for specified relationships to a query.

        Args:
            query: The SQLAlchemy query object.
            *relationships: Class-bound attributes representing relationships to load.

        Returns:
            The modified query with loading options applied.
        """
        if relationships:
            options = [selectinload(rel) for rel in relationships]
            query = query.options(*options)
        return query

    async def get_all(
        self,
        cls: Type[ModelT],
        load_relationships_list: Optional[list[InstrumentedAttribute]] = None,
    ) -> list[ModelT]:
        """Retrieve all instances of the specified model from the database.

        Args:
            cls: The type of the model.
            load_relationships: Optional list of relationships to load.

        Returns:
            list[ModelT]: A list of instances of the specified model.
        """
        q = select(cls)
        q = self._load_relationships(q, load_relationships_list)
        result = await self.session.execute(q)
        return result.unique().scalars().all()

    async def get(
        self,
        cls: Type[ModelT],
        instance_id: Union[int, IdField],
        load_relationships_list: Optional[list[InstrumentedAttribute]] = None,
    ) -> Optional[ModelT]:
        """Retrieve an instance of the specified model by its ID.

        Args:
            cls: The type of the model.
            instance_id: The ID of the instance to retrieve.
            load_relationships: Optional list of relationships to load.

        Returns:
            Optional[ModelT]:
                The instance of the specified model with
                the given ID, or None if not found.
        """
        q = select(cls).where(cls.id == instance_id)
        q = self._load_relationships(q, load_relationships_list)
        result = await self.session.execute(q)
        return result.scalars().first()

    async def filter_by(
        self,
        cls: Type[ModelT],
        attribute: InstrumentedAttribute,
        value: Any,
        operator: DatabaseFilterOperator = DatabaseFilterOperator.EQUAL,
        load_relationships_list: Optional[list[str]] = None,
    ) -> list[ModelT]:
        """
        Filters the records of a given model by a specified attribute and value.

        Args:
            cls: The model class.
            attribute: The attribute to filter by.
            value: The value to filter with.
            operator: The operator to use for the filter (default: EQUAL).

        Returns:
            list[Type[ModelT]]: The filtered records.

        Raises:
            None
        """
        if operator == DatabaseFilterOperator.LIKE:
            condition = attribute.ilike(f"%{value}%")
        elif operator == DatabaseFilterOperator.IS_NOT:
            condition = attribute.is_not(value)
        else:
            condition = text(f"{attribute.key} {operator.value} :val")

        q = select(cls).where(condition).params(val=value)
        q = self._load_relationships(q, load_relationships_list)

        result = await self.session.execute(q)

        return result.unique().scalars().all()

    async def filter_by_multiple(
        self,
        cls: Type[ModelT],
        conditions: List[Tuple[InstrumentedAttribute, Any, DatabaseFilterOperator]],
        load_relationships_list: Optional[list[str]] = None,
    ) -> list[ModelT]:
        """
        Filters the records of a given model by multiple attributes and values.

        Args:
            cls: The model class.
            conditions: A list of tuples where each tuple contains an attribute to filter by,
                        a value to filter with, and an optional operator
                        (if not provided, EQUAL is used).
            load_relationships_list: Optional list of relationships to load.

        Returns:
            list[ModelT]: The filtered records.
        """

        where_conditions = []
        params = {}
        for i, (attribute, value, operator) in enumerate(conditions):
            param_name = f"val{i}"

            if operator == DatabaseFilterOperator.LIKE:
                condition = attribute.ilike(f"%{value}%")
            elif operator == DatabaseFilterOperator.IS_NOT:
                condition = attribute.is_not(value)
            else:
                condition = text(f"{attribute.key} {operator.value} :{param_name}")
                params[param_name] = value

            where_conditions.append(condition)

        q = select(cls)
        if where_conditions:
            for condition in where_conditions:
                q = q.where(condition)

        q = q.params(**params)
        q = self._load_relationships(q, load_relationships_list)

        result = await self.session.execute(q)

        return result.scalars().unique().all()

    async def get_scheduled_transactions_by_frequency(
        self,
        frequency_id: int,
        today: datetime,
    ) -> list[models.TransactionScheduled]:
        """
        Retrieve all scheduled transactions for a specific frequency
        that are active and not yet processed today.

        Args:
            frequency_id (int): The frequency ID to filter by.
            today (datetime): The current date to use for filtering.
            date_filter_func (Callable[[datetime], datetime]):
                A date transformation function to filter creation dates
                in the `Transaction` table.

        Returns:
            list[models.TransactionScheduled]: A list of scheduled transactions.
        """
        model = models.TransactionScheduled

        def get_period_start_date(frequency_id: int) -> datetime:
            match frequency_id:
                case Frequency.DAILY.value | Frequency.ONCE.value:
                    return today
                case Frequency.WEEKLY.value:
                    return today - timedelta(days=7)
                case Frequency.MONTHLY.value:
                    return today.replace(month=today.month - 1)
                case Frequency.YEARLY.value:
                    return today.replace(year=today.year - 1)

            return today

        transaction_exists_condition = ~exists().where(
            and_(
                models.Transaction.scheduled_transaction_id == model.id,
                func.date(models.Transaction.created_at) == func.date(today),
                func.date(models.Transaction.created_at)
                >= get_period_start_date(frequency_id),
            )
        )

        query = select(model).where(
            model.date_start <= today,
            model.date_end >= today,
            model.is_active == True,
            model.frequency_id == frequency_id,
            transaction_exists_condition,
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def get_transactions_from_period(
        self, account_id: int, start_date: datetime, end_date: datetime
    ) -> list[models.Transaction]:
        """Retrieve transactions for a specific account within a given period.

        Args:
            account_id: The ID of the account.
            start_date: The start date of the period.
            end_date: The end date of the period.

        Returns:
            list[models.Transaction]: A list of transactions within the specified period.

        Raises:
            None
        """
        transaction = models.Transaction
        information = models.TransactionInformation
        class_date = information.date

        query = (
            select(transaction)
            .options(joinedload(transaction.offset_transaction))
            .join(transaction.information)
            .filter(class_date <= end_date)
            .filter(class_date >= start_date)
            .filter(account_id == transaction.account_id)
        )

        result = await self.session.execute(query)
        return result.scalars().all()

    async def save(self, obj: Union[ModelT, List[ModelT]]) -> None:
        """Save an object or a list of objects to the database.

        Args:
            obj: The object or list of objects to save.

        Returns:
            None

        Raises:
            None
        """
        if isinstance(obj, list):
            self.session.add_all(obj)
            return

        self.session.add(obj)

    async def commit(self) -> None:
        """Commit the changes made in the session to the database.

        Args:
            session: The database session.

        Returns:
            None

        Raises:
            None
        """
        await self.session.commit()

    async def update(self, cls: Type[ModelT], instance_id: int, **kwargs) -> None:
        """Update an instance of the specified model with the given ID.

        Args:
            cls: The type of the model.
            instance_id: The ID of the instance to update.
            **kwargs: The attributes and values to update.

        Returns:
            None

        Raises:
            None
        """
        query = (
            sql_update(cls)
            .where(cls.id == instance_id)
            .values(**kwargs)
            .execution_options(synchronize_session="fetch")
        )
        await self.session.execute(query)

    async def delete(self, obj: Type[ModelT]) -> None:
        """Delete an object from the database.

        Args:
            obj: The object to delete.

        Returns:
            None

        Raises:
            None
        """

        # TODO: Test this
        # if isinstance(obj, list):
        #     for object in obj:
        #         self.session.delete(object)
        #     return

        # TODO: Await needed?
        await self.session.delete(obj)

    async def refresh(self, obj: Type[ModelT]) -> None:
        """Refresh the state of an object from the database.

        Args:
            obj: The object to refresh.

        Returns:
            None

        Raises:
            None
        """
        return await self.session.refresh(obj)

    async def refresh_all(self, object_list: list[Type[ModelT]]) -> None:
        """Refresh the state of multiple objects from the database.

        Args:
            object_list: The list of objects to refresh.

        Returns:
            None

        Raises:
            None
        """
        for obj in object_list:
            await self.session.refresh(obj)
