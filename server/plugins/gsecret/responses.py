from pydantic import BaseModel


class SecretData(BaseModel):
    key: str
    id: str
    value: str
    
class NotSupportedData(BaseModel):
    detail: str = "Not Supported"

class UnauthorisedData(BaseModel):
    detail: str

class SecretNotFoundData(BaseModel):
    detail: str = "Secret not found"
