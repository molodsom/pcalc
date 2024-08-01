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


def get_price(tag_name: str, context: Dict[str, Any], prices: List[Dict[str, Any]], fallback_value=0.0) -> float:
    value = fallback_value
    for price in prices:
        if price['tag_name'] == tag_name:
            if check_extra_conditions(price.get("extra", {}), context):
                value = price['price']
    return value


def eval_formula(formula: str, context: Dict[str, Any], prices: List[Dict[str, Any]]) -> Dict[str, Any]:
    def replace_if_conditions(formula: str) -> str:
        return re.sub(r'\bif\b', 'np.where', formula).replace(";", ",")

    formula = replace_if_conditions(formula)

    def price(tag_name: str, fallback_value=0.0):
        return get_price(tag_name, context, prices, fallback_value)

    def replace_context_vars(match):
        key = match.group(0)
        value = context[key]
        if isinstance(value, str):
            return f'"{value}"'
        return str(value)

    tokens = re.split(r'("[^"]*")', formula)
    for i, token in enumerate(tokens):
        if not token.startswith('"'):
            for key in context:
                pattern = r'\b' + re.escape(key) + r'\b'
                token = re.sub(pattern, replace_context_vars, token)
        tokens[i] = token
    formula = ''.join(tokens)

    try:
        local_context = {"np": np, "price": price}
        result = eval(formula, {}, local_context)
        if isinstance(result, np.ndarray):
            result = result.tolist()
        return {"value": result, "error": ""}
    except Exception as e:
        return {"value": None, "error": str(e)}


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


def format_floats(context):
    for key, value in context.items():
        if isinstance(value, float):
            if value.is_integer():
                context[key] = int(value)
            else:
                context[key] = f"{value:.2f}"
    return context
