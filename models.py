from datetime import date

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Date

from db import session, engine

Base = declarative_base()


class YandexRegion(Base):
    __tablename__ = 'yandex_regions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    city_name = Column(String)
    region = Column(String)
    yandex_id = Column(Integer)
    updated = Column(Date)

    def __repr__(self):
        return self.city_name

    @classmethod
    def create_or_update(cls, region, yandex_id, city_name):
        instance = session.query(cls).filter_by(city_name=city_name, region=region).first()
        today = date.today()
        if instance:
            instance.yandex_id = yandex_id
            instance.updated = today
        else:
            instance = cls(city_name=city_name, yandex_id=yandex_id, region=region, updated=today)
        session.add(instance)
        session.commit()


class DeliveryCostOverride(Base):
    __tablename__ = 'delivery_cost_override'

    id = Column(Integer, primary_key=True, autoincrement=True)
    city_name = Column(String, unique=True)
    region_name = Column(String, unique=True)
    rate = Column(Integer)


Base.metadata.create_all(engine)
