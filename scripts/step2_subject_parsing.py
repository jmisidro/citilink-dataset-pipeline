#!/usr/bin/env python3
"""
Subject-Centric INCEpTION Parser

This script converts INCEpTION annotations (JSON format) into a subject-centric
structure, including agenda items and detailed voting information.
"""

import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Mapping for detailed personal information types
PERSONAL_INFO_TYPE_MAPPING = {
    "Name": "PERSONAL-NAME",
    "Date": "PERSONAL-DATE",
    "Time": "PERSONAL-TIME",
    "Address": "PERSONAL-ADDRESS",
    "Position and Department": "PERSONAL-POSITION",
    "Personal Information": "PERSONAL-INFO",
    "Phone Number": "PERSONAL-PHONE",
    "Administrative Information": "PERSONAL-ADMIN",
    "License Plate": "PERSONAL-LICENSE",
    "Vehicle": "PERSONAL-VEHICLE",
    "Company or Institution": "PERSONAL-COMPANY",
    "Location": "PERSONAL-LOCATION",
    "Job": "PERSONAL-JOB",
    "Artistic Activity": "PERSONAL-ARTISTIC",
    "Degree": "PERSONAL-DEGREE",
    "Faculty and University": "PERSONAL-FACULTY",
    "Family Relationship": "PERSONAL-FAMILY",
    "Other": "PERSONAL-OTHER",
    "Public Personal Information": "PERSONAL-PUBLIC"
}

