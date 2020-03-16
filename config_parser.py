import configparser

config = configparser.ConfigParser()
config.read('config.ini')

bxb_config = config['Boxberry']
ym_config = config['YandexMarket']
general_config = config['General']
