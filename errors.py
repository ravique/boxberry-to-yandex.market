class PointParseError(Exception):
    pass


class BoxberryError(Exception):
    pass


class ClientError(Exception):
    def __init__(self, service: str = 'Service', error_text: str = 'No text'):
        self.message = '{} returned error code. Message: {}'.format(service, error_text)

    def __str__(self):
        return self.message


class ClientConnectionError(Exception):
    def __init__(self, service: str = 'Service', error_text: str = 'No text'):
        self.message = '{} returned 5xx code. Message: {}'.format(service, error_text)

    def __str__(self):
        return self.message
