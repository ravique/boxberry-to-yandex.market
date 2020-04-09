import logging

from config_parser import general_config

filename = general_config.get('log_file_name', None) or 'all_log.log'

logging.basicConfig(filename="all_log.log",
                    level=logging.INFO,
                    format='%(asctime)-15s %(levelname)s %(message)s',
                    filemode='a')
logger = logging.getLogger('BoxberryParserLog')
