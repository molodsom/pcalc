from pydantic import BaseModel
from typing import List, Dict, Any


class Service(BaseModel):
    name: str
    variables: List[str]
    formula: str


class CalculationRequest(BaseModel):
    service_name: str
    parameters: Dict[str, Any]
