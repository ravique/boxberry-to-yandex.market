import configparser

config = configparser.ConfigParser()
config.read('config.ini')

bxb_config = config['Boxberry']
ym_config = config['YandexMarket']
