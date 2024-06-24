import re

import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from pymongo import MongoClient
from bson import ObjectId

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = MongoClient("mongodb://127.0.0.1:27017/")
db = client["calculator_db"]


class Calculator(BaseModel):
    name: str


class Variable(BaseModel):
    calculator_id: str
    tag_name: str
    name: str
    description: Optional[str] = None
    data_type: str
    default_value: Any
    choices: Optional[List[Any]] = None
    order: int
    widget: Optional[str] = None
    formula: Optional[str] = None
    is_output: bool = False
    required: bool = False


class Price(BaseModel):
    calculator_id: str
    tag_name: str
    price: float
    extra: Optional[Dict[str, Any]] = None
    description: Optional[str] = None
    order: int


class Template(BaseModel):
    calculator_id: str
    html: str


def get_price(tag_name: str, context: Dict[str, Any], prices: List[Dict[str, Any]], fallback_value=0.0):
    value = fallback_value
    for price in prices:
        if price['tag_name'] == tag_name:
            if check_extra_conditions(price.get("extra", {}), context):
                value = price['price']
    return value


def eval_formula(formula: str, context: Dict[str, Any], prices: List[Dict[str, Any]]) -> Any:
    formula = formula.replace("if", "np.where").replace(";", ",")

    def price(tag_name: str, fallback_value=0.0):
        return get_price(tag_name, context, prices, fallback_value)

    for key, value in context.items():
        pattern = r'\b' + re.escape(key) + r'\b'
        formula = re.sub(pattern, str(value), formula)

    try:
        local_context = {"np": np, "price": price}
        return eval(formula, {}, local_context)
    except Exception as e:
        print(f"Error evaluating formula: {formula} with context {context} - {e}")
        return


def check_extra_conditions(extra: Dict[str, Any], context: Dict[str, Any]) -> bool:
    if not extra:
        return True
    for key, value in extra.items():
        if key.endswith("__gte"):
            actual_key = key[:-5]
            if actual_key in context and context[actual_key] < value:
                return False
        elif key.endswith("__lte"):
            actual_key = key[:-5]
            if actual_key in context and context[actual_key] > value:
                return False
        elif key.endswith("__gt"):
            actual_key = key[:-4]
            if actual_key in context and context[actual_key] <= value:
                return False
        elif key.endswith("__lt"):
            actual_key = key[:-4]
            if actual_key in context and context[actual_key] >= value:
                return False
        elif key.endswith("__eq"):
            actual_key = key[:-4]
            if actual_key in context and context[actual_key] != value:
                return False
        elif key.endswith("__ne"):
            actual_key = key[:-4]
            if actual_key in context and context[actual_key] == value:
                return False
        elif key.endswith("__in"):
            actual_key = key[:-4]
            if actual_key in context and context[actual_key] not in value:
                return False
        else:
            if key in context and context[key] != value:
                return False
    return True


@app.get("/calculator")
async def get_calculators():
    calculators = list(db.calculators.find())
    for calculator in calculators:
        calculator["_id"] = str(calculator["_id"])
    return calculators


@app.get("/calculator/{calculator_id}")
async def get_calculator(calculator_id: str):
    calculator = db.calculators.find_one({"_id": ObjectId(calculator_id)})
    if not calculator:
        raise HTTPException(status_code=404, detail="Calculator not found")
    calculator["_id"] = str(calculator["_id"])
    return calculator


@app.post("/calculator")
async def create_calculator(calculator: Calculator):
    result = db.calculators.insert_one(calculator.dict())
    return {"_id": str(result.inserted_id)}


@app.post("/calculator/{calculator_id}/variable")
async def create_variable(calculator_id: str, variable: Variable):
    variable.calculator_id = calculator_id
    result = db.variables.insert_one(variable.dict())
    return {"_id": str(result.inserted_id)}


@app.post("/calculator/{calculator_id}/price")
async def create_price(calculator_id: str, price: Price):
    price.calculator_id = calculator_id
    result = db.prices.insert_one(price.dict())
    return {"_id": str(result.inserted_id)}


@app.delete("/calculator/{calculator_id}")
async def delete_calculator(calculator_id: str):
    result = db.calculators.delete_one({"_id": ObjectId(calculator_id)})
    db.variables.delete_many({"calculator_id": calculator_id})
    db.prices.delete_many({"calculator_id": calculator_id})
    return {"deleted_count": result.deleted_count}


@app.get("/calculator/{calculator_id}/variable")
async def get_variables(calculator_id: str):
    variables = list(db.variables.find({"calculator_id": calculator_id}).sort("order", 1))
    for variable in variables:
        variable["_id"] = str(variable["_id"])
    if not variables:
        raise HTTPException(status_code=404, detail="Variables not found for the given calculator_id")
    return variables


@app.get("/calculator/{calculator_id}/variable/{variable_id}")
async def get_variable(calculator_id: str, variable_id: str):
    variable = db.variables.find_one({"calculator_id": calculator_id, "_id": ObjectId(variable_id)})
    if not variable:
        raise HTTPException(status_code=404, detail="Variable not found for the given calculator_id and variable_id")
    return variable


