from pydantic import BaseModel, Field, ConfigDict
from typing import Generic, TypeVar

T = TypeVar("T")

class BaseResponse(BaseModel, Generic[T]):
    model_config = ConfigDict(json_schema_extra={"required": ["code", "err_msg", "data"]})

    code: int = Field(200, description="状态码")
    err_msg: str = Field('', description="错误信息")
    data: T
