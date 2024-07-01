from typing import Optional, Any, Dict

from pydantic import BaseModel


class Calculator(BaseModel):
    name: str


class Variable(BaseModel):
    name: str
    tag_name: str
    description: Optional[str] = None
    data_type: str
    default_value: Any
    formula: Optional[str] = None
    widget: Optional[str] = None
    is_output: bool
    required: bool
    order: int
    calculator_id: Optional[str] = None


class Price(BaseModel):
    description: str
    tag_name: str
    price: float
    extra: Optional[Dict[str, Any]] = None
    order: int
    calculator_id: Optional[str] = None


class Template(BaseModel):
    calculator_id: str
    html: str
