# restful.py
Python framework for rest services that sits on top of web.py and uses content negotiation to delegate through to methods

# Running
An example of web.py service bootrap can be found at [example_service.py](restful/example_service.py)

    $ python example_service.py

Request Examples:

	Request with no accept header
    $ curl http://localhost:8080/auth
    {"message": "Accept header */* is not a valid format.  Valid format: application/vnd.com.company.service.*.v<x>+<protocol> where <x> is the versionnumber and <protocol> is the protocol (i.e. json)", "code": "Invalid.AcceptHeader"}

    Request for non-existent resource
    $ curl -XPOST -H "Accept: application/vnd.com.restful.service.auth.v1+json" http://localhost:8080/auth
    {"message": "No handler exists for POST with accept header application/vnd.com.restful.service.auth.v1+json.", "code": ""}

    Request with accept header for resource that has no auth required
    $ curl -H "Accept: application/vnd.com.restful.service.auth.v1+json" http://localhost:8080/auth
    {"response": "GET_v1"}

    Request for resource that requires an auth header but none was supplied
    $ curl -XPOST -H "Accept: application/vnd.com.restful.service.echo.v1+json" http://localhost:8080/echo
    {"message": "No authorization header was supplied in the request and one is required.", "code": "Missing.AuthHeader"}

    Request with invalid auth header
    $ curl -XPOST -H "Accept: application/vnd.com.restful.service.echo.v1+json" -H "Authorization: 12345" http://localhost:8080/echo
    {"message": "The supplied authorization header 12345 is invalid.", "code": "Invalid.AuthHeader"}

    Request for POST resource with no body supplied
    $ curl -XPOST -H "Accept: application/vnd.com.restful.service.echo.v1+json" -H "Authorization: abcd-12345" http://localhost:8080/echo
    {"message": "A body is required for this svc call.", "code": "Missing.RequestBody"}

    Request for v1 resource
    $ curl -XPOST -H "Accept: application/vnd.com.restful.service.echo.v1+json" -H "Authorization: abcd-12345" http://localhost:8080/echo -d '{"foo":"bar"}'
    {"data": {"foo": "bar"}, "method": "POST_v1"}

    Request for v2 resource
    $ curl -XPOST -H "Accept: application/vnd.com.restful.service.echo.v2+json" -H "Authorization: abcd-12345" http://localhost:8080/echo -d '{"foo":"bar2"}'
    {"data": {"foo": "bar2"}, "method": "POST_v2"}