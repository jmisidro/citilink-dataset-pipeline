#!/usr/bin/env python3
"""
Reorganize datasets by agenda items.

This script transforms the document structure to group subjects under their
corresponding agenda items instead of having agenda_item as a property within
each subject.

Input: Municipality-level files from Step 3
Output: Agenda-centric structure in 04_agendas/
"""

import json
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any
from collections import defaultdict

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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


def extract_minute_sort_key(minute_id: str) -> tuple:
    """
    Extract sorting key from minute_id for chronological ordering.
    Format: Municipality_cm_NUMBER_YYYY-MM-DD
    Returns: (year, month, day, minute_number)
    """
    try:
        # Split by underscore: ['Municipality', 'cm', 'NUMBER', 'YYYY-MM-DD']
        parts = minute_id.split('_')
        if len(parts) >= 4:
            minute_number = int(parts[2])  # Extract minute number
            date_part = parts[3]  # YYYY-MM-DD
            
            # Parse date
            year, month, day = date_part.split('-')
            return (int(year), int(month), int(day), minute_number)
    except (ValueError, IndexError):
        logger.warning(f"Could not parse minute_id for sorting: {minute_id}")
        return (0, 0, 0, 0)
    
    return (0, 0, 0, 0)


def reorganize_by_agenda_items(document_data: Dict[str, Any]) -> Dict[str, Any]:
    """Reorganize a document to group subjects under agenda items."""
    
    # Extract document-level fields
    # Create new structure with agenda_items
    reorganized = {
        'minute_id': document_data['minute_id'],
        'full_text': document_data['full_text'],
        'personal_info': document_data.get('personal_info', []),
        'metadata': document_data['metadata'],
        'agenda_items': []
    }
    
    # Group subjects by agenda_item, preserving order
    agenda_map = {}  # Use dict to preserve insertion order (Python 3.7+)
    agenda_order = []  # Track the order agenda items first appear
    
    for subject in document_data.get('subjects', []):
        # Get agenda_item text
        agenda_item = subject.get('agenda_item', {})
        agenda_text = agenda_item.get('text', 'NO_AGENDA_ITEM')
        
        # Track first occurrence to preserve order
        if agenda_text not in agenda_map:
            agenda_order.append(agenda_text)
            agenda_map[agenda_text] = []
        
        # Create a copy of subject without agenda_item
        subject_copy = {k: v for k, v in subject.items() if k != 'agenda_item'}
        
        # Add to agenda map
        agenda_map[agenda_text].append({
            'agenda_item_obj': agenda_item,
            'subject': subject_copy
        })
    
    # Create agenda_items array with item_id, preserving original order
    item_id = 1
    for agenda_text in agenda_order:
        items = agenda_map[agenda_text]
        # Get the full agenda_item object from first subject
        agenda_item_obj = items[0]['agenda_item_obj']
        
        agenda_item_entry = {
            'item_id': item_id,
            'item_title': agenda_text,
            'subjects': [item['subject'] for item in items]
        }
        
        reorganized['agenda_items'].append(agenda_item_entry)
        item_id += 1
    
    return reorganized


def reorganize_municipality_file(input_file: Path, output_file: Path, debug: bool = False) -> bool:
    """Reorganize a single municipality file by agenda items."""
    logger.info(f"Reorganizing {input_file.name}")
    
    data = load_json_file(input_file)
    if not data or "minutes" not in data:
        logger.error(f"Invalid data structure in {input_file}")
        return False
    
    # New structure: municipalities array
    reorganized_data = {"municipalities": []}
    total_agenda_items = 0
    total_subjects = 0
    
    # Process each municipality and document
    for municipality_name, documents in data["minutes"].items():
        logger.info(f"  Processing {municipality_name}: {len(documents)} documents")
        
        municipality_entry = {
            "municipality": municipality_name,
            "minutes": []
        }
        
        for minute_id, document_data in documents.items():
            reorganized_doc = reorganize_by_agenda_items(document_data)
            municipality_entry["minutes"].append(reorganized_doc)
            
            num_agenda_items = len(reorganized_doc['agenda_items'])
            num_subjects = sum(len(item['subjects']) for item in reorganized_doc['agenda_items'])
            total_agenda_items += num_agenda_items
            total_subjects += num_subjects
            
            if debug:
                logger.debug(f"    {minute_id}: {num_agenda_items} agenda items, {num_subjects} subjects")
        
        # Sort minutes chronologically by date and minute number
        municipality_entry["minutes"].sort(key=lambda m: extract_minute_sort_key(m['minute_id']))
        
        reorganized_data["municipalities"].append(municipality_entry)
    
    logger.info(f"  Total: {total_agenda_items} agenda items, {total_subjects} subjects")
    
    # Save reorganized data
    if save_json_file(reorganized_data, output_file):
        logger.info(f"  ✅ Reorganized → {output_file}")
        return True
    else:
        logger.error(f"  ❌ Failed to save {output_file}")
        return False


def reorganize_datasets(input_dir: Path, output_dir: Path, debug: bool = False) -> bool:
    """Reorganize all municipality datasets by agenda items."""
    logger.info(f"Reorganizing datasets from {input_dir}")
    logger.info(f"Output: {output_dir}")
    
    # Find all municipality files
    municipality_files = list(input_dir.glob("*.json"))
    
    if not municipality_files:
        logger.error(f"No municipality files found in {input_dir}")
        return False
    
    logger.info(f"Found {len(municipality_files)} municipality files")
    
    success_count = 0
    for municipality_file in municipality_files:
        output_file = output_dir / municipality_file.name
        if reorganize_municipality_file(municipality_file, output_file, debug):
            success_count += 1
    
    logger.info(f"✅ Reorganization complete: {success_count}/{len(municipality_files)} files processed")
    return success_count > 0


def main():
    parser = argparse.ArgumentParser(
        description="Reorganize datasets by agenda items"
    )
    
    parser.add_argument(
        '--input_dir',
        type=str,
        required=True,
        help='Input directory containing municipality-level datasets'
    )
    
    parser.add_argument(
        '--output_dir',
        type=str,
        required=True,
        help='Output directory for agenda-centric datasets'
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
    
    success = reorganize_datasets(input_dir, output_dir, debug=args.debug)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
