from typing import Optional, Any, Dict, List

from pydantic import BaseModel


class Calculator(BaseModel):
    name: str


class Variable(BaseModel):
    name: str
    tag_name: str
    description: Optional[str] = None
    data_type: str = 'str'
    default_value: Any = None
    formula: Optional[str] = None
    widget: Optional[str] = None
    choices: Optional[List[str]] = None
    is_output: bool = False
    required: bool = False
    order: int = 1
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
