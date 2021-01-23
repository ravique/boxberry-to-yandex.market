import json

import pytest
import requests
import requests_mock

from client import Client, BoxberryClient
from errors import ClientError, ClientConnectionError, BoxberryError


# class TestClient:
#     def setup(self):
#         self.client = Client()
#         self.client._base_request = requests.Request(url='http://example.com')
#
#     def test_prepare_get(self):
#         r = self.client.prepare_get()
#         assert r.method == 'GET'
#         assert r.url == 'http://example.com/'
#
#         r2 = self.client.prepare_get(request=requests.Request(url='http://example2.com'))
#         assert r2.url == 'http://example2.com/'
#
#     def test_prepare_post(self):
#         r = self.client.prepare_post(payload={'foo': 'bar'}, request=requests.Request(url='http://example2.com'))
#
#         assert r.method == 'POST'
#         assert json.loads(r.body) == {'foo': 'bar'}
#         assert r.url == 'http://example2.com/'
#
#     def test_prepare_put(self):
#         r = self.client.prepare_put(payload={'foo': 'bar'}, request=requests.Request(url='http://example2.com'))
#         assert r.method == 'PUT'
#         assert json.loads(r.body) == {'foo': 'bar'}
#         assert r.url == 'http://example2.com/'
#
#     def test_prepare_delete(self):
#         r = self.client.prepare_delete(request=requests.Request(url='http://example2.com'))
#
#         assert r.method == 'DELETE'
#         assert r.url == 'http://example2.com/'
#
#     def test_send_get(self):
#         with requests_mock.Mocker() as m:
#             m.get('http://example.com', text=json.dumps({'foo': 'bar'}))
#             r = self.client.prepare_get()
#
#             assert self.client.send(prepared_request=r) == {'foo': 'bar'}
#
#     def test_send_get_500(self):
#         with requests_mock.Mocker() as m:
#             m.get('http://example.com', status_code='500')
#             r = self.client.prepare_get()
#             with pytest.raises(ClientConnectionError):
#                 self.client.send(prepared_request=r, max_attempts=1)
#
#     def test_send_get_404(self):
#         with requests_mock.Mocker() as m:
#             m.get('http://example.com', status_code='404')
#             r = self.client.prepare_get()
#             with pytest.raises(ClientConnectionError):
#                 self.client.send(prepared_request=r, max_attempts=1)
#
#     def test_send_get_400(self):
#         with requests_mock.Mocker() as m:
#             m.get('http://example.com', status_code='401')
#             r = self.client.prepare_get()
#             with pytest.raises(ClientError):
#                 self.client.send(prepared_request=r, max_attempts=1)
#
#     def test_send_get_connection_error(self):
#         with requests_mock.Mocker() as m:
#             m.get('http://example.com', exc=ConnectionError)
#             r = self.client.prepare_get()
#             with pytest.raises(ConnectionError):
#                 self.client.send(prepared_request=r, max_attempts=1)
#
#     def test_send_post(self):
#         with requests_mock.Mocker() as m:
#             m.post('http://example.com', text=json.dumps({'foo': 'bar'}))
#             r = self.client.prepare_post()
#
#             assert self.client.send(prepared_request=r) == {'foo': 'bar'}


class TestBoxberryClient:
    def setup(self):
        self.client = BoxberryClient(token='32768', api_url='http://example.com')
        # self.client._base_request = requests.Request(url='http://example.com')

    def test_send_get_402(self):
        with requests_mock.Mocker() as m:
            m.get('http://example.com', status_code='402')
            r = self.client.prepare_get()
            with pytest.raises(ClientConnectionError):
                self.client.send(prepared_request=r, max_attempts=1)

    def test_check_and_convert_response(self):
        with requests_mock.Mocker() as m:
            m.get('http://example.com', status_code=400, text=json.dumps({
                'err': 'any error'
            }))
            response = requests.get('http://example.com')

            with pytest.raises(BoxberryError):
                self.client.check_and_convert_response(response)
