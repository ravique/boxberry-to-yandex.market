import json
import time
from copy import deepcopy
from typing import Optional, Union

import requests
from requests import RequestException

from config_parser import general_config
from errors import BoxberryError, ClientError, ClientConnectionError
from logger import logger
from normalize_dict import STRONG_NORMALIZE, REGULAR_NORMALIZE


class Client:
    def __init__(self):
        self.service_name = None
        self._session = requests.Session()
        self._base_request = None
        self._timeout = 10

    def check_and_convert_response(self, response: requests.Response) -> Union[dict, list]:
        status_code = response.status_code

        if str(status_code)[0] == '5' or status_code == 404:  # Server, connection error or 404
            raise ClientConnectionError(service=self.service_name, error_text=response.text)

        elif str(status_code)[0] != '2':
            raise ClientError(service=self.service_name, error_text=response.text)

        return json.loads(response.text)

    def prepare_get(self, request: requests.Request = None, params: dict = None) -> requests.PreparedRequest:
        if not request:
            get_request = deepcopy(self._base_request)
        else:
            get_request = request

        get_request.method = 'GET'
        if params:
            get_request.params.update(params)
        return get_request.prepare()

    def prepare_post(self, request: requests.Request = None, payload=None) -> requests.PreparedRequest:
        if not request:
            post_request = deepcopy(self._base_request)
        else:
            post_request = request

        post_request.method = 'POST'
        if payload:
            post_request.json = payload
        return post_request.prepare()

    def prepare_put(self, request: requests.Request = None, payload=None) -> requests.PreparedRequest:
        if not request:
            post_request = deepcopy(self._base_request)
        else:
            post_request = request

        post_request.method = 'PUT'
        if payload:
            post_request.json = payload
        return post_request.prepare()

    def prepare_delete(self, request: requests.Request = None) -> requests.PreparedRequest:
        if not request:
            delete_request = deepcopy(self._base_request)
        else:
            delete_request = request

        delete_request.method = 'DELETE'
        return delete_request.prepare()

    def send(self,
             prepared_request: requests.PreparedRequest,
             timeout: int = 10) -> Union[list, dict]:
        response = 'No response'

        for i in range(1, int(general_config['max_attempts'])):
            try:
                response = self._session.send(prepared_request, timeout=self._timeout)
            except RequestException as e:
                logger.warn(msg=e)
                continue
            try:
                dict_response = self.check_and_convert_response(response)
            except ClientConnectionError:
                logger.warn(msg='{} did not respond. Attempt  #{}'.format(self.service_name, i))
                # Try to perform new request
                time.sleep(timeout)
            except ClientError as e:
                logger.error(msg=e)
                raise e
            else:
                return dict_response
        raise ClientConnectionError('Can not get data after {} attempts. {}'.format(int(general_config['max_attempts']),
                                                                                    response.text))


class BoxberryClient(Client):

    def __init__(self, token: str, api_url: object = None):
        Client.__init__(self)
        self.service_name = 'Boxberry'
        self._token = token
        self._api_url = api_url or 'http://api.boxberry.ru/json.php'
        self._base_request = requests.Request(url=self._api_url, params={'token': self._token})

    def check_and_convert_response(self, response: requests.Response) -> Union[dict, list]:
        status_code = response.status_code
        loaded_response = json.loads(response.text)

        if str(status_code)[0] == '5' or status_code in (404, 402):
            # Server, connection error, 404 or incorrect `402: Hit rate limit of 2 parallel requests`
            raise ClientConnectionError(service=self.service_name, error_text=response.text)

        elif str(status_code)[0] != '2':
            if isinstance(loaded_response, dict) and 'err' in loaded_response.keys():
                raise BoxberryError(loaded_response['err'])
            if isinstance(loaded_response, list) and 'err' in loaded_response[0].keys():
                raise BoxberryError(loaded_response[0]['err'])
            if not isinstance(loaded_response, list) and not isinstance(loaded_response, dict):
                raise BoxberryError('Can not convert Boxberry response to the list or dict')
        return loaded_response

    # Main methods

    def get_cities(self):
        pr = self.prepare_get(params={'method': 'ListCities'})
        return self.send(pr)

    def get_point_info(self, point_code: str) -> dict:
        pr = self.prepare_get(params={'method': 'PointsDescription', 'code': point_code})
        return self.send(pr)

    def get_points_codes_list(self, city_code: int = None):
        params = {'method': 'ListPointsShort'}
        if city_code:
            params.update({'CityCode': city_code})
        pr = self.prepare_get(params=params)
        return self.send(pr)

    def get_points_list(self, city_code: int = None):
        params = {'method': 'ListPoints'}
        if city_code:
            params.update({'CityCode': city_code})
        pr = self.prepare_get(params=params)
        return self.send(pr)

    def get_point_rate(self, point_code: str, default_weight: int, target_start: str):
        params = {
            'method': 'DeliveryCosts',
            'weight': default_weight,
            'target': point_code,
            'targetstart': target_start,
        }

        pr = self.prepare_get(params=params)
        return self.send(pr)

    # Helpers

    def get_cities_of_region(self, region_names: list) -> list:
        return [city for city in self.get_cities() if city['Region'] in region_names]

    def get_city_codes(self, city_names: list) -> Optional[list]:
        city_codes = []
        for city_name in city_names:
            city_code = [city['Code'] for city in self.get_cities() if city['Name'] in city_name]
            if not city_code:
                logger.warn(msg='No city code found for city {}'.format(city_name))
                continue
            city_codes.append(city_code)

        return city_codes

    def get_cities_codes(self, cities: list) -> list:
        return [city['Code'] for city in cities]


