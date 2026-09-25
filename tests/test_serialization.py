"""Tests for Pydantic v2 serialization of non-native types."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from pydantic import BaseModel

from folioman_client.models import (
    Holding,
    NavPoint,
    Transaction,
)
from folioman_intelligence.types import (
    ConfiguredDate,
    ConfiguredDatetime,
    ConfiguredDecimal,
    ConfiguredPath,
    ConfiguredTime,
    ConfiguredTimedelta,
    ConfiguredUUID,
)


class SampleModel(BaseModel):
    decimal_val: ConfiguredDecimal
    optional_decimal: ConfiguredDecimal | None = None
    date_val: ConfiguredDate
    optional_date: ConfiguredDate | None = None
    datetime_val: ConfiguredDatetime
    time_val: ConfiguredTime
    timedelta_val: ConfiguredTimedelta
    uuid_val: ConfiguredUUID
    path_val: ConfiguredPath


def test_custom_types_attribute_types_preserved():
    now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
    today = date(2026, 9, 20)
    uid = uuid4()

    instance = SampleModel(
        decimal_val=Decimal("123.456"),
        date_val=today,
        datetime_val=now,
        time_val=time(14, 30, 0),
        timedelta_val=timedelta(minutes=15),
        uuid_val=uid,
        path_val=Path("foo/bar.txt"),
    )

    # In Python, model attributes retain rich native types
    assert isinstance(instance.decimal_val, Decimal)
    assert instance.decimal_val == Decimal("123.456")
    assert isinstance(instance.date_val, date)
    assert isinstance(instance.datetime_val, datetime)
    assert isinstance(instance.time_val, time)
    assert isinstance(instance.timedelta_val, timedelta)
    assert isinstance(instance.uuid_val, UUID)
    assert isinstance(instance.path_val, Path)


def test_custom_types_serialization_converts_to_primitives():
    now = datetime(2026, 9, 20, 12, 0, 0, tzinfo=timezone.utc)
    today = date(2026, 9, 20)
    uid = uuid4()

    instance = SampleModel(
        decimal_val=Decimal("123.456"),
        optional_decimal=None,
        date_val=today,
        optional_date=None,
        datetime_val=now,
        time_val=time(14, 30, 0),
        timedelta_val=timedelta(minutes=15),
        uuid_val=uid,
        path_val=Path("foo/bar.txt"),
    )

    # .model_dump() converts types to primitives
    dumped = instance.model_dump()
    assert isinstance(dumped["decimal_val"], float)
    assert dumped["decimal_val"] == 123.456
    assert dumped["optional_decimal"] is None
    assert dumped["date_val"] == "2026-09-20"
    assert dumped["optional_date"] is None
    assert dumped["datetime_val"] == "2026-09-20T12:00:00+00:00"
    assert dumped["time_val"] == "14:30:00"
    assert dumped["timedelta_val"] == 900.0
    assert dumped["uuid_val"] == str(uid)
    assert dumped["path_val"] == "foo/bar.txt"

    # .model_dump_json() creates valid JSON string
    json_str = instance.model_dump_json()
    assert '"decimal_val":123.456' in json_str
    assert '"optional_decimal":null' in json_str
    assert '"date_val":"2026-09-20"' in json_str


def test_holding_model_serialization():
    holding = Holding(
        security_id=101,
        name="Quant Active Fund",
        security_type="MF",
        units=Decimal("1250.75"),
        value_inr=Decimal("50000.50"),
        invested_inr=Decimal("40000.00"),
        latest_nav=Decimal("40.00"),
        day_change_inr=None,
    )

    # In Python, attributes are Decimals
    assert isinstance(holding.units, Decimal)
    assert holding.units == Decimal("1250.75")
    assert holding.day_change_inr is None

    # Serialization produces floats
    dumped = holding.model_dump()
    assert isinstance(dumped["units"], float)
    assert dumped["units"] == 1250.75
    assert isinstance(dumped["value_inr"], float)
    assert dumped["value_inr"] == 50000.50
    assert dumped["day_change_inr"] is None


def test_navpoint_and_transaction_serialization():
    nav_pt = NavPoint(date=date(2026, 1, 15), nav=Decimal("120.45"))
    dumped_nav = nav_pt.model_dump()
    assert dumped_nav["date"] == "2026-01-15"
    assert dumped_nav["nav"] == 120.45

    txn = Transaction(
        id=1,
        investor_id=10,
        security_id=101,
        date=date(2026, 1, 10),
        transaction_type="BUY",
        units=Decimal("50.0"),
        nav_or_price=Decimal("100.0"),
        amount=Decimal("5000.0"),
    )
    dumped_txn = txn.model_dump()
    assert dumped_txn["date"] == "2026-01-10"
    assert dumped_txn["units"] == 50.0
    assert dumped_txn["nav_or_price"] == 100.0
    assert dumped_txn["amount"] == 5000.0
    assert dumped_txn["fees"] == 0.0
