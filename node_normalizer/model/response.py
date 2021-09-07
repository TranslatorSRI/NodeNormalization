"""
API Response Models not described in reasoner-pydantic
"""

from pydantic import BaseModel

from typing import Dict, List


class SemanticTypes(BaseModel):
    semantic_types: Dict[str, List]

    class Config:
        schema_extra = {
            "example": {
                "semantic_types": {
                    "types": [
                        "cellular_component",
                        "named_thing",
                        "etc."
                    ]
                }
            }
        }


class CuriePivot(BaseModel):
    curie_prefix: Dict[str, str]

class ConflationList(BaseModel):
    conflations: List