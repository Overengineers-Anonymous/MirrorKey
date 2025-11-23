from shatter_api import RequestQueryParams, RequestHeaders


class AuthHeader(RequestHeaders):
    authorization: str

class KeyQueryParams(RequestQueryParams):
    key: str

class IDQueryParams(RequestQueryParams):
    id: str

class WriteSecretIdQueryParams(RequestQueryParams):
    value: str

class WriteSecretKeyQueryParams(RequestQueryParams):
    key: str
    value: str
