"""
API Response Models not described in reasoner-pydantic
"""
from enum import Enum

from pydantic import BaseModel

from typing import Dict, List


class SemanticTypes(BaseModel):
    semantic_types: Dict[str, List]

    class Config:
        schema_extra = {"example": {"semantic_types": {"types": ["biolink:Cell", "biolink:AnatomicalEntity", "etc."]}}}


class CuriePivot(BaseModel):
    curie_prefix: Dict[str, str]


class ConflationList(BaseModel):
    conflations: List


class ConflationType(str, Enum):
    GENE_PROTEIN = "gene_protein"
    CHEMICAL_DRUG = "chemical_drug"