class YandexMarketClient(Client):
    def __init__(self, ym_token: str, ym_client_id: str, ym_campaign_id: str, ym_api_url=None):
        Client.__init__(self)
        self.service_name = 'YandexMarket'
        self._ym_token = ym_token
        self._ym_client_id = ym_client_id
        self._ym_campaign_id = ym_campaign_id
        self._api_url = ym_api_url or 'https://api.partner.market.yandex.ru/v2/'
        self._base_request = requests.Request(url=self._api_url,
                                              params={
                                                  'oauth_token': self._ym_token,
                                                  'oauth_client_id': self._ym_client_id
                                              })
        self._init_outlets_url()

    def _init_outlets_url(self):
        self._outlets_url = deepcopy(
            self._base_request
        )
        self._outlets_url.url = self._api_url + 'campaigns/{}/outlets.json'.format(self._ym_campaign_id)

    def multipage_get(self, request: requests.Request, list_name: str) -> list:
        rq = self.prepare_get(request=request)
        response_dict = self.send(rq)
        entities_list = response_dict.get(list_name, [])

        if not response_dict.get('paging'):
            return entities_list

        while 'nextPageToken' in response_dict.get('paging', {}).keys():
            rq = self.prepare_get(request=request, params={'page_token': response_dict['paging']['nextPageToken']})
            response_dict = self.send(rq)
            new_entities = response_dict.get(list_name)
            entities_list += new_entities
            time.sleep(1)
        return entities_list

    def get_published_outlets(self) -> list:
        return self.multipage_get(
            request=self._outlets_url,
            list_name='outlets'
        )

    def get_outlets_by_type(self, outlet_type: str) -> dict:
        """
        :param outlet_type: bxb, self, sdek
        :return: list of outlets codes
        """
        return {outlet['shopOutletCode']: outlet for outlet in self.get_published_outlets() if
                outlet.get('shopOutletCode', None) and outlet_type in outlet['shopOutletCode'].split('_')}

    def post_outlet(self, bxb_point):
        rq = self.prepare_post(request=self._outlets_url, payload=bxb_point)
        self.send(rq)

    def update_outlet(self, outlet_id, bxb_point):
        outlet_put_request = deepcopy(
            self._base_request
        )
        outlet_put_request.url = self._api_url + 'campaigns/{}/outlets/{}.json'.format(self._ym_campaign_id,
                                                                                       outlet_id)

        rq = self.prepare_put(request=outlet_put_request, payload=bxb_point)
        self.send(rq)

    def delete_outlet(self, outlet_id):
        outlet_delete_request = deepcopy(
            self._base_request
        )
        outlet_delete_request.url = self._api_url + 'campaigns/{}/outlets/{}.json'.format(self._ym_campaign_id,
                                                                                          outlet_id)
        rq = self.prepare_delete(request=outlet_delete_request)
        self.send(rq)

    def get_region_id(self, bxb_point, attempts=10):
        region_get_request = deepcopy(
            self._base_request
        )

        city_name = bxb_point.get('CityName')
        if not city_name:
            return

        region_get_request.url = self._api_url + 'regions.json'
        region_get_request.params.update({'name': city_name})

        rq = self.prepare_get(request=region_get_request)

        for _ in range(attempts):
            try:
                regions_response = self.send(rq)
            except ClientError:
                continue

            regions = regions_response.get('regions')

            if not regions:
                raise ClientError('No region {} was found in Yandex.API'.format(city_name))

            if len(regions) > 1:
                for region in regions:
                    region_id = None
                    found_areas = []
                    area_name = bxb_point.get('Area')

                    while 'parent' in region.keys():
                        if region.get('type') in ('TOWN', 'CITY', 'REPUBLIC_AREA') and not region_id:
                            region_id = region['id']
                        found_areas.append(region.get('name'))
                        region = region['parent']

                    if area_name in found_areas:
                        return region_id

            else:
                region = regions[0]
                while 'parent' in region.keys():
                    if region.get('type') in ('TOWN', 'CITY', 'REPUBLIC_AREA'):
                        return region['id']
                    region = region['parent']


def convert_region_names_for_yandex(point):
    area = point.get('Area')
    strong_normalized = False
    for item, replacement in STRONG_NORMALIZE.items():
        if item in area:
            area = area.replace(item, replacement)
            strong_normalized = True

    if not strong_normalized:
        if 'Респ' in area:
            area = 'Республика {}'.format(area)
        for item, replacement in REGULAR_NORMALIZE.items():
            area = area.replace(item, replacement)

    point['Area'] = area

    return point
