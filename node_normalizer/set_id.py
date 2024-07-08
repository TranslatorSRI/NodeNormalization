# set_id.py
# Code related to generating IDs for sets (as in https://github.com/TranslatorSRI/NodeNormalization/issues/256).
import base64
import hashlib
import logging

from .model import SetIDResponse
from .normalizer import get_normalized_nodes


async def generate_set_id(app, curies, conflations) -> SetIDResponse:
    # Step 0. Prepare the SetIDResponse by filling it with the arguments.
    response = SetIDResponse(
        curies=curies,
        conflations=conflations
    )

    # Step 1. Normalize the curies given the conflation settings.
    gene_protein_conflation = "GeneProtein" in conflations
    drug_chemical_conflation = "DrugChemical" in conflations

    # We use get_normalized_nodes() to normalize all the CURIEs for us.
    normalization_results = await get_normalized_nodes(
        app, curies, gene_protein_conflation, drug_chemical_conflation, include_descriptions=False
    )

    # We prepare a set of sorted, deduplicated curies.
    curies_normalized_already = set()
    normalized_curies = []
    for curie in curies:
        if curie in normalization_results:
            result = normalization_results[curie]
            if 'id' in result and 'identifier' in result['id']:
                preferred_id = result['id']['identifier']
                if preferred_id in curies_normalized_already:
                    # Don't duplicate normalized IDs: that way if someone queries for ['id1', 'id2', 'id3'] where
                    # they normalize to ['nr1', 'nr2', 'nr2'], we can come up with the set ['nr1', 'nr2'], which will
                    # be a better set_id().
                    pass
                else:
                    normalized_curies.append(preferred_id)
                    curies_normalized_already.add(preferred_id)
            else:
                # We got back a normalization response, but no preferred ID. This shouldn't happen.
                logging.warning(
                    f"Normalized CURIE {curie} returned a response but not a preferred identifier: {normalization_results[curie]}"
                )
                normalized_curies.append(curie)
                curies_normalized_already.add(curie)
        else:
            # No normalized identifier.
            normalized_curies.append(curie)
            curies_normalized_already.add(curie)

    sorted_normalized_curies = sorted(normalized_curies)
    response.normalized_curies = sorted_normalized_curies

    # Do we have any normalized CURIEs? If not, return now.
    if not sorted_normalized_curies:
        return response

    # We convert the list of normalized CURIEs into a unique hash. The simplest way to do this would be to use a hashing
    # function, but we might someday want this to be reversible (see
    # https://github.com/TranslatorSRI/NodeNormalization/issues/256#issuecomment-2197465751), so let's try using base64
    # encoding instead.
    normalized_string = "|".join(sorted_normalized_curies)
    response.base64hash = base64.b64encode(normalized_string.encode('utf-8')).decode('utf-8')

    # Let's generate a hash too, why not.
    response.sha256hash = hashlib.sha256(normalized_string.encode('utf-8')).hexdigest()

    return response
