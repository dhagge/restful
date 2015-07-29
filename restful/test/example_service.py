'''
Sample launcher for restful web.py

@author: dhagge
'''
import sys
sys.path.insert(0, '../') # just manipulate path to allow importing of service

import web, service, uuid

''' provide custom auth handler (optional - only needed if auth is required) '''
valid_auth = ['abcd-12345']
def my_auth_handler(auth_header):
    return service.AuthValid if auth_header in valid_auth else service.AuthNotFound
service.auth_handler = my_auth_handler

''' provide custom audit handler (optional - only if audit trail is needed) '''
def my_audit_handler(path, http_method, http_payload, response):
    pass # do whatever - i.e. log to DB
service.audit_handler = my_audit_handler

''' provide custom session handler (optional - only needed if session management is required) '''
class SessionHandler():
    def setup(self): pass
    def committ(self): pass
    def rollback(self): pass
    def close(self): pass
service.session_handler = SessionHandler()

class AuthService(service.ServiceParent):
    ''' A resource class which does NOT require an auth header '''

    @service.attributes("application/vnd.com.restful.service.auth.v1", auth_required=False)
    def GET_v1(self):
        auth = uuid.uuid1()
        valid_auth.append(auth)
        return { 'auth': auth }

class EchoService(service.ServiceParent):
    ''' A resource class with methods that DO require an auth header '''

    @service.attributes("application/vnd.com.restful.service.echo.v1")
    def POST_v1(self, *args, **kwargs):
        data = self._get_request_body()
        return { 'method': 'POST_v1', 'data': data}

    @service.attributes("application/vnd.com.restful.service.echo.v2")
    def POST_v2(self, *args, **kwargs):
        data = self._get_request_body()
        return { 'method': 'POST_v2', 'data': data}

    @service.attributes("application/vnd.com.restful.service.echo.v1")
    def PUT_v1(self, *args, **kwargs):
        data = self._get_request_body()
        return { 'method': 'PUT_v1', 'data': data}

''' init web.py '''
urls = (
    '/auth', 'AuthService',
    '/echo', 'EchoService'
)

webapp = web.application(urls, globals())
# mod_wsgi convention looks for a wsgifunc variable named 'application'
application = webapp.wsgifunc()

# startup in non-wsgi mode (i.e. from command line or in IDE)
if __name__ == '__main__':
    web.httpserver.runbasic(webapp.wsgifunc(), ("0.0.0.0", 8080))