@app.put("/calculator/{calculator_id}/variable")
async def update_variables(calculator_id: str, variables: List[Variable]):
    db.variables.delete_many({"calculator_id": calculator_id})
    db.variables.insert_many([var.dict() for var in variables])
    return {"message": "Variables updated successfully"}


@app.post("/calculator/{calculator_id}/variable")
async def create_variables(calculator_id: str, variables: List[Variable]):
    for variable in variables:
        variable.calculator_id = calculator_id
    result = db.variables.insert_many([var.dict() for var in variables])
    return {"inserted_ids": [str(id) for id in result.inserted_ids]}


@app.patch("/calculator/{calculator_id}/variable/{variable_id}")
async def patch_variable(calculator_id: str, variable_id: str, variable: Variable):
    result = db.variables.update_one({"calculator_id": calculator_id, "_id": ObjectId(variable_id)},
                                     {"$set": variable.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Variable not found")
    return {"message": "Variable patched successfully"}


@app.delete("/calculator/{calculator_id}/variable/{variable_id}")
async def delete_variable(calculator_id: str, variable_id: str):
    result = db.variables.delete_one({"calculator_id": calculator_id, "_id": ObjectId(variable_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Variable not found")
    return {"message": "Variable deleted successfully"}


@app.get("/calculator/{calculator_id}/price")
async def get_prices(calculator_id: str):
    prices = list(db.prices.find({"calculator_id": calculator_id}).sort("order", 1))
    for price in prices:
        price["_id"] = str(price["_id"])
    if not prices:
        raise HTTPException(status_code=404, detail="Prices not found for the given calculator_id")
    return prices


@app.get("/calculator/{calculator_id}/price/{price_id}")
async def get_price(calculator_id: str, price_id: str):
    price = db.prices.find_one({"calculator_id": calculator_id, "_id": ObjectId(price_id)})
    if not price:
        raise HTTPException(status_code=404, detail="Price not found for the given calculator_id and price_id")
    return price


@app.put("/calculator/{calculator_id}/price")
async def update_prices(calculator_id: str, prices: List[Price]):
    db.prices.delete_many({"calculator_id": calculator_id})
    for price in prices:
        price.calculator_id = calculator_id
    db.prices.insert_many([price.dict() for price in prices])
    return {"message": "Prices updated successfully"}


@app.patch("/calculator/{calculator_id}/price")
async def patch_prices(calculator_id: str, prices: List[Price]):
    for price in prices:
        db.prices.update_one({"calculator_id": calculator_id, "_id": ObjectId(price.id)}, {"$set": price.dict()})
    return {"message": "Prices patched successfully"}


@app.patch("/calculator/{calculator_id}/price/{price_id}")
async def patch_price(calculator_id: str, price_id: str, price: Price):
    result = db.prices.update_one({"calculator_id": calculator_id, "_id": ObjectId(price_id)}, {"$set": price.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Price not found")
    return {"message": "Price patched successfully"}


@app.delete("/calculator/{calculator_id}/price/{price_id}")
async def delete_price(calculator_id: str, price_id: str):
    result = db.prices.delete_one({"calculator_id": calculator_id, "_id": ObjectId(price_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Price not found")
    return {"message": "Price deleted successfully"}


@app.post("/template/")
async def create_template(template: Template):
    result = db.templates.insert_one(template.dict())
    return {"_id": str(result.inserted_id)}


@app.post("/calculator/{calculator_id}")
async def calculate(calculator_id: str, input_data: Dict[str, Any], as_html: Optional[bool] = False):
    calculator = db.calculators.find_one({"_id": ObjectId(calculator_id)})
    if not calculator:
        raise HTTPException(status_code=404, detail="Calculator not found")

    variables = list(db.variables.find({"calculator_id": calculator_id}))
    prices = list(db.prices.find({"calculator_id": calculator_id}))

    variables.sort(key=lambda x: x['order'])
    prices.sort(key=lambda x: x['order'])

    context = input_data.copy()

    for variable in variables:
        tag_name = variable.get('tag_name', '').lower()
        formula = variable.get('formula')
        if variable["widget"] and tag_name not in context:
            raise HTTPException(status_code=400, detail=f"Missing input for {tag_name}")
        if formula:
            context[tag_name] = eval_formula(formula, context, prices)
        else:
            context[tag_name] = input_data.get(tag_name, variable["default_value"])

    output = []
    for variable in variables:
        tag_name = variable.get('tag_name', '').lower()
        value = context[tag_name]
        if variable["is_output"] and context[tag_name]:
            if isinstance(value, float) or variable["data_type"] == "float":
                value = "{0:.2f}".format(np.round(context[tag_name], 2))
            output.append({
                "name": variable["name"],
                "tag_name": tag_name,
                "value": value
            })

    if as_html:
        template = db.templates.find_one({"calculator_id": calculator_id})
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        html_output = template["html"]
        for key, value in context.items():
            html_output = html_output.replace(f"{{{{ {key} }}}}", str(value))
        return {"html": html_output}

    return output


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
