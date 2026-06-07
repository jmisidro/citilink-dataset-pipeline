#!/usr/bin/env python3
"""
Remove Rodrigo-delimited intervals from INCEpTION annotations.

This script processes INCEpTION JSON files and REMOVES the content between
"Rodrigo: inicio" and "Rodrigo: fim" markers (which mark invalid/excerpt content).
This ensures the parser only processes the validated document content.

Input: INCEpTION annotations with Rodrigo markers delimiting content to remove
Output: Cleaned INCEpTION annotations with Rodrigo-marked intervals removed
"""

import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Offset pairs to adjust when modifying text
OFFSET_PAIRS = [
    ("begin", "end"),
]


def load_json(path: Path) -> Dict[str, Any]:
    """Load JSON file with error handling."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading {path}: {e}")
        return {}


def save_json(path: Path, data: Dict[str, Any]) -> bool:
    """Save data to JSON file."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving {path}: {e}")
        return False


def get_sofa_ann_and_text(data: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
    """Extract SOFA annotation and text from INCEpTION data."""
    for ann in data.get("%FEATURE_STRUCTURES", []):
        if ann.get("%TYPE") == "uima.cas.Sofa":
            return ann, ann.get("sofaString", "")
    raise ValueError("uima.cas.Sofa not found in JSON.")


def set_sofa_text(sofa_ann: Dict[str, Any], new_text: str) -> None:
    """Update SOFA text in annotation."""
    sofa_ann["sofaString"] = new_text


def extract_rodrigo_intervals(data: Dict[str, Any]) -> List[Tuple[int, int]]:
    """
    Extract intervals marked by Rodrigo inicio/fim pairs.
    
    Returns:
        List of (start, end) tuples representing valid document intervals
    """
    inicios = []
    fins = []
    
    for ann in data.get("%FEATURE_STRUCTURES", []):
        if ann.get("%TYPE") == "custom.Span" and "Rodrigo" in ann:
            if ann["Rodrigo"] == "inicio":
                inicios.append(ann["begin"])
            elif ann["Rodrigo"] == "fim":
                fins.append(ann["end"])
    
    # Sort and pair up
    inicios.sort()
    fins.sort()
    
    if len(inicios) != len(fins):
        logger.warning(f"Mismatched Rodrigo markers: {len(inicios)} inicios, {len(fins)} fins")
    
    return list(zip(inicios, fins))


def delete_intervals_and_adjust(data: Dict[str, Any], intervals_to_delete: List[Tuple[int, int]]) -> bool:
    """
    Delete specified intervals from text and adjust all annotations.
    
    Args:
        data: INCEpTION JSON data
        intervals_to_delete: List of (start, end) intervals to remove
        
    Returns:
        True if successful, False otherwise
    """
    if not intervals_to_delete:
        logger.info("No intervals to delete - keeping file as-is")
        return True
    
    # Get original text
    sofa_ann, original_text = get_sofa_ann_and_text(data)
    
    # Sort intervals by start position
    intervals = sorted(intervals_to_delete, key=lambda x: x[0])
    
    # Delete intervals one by one, adjusting for cumulative shift
    total_deleted = 0
    shifted = 0
    
    for start, end in intervals:
        # Adjust positions for previous deletions
        start_adj = start - shifted
        end_adj = end - shifted
        
        if start_adj < 0 or end_adj < 0 or end_adj > len(sofa_ann["sofaString"]) or end_adj <= start_adj:
            logger.error(f"Invalid interval after adjustment: [{start_adj}, {end_adj})")
            return False
        
        deleted = delete_interval_inplace(data, sofa_ann, start_adj, end_adj)
        total_deleted += deleted
        shifted += (end - start)
    
    logger.debug(f"Deleted {total_deleted} characters total")
    logger.debug(f"Original text length: {len(original_text)}, new length: {len(sofa_ann['sofaString'])}")
    
    return True


def delete_interval_inplace(data: Dict[str, Any], sofa_ann: Dict[str, Any], 
                           start_del: int, end_del: int) -> int:
    """
    Delete a single interval from text and adjust annotations in-place.
    
    Args:
        data: INCEpTION JSON data
        sofa_ann: SOFA annotation containing the text
        start_del: Start position of interval to delete
        end_del: End position of interval to delete
        
    Returns:
        Number of characters deleted
    """
    text = sofa_ann["sofaString"]
    deleted_len = end_del - start_del
    
    # Remove the interval from text
    new_text = text[:start_del] + text[end_del:]
    sofa_ann["sofaString"] = new_text
    
    # Adjust all annotations
    survivors = []
    removed_count = 0
    
    for ann in data.get("%FEATURE_STRUCTURES", []):
        if ann is sofa_ann:
            survivors.append(ann)
            continue
        
        # Check if annotation has offset pairs
        has_offsets = any(fb in ann and fe in ann for fb, fe in OFFSET_PAIRS)
        
        if not has_offsets:
            # No offsets to adjust, keep as-is
            survivors.append(ann)
            continue
        
        # Adjust offset pairs
        mod = dict(ann)
        to_remove = False
        
        for fb, fe in OFFSET_PAIRS:
            if fb in mod and fe in mod and mod[fb] is not None and mod[fe] is not None:
                begin = int(mod[fb])
                end = int(mod[fe])
                
                # Check how annotation relates to deleted interval
                if end <= start_del:
                    # Annotation is entirely before deleted interval - no change needed
                    pass
                elif begin >= end_del:
                    # Annotation is entirely after deleted interval - shift back
                    mod[fb] = begin - deleted_len
                    mod[fe] = end - deleted_len
                elif begin >= start_del and end <= end_del:
                    # Annotation is entirely within deleted interval - remove it
                    to_remove = True
                    break
                elif begin < start_del < end <= end_del:
                    # Annotation starts before and ends within deleted interval
                    mod[fe] = start_del
                elif start_del <= begin < end_del < end:
                    # Annotation starts within and ends after deleted interval
                    mod[fb] = start_del
                    mod[fe] = end - deleted_len
                elif begin < start_del and end > end_del:
                    # Annotation spans the entire deleted interval
                    mod[fe] = end - deleted_len
        
        if not to_remove:
            survivors.append(mod)
        else:
            removed_count += 1
    
    # Remove relations pointing to deleted annotations
    remaining_ids = {ann.get("%ID") for ann in survivors if "%ID" in ann}
    cleaned = []
    
    for ann in survivors:
        if ann.get("%TYPE") == "custom.Relation":
            dep = ann.get("@Dependent")
            gov = ann.get("@Governor")
            if (dep is not None and dep not in remaining_ids) or \
               (gov is not None and gov not in remaining_ids):
                removed_count += 1
                continue
        cleaned.append(ann)
    
    data["%FEATURE_STRUCTURES"] = cleaned
    
    logger.debug(f"Kept {len(cleaned)} annotations, removed {removed_count}")
    
    return deleted_len


def process_file_pair(rodrigo_file: Path, inception_file: Path, output_file: Path) -> bool:
    """
    Process a file pair: extract Rodrigo intervals from one file and apply to another.
    
    Args:
        rodrigo_file: Path to file with Rodrigo boundary markers
        inception_file: Path to file with up-to-date annotations to be cleaned
        output_file: Path to output file
        
    Returns:
        True if successful, False otherwise
    """
    logger.info(f"Processing {inception_file.name}")
    logger.debug(f"  Rodrigo boundaries from: {rodrigo_file.name}")
    logger.debug(f"  Applying to: {inception_file.name}")
    
    # Load Rodrigo boundary file
    rodrigo_data = load_json(rodrigo_file)
    if not rodrigo_data:
        logger.warning(f"  Could not load Rodrigo file, processing inception file as-is")
        inception_data = load_json(inception_file)
        if inception_data and save_json(output_file, inception_data):
            logger.info(f"  ✅ No Rodrigo file - copied inception file as-is → {output_file.name}")
            return True
        return False
    
    # Extract Rodrigo intervals
    intervals = extract_rodrigo_intervals(rodrigo_data)
    
    if not intervals:
        logger.info(f"  No Rodrigo intervals found - processing inception file as-is")
        inception_data = load_json(inception_file)
        if inception_data and save_json(output_file, inception_data):
            logger.info(f"  ✅ No Rodrigo markers - copied inception file as-is → {output_file.name}")
            return True
        return False
    
    logger.info(f"  Found {len(intervals)} Rodrigo interval(s) to remove: {intervals}")
    
    # Load inception file (the one with up-to-date annotations)
    inception_data = load_json(inception_file)
    if not inception_data:
        logger.error(f"  ❌ Could not load inception file")
        return False
    
    # Delete intervals and adjust annotations on the inception data
    if not delete_intervals_and_adjust(inception_data, intervals):
        logger.error(f"  ❌ Failed to delete intervals")
        return False
    
    # Save result
    if save_json(output_file, inception_data):
        logger.info(f"  ✅ Removed intervals → {output_file.name}")
        return True
    else:
        logger.error(f"  ❌ Failed to save {output_file.name}")
        return False


def process_directories(rodrigo_dir: Path, inception_dir: Path, output_dir: Path, debug: bool = False) -> bool:
    """
    Process file pairs: extract Rodrigo boundaries from one directory and apply to files in another.
    
    Args:
        rodrigo_dir: Directory containing files with Rodrigo boundary markers
        inception_dir: Directory containing files with up-to-date annotations
        output_dir: Directory for output files
        debug: Enable debug logging
        
    Returns:
        True if at least one file was processed successfully
    """
    logger.info(f"Processing file pairs:")
    logger.info(f"  Rodrigo boundaries from: {rodrigo_dir}")
    logger.info(f"  Applying to inception files from: {inception_dir}")
    logger.info(f"  Output directory: {output_dir}")
    
    if debug:
        logger.setLevel(logging.DEBUG)
    
    # Find all JSON files in inception directory (these are the ones we want to process)
    inception_files = list(inception_dir.glob("*.json"))
    
    if not inception_files:
        logger.error(f"No JSON files found in inception directory: {inception_dir}")
        return False
    
    logger.info(f"Found {len(inception_files)} inception files to process")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Process each file pair
    success_count = 0
    for inception_file in inception_files:
        # Find corresponding Rodrigo file
        rodrigo_file = rodrigo_dir / inception_file.name
        output_file = output_dir / inception_file.name
        
        if process_file_pair(rodrigo_file, inception_file, output_file):
            success_count += 1
    
    logger.info(f"✅ Processing complete: {success_count}/{len(inception_files)} files processed successfully")
    return success_count > 0


def main():
    parser = argparse.ArgumentParser(
        description="Extract Rodrigo-delimited intervals from INCEpTION annotations"
    )
    
    parser.add_argument(
        '--rodrigo_dir',
        type=str,
        required=True,
        help='Directory containing files with Rodrigo boundary markers'
    )
    
    parser.add_argument(
        '--inception_dir',
        type=str,
        required=True,
        help='Directory containing INCEpTION files with up-to-date annotations'
    )
    
    parser.add_argument(
        '--output_dir',
        type=str,
        required=True,
        help='Output directory for processed files'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    rodrigo_dir = Path(args.rodrigo_dir)
    inception_dir = Path(args.inception_dir)
    output_dir = Path(args.output_dir)
    
    if not rodrigo_dir.exists():
        logger.error(f"Rodrigo directory not found: {rodrigo_dir}")
        return 1
    
    if not inception_dir.exists():
        logger.error(f"Inception directory not found: {inception_dir}")
        return 1
    
    success = process_directories(rodrigo_dir, inception_dir, output_dir, debug=args.debug)
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
