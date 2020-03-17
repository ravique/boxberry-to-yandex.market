from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine('sqlite:///yandex_regions.db')
Session = sessionmaker()
Session.configure(bind=engine)
session = Session()