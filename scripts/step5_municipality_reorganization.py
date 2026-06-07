#!/usr/bin/env python3
"""
Reorganize translated datasets into final structure.

This script:
1. Groups documents by municipality into separate JSON files
2. Creates a combined JSON file with all municipalities

Input: Translated individual document files
Output: Municipality-specific files + all_municipalities.json
"""

import json
import logging
import argparse
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


def reorganize_datasets(input_dir: Path, output_dir: Path, debug: bool = False) -> bool:
    """Reorganize datasets by municipality and create combined file."""
    logger.info(f"Reorganizing datasets from {input_dir}")
    logger.info(f"Output: {output_dir}")
    
    # Find all JSON files
    json_files = list(input_dir.glob("*.json"))
    
    if not json_files:
        logger.error(f"No JSON files found in {input_dir}")
        return False
    
    logger.info(f"Found {len(json_files)} JSON files to reorganize")
    
    # Group documents by municipality
    municipalities = defaultdict(dict)
    total_documents = 0
    total_subjects = 0
    
    for json_file in json_files:
        data = load_json_file(json_file)
        if not data or "minutes" not in data:
            logger.warning(f"Skipping {json_file.name}: Invalid structure")
            continue
        
        # Extract municipality and document data
        for municipality_name, documents in data["minutes"].items():
            for doc_id, document_data in documents.items():
                municipalities[municipality_name][doc_id] = document_data
                total_documents += 1
                total_subjects += len(document_data.get('subjects', []))
                
                if debug:
                    logger.debug(f"  Added {doc_id} to {municipality_name}")
    
    logger.info(f"Grouped {total_documents} documents into {len(municipalities)} municipalities")
    logger.info(f"Total subjects: {total_subjects}")
    
    # Save individual municipality files
    success_count = 0
    for municipality_name, documents in municipalities.items():
        municipality_data = {
            "minutes": {
                municipality_name: documents
            }
        }
        
        output_file = output_dir / f"{municipality_name}.json"
        if save_json_file(municipality_data, output_file):
            logger.info(f"  ✅ Saved {municipality_name}.json ({len(documents)} documents)")
            success_count += 1
        else:
            logger.error(f"  ❌ Failed to save {municipality_name}.json")
    
    # Create combined file with all municipalities
    all_municipalities_data = {
        "minutes": dict(municipalities)
    }
    
    combined_file = output_dir / "all_municipalities.json"
    if save_json_file(all_municipalities_data, combined_file):
        logger.info(f"  ✅ Saved all_municipalities.json ({total_documents} documents)")
        success_count += 1
    else:
        logger.error(f"  ❌ Failed to save all_municipalities.json")
    
    logger.info(f"✅ Reorganization complete: {success_count} files created")
    return success_count > 0


def main():
    parser = argparse.ArgumentParser(
        description="Reorganize translated datasets by municipality"
    )
    
    parser.add_argument(
        '--input_dir',
        type=str,
        required=True,
        help='Input directory containing translated datasets'
    )
    
    parser.add_argument(
        '--output_dir',
        type=str,
        required=True,
        help='Output directory for reorganized datasets'
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
