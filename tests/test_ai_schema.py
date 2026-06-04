import jsonschema
from ai_recommendation import SCHEMA


def test_valid_schema():
    data = {
        "recommendations": [
            {"title": "Inception", "year": 2010, "reason": "Zihin bükücü bilimkurgu", "tmdb_search": "Inception"}
        ],
        "summary": "Harika bir seçim"
    }
    jsonschema.validate(instance=data, schema=SCHEMA)


def test_invalid_schema_missing_reason():
    data = {
        "recommendations": [
            {"title": "Inception", "year": 2010}
        ]
    }
    try:
        jsonschema.validate(instance=data, schema=SCHEMA)
        assert False, "Validation should fail when reason is missing"
    except jsonschema.ValidationError:
        assert True
