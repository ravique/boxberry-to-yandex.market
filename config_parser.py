import configparser
import os

filename = os.path.join(os.path.dirname(__file__), 'config.ini')

config = configparser.ConfigParser()
config.read(filename)

bxb_config = config['Boxberry']
ym_config = config['YandexMarket']
general_config = config['General']
