import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Any, Dict
from bson import ObjectId

import models
from helpers import get_all_variables, validate_all_formulas, eval_formula
from settings import db

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


@app.get("/calculator")
async def get_calculators():
    calculators = list(db.calculators.find())
    for calculator in calculators:
        calculator["_id"] = str(calculator["_id"])
    return calculators


@app.post("/calculator")
async def create_calculator(calculator: models.Calculator):
    result = db.calculators.insert_one(calculator.dict())
    return {"_id": str(result.inserted_id)}


@app.get("/calculator/{calculator_id}")
async def get_calculator(calculator_id: str):
    calculator = db.calculators.find_one({"_id": ObjectId(calculator_id)})
    if not calculator:
        raise HTTPException(status_code=404, detail="Calculator not found")
    calculator["_id"] = str(calculator["_id"])
    return calculator


@app.post("/calculator/{calculator_id}/variable")
async def create_variable(calculator_id: str, variables: List[models.Variable]):
    existing_variables = get_all_variables(calculator_id)
    all_variables = existing_variables + [v.dict() for v in variables]

    for variable in variables:
        variable.calculator_id = calculator_id
        if variable.formula:
            errors = validate_all_formulas(calculator_id, [models.Variable(**v) for v in all_variables])
            if errors:
                error_messages = [f"Error in variable {tag_name}: {error}" for tag_name, error in errors]
                raise HTTPException(status_code=400, detail="; ".join(error_messages))
        db.variables.insert_one({**variable.dict(), "calculator_id": calculator_id})
    return {"message": "Variables added successfully"}


@app.post("/calculator/{calculator_id}/price")
async def create_price(calculator_id: str, price: models.Price):
    price.calculator_id = calculator_id
    result = db.prices.insert_one(price.dict())
    return {"_id": str(result.inserted_id)}


@app.get("/calculator/{calculator_id}/variable")
async def get_variables(calculator_id: str):
    variables = list(db.variables.find({"calculator_id": calculator_id}).sort("order", 1))
    for variable in variables:
        variable["_id"] = str(variable["_id"])
    return variables


@app.get("/calculator/{calculator_id}/variable/{variable_id}")
async def get_variable(calculator_id: str, variable_id: str):
    variable = db.variables.find_one({"calculator_id": calculator_id, "_id": ObjectId(variable_id)})
    if not variable:
        raise HTTPException(status_code=404, detail="Variable not found for the given calculator_id and variable_id")
    return variable


@app.put("/calculator/{calculator_id}/variable")
async def update_variables(calculator_id: str, variables: List[models.Variable]):
    db.variables.delete_many({"calculator_id": calculator_id})
    db.variables.insert_many([var.dict() for var in variables])
    return {"message": "Variables updated successfully"}


@app.patch("/calculator/{calculator_id}/variable/{variable_id}")
async def update_variable(calculator_id: str, variable_id: str, variable: models.Variable):
    variable.calculator_id = calculator_id

    existing_variables = get_all_variables(calculator_id)
    updated_variables = []
    for v in existing_variables:
        if str(v["_id"]) == variable_id:
            updated_variables.append(variable.dict())
        else:
            updated_variables.append(v)

    if variable.formula:
        errors = validate_all_formulas(calculator_id, [models.Variable(**v) for v in updated_variables])
        if errors:
            error_messages = [f"Error in variable {tag_name}: {error}" for tag_name, error in errors]
            raise HTTPException(status_code=400, detail="; ".join(error_messages))

    update_result = db.variables.update_one(
        {"_id": ObjectId(variable_id)},
        {"$set": {**variable.dict(), "calculator_id": calculator_id}}
    )
    if update_result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Variable not found or no changes detected")
    return {"message": "Variable updated successfully"}


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
    return prices


@app.get("/calculator/{calculator_id}/price/{price_id}")
async def get_price(calculator_id: str, price_id: str):
    price = db.prices.find_one({"calculator_id": calculator_id, "_id": ObjectId(price_id)})
    if not price:
        raise HTTPException(status_code=404, detail="Price not found for the given calculator_id and price_id")
    return price


@app.put("/calculator/{calculator_id}/price")
async def update_prices(calculator_id: str, prices: List[models.Price]):
    db.prices.delete_many({"calculator_id": calculator_id})
    for price in prices:
        price.calculator_id = calculator_id
    db.prices.insert_many([price.dict() for price in prices])
    return {"message": "Prices updated successfully"}


@app.patch("/calculator/{calculator_id}/price")
async def patch_prices(calculator_id: str, prices: List[models.Price]):
    for price in prices:
        db.prices.update_one({"calculator_id": calculator_id, "_id": ObjectId(price.id)}, {"$set": price.dict()})
    return {"message": "Prices patched successfully"}


@app.patch("/calculator/{calculator_id}/price/{price_id}")
async def patch_price(calculator_id: str, price_id: str, price: models.Price):
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


@app.post("/calculator/{calculator_id}/template")
async def create_template(calculator_id: str, template: models.Template):
    template_data = template.dict()
    template_data["calculator_id"] = calculator_id
    result = db.templates.insert_one(template_data)
    return {"_id": str(result.inserted_id)}


@app.get("/calculator/{calculator_id}/template")
async def get_template(calculator_id: str):
    template = db.templates.find_one({"calculator_id": calculator_id})
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@app.put("/calculator/{calculator_id}/template")
async def update_template(calculator_id: str, template: models.Template):
    result = db.templates.update_one(
        {"calculator_id": calculator_id},
        {"$set": {"html": template.html}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template updated successfully"}


@app.delete("/calculator/{calculator_id}/template")
async def delete_template(calculator_id: str):
    result = db.templates.delete_one({"calculator_id": calculator_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Template not found")
    return {"message": "Template deleted successfully"}


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
