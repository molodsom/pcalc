from typing import Dict, Any, List
import re

import numpy as np
from bson import ObjectId

import models
from settings import db


def validate_formula(formula: str, context: Dict[str, Any]):
    try:
        eval(formula, {}, context)
    except Exception as e:
        return str(e)
    return None


def get_all_variables(calculator_id: str):
    return list(db.variables.find({"calculator_id": ObjectId(calculator_id)}).sort("order", 1))


def get_all_prices(calculator_id: str):
    return list(db.prices.find({"calculator_id": ObjectId(calculator_id)}).sort("order", 1))


def build_context(variables: List[models.Variable]):
    context = {}
    for variable in variables:
        context[variable.tag_name] = variable.default_value
    return context


def validate_all_formulas(calculator_id: str, variables: List[models.Variable]):
    variables = sorted(variables, key=lambda x: x.order)
    context = build_context(variables)
    prices = get_all_prices(calculator_id)
    errors = []
    for variable in variables:
        if variable.formula:
            result = eval_formula(variable.formula, context, prices)
            if isinstance(result, str):
                errors.append((variable.tag_name, result))
            else:
                context[variable.tag_name] = result
        else:
            context[variable.tag_name] = variable.default_value
    return errors


def eval_formula(formula: str, context: Dict[str, Any], prices: List[Dict[str, Any]]) -> Any:
    local_context = {}
    formula = formula.replace("if", "np.where")

    def price(tag_name: str, fallback_value=0.0):
        value = fallback_value
        for price in prices:
            if price['tag_name'] == tag_name:
                if check_extra_conditions(price.get("extra", {}), context):
                    value = price['price']
        return value

    for key, value in context.items():
        pattern = r'\b' + re.escape(key) + r'\b'
        if value is None:
            value = 0
        formula = re.sub(pattern, str(value), formula)

    try:
        local_context = {"np": np, "price": price}
        local_context.update(context)
        # print(f"Evaluating formula: {formula} with context {local_context}")
        return eval(formula, {}, local_context)
    except Exception as e:
        print(f"Error evaluating formula: {formula} with context {local_context} - {e}")
        return None


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
