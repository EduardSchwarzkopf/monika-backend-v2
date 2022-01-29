from sqlalchemy import or_, extract
from . import models
from fastapi_sqlalchemy import db
from datetime import datetime


def __str_to_class(classname: str):
    return getattr(models, classname)


def __db_action(action_name: str, object):
    method = getattr(db.session, action_name)
    method(object)


def __db_query_action(filter_option: str, name: str, attribute: str, value: str):
    class_ = __str_to_class(name)
    attr = getattr(class_, attribute)
    return getattr(db.session.query(class_), filter_option)(attr == value)


def get_all(name: str):
    class_ = __str_to_class(name)
    return db.session.query(class_).all()


def filter(name: str, attribute: str, value: str):
    return __db_query_action("filter", name, attribute, value)


def filter_by(name: str, attribute: str, value: str):
    return __db_query_action("filter_by", name, attribute, value)


def get(name: str, id: int):
    class_ = __str_to_class(name)
    return db.session.query(class_).get(id)


def get_from_month(name: str, date: datetime, attribute: str, value: str):
    class_ = __str_to_class(name)
    attribute = getattr(class_, attribute)

    information_class = __str_to_class(name + "Information")
    class_date = information_class.date
    month = extract("month", class_date)
    year = extract("year", class_date)

    return (
        db.session.query(class_)
        .join(class_.information)
        .filter(year == date.year)
        .filter(month == date.month)
        .filter(value == attribute)
        .all()
    )


def get_scheduled_transactions_for_date(date: datetime):
    ts = models.TransactionScheduled
    return (
        db.session.query(ts)
        .filter(ts.date_start <= date)
        .filter(or_(ts.date_end == None, ts.date_end >= date))
        .all()
    )


def save(object: models):
    if isinstance(object, list):
        return __db_action("add_all", object)

    return __db_action("add", object)


def delete(object: models):
    return __db_action("delete", object)


def refresh(object: models):
    return __db_action("refresh", object)
