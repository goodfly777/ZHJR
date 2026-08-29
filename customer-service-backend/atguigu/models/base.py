from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """sqlalchemy orm 实体类必须继承自此类"""
    pass