'''
Define restful semantics.

@author: damianhagge
'''
import inspect, json, web, logging, traceback


from datetime import datetime

mime_formatters = {
    "json": lambda val: json.dumps(val),
    "text": lambda val: val
}

""" Setup handlers which will be called when services are invoked """

AuthValid, AuthNotFound, AuthExpired = range(3)
auth_handler = lambda *args: True

audit_handler = lambda *args: None

#setup a dummy session
class Object(object):
    pass
session = Object()
session.setup = lambda *args: None
session.commit = lambda *args: None
session.rollback = lambda *args: None
session.close = lambda *args: None

class ServiceParent(object):
    '''
    Class that handles HTTP methods and delegates to child methods
    that declare (via decorators) that they handle the appropriate
    Accept header
    '''

    def GET(self, *args, **kwargs):
        return self._delegate('GET', *args, **kwargs)

    def POST(self, *args, **kwargs):
        return self._delegate('POST', *args, **kwargs)

    def PUT(self, *args, **kwargs):
        return self._delegate('PUT', *args, **kwargs)

    def DELETE(self, *args, **kwargs):
        return self._delegate('DELETE', *args, **kwargs)

    def _delegate(self, http_method, *args, **kwargs):
#        import pdb; pdb.set_trace()
        try:
            session.setup() # init any sessions (i.e. for DB transactions, etc.)

            print 'Handling request: %s %s/%s' % (web.ctx.method, web.ctx.home, web.ctx.fullpath)

            methods = self._find_methods(http_method)

            accept_header, accept, fmt = self._parse_accept_header()

            method = [m for m in methods if hasattr(m, '_accept_decorator') and m._accept_decorator == accept]
            if not method:
                raise self._create_rest_error(web.NotAcceptable(), '',
                                            'No handler exists for %s with accept header %s.' % (http_method, accept_header))

            mime_formatter = mime_formatters.get(fmt)
            if not mime_formatter:
                raise self._create_rest_error(web.NotAcceptable, 'Invalid.MimeType',
                                            'No handler exists for mime type %s in header %s.' % (format, accept_header))

            method = method[0]
            print 'Delegating %s call to %s for accept header %s' % (http_method, method.__name__, accept_header)

            if method._auth_required == True:
                self._verify_auth_header(method)

            response = method(self, *args, **kwargs)

            try:
                if isinstance(response, dict) or isinstance(response, list): # plain dict to encode as json
                    response = mime_formatter(response) # object with data payload
                elif hasattr(response, 'data'):
                    setattr(response, 'message', mime_formatter(response.data))
            except:
                print 'Could not generate json for data: %s' % response
            web.header('Content-Type', accept_header)

            print 'Returning response: %s' % truncate(response)

            # log in the service_audit_log:
            self._audit_log(http_method, accept_header, response)

            session.commit()
            return response

        except Exception, e:
            session.rollback()
            if isinstance(e, web.HTTPError):
                # log in the service_audit_log:
                self._audit_log(http_method, '', '%s' % e)

                payload = None
                if hasattr(e, 'data'):
                    payload = e.data

                print 'Returning rest error: %s, payload: %s' % (e, payload)
                raise
            else: # system exception
                print 'Error invoking rest service method, returning system exception.'
                print(traceback.format_exc())
                raise web.InternalError(json.dumps({'code':'System.Error', 'message':'A system error occurred.'}))
        finally:
            session.close()

    def _parse_accept_header(self):
        accept_header = web.ctx.env.get('HTTP_ACCEPT', None)
        if accept_header is None:
            raise self._create_rest_error(web.NotAcceptable, 'Missing.AcceptHeader', 'No accept header was supplied in the request and one is required.')
        accept_header_parts = str(accept_header).split('+')
        if len(accept_header_parts) is not 2:
            raise self._create_rest_error(web.NotAcceptable, 'Invalid.AcceptHeader',
                                        'Accept header %s is not a valid format.  Valid format: ' % accept_header + \
                                        'application/vnd.com.company.service.*.v<x>+<protocol> where <x> is the version' + \
                                        'number and <protocol> is the protocol (i.e. json)')
        return accept_header, accept_header_parts[0], accept_header_parts[1]

    def _verify_auth_header(self, method):
        auth_header = web.ctx.env.get('HTTP_AUTHORIZATION', None)
        if auth_header is None:
            raise self._create_rest_error(web.NotAcceptable, 'Missing.AuthHeader', 'No authorization header was supplied in the request and one is required.')

        auth_status = auth_handler(auth_header)
        if auth_status == AuthNotFound:
            raise self._create_rest_error(web.NotAcceptable, 'Invalid.AuthHeader',
                                          'The supplied authorization header %s is invalid.' % auth_header)
        elif auth_status == AuthExpired:
            raise self._create_rest_error(web.NotAcceptable, 'Expired.Auth',
                                          'The supplied authorization header %s is expired.' % auth_header)

    def _find_methods(self, method):
        '''
            Find all methods that start with the name as the supplied method
            i.e. self.findMethod('GET') will find all methods that match 'GET_*'
        '''
        def method_starts_with(obj):
            return hasattr(obj, '__call__') and hasattr(obj, '__name__') and obj.__name__.startswith(method + "_")
        # don't return the tuple - return the actual method which is tuple[1]
        return [m[1] for m in inspect.getmembers(type(self), method_starts_with)]

    def _create_rest_error(self, error, code, message, payload=None):
        if payload == None: payload = {}
        print 'Creating rest error code: %s, message: %s, payload: %s' % (code, message, payload)
        payload['code'] = code;
        payload['message'] = message;
        error.message = json.dumps(payload)
        error.data = error.message
        return error

    def _get_request_body(self):
        data = str(web.data())
        if not data:
            raise self._create_rest_error(web.BadRequest, 'Missing.RequestBody', 'A body is required for this svc call.')
        return json.loads(data)

    def _audit_log(self, http_method, accept_header, response):
        http_payload = ""
        if http_method == "GET" and web.ctx.query != "":
            http_payload = web.ctx.query
        elif http_method in ["POST", "PUT", "DELETE"]:
            http_payload = web.data()
        path = web.ctx.homepath + web.ctx.path

        audit_handler(path, http_method, http_payload, response)

def truncate(val):
    '''Trim the string if it's greater than 500 chars - we don't want to fill the logs with too paylaod responses'''
    max = 2000
    return (val[:max] + '...') if len(val) > max else val

def attributes(accept, **kwargs):
    """Specifies the following attributes for the restful endpoint:
        accept: the value of the Accept version header that this method takes
        auth_required: if true this method requires auth
    Example:
    .. code-block:: python

        import restful
        class SomeController(ServiceParent):

            @restful.attributes("application/vnd.com.company.service.auth.v1+json",
                                auth_required=True)
            def comment(self, id):

    """
    def register_decorator(method):
        """Register the decorator as a private attribute of the method"""
        method._accept_decorator = accept
        method._auth_required = kwargs.get('auth_required', True)
        return method
    return register_decorator
