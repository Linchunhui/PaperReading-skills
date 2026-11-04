"""Mechanical measurement checks. Passing these never certifies semantic support."""
from decimal import Decimal, InvalidOperation
import re


NUMBER = re.compile(r"(?<![\w.])[+−-]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?(?:[eE][+−-]?\d+)?(?![\w.])")


def numbers(text):
    values = set()
    for token in NUMBER.findall(text):
        try:
            values.add(Decimal(token.replace(",", "").replace("−", "-")))
        except InvalidOperation:
            pass
    for coefficient, exponent in re.findall(r"([+−-]?\d+(?:\.\d+)?)\s*[×x·]\s*10\s*\^\s*\{?([+−-]?\d+)\}?", text):
        power = int(exponent.replace("−", "-"))
        if abs(power) <= 1000:
            values.add(Decimal(coefficient.replace("−", "-")) * (Decimal(10) ** power))
    return values


def measurement_errors(fact, evidence):
    if fact.get("kind") != "reported_result" or not fact.get("observation"):
        return []
    observation = fact["observation"]
    quotes = "\n".join(evidence[e]["quote"] for e in fact.get("evidence_ids", []) if e in evidence)
    raw = observation.get("raw_value")
    value = observation.get("value")
    errors = []
    # A reported measurement must appear in the cited spans. Derived deltas belong to synthesis.
    if raw and numbers(str(raw)) and not numbers(str(raw)) <= numbers(quotes):
        errors.append("Reported raw measurement is absent from cited spans: " + fact["fact_id"])
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        numerical = Decimal(str(value))
        if numerical not in numbers(quotes):
            errors.append("Reported numeric value is absent from cited spans (retain original scale/unit): " + fact["fact_id"])
        if raw and numbers(str(raw)) and numerical not in numbers(str(raw)):
            errors.append("value and raw_value use different numbers/scales: " + fact["fact_id"])
    return errors
