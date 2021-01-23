import logging
import os

from config_parser import general_config

filename = general_config.get('log_file_name', None) or 'all_log.log'
path = os.path.join(os.path.dirname(__file__), filename)

logging.basicConfig(filename=path,
                    level=logging.INFO,
                    format='%(asctime)-15s %(levelname)s %(message)s',
                    filemode='a')
logger = logging.getLogger('BoxberryParserLog')
