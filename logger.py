import logging

logging.basicConfig(filename="all_log.log",
                    level=logging.INFO,
                    format='%(asctime)-15s %(levelname)s %(message)s',
                    filemode='a')
logger = logging.getLogger('BoxberryParserLog')
