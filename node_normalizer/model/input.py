"""
API Input Models not described in reasoner-pydantic
"""

from pydantic import BaseModel, Field

from typing import List


class CurieList(BaseModel):
    """Curie list input model"""

    curies: List[str] = Field(
        ...,  # Ellipsis means field is required
        title='List of CURIEs to normalize',
        min_items=1
    )

    conflate:bool = Field(
        True,
        title="Whether to apply gene/protein conflation"
    )

    description: bool = Field(
        False,
        title="Whether to return CURIE descriptions when possible"
    )

    drug_chemical_conflate: bool = Field(
        False,
        title="Whether to apply drug/chemical conflation"
    )

    class Config:
        schema_extra = {
            "example": {
                "curies": ['MESH:D014867', 'NCIT:C34373'],
                "conflate": True,
                "description": False,
                "drug_chemical_conflate": False,
            }
        }


class SemanticTypesInput(BaseModel):
    """Semantic type input model"""

    semantic_types: List[str] = Field(
        ...,  # required field
        title='list of semantic types',
    )

    class Config:
        schema_extra = {
            "example": {
                "semantic_types": ['biolink:ChemicalEntity', 'biolink:AnatomicalEntity']
            }
        }
