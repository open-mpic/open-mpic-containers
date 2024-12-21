import requests


# not a mock client, but a real client for live API testing
class TestingApiClient:
    def __init__(self):
        self.service_base_url = "http://localhost:8000/mpic-coordinator"
        self._session = requests.Session()

    def get(self, url_suffix):
        return self._session.get(self.service_base_url + '/' + url_suffix)

    def post(self, url_suffix, data):
        headers = {
            'content-type': 'application/json',
        }
        response = self._session.post(self.service_base_url + '/' + url_suffix, headers=headers, data=data)
        return response

    def close(self):
        self._session.close()
