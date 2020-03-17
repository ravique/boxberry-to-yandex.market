from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

from db import session, engine

Base = declarative_base()


class YandexRegion(Base):
    __tablename__ = 'yandex_regions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True)
    yandex_id = Column(Integer, unique=True)

    def __repr__(self):
        return self.name

    def get_or_create(self, id, name):
        instance = session.query(self).filter_by(name=name)
        if instance:
            return instance
        else:
            new_instance = self.__class__(id=id, name=name)
            session.add(new_instance)
            session.commit()



Base.metadata.create_all(engine)

def test2():
    x = session.query(YandexRegion).all()
    print(x)

test2()

