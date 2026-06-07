#!/usr/bin/env python3
"""
Finalize subject-centric datasets with mapping-based normalization.

Translates and normalizes Portuguese field values to English following
the CitiLink annotation schema.

Input: Datasets with metadata from Step 3
Output: Final production-ready datasets with normalized labels
"""

import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_translation_mappings() -> Dict[str, Dict[str, str]]:
    """Define translation mappings for Portuguese to English normalization."""
    return {
        # Meeting types and metadata
        'metadata_values': {
            'Ordinária': 'ordinary',
            'ordinária': 'ordinary',
            'ORDINÁRIA': 'ordinary',
            'Extraordinária': 'extraordinary',
            'extraordinária': 'extraordinary',
            'EXTRAORDINÁRIA': 'extraordinary',
            'Presidente': 'president',
            'presidente': 'president',
            'Vice-Presidente': 'vice_president',
            'vice-presidente': 'vice_president',
            'Vereadores': 'councilors',
            'vereadores': 'councilors',
            'Vereador': 'councilors',
            'vereador': 'councilors',
            'Funcionários': 'staff',
            'funcionários': 'staff',
            'Funcionário': 'staff',
            'funcionário': 'staff',
            'Presente': 'present',
            'presente': 'present',
            'Ausente': 'absent',
            'ausente': 'absent',
            'Substituído': 'replaced',
            'substituído': 'replaced',
            },

        # Subject topics
        'subject_topics': {
            'Administração Geral, Finanças e Recursos Humanos': 'General Administration, Finance, and Human Resources',
            'Ambiente': 'Environment',
            'Energia e Telecomunicações': 'Energy and Telecommunications',
            'Trânsito, Transportes e Comunicações': 'Traffic, Transport, and Communications',
            'Educação e Formação Profissional': 'Education and Vocational Training',
            'Património': 'Heritage',
            'Cultura': 'Culture',
            'Ciência': 'Science',
            'Saúde': 'Health',
            'Proteção Animal': 'Animal Protection',
            'Desporto': 'Sports',
            'Ação Social': 'Social Action',
            'Habitação': 'Housing',
            'Proteção Civil': 'Civil Protection',
            'Polícia Municipal': 'Municipal Police',
            'Obras Públicas': 'Public Works',
            'Ordenamento do Território': 'Land Use Planning',
            'Obras Particulares': 'Private Works',
            'Atividades Económicas': 'Economic Activities',
            'Cooperação Externa e Relações Internacionais': 'External Cooperation and International Relations',
            'Comunicação e Relações Públicas': 'Communication and Public Relations',
            'Outros': 'Other'
        }
    }


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load JSON file with error handling."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return {}


def save_json_file(data: Dict[str, Any], file_path: Path) -> bool:
    """Save data to JSON file."""
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")
        return False


def translate_value(value: Any, mappings: Dict[str, str]) -> Any:
    """Translate a value using the provided mapping."""
    if isinstance(value, str):
        return mappings.get(value, value)
    elif isinstance(value, list):
        return [translate_value(v, mappings) for v in value]
    elif isinstance(value, dict):
        return {k: translate_value(v, mappings) for k, v in value.items()}
    return value