class SubjectParser:
    def __init__(self, inception_file_path: Path, output_dir: Path, debug: bool = False):
        self.inception_file_path = inception_file_path
        self.output_dir = output_dir
        self.debug = debug
        if debug:
            logger.setLevel(logging.DEBUG)
        
        self.data = self._load_json()
        self.document_text = self._get_document_text()
        self.feature_structures = []
        self._extract_feature_structures()

    def _load_json(self) -> Dict[str, Any]:
        """Loads the INCEpTION JSON file."""
        logger.info(f"Loading INCEpTION file: {self.inception_file_path}")
        with open(self.inception_file_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _get_document_text(self) -> Optional[str]:
        """Extracts the full document text from the INCEpTION JSON."""
        # Try to find sofa text in feature structures
        feature_structures = self.data.get("%FEATURE_STRUCTURES", [])
        for fs in feature_structures:
            if fs.get("%TYPE") == "uima.cas.Sofa":
                sofa_string = fs.get("sofaString", "")
                if sofa_string:
                    logger.info(f"Found document text: {len(sofa_string)} characters")
                    return sofa_string
        
        logger.warning("Could not find document text (sofaString) in the INCEpTION file.")
        return None

    def _extract_feature_structures(self):
        """Extract all feature structures from the INCEpTION JSON."""
        raw_feature_structures = self.data.get("%FEATURE_STRUCTURES", [])
        logger.info(f"Loaded {len(raw_feature_structures)} feature structures from file.")

        # Filter out feature structures explicitly marked as not validated.
        # Some exported annotations (e.g., votation-related spans) may have
        # "Validated": "no" and should not be loaded/processed.
        self.feature_structures = []
        for fs in raw_feature_structures:
            # Skip any feature structure explicitly marked as not validated
            if str(fs.get("Validated", "")).lower() == "no":
                logger.debug(f"Skipping unvalidated feature structure id={fs.get('%ID')} type={fs.get('%TYPE')}")
                continue
            self.feature_structures.append(fs)

        logger.info(f"Using {len(self.feature_structures)} feature structures after filtering unvalidated ones.")
        
        # Build StringArray map for quick lookup
        self.string_arrays = {}
        for fs in self.feature_structures:
            if fs.get("%TYPE") == "uima.cas.StringArray":
                fs_id = fs.get("%ID")
                elements = fs.get("%ELEMENTS", [])
                if fs_id:
                    self.string_arrays[fs_id] = elements
        logger.debug(f"Found {len(self.string_arrays)} StringArray objects")
        
        # Extract and apply personal information masking
        #self._extract_and_mask_personal_info()
    
    def _extract_and_mask_personal_info(self):
        """Extract personal information annotations and mask them in the document text."""
        personal_info_segments = []
        
        for fs in self.feature_structures:
            label = fs.get("label")
            if (fs.get("%TYPE") == "custom.Span" and 
                (label == "Informação Pessoal" or label == "Public Personal Information")):
                begin = fs.get("begin")
                end = fs.get("end")
                if begin is not None and end is not None:
                    personal_info_segments.append({
                        'begin': begin,
                        'end': end,
                        'id': fs.get("%ID")
                    })
        
        if personal_info_segments:
            logger.info(f"Found {len(personal_info_segments)} personal information segments to mask")
            self.document_text = self._mask_personal_information(self.document_text, personal_info_segments)
        else:
            logger.debug("No personal information segments found")
    
    def _mask_personal_information(self, text: str, personal_info_segments: List[Dict[str, Any]]) -> str:
        """
        Replace personal information spans in text with asterisks (*) to preserve span consistency.
        """
        if not text or not personal_info_segments:
            return text
        
        # Sort segments by start position in reverse order to maintain offsets
        sorted_segments = sorted(personal_info_segments, key=lambda x: x['begin'], reverse=True)
        
        result = text
        for segment in sorted_segments:
            start_pos = segment['begin']
            end_pos = segment['end']
            
            # Replace the span with asterisks (same length)
            masked_length = end_pos - start_pos
            masked_text = '*' * masked_length
            
            result = result[:start_pos] + masked_text + result[end_pos:]
        
        return result

    def _get_span_text(self, begin: int, end: int) -> str:
        """Extracts text for a given span."""
        if self.document_text:
            return self.document_text[begin:end]
        return ""
    
    def _adjust_start_boundary(self, pos: int) -> int:
        """
        Adjust start boundary to avoid cutting words.
        Move backward to include any partial word.
        """
        if pos <= 0 or not self.document_text:
            return pos
        
        # Move backward to find the start of the current word or whitespace
        while pos > 0 and self.document_text[pos - 1].isalnum():
            pos -= 1
        
        return pos
    
    def _adjust_end_boundary(self, pos: int) -> int:
        """
        Adjust end boundary to avoid cutting words.
        Move forward to complete any partial word.
        """
        if not self.document_text or pos >= len(self.document_text):
            return pos
        
        # Move forward to find the end of the current word
        while pos < len(self.document_text) and self.document_text[pos].isalnum():
            pos += 1
        
        return pos

    def _extract_boundary_pairs(self) -> List[Tuple[int, int, List[str], Optional[str], Optional[Dict[str, Any]]]]:
        """
        Extract subject boundaries from 'Fronteira Inicial' and 'Fronteira Final' markers.
        Returns list of (begin, end, topics, tema, subject) tuples representing subject boundaries.
        """
        fronteira_spans = []
        assunto_annotations = {}  # Map position to full Assunto annotation data
        
        # First, collect all fronteira markers and Assunto annotations
        for fs in self.feature_structures:
            if fs.get("%TYPE") == "custom.Span" and fs.get("label") == "Assunto":
                fronteira = fs.get("Fronteira")
                tema = fs.get("Tema")
                atributos2_ref = fs.get("@Atributos2")
                begin = fs.get("begin")
                end = fs.get("end")
                
                # Get topics from @Atributos2 reference
                topics = []
                if atributos2_ref and atributos2_ref in self.string_arrays:
                    topics = self.string_arrays[atributos2_ref]
                
                if fronteira:
                    # This is a boundary marker
                    fronteira_spans.append({
                        'type': fronteira,
                        'begin': begin,
                        'end': end
                    })
                elif tema or topics or atributos2_ref:
                    # This is an Assunto annotation with tema/topics (subject)
                    # Extract Resumo field if it exists
                    resumo = fs.get("Resumo")
                    assunto_annotations[begin] = {
                        'begin': begin,
                        'end': end,
                        'tema': tema,
                        'topics': topics,
                        'resumo': resumo,  # Add summary field
                        'text': self._get_span_text(begin, end) if begin is not None and end is not None else None
                    }
        
        # Sort by position
        fronteira_spans.sort(key=lambda x: x['begin'])
        
        logger.debug(f"Found {len(fronteira_spans)} fronteira markers and {len(assunto_annotations)} Assunto annotations")
        
        # Pair up Inicial and Final markers
        # Handle cases where Fronteira Final might be missing between consecutive Fronteira Inicial markers
        boundaries = []
        i = 0
        while i < len(fronteira_spans):
            if fronteira_spans[i]['type'] == 'Fronteira Inicial':
                # Find the next Fronteira Final or next Fronteira Inicial
                found_final = False
                for j in range(i + 1, len(fronteira_spans)):
                    if fronteira_spans[j]['type'] == 'Fronteira Final':
                        # Normal case: found matching Final marker
                        start_pos = fronteira_spans[i]['begin']
                        end_pos = fronteira_spans[j]['end']
                        
                        # Adjust boundaries to avoid cutting words
                        start_pos = self._adjust_start_boundary(start_pos)
                        end_pos = self._adjust_end_boundary(end_pos)
                        
                        # Find Assunto annotation within this boundary to get tema, topics, resumo, and subject
                        tema = None
                        topics = []
                        resumo = None
                        subject = None
                        
                        for pos, assunto_data in assunto_annotations.items():
                            if start_pos <= pos <= end_pos:
                                tema = assunto_data['tema']
                                topics = assunto_data['topics']
                                resumo = assunto_data['resumo']  # Extract resumo
                                # Create subject object
                                if assunto_data['text']:
                                    subject = {
                                        'text': assunto_data['text'],
                                        'start': assunto_data['begin'],
                                        'end': assunto_data['end']
                                    }
                                break
                        
                        boundaries.append((start_pos, end_pos, topics, tema, resumo, subject))
                        i = j
                        found_final = True
                        break
                    elif fronteira_spans[j]['type'] == 'Fronteira Inicial':
                        # Edge case: Found another Inicial before finding a Final
                        # This means Fronteira Final is missing. Use the position just before
                        # the next Inicial as the end boundary
                        logger.warning(
                            f"Missing Fronteira Final between Inicial at {fronteira_spans[i]['begin']} "
                            f"and next Inicial at {fronteira_spans[j]['begin']}. "
                            f"Using position before next Inicial as end boundary."
                        )
                        start_pos = fronteira_spans[i]['begin']
                        # End just before the next Inicial marker
                        end_pos = fronteira_spans[j]['begin'] - 1
                        
                        # Adjust boundaries to avoid cutting words
                        start_pos = self._adjust_start_boundary(start_pos)
                        end_pos = self._adjust_end_boundary(end_pos)
                        
                        # Find Assunto annotation within this boundary
                        tema = None
                        topics = []
                        resumo = None
                        subject = None
                        
                        for pos, assunto_data in assunto_annotations.items():
                            if start_pos <= pos <= end_pos:
                                tema = assunto_data['tema']
                                topics = assunto_data['topics']
                                resumo = assunto_data['resumo']  # Extract resumo
                                if assunto_data['text']:
                                    subject = {
                                        'text': assunto_data['text'],
                                        'start': assunto_data['begin'],
                                        'end': assunto_data['end']
                                    }
                                break
                        
                        boundaries.append((start_pos, end_pos, topics, tema, resumo, subject))
                        # Set i to j-1 because the loop will increment it to j at the end
                        # This ensures the next Inicial marker at position j is processed next iteration
                        i = j - 1
                        found_final = True
                        break
                
                if not found_final:
                    logger.warning(f"No matching Fronteira Final found for Inicial at position {fronteira_spans[i]['begin']}")
            # Always increment i at the end of each iteration
            i += 1
        
        logger.info(f"Found {len(boundaries)} subject boundaries")
        return boundaries

    def _extract_agenda_items(self) -> List[Dict[str, Any]]:
        """Extracts all 'Ordem do Dia' (agenda item) annotations."""
        agenda_items = []
        for fs in self.feature_structures:
            if fs.get("%TYPE") == "custom.Span" and fs.get("label") == "Ordem do Dia":
                begin = fs.get("begin")
                end = fs.get("end")
                if begin is not None and end is not None:
                    agenda_items.append({
                        'begin': begin,
                        'end': end,
                        'text': self._get_span_text(begin, end)
                    })
        logger.info(f"Found {len(agenda_items)} agenda items.")
        return sorted(agenda_items, key=lambda x: x['begin'])

    def _extract_entities_in_range(self, begin: int, end: int) -> List[Dict[str, Any]]:
        """Extract all entity annotations within a given range."""
        entities = []
        for fs in self.feature_structures:
            if fs.get("%TYPE") == "custom.Span":
                fs_begin = fs.get("begin")
                fs_end = fs.get("end")
                label = fs.get("label")
                
                # Check if span is within range
                if (fs_begin is not None and fs_end is not None and 
                    fs_begin >= begin and fs_end <= end and
                    label not in ["Assunto", "Informação Pessoal"]):  # Skip these labels
                    
                    entity = {
                        'id': fs.get("%ID"),
                        'type': label,
                        'begin': fs_begin,
                        'end': fs_end,
                        'text': self._get_span_text(fs_begin, fs_end)
                    }
                    
                    # Add relevant attributes
                    if label == "Posicionamento":
                        if fs.get("Posicionamento"):
                            entity['subtype'] = fs.get("Posicionamento")
                        if fs.get("posicionamento"):
                            entity['posicionamento'] = fs.get("posicionamento")
                    elif label == "Metadados":
                        if fs.get("Metadados"):
                            entity['subtype'] = fs.get("Metadados")
                        if fs.get("Partido"):
                            entity['partido'] = fs.get("Partido")
                        if fs.get("Participantes"):
                            entity['participantes'] = fs.get("Participantes")
                    
                    entities.append(entity)
        
        return entities

    def _extract_relations_for_entities(self, entity_ids: set) -> List[Dict[str, Any]]:
        """Extract all relations involving the given entity IDs."""
        relations = []
        for fs in self.feature_structures:
            if fs.get("%TYPE") == "custom.Relation":
                governor_id = fs.get("@Governor")
                dependent_id = fs.get("@Dependent")
                label = fs.get("label")
                
                # For most relations, both entities must be in our set
                # But for "objeto de votação", the dependent (Assunto) might not be in entity_ids
                if label == "objeto de votação" and governor_id in entity_ids:
                    # Include this relation even if dependent is not in entity_ids
                    relation = {
                        'id': fs.get("%ID"),
                        'type': label,
                        'governor': governor_id,
                        'dependent': dependent_id
                    }
                    relations.append(relation)
                elif governor_id in entity_ids and dependent_id in entity_ids:
                    relation = {
                        'id': fs.get("%ID"),
                        'type': label,
                        'governor': governor_id,
                        'dependent': dependent_id
                    }
                    
                    # Add relation-specific attributes
                    if fs.get("posicionamento"):
                        relation['posicionamento'] = fs.get("posicionamento")
                    if fs.get("resultado"):
                        relation['resultado'] = fs.get("resultado")
                    
                    relations.append(relation)
        
        return relations

    def _process_voting_for_subject(self, subject_begin: int, subject_end: int) -> List[Dict[str, Any]]:
        """Extract and process voting information for a subject. Returns array of voting objects."""
        # Extract all entities in the subject range
        entities = self._extract_entities_in_range(subject_begin, subject_end)
        entity_ids = {e['id'] for e in entities}
        
        # Extract relations
        relations = self._extract_relations_for_entities(entity_ids)
        
        # Build entity map for quick lookup
        entity_map = {e['id']: e for e in entities}
        
        # Find voting spans ("Votação" entities)
        voting_spans = [e for e in entities if e.get('subtype') == 'Votação']
        
        # Build array of voting objects (one per voting span)
        voting_array = []
        
        for voting_span in voting_spans:
            voting_id = voting_span['id']
            
            # Initialize voting object for this voting span with correct field order:
            # voting_evidence, voters, non_voters, global_tally
            voting_obj = {
                'voting_evidence': {
                    'text': voting_span.get('text', ''),
                    'start': voting_span.get('begin'),
                    'end': voting_span.get('end')
                },
                'vote_type': None,
                'voters': {
                    'in_favor': [],
                    'against': [],
                    'abstention': [],
                    'blank': []
                },
                'non_voters': [],
                'global_tally': None
            }
            
            # Find all relations connected to this voting span
            for rel in relations:
                # Handle posicionamento relations (voters)
                if rel['type'] == 'posicionamento' and rel['dependent'] == voting_id:
                    voter_id = rel['governor']
                    voter = entity_map.get(voter_id)
                    posicionamento = rel.get('posicionamento', '').lower()
                    
                    if voter:
                        v_begin = voter.get('begin')
                        v_end = voter.get('end')
                        # Removed skip for zero-length anchor spans as they are intentional in this dataset
                        voter_info = {
                            'text': voter.get('text', ''),
                            'start': v_begin,
                            'end': v_end
                        }
                        
                        # Add partido if available
                        if 'partido' in voter:
                            voter_info['partido'] = voter['partido']
                        
                        # Determine voter type
                        voter_subtype = voter.get('subtype', '').lower()
                        
                        # Map positioning to voting categories
                        if voter_subtype == 'não votante' or voter_subtype == 'nao votante':
                            voting_obj['non_voters'].append(voter_info)
                        elif 'favor' in posicionamento or posicionamento == 'a favor':
                            voting_obj['voters']['in_favor'].append(voter_info)
                        elif 'contra' in posicionamento or posicionamento == 'contra':
                            voting_obj['voters']['against'].append(voter_info)
                        elif 'absten' in posicionamento or posicionamento in ['abstenção', 'abstencao']:
                            voting_obj['voters']['abstention'].append(voter_info)
                        elif 'branco' in posicionamento or posicionamento == 'em branco':
                            voting_obj['voters']['blank'].append(voter_info)
                        else:
                            logger.warning(
                                f"Unknown posicionamento value '{posicionamento}' for voter "
                                f"id={voter_id} — skipping voter"
                            )
                
                # Handle resultado (global tally)
                elif rel['type'] == 'resultado' and rel['dependent'] == voting_id:
                    resultado = rel.get('resultado')
                    if resultado:
                        # Try to find the resultado entity to get position info
                        resultado_id = rel['governor']
                        resultado_entity = entity_map.get(resultado_id)
                        
                        # Determine vote type based on text
                        vote_type = None
                        if 'unanimidade' in resultado.lower():
                            vote_type = 'unanimous'
                        elif 'maioria' in resultado.lower():
                            vote_type = 'majority'
                        
                        if resultado_entity:
                            voting_obj['global_tally'] = {
                                'text': resultado,
                                'start': resultado_entity.get('begin'),
                                'end': resultado_entity.get('end'),
                                'type': vote_type
                            }
                        else:
                            voting_obj['global_tally'] = {
                                'text': resultado,
                                'start': None,
                                'end': None,
                                'type': vote_type
                            }

                # Handle método de votação (vote_type)
                elif rel['type'] == 'método de votação' and rel['governor'] == voting_id:
                    method_span = entity_map.get(rel['dependent'])
                    if method_span:
                        m_begin = method_span.get('begin')
                        m_end = method_span.get('end')
                        if m_begin is not None and m_end is not None:
                            voting_obj['vote_type'] = {
                                'text': method_span.get('text', ''),
                                'start': m_begin,
                                'end': m_end,
                            }

            # Keep vote_type optional in output schema
            if voting_obj.get('vote_type') is None:
                voting_obj.pop('vote_type', None)
            
            voting_array.append(voting_obj)
        
        return voting_array

    def _extract_vote_method_in_range(self, begin: int, end: int) -> Optional[Dict[str, Any]]:
        """
        Find a 'método de votação' relation whose @Governor (Votação span) lies within
        [begin, end] and return the text/start/end of the @Dependent (Posicionamento/Método)
        span.  Returns None when no such relation is found.
        """
        # Collect IDs of all entities within range (Votação spans will be among them)
        entity_ids_in_range = set()
        for fs in self.feature_structures:
            if fs.get("%TYPE") == "custom.Span":
                fs_begin = fs.get("begin")
                fs_end = fs.get("end")
                if (fs_begin is not None and fs_end is not None and
                        fs_begin >= begin and fs_end <= end):
                    entity_ids_in_range.add(fs.get("%ID"))

        # Build a quick ID→span map for resolving the dependent
        span_by_id = {fs.get("%ID"): fs for fs in self.feature_structures
                      if fs.get("%TYPE") == "custom.Span"}

        for fs in self.feature_structures:
            if (fs.get("%TYPE") == "custom.Relation" and
                    fs.get("label") == "método de votação"):
                governor_id = fs.get("@Governor")
                dependent_id = fs.get("@Dependent")
                # The Votação span (@Governor) must be within the given range
                if governor_id in entity_ids_in_range:
                    dep_span = span_by_id.get(dependent_id)
                    if dep_span:
                        dep_begin = dep_span.get("begin")
                        dep_end = dep_span.get("end")
                        if dep_begin is not None and dep_end is not None:
                            return {
                                "text": self._get_span_text(dep_begin, dep_end),
                                "start": dep_begin,
                                "end": dep_end
                            }
        return None

    def _build_voting_for_votacao_span(self, votacao_span_id: int) -> Optional[Dict[str, Any]]:
        """
        Build a single voting object for a specific Votação span ID.

        Used to attach voting data to sub-subjects, where the Votação span lies
        outside (just after) the Subassunto span boundary so the standard range-based
        helper cannot find it.
        """
        span_by_id = {fs.get("%ID"): fs for fs in self.feature_structures
                      if fs.get("%TYPE") == "custom.Span"}

        votacao_span = span_by_id.get(votacao_span_id)
        if not votacao_span:
            return None

        v_begin = votacao_span.get("begin")
        v_end = votacao_span.get("end")

        voting_obj: Dict[str, Any] = {
            "voting_evidence": {
                "text": self._get_span_text(v_begin, v_end) if (v_begin is not None and v_end is not None) else "",
                "start": v_begin,
                "end": v_end,
            },
            "vote_type": None,
            "voters": {
                "in_favor": [],
                "against": [],
                "abstention": [],
                "blank": [],
            },
            "non_voters": [],
            "global_tally": None,
        }

        for fs in self.feature_structures:
            if fs.get("%TYPE") != "custom.Relation":
                continue
            rel_label = fs.get("label")
            is_method_relation = rel_label == "método de votação"
            if not (
                fs.get("@Dependent") == votacao_span_id
                or (is_method_relation and fs.get("@Governor") == votacao_span_id)
            ):
                continue

            # Método relation is Votação(@Governor) -> Método(@Dependent), so resolve
            # the dependent method span directly and continue.
            if is_method_relation:
                method_span = span_by_id.get(fs.get("@Dependent"))
                if method_span:
                    m_begin = method_span.get("begin")
                    m_end = method_span.get("end")
                    if m_begin is not None and m_end is not None:
                        voting_obj["vote_type"] = {
                            "text": self._get_span_text(m_begin, m_end),
                            "start": m_begin,
                            "end": m_end,
                        }
                continue

            governor_id = fs.get("@Governor")
            governor_span = span_by_id.get(governor_id)
            if not governor_span:
                continue

            g_begin = governor_span.get("begin")
            g_end = governor_span.get("end")
            # Removed skip for zero-length anchor spans as they are intentional in this dataset
            voter_info: Dict[str, Any] = {
                "text": self._get_span_text(g_begin, g_end) if (g_begin is not None and g_end is not None) else "",
                "start": g_begin,
                "end": g_end,
            }
            if "partido" in governor_span:
                voter_info["partido"] = governor_span["partido"]

            label = fs.get("label")
            if label == "posicionamento":
                posicionamento = (fs.get("posicionamento") or "").lower()
                # In raw INCEpTION spans the participant type is in the capitalized
                # "Posicionamento" feature, not a processed "subtype" key.
                voter_span_type = (governor_span.get("Posicionamento") or "").lower()

                if (voter_span_type in ("não votante", "nao votante", "não presente", "nao presente")
                        or "presente" in posicionamento):
                    voting_obj["non_voters"].append(voter_info)
                elif "favor" in posicionamento or posicionamento == "a favor":
                    voting_obj["voters"]["in_favor"].append(voter_info)
                elif "contra" in posicionamento:
                    voting_obj["voters"]["against"].append(voter_info)
                elif "absten" in posicionamento:
                    voting_obj["voters"]["abstention"].append(voter_info)
                elif "branco" in posicionamento:
                    voting_obj["voters"]["blank"].append(voter_info)
                else:
                    logger.warning(
                        f"Unknown posicionamento value '{posicionamento}' for voter "
                        f"id={governor_id} in sub-subject voting — skipping"
                    )
            elif label == "resultado":
                resultado_val = fs.get("resultado")
                if resultado_val:
                    r_lower = resultado_val.lower()
                    vote_type = None
                    if "unanimidade" in r_lower:
                        vote_type = "unanimous"
                    elif "maioria" in r_lower:
                        vote_type = "majority"
                    voting_obj["global_tally"] = {
                        "text": resultado_val,
                        "start": g_begin,
                        "end": g_end,
                        "type": vote_type,
                    }

        # Keep vote_type optional in output schema
        if voting_obj.get("vote_type") is None:
            voting_obj.pop("vote_type", None)

        return voting_obj

    def _extract_sub_subjects(self, subject_begin: int, subject_end: int) -> List[Dict[str, Any]]:
        """
        Extract 'Subassunto' span annotations that fall within the subject boundaries.
        Each sub-subject gets its own full voting breakdown.

        The 'método de votação' relation links a Votação span (@Governor) to a
        Posicionamento/Método span (@Dependent).  In practice the Votação span immediately
        *follows* the Subassunto span in the text, so we associate each método de votação
        with the sub-subject whose end position is the closest predecessor of the Votação
        span's begin.  The actual voting object is built from that Votação span via
        _build_voting_for_votacao_span so that voters outside the Subassunto boundary are
        captured correctly.
        """
        sub_subjects = []

        for fs in self.feature_structures:
            if (fs.get("%TYPE") == "custom.Span" and
                    fs.get("label") == "Subassunto"):
                begin = fs.get("begin")
                end = fs.get("end")

                if (begin is None or end is None or
                        begin < subject_begin or end > subject_end):
                    continue

                # Theme stored as 'TemaSubassunto' (Covilha-style) or 'Tema' (Alandroal-style)
                theme = fs.get("TemaSubassunto") or fs.get("Tema")

                text = self._get_span_text(begin, end)

                sub_subject: Dict[str, Any] = {
                    "text": text,
                    "start": begin,
                    "end": end,
                }
                if theme:
                    sub_subject["theme"] = theme

                sub_subjects.append(sub_subject)

        sub_subjects.sort(key=lambda x: x["start"])

        # Associate método de votação relations with sub-subjects.
        # The Votação span (@Governor) immediately follows the associated Subassunto
        # span, so we pick the sub-subject whose end is the nearest predecessor of the
        # Votação span. For each match we attach voting (built from the Votação span
        # itself); vote_type is included inside each voting object.
        if sub_subjects:
            span_by_id = {fs.get("%ID"): fs for fs in self.feature_structures
                          if fs.get("%TYPE") == "custom.Span"}

            for fs in self.feature_structures:
                if (fs.get("%TYPE") == "custom.Relation" and
                        fs.get("label") == "método de votação"):
                    governor_id = fs.get("@Governor")
                    dependent_id = fs.get("@Dependent")

                    gov_span = span_by_id.get(governor_id)
                    dep_span = span_by_id.get(dependent_id)
                    if not gov_span or not dep_span:
                        continue

                    gov_begin = gov_span.get("begin")
                    if gov_begin is None:
                        continue
                    # Only consider governors that fall within the subject range
                    if not (subject_begin <= gov_begin <= subject_end):
                        continue

                    dep_begin = dep_span.get("begin")
                    dep_end = dep_span.get("end")
                    if dep_begin is None or dep_end is None:
                        continue

                    # Find the sub-subject whose end is the closest predecessor
                    best_ss = None
                    best_gap = float("inf")
                    for ss in sub_subjects:
                        if ss["end"] <= gov_begin:
                            gap = gov_begin - ss["end"]
                            if gap < best_gap:
                                best_gap = gap
                                best_ss = ss

                    if best_ss is not None:
                        # Build a full voting object from the Votação span (@Governor)
                        ss_voting = self._build_voting_for_votacao_span(governor_id)
                        if ss_voting:
                            best_ss["voting"] = [ss_voting]
                        logger.debug(
                            f"Assigned voting (with vote_type when present) to sub-subject "
                            f"@{best_ss['start']}-{best_ss['end']} (gap={best_gap})"
                        )

        logger.debug(f"Found {len(sub_subjects)} sub-subjects in range [{subject_begin}, {subject_end}]")
        return sub_subjects

    def _associate_subjects_with_agenda_items(self, subjects: List[Dict[str, Any]], agenda_items: List[Dict[str, Any]], municipality: str = "Unknown"):
        """
        Associates each subject with its containing agenda item.
        Agenda items are section headers that come BEFORE their content subjects.
        We find the last agenda item that starts before each subject.
        """
        logger.debug(f"Associating {len(subjects)} subjects with {len(agenda_items)} agenda items")
        
        # Log first few agenda items for debugging
        if logger.isEnabledFor(logging.DEBUG):
            for i, item in enumerate(agenda_items[:3]):
                logger.debug(f"Agenda item {i}: {item['begin']}-{item['end']} '{item['text'][:50]}'...")
        
        for subject in subjects:
            subject['agenda_item'] = None
            
            # Find the last agenda item that starts before this subject
            for item in reversed(agenda_items):
                # In Porto, the agenda item is usually the subject title itself and might start
                # exactly at the subject boundary or slightly after due to boundary adjustments.
                tolerance = 100 if municipality == "Porto" else 0
                
                if (municipality == "Porto" and item['begin'] <= subject['begin'] + tolerance) or \
                   (municipality != "Porto" and item['begin'] < subject['begin']):
                    # Store as object with text, start, end
                    subject['agenda_item'] = {
                        'text': item['text'],
                        'start': item['begin'],
                        'end': item['end']
                    }
                    logger.debug(f"Subject {subject['begin']}-{subject['end']} associated with agenda item '{item['text'][:30]}...'")
                    break
            
            if not subject['agenda_item']:
                logger.warning(f"Subject at position {subject['begin']}-{subject['end']} not associated with any agenda item.")
                # Set a default empty agenda item object
                subject['agenda_item'] = {
                    'text': '',
                    'start': subject['begin'],
                    'end': subject['begin']
                }

    def _generate_subject_id(self, doc_id: str, subject_number: int) -> str:
        """Generates a unique ID for a subject."""
        return f"{doc_id}_{subject_number}"
    
    def _extract_subject(self, subject_begin: int, subject_end: int) -> Optional[Dict[str, Any]]:
        """Extract the 'subject' (objeto de votação) for a subject."""
        # Extract entities and relations in range
        entities = self._extract_entities_in_range(subject_begin, subject_end)
        entity_ids = {e['id'] for e in entities}
        relations = self._extract_relations_for_entities(entity_ids)
        
        # Look for "objeto de votação" relations
        for rel in relations:
            if rel['type'] == 'objeto de votação':
                # The dependent is the Assunto (subject) being voted on
                voting_subject_id = rel['dependent']
                
                # Look up in all feature structures
                for fs in self.feature_structures:
                    if fs.get("%ID") == voting_subject_id:
                        vs_begin = fs.get("begin")
                        vs_end = fs.get("end")
                        if vs_begin is not None and vs_end is not None:
                            return {
                                'text': self._get_span_text(vs_begin, vs_end),
                                'start': vs_begin,
                                'end': vs_end
                            }
        
        return None

    def _extract_personal_info(self) -> List[Dict[str, Any]]:
        """
        Extract personal information annotations from INCEpTION.
        Returns list of personal info annotations with text, type, start, and end positions.
        """
        logger.info("Extracting personal information annotations...")
        
        personal_info_list = []
        
        # Extract personal information annotations (both types)
        for fs in self.feature_structures:
            if fs.get("%TYPE") == "custom.Span":
                label = fs.get("label")
                
                # Handle both "Informação Pessoal" and "Public Personal Information"
                if label == "Informação Pessoal" or label == "Public Personal Information":
                    begin = fs.get("begin")
                    end = fs.get("end")
                    
                    if begin is not None and end is not None:
                        text = self._get_span_text(begin, end)
                        
                        # Determine entity type based on label
                        if label == "Public Personal Information":
                            entity_type = "PERSONAL-PUBLIC"
                        else:
                            # "Informação Pessoal" - check PersonalInformation attribute
                            personal_info_type = fs.get("PersonalInformation")
                            if personal_info_type and personal_info_type in PERSONAL_INFO_TYPE_MAPPING:
                                entity_type = PERSONAL_INFO_TYPE_MAPPING[personal_info_type]
                            else:
                                # Backward compatibility: use generic PERSONAL type
                                entity_type = "PERSONAL"
                        
                        personal_info_list.append({
                            "category": entity_type,
                            "text": text,
                            "start": begin,
                            "end": end
                        })
        
        logger.info(f"Extracted {len(personal_info_list)} personal information annotations")
        return personal_info_list

    def _extract_metadata(self) -> Dict[str, Any]:
        """
        Extract document-level metadata from INCEpTION annotations.
        Returns metadata dict with information about the meeting.
        """
        logger.info("Extracting document metadata...")
        
        # Initialize metadata fields
        begin_time = None
        end_time = None
        location = None
        date = None
        minute_number = None
        meeting_type = None
        participants = []
        
        # Extract metadata from Metadados annotations
        # Accept "yes", or None (missing) validation status for metadata
        for fs in self.feature_structures:
            if (fs.get("%TYPE") == "custom.Span" and
                fs.get("label") == "Metadados" and
                fs.get("Validated") not in ["no"]):
                
                meta_type = fs.get("Metadados")
                begin = fs.get("begin")
                end = fs.get("end")
                text = self._get_span_text(begin, end) if begin is not None and end is not None else None
                
                if meta_type == "Número da ata":
                    minute_number = {"text": text, "start": begin, "end": end}
                elif meta_type == "Data":
                    date = {"text": text, "start": begin, "end": end}
                elif meta_type == "Horário" and fs.get("Horrio") == "início":
                    begin_time = {"text": text, "start": begin, "end": end}
                elif meta_type == "Horário" and fs.get("Horrio") == "fim":
                    end_time = {"text": text, "start": begin, "end": end}
                elif meta_type == "Local":
                    location = {"text": text, "start": begin, "end": end}
                elif meta_type == "Tipo de reunião":
                    meeting_type = {"text": text, "start": begin, "end": end}
                    # Also capture the TipodeReunio field if present
                    if fs.get("TipodeReunio") and not meeting_type.get("text"):
                        meeting_type["text"] = fs.get("TipodeReunio")
                elif meta_type == "Participantes":
                    participant_type = fs.get("Participantes", "").lower()
                    
                    # Anonymize if it's funcionário or público
                    if participant_type in ["funcionários", "funcionario", "público", "publico"]:
                        masked = "*" * len(text) if text else None
                        name_value = masked
                    else:
                        name_value = text
                    
                    participant = {
                        "name": name_value,
                        "type": participant_type,
                        "start": begin,
                        "end": end,
                    }
                    
                    # Add party and presence information if available
                    if "Partido" in fs:
                        participant["party"] = fs["Partido"]
                    if "Presena" in fs:
                        participant["present"] = fs["Presena"].lower()
                    
                    participants.append(participant)
        
        # Extract municipality and year from filename
        doc_path = Path(self.inception_file_path)
        municipality = doc_path.stem.split("_")[0].title() if "_" in doc_path.stem else "Unknown"
        
        # Extract year from date format: YYYY-MM-DD
        year = None
        if date and date.get("text"):
            # Try to extract year from date string (formats: DD/MM/YYYY, YYYY-MM-DD)
            date_text = date["text"]
            if "-" in date_text:
                parts = date_text.split("-")
                if len(parts) >= 1 and len(parts[0]) == 4:
                    year = parts[0]
            elif "/" in date_text:
                parts = date_text.split("/")
                if len(parts) == 3 and len(parts[2]) == 4:
                    year = parts[2]
        
        # Fallback: extract from filename (e.g., Alandroal_cm_001_2024-01-03)
        if not year:
            filename_parts = doc_path.stem.split("_")
            if len(filename_parts) >= 4:
                date_part = filename_parts[3]  # Should be like "2024-01-03"
                if "-" in date_part:
                    year = date_part.split("-")[0]
        
        metadata = {
            "municipality": municipality,
            "year": year,
            "minute_number": minute_number,
            "date": date,
            "location": location,
            "meeting_type": meeting_type,
            "begin_time": begin_time,
            "end_time": end_time,
            "participants": participants,
        }
        
        logger.info(f"Extracted metadata: {len(participants)} participants, meeting_type: {meeting_type}")
        return metadata

    def parse(self):
        """
        Main parsing function to orchestrate the subject extraction and transformation.
        """
        logger.info("Starting subject-centric parsing...")
        
        if not self.document_text:
            logger.error("Cannot parse without document text.")
            return None

        doc_id = self.inception_file_path.stem
        
        # Extract subject boundaries using Fronteira markers
        boundaries = self._extract_boundary_pairs()
        
        logger.info(f"Total subjects extracted: {len(boundaries)}")
        
        # Extract agenda items
        agenda_items = self._extract_agenda_items()
        
        # Build subjects from boundaries
        subjects = []
        for start, end, topics, tema, resumo, subject in boundaries:
            subject = {
                'begin': start,
                'end': end,
                'text': self._get_span_text(start, end),
                'tema': tema,
                'topics': topics,
                'resumo': resumo,  # Add resumo field
                'subject': subject
            }
            subjects.append(subject)
        
        # Extract municipality from minute_id (e.g., "Alandroal_cm_001_2024" -> "Alandroal")
        municipality = doc_id.split('_')[0].title() if '_' in doc_id else "Unknown"
        
        # Associate subjects with agenda items
        self._associate_subjects_with_agenda_items(subjects, agenda_items, municipality)
        
        # Extract metadata
        metadata = self._extract_metadata()
        
        # Extract personal information
        personal_info = self._extract_personal_info()
        
        # Build subject outputs (no anonymization here - will be done in Step 1.5)
        logger.info(f"Building output structure for {len(subjects)} subjects...")
        
        # Process subjects and voting
        output_subjects = []
        for i, subject_data in enumerate(subjects):
            subject_id = self._generate_subject_id(doc_id, i + 1)
            
            # Get subject text
            subject_text = self._get_span_text(subject_data['begin'], subject_data['end'])
            
            # Process voting for this subject
            voting_info = self._process_voting_for_subject(subject_data['begin'], subject_data['end'])
            
            # Build subject object
            output_subject = {
                'subject_id': subject_id,
                'text': subject_text,
                'start': subject_data['begin'],
                'end': subject_data['end'],
                'agenda_item': subject_data['agenda_item']
            }
            
            # Add subject annotation if available
            if subject_data.get('subject'):
                subj_ann = subject_data['subject']
                output_subject['subject'] = {
                    'text': subj_ann['text'],
                    'start': subj_ann['start'],
                    'end': subj_ann['end']
                }
            
            # Add topics if available
            if subject_data.get('topics'):
                output_subject['topics'] = subject_data['topics']

            # Add theme if available
            if subject_data.get('tema'):
                output_subject['theme'] = subject_data['tema']
            
            # Add summary if available
            if subject_data.get('resumo'):
                output_subject['summary'] = subject_data['resumo']
            
            # Add voting array
            output_subject['voting'] = voting_info

            # Extract sub-subjects and add when present
            sub_subjects = self._extract_sub_subjects(subject_data['begin'], subject_data['end'])
            if sub_subjects:
                output_subject['sub_subjects'] = sub_subjects

            output_subjects.append(output_subject)
        
        # Prepare final output structure (original text - will be anonymized in Step 1.5)
        output_data = {
            "minutes": {
                municipality: {
                    doc_id: {
                        "minute_id": doc_id,
                        "full_text": self.document_text,  # Original text
                        "personal_info": personal_info,  # Personal info annotations for anonymization step
                        "metadata": metadata,
                        "subjects": output_subjects
                    }
                }
            }
        }

        # Save the output
        output_filename = self.output_dir / f"{doc_id}_subjects.json"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Successfully parsed {len(output_subjects)} subjects and saved to {output_filename}")
        return output_data

def main():
    parser = argparse.ArgumentParser(
        description="Subject-Centric INCEpTION Parser",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'inception_file',
        type=str,
        help='Path to the INCEpTION JSON file'
    )
    
    parser.add_argument(
        '--output_dir',
        type=str,
        default='outputs',
        help='Output directory for processed files (default: outputs)'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    inception_file = Path(args.inception_file)
    output_dir = Path(args.output_dir)
    
    if not inception_file.exists():
        logger.error(f"INCEpTION file not found: {inception_file}")
        return 1
    
    # Parse the file
    subject_parser = SubjectParser(inception_file, output_dir, debug=args.debug)
    result = subject_parser.parse()
    
    if result:
        logger.info("✅ Parsing completed successfully!")
        return 0
    else:
        logger.error("❌ Parsing failed")
        return 1

if __name__ == "__main__":
    exit(main())
