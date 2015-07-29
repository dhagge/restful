'''
Tests for the restful framework component

@author: damianhagge
'''
import json

import datetime, time, web, service
from nose.tools import eq_, ok_

not_found_auth_header = '12345'
expired_auth_header = 'ebd66f0d-6709-42ab-9a84-e9527d0d8e1d'

class TestRestful():

    def setup(self):
        """ init web.py """
        urls = (
            '/', 'TestService',
            '/foo/(.+)', 'TestService2'
        )
        self.app = web.application(urls, globals())

        def auth_handler(auth_header):
            if auth_header == not_found_auth_header:
                return service.AuthNotFound
            elif auth_header == expired_auth_header:
                return service.AuthExpired
            else:
                return service.AuthValid
        service.auth_handler = auth_handler

    def test_GET_v1(self):
        response = self.app.request('/', 'GET', headers = {'Accept': 'application/vnd.com.company.service.test.v1+json'})
        eq_(response.status, '200 OK')
        eq_(response.data, '{"payload": "GET_v1"}')

    def test_GET_bad_accept_header(self):
        response = self.app.request('/', 'GET', headers = {'Accept': 'application/vnd.com.company.service.test.v22+json'})
        eq_(response.status, '406 Not Acceptable')

    def test_GET_v2_with_audit_handler(self):
        original_audit_handler = service.audit_handler

        try:
            def audit_handler(*args):
                eq_(args[0], '/') # path
                eq_(args[1], 'GET') # http_method
                eq_(args[2], '') # http_payload
                eq_(args[3], 'GET_v2') # response
            service.audit_handler = audit_handler

            response = self.app.request('/', 'GET', headers = {'Accept': 'application/vnd.com.company.service.test.v2+json',
                                                               'Authorization': '30e986a5-0429-45ef-9295-faf9a3775907'})
            eq_(response.status, '200 OK')
            eq_(response.data, 'GET_v2')
        finally:
            service.audit_handler = original_audit_handler

    def test_GET_v2_no_auth_header(self):
        response = self.app.request('/', 'GET', headers = {'Accept': 'application/vnd.com.company.service.test.v2+json'})
        eq_(response.status, '406 Not Acceptable')

    def test_POST_v1(self):
        response = self.app.request('/', 'POST', headers = {'Accept': 'application/vnd.com.company.service.test.v1+json'})
        eq_(response.status, '200 OK')

    def test_PUT_v1(self):
        original_audit_handler = service.audit_handler

        try:
            def audit_handler(*args):
                eq_(args[0], '/') # path
                eq_(args[1], 'PUT') # http_method
                eq_(args[2], '{"foo":"bar"}') # http_payload
                eq_(args[3], 'PUT_v1') # response
            service.audit_handler = audit_handler

            response = self.app.request('/', 'PUT', data='{"foo":"bar"}',
                                        headers = {'Accept': 'application/vnd.com.company.service.test.v1+json',
                                                   'Authorization': '30e986a5-0429-45ef-9295-faf9a3775907'})
            eq_(response.status, '200 OK')
            eq_(response.data, 'PUT_v1')
        finally:
            service.audit_handler = original_audit_handler

    def test_PUT_v1_no_auth_header(self):
        response = self.app.request('/', 'PUT', headers = {'Accept': 'application/vnd.com.company.service.test.v1+json'})
        eq_(response.status, '406 Not Acceptable')

    def test_DELETE_v1_bad_accept_header(self):
        response = self.app.request('/', 'DELETE',  headers = {'Accept': 'application/vnd.com.company.service.test.v1+json'})
        eq_(response.status, '406 Not Acceptable')

    def test_DELETE_v1(self):
        response = self.app.request('/', 'DELETE', headers = {'Accept': 'application/vnd.com.company.service.test.v3+json'})
        eq_(response.status, '200 OK')
        eq_(response.data, 'DELETE_v3')

    def test_DELETE_v1_invalid_mime_extention(self):
        response = self.app.request('/', 'DELETE', headers = {'Accept': 'application/vnd.com.company.service.test.v3+html'})
        eq_(response.status, '406 Not Acceptable')

    def test_GET_v1_no_mime_type(self):
        response = self.app.request('/', 'GET', headers = {'Accept': 'application/vnd.com.company.service.test.v1'})
        eq_(response.status, '406 Not Acceptable')

    def test_argumentUnpacking_andDictPayload(self):
        response = self.app.request('/foo/12345A', 'GET', headers = {'Accept': 'application/vnd.com.company.service.test.v1+json'})
        eq_(response.status, '200 OK')
        eq_(response.data, '{"payload": "GET_v1 12345A"}')

    def test_restfulError(self):
        response = self.app.request('/foo/12345A', 'PUT', headers = {'Accept': 'application/vnd.com.company.service.test.v1+json'})
        eq_(response.status, '400 Bad Request')
        data = json.loads(response.data)
        eq_(data['code'], 'NotFound.Foo')
        eq_(data['message'], 'message')

    def test_systemError(self):
        response = self.app.request('/foo/12345A', 'POST', headers = {'Accept': 'application/vnd.com.company.service.test.v1+json'})
        eq_(response.status, '500 Internal Server Error')
        data = json.loads(response.data)
        eq_(data['code'], 'System.Error')
        eq_(data['message'], 'A system error occurred.')

    def test_GET_v2_auth_header_non_existent(self):
        response = self.app.request('/', 'GET', headers = {'Accept': 'application/vnd.com.company.service.test.v2+json',
                                                           'Authorization': not_found_auth_header})
        eq_(response.status, '406 Not Acceptable')
        data = json.loads(response.data)
        eq_(data['code'], 'Invalid.AuthHeader')

    def test_GET_v2_auth_header_expired_auth(self):
        response = self.app.request('/', 'GET', headers = {'Accept': 'application/vnd.com.company.service.test.v2+json',
                                                           'Authorization': expired_auth_header})
        eq_(response.status, '406 Not Acceptable')
        data = json.loads(response.data)
        eq_(data['code'], 'Expired.Auth')

class TestService(service.ServiceParent):
    """
    Restful service class for testing various endpoint-attribute combinations
    """
    def __init__(self):
        super(TestService, self).__init__()

    @service.attributes("application/vnd.com.company.service.test.v1", auth_required=False)
    def GET_v1(self):
        return dict({'payload':'GET_v1'})

    @service.attributes("application/vnd.com.company.service.test.v2")
    def GET_v2(self):
        return "GET_v2"

    @service.attributes("application/vnd.com.company.service.test.v1", auth_required=False)
    def POST_v1(self):
        return dict({"payload":"POST_v1","value":"another"})

    @service.attributes("application/vnd.com.company.service.test.v1", auth_required=True)
    def PUT_v1(self):
        return "PUT_v1"

    @service.attributes("application/vnd.com.company.service.test.v3", auth_required=False)
    def DELETE_v3(self):
        return "DELETE_v3"

class TestService2(service.ServiceParent):
    """
    Restful service class for testing argument unpacking
    """
    def __init__(self):
        super(TestService2, self).__init__()

    @service.attributes("application/vnd.com.company.service.test.v1", auth_required=False)
    def GET_v1(self, bar):
        return dict({'payload':'GET_v1 ' + str(bar)})

    @service.attributes("application/vnd.com.company.service.test.v1", auth_required=False)
    def PUT_v1(self, bar):
        raise self._create_rest_error(web.BadRequest, 'NotFound.Foo', 'message')

    @service.attributes("application/vnd.com.company.service.test.v1", auth_required=False)
    def POST_v1(self, bar):
        raise Exception()