def normalize_subject(subject: Dict[str, Any], mappings: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    """Normalize a single subject with translations."""
    
    # Translate topics
    if 'topics' in subject and isinstance(subject['topics'], list):
        subject['topics'] = [
            mappings['subject_topics'].get(topic, topic)
            for topic in subject['topics']
        ]
    
    # Translate theme
    if 'theme' in subject:
        subject['theme'] = mappings['subject_topics'].get(subject['theme'], subject['theme'])
    
    # # Infer and populate global_tally when null
    # if 'voting' in subject and isinstance(subject['voting'], list):
    #     for voting in subject['voting']:
    #         if voting.get('global_tally') is None:
    #             # Infer vote type from voters
    #             vote_type = infer_vote_type(voting)
    #             if vote_type:
    #                 # Create a synthetic global_tally from voting_evidence
    #                 voting_evidence = voting.get('voting_evidence', {})
    #                 voting['global_tally'] = {
    #                     'text': voting_evidence.get('text', ''),
    #                     'start': voting_evidence.get('start'),
    #                     'end': voting_evidence.get('end'),
    #                     'type': vote_type
    #                 }
    
    return subject


def infer_vote_type(voting: Dict[str, Any]) -> str:
    """Infer vote type (unanimous/majority) from voter data."""
    voters = voting.get('voters', {})
    in_favor = len(voters.get('in_favor', []))
    against = len(voters.get('against', []))
    abstention = len(voters.get('abstention', []))
    
    # If there are any against votes or abstentions, it's majority
    if against > 0 or abstention > 0:
        return 'majority'
    
    # If there's at least one in_favor vote and no opposition, it's unanimous
    if in_favor > 0:
        return 'unanimous'
    
    # If no voters are recorded, we can't infer - return None
    return None


def normalize_metadata(metadata: Dict[str, Any], mappings: Dict[str, Dict[str, str]]) -> Dict[str, Any]:
    """Normalize metadata fields."""
    
    # Translate meeting_type (handles both dict and string formats)
    if 'meeting_type' in metadata:
        meeting_type_value = metadata['meeting_type']
        if isinstance(meeting_type_value, dict) and 'text' in meeting_type_value:
            # Extract text from nested dict
            meeting_type_text = meeting_type_value['text']
            translated = mappings['metadata_values'].get(meeting_type_text, meeting_type_text)
            metadata['meeting_type']['type'] = translated
        elif isinstance(meeting_type_value, str):
            metadata['meeting_type'] = mappings['metadata_values'].get(
                meeting_type_value, meeting_type_value
            )
    
    # Translate participants
    if 'participants' in metadata and isinstance(metadata['participants'], list):
        for participant in metadata['participants']:
            # Translate type
            if 'type' in participant:
                if isinstance(participant['type'], dict) and 'text' in participant['type']:
                    type_text = participant['type']['text']
                    participant['type']['text'] = mappings['metadata_values'].get(type_text, type_text)
                elif isinstance(participant['type'], str):
                    participant['type'] = mappings['metadata_values'].get(
                        participant['type'], participant['type']
                    )
            
            # Translate present
            if 'present' in participant:
                if isinstance(participant['present'], dict) and 'text' in participant['present']:
                    present_text = participant['present']['text']
                    participant['present']['text'] = mappings['metadata_values'].get(present_text, present_text)
                elif isinstance(participant['present'], str):
                    participant['present'] = mappings['metadata_values'].get(
                        participant['present'], participant['present']
                    )
    
    return metadata


def finalize_municipality_file(input_file: Path, output_file: Path, mappings: Dict[str, Dict[str, str]], debug: bool = False) -> bool:
    """Finalize a single municipality file."""
    logger.info(f"Finalizing {input_file.name}")
    
    data = load_json_file(input_file)
    if not data or "minutes" not in data:
        logger.error(f"Invalid data structure in {input_file}")
        return False
    
    # Process each municipality and document
    for municipality_name, documents in data["minutes"].items():
        logger.info(f"  Processing {municipality_name}: {len(documents)} documents")
        
        for minute_id, document_data in documents.items():
            # Normalize subjects
            if "subjects" in document_data:
                for subject in document_data["subjects"]:
                    normalize_subject(subject, mappings)
            
            # Normalize metadata
            if "metadata" in document_data:
                normalize_metadata(document_data["metadata"], mappings)
            
            if debug:
                logger.debug(f"    {minute_id}: {len(document_data.get('subjects', []))} subjects normalized")
    
    # Save finalized data
    if save_json_file(data, output_file):
        logger.info(f"  ✅ Finalized → {output_file}")
        return True
    else:
        logger.error(f"  ❌ Failed to save {output_file}")
        return False


def finalize_datasets(input_dir: Path, output_dir: Path, debug: bool = False) -> bool:
    """Finalize all municipality datasets."""
    logger.info(f"Finalizing datasets from {input_dir}")
    logger.info(f"Output: {output_dir}")
    
    # Get translation mappings
    mappings = get_translation_mappings()
    
    # Find all municipality files
    municipality_files = list(input_dir.glob("*.json"))
    
    if not municipality_files:
        logger.error(f"No municipality files found in {input_dir}")
        return False
    
    logger.info(f"Found {len(municipality_files)} municipality files")
    
    success_count = 0
    for municipality_file in municipality_files:
        output_file = output_dir / municipality_file.name
        if finalize_municipality_file(municipality_file, output_file, mappings, debug):
            success_count += 1
    
    logger.info(f"✅ Finalization complete: {success_count}/{len(municipality_files)} files processed")
    return success_count > 0


def main():
    parser = argparse.ArgumentParser(
        description="Finalize subject-centric datasets with translations"
    )
    
    parser.add_argument(
        '--input_dir',
        type=str,
        required=True,
        help='Input directory containing datasets with metadata'
    )
    
    parser.add_argument(
        '--output_dir',
        type=str,
        required=True,
        help='Output directory for finalized datasets'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return 1
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    success = finalize_datasets(input_dir, output_dir, debug=args.debug)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
