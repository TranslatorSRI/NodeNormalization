"""
API Input Models not described in reasoner-pydantic
"""

from pydantic import BaseModel, Field

from typing import List

from typing import Optional

from node_normalizer.model.response import ConflationType


class CurieList(BaseModel):
    """Curie list input model"""

    curies: List[str] = Field(
        ...,  # Ellipsis means field is required
        title='list of nodes formatted as curies',
        min_items=1
    )

    conflation_type: Optional[ConflationType]
    # conflate:bool = Field(
    #     True,
    #     title="Whether to apply conflation"
    # )

    class Config:
        schema_extra = {
            "example": {
                "curies": ['MESH:D014867', 'NCIT:C34373'],
                "conflate": True
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
                "semantic_types": ['biolink:ChemicalSubstance', 'biolink:AnatomicalEntity']
            }
        }
