#!/usr/bin/env python3
"""
Anonymization Step for CitiLink Pipeline

This script anonymizes personal information in parsed subject files.
It reads files from step 1 (parsed subjects) and outputs anonymized versions.
"""

import json
import logging
import argparse
from pathlib import Path
from typing import Dict, List, Any

# Import anonymization module
from anonymize_pipeline import anonymize_document

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def anonymize_parsed_file(input_file: Path, output_dir: Path) -> bool:
    """
    Anonymize a single parsed subject file.
    
    Args:
        input_file: Path to input JSON file (from step 1)
        output_dir: Directory to write anonymized output
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Processing: {input_file.name}")
        
        # Load input file
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Process each municipality -> document
        for municipality, docs in data.get("minutes", {}).items():
            for doc_id, doc_data in docs.items():
                logger.info(f"  Anonymizing document: {doc_id}")
                
                # Extract data
                full_text = doc_data.get("full_text", "")
                personal_info = doc_data.get("personal_info", [])
                subjects = doc_data.get("subjects", [])
                metadata = doc_data.get("metadata", {})
                
                # Collect all annotations for offset adjustment
                all_annotations = []
                
                # Add subject annotations
                for subject in subjects:
                    # Subject boundary
                    all_annotations.append({
                        'type': 'subject_boundary',
                        'start': subject['start'],
                        'end': subject['end'],
                        'text': subject['text']
                    })
                    
                    # Subject annotation (objeto de votação)
                    if 'subject' in subject:
                        all_annotations.append({
                            'type': 'subject_annotation',
                            'start': subject['subject']['start'],
                            'end': subject['subject']['end'],
                            'text': subject['subject']['text']
                        })
                    
                    # Voting annotations
                    for voting in subject.get('voting', []):
                        # Voting evidence
                        if 'voting_evidence' in voting:
                            ve = voting['voting_evidence']
                            all_annotations.append({
                                'type': 'voting_evidence',
                                'start': ve['start'],
                                'end': ve['end'],
                                'text': ve['text']
                            })

                        # Vote type (método de votação) inside voting object
                        if 'vote_type' in voting:
                            vt = voting['vote_type']
                            all_annotations.append({
                                'type': 'voting_vote_type',
                                'start': vt['start'],
                                'end': vt['end'],
                                'text': vt['text']
                            })
                        
                        # Voters (including blank)
                        for category in ['in_favor', 'against', 'abstention', 'blank']:
                            for voter in voting.get('voters', {}).get(category, []):
                                all_annotations.append({
                                    'type': f'voter_{category}',
                                    'start': voter['start'],
                                    'end': voter['end'],
                                    'text': voter['text']
                                })
                        
                        # Non-voters
                        for non_voter in voting.get('non_voters', []):
                            all_annotations.append({
                                'type': 'non_voter',
                                'start': non_voter['start'],
                                'end': non_voter['end'],
                                'text': non_voter['text']
                            })

                        # Global tally span (when offsets are available)
                        gt = voting.get('global_tally')
                        if isinstance(gt, dict) and gt.get('start') is not None and gt.get('end') is not None:
                            all_annotations.append({
                                'type': 'global_tally',
                                'start': gt['start'],
                                'end': gt['end'],
                                'text': gt.get('text', '')
                            })
                    
                    # Sub-subject annotations
                    for sub_subj in subject.get('sub_subjects', []):
                        all_annotations.append({
                            'type': 'sub_subject_boundary',
                            'start': sub_subj['start'],
                            'end': sub_subj['end'],
                            'text': sub_subj['text']
                        })
                        # Sub-subject voting
                        for ss_voting in sub_subj.get('voting', []):
                            if 'voting_evidence' in ss_voting:
                                ve = ss_voting['voting_evidence']
                                all_annotations.append({
                                    'type': 'sub_subject_voting_evidence',
                                    'start': ve['start'],
                                    'end': ve['end'],
                                    'text': ve['text']
                                })
                            if 'vote_type' in ss_voting:
                                vt = ss_voting['vote_type']
                                all_annotations.append({
                                    'type': 'sub_subject_voting_vote_type',
                                    'start': vt['start'],
                                    'end': vt['end'],
                                    'text': vt['text']
                                })
                            for category in ['in_favor', 'against', 'abstention', 'blank']:
                                for voter in ss_voting.get('voters', {}).get(category, []):
                                    all_annotations.append({
                                        'type': f'sub_subject_voter_{category}',
                                        'start': voter['start'],
                                        'end': voter['end'],
                                        'text': voter['text']
                                    })
                            for non_voter in ss_voting.get('non_voters', []):
                                all_annotations.append({
                                    'type': 'sub_subject_non_voter',
                                    'start': non_voter['start'],
                                    'end': non_voter['end'],
                                    'text': non_voter['text']
                                })

                            gt = ss_voting.get('global_tally')
                            if isinstance(gt, dict) and gt.get('start') is not None and gt.get('end') is not None:
                                all_annotations.append({
                                    'type': 'sub_subject_global_tally',
                                    'start': gt['start'],
                                    'end': gt['end'],
                                    'text': gt.get('text', '')
                                })
                
                # Add metadata annotations
                for field_name, field_value in metadata.items():
                    if isinstance(field_value, dict) and 'start' in field_value and 'end' in field_value:
                        all_annotations.append({
                            'type': f'metadata_{field_name}',
                            'start': field_value['start'],
                            'end': field_value['end'],
                            'text': field_value.get('text', field_value.get('name', '')),
                            'partido': field_value.get('partido')
                        })
                    elif isinstance(field_value, list):
                        for item in field_value:
                            if isinstance(item, dict) and 'start' in item and 'end' in item:
                                all_annotations.append({
                                    'type': f'metadata_{field_name}_item',
                                    'start': item['start'],
                                    'end': item['end'],
                                    'text': item.get('text', item.get('name', '')),
                                    'partido': item.get('partido')
                                })
                
                # Anonymize
                logger.info(f"    Anonymizing {len(personal_info)} personal info annotations")
                anonymized_text, adjusted_annotations, anonymized_personal_info = anonymize_document(
                    full_text,
                    personal_info,
                    all_annotations
                )
                
                # Create annotation lookup (use ORIGINAL offsets as keys)
                annotation_map = {}
                for ann in adjusted_annotations:
                    # Use original offsets for the key (before adjustment)
                    original_start = ann.get('original_start', ann.get('start'))
                    original_end = ann.get('original_end', ann.get('end'))
                    key = f"{ann['type']}_{original_start}_{original_end}"
                    annotation_map[key] = ann
                
                # Update subjects with adjusted offsets
                updated_subjects = []
                for subject in subjects:
                    # Find adjusted subject boundary
                    subj_key = f"subject_boundary_{subject['start']}_{subject['end']}"
                    adj_subj = annotation_map.get(subj_key, subject)
                    
                    updated_subject = {
                        'subject_id': subject['subject_id'],
                        'text': anonymized_text[adj_subj['start']:adj_subj['end']],
                        'start': adj_subj['start'],
                        'end': adj_subj['end'],
                        'agenda_item': subject.get('agenda_item')
                    }
                    
                    # Update subject annotation
                    if 'subject' in subject:
                        subj_ann = subject['subject']
                        subj_ann_key = f"subject_annotation_{subj_ann['start']}_{subj_ann['end']}"
                        adj_subj_ann = annotation_map.get(subj_ann_key, subj_ann)
                        updated_subject['subject'] = {
                            'text': anonymized_text[adj_subj_ann['start']:adj_subj_ann['end']],
                            'start': adj_subj_ann['start'],
                            'end': adj_subj_ann['end']
                        }
                    
                    # Copy topics, theme, and summary
                    if 'topics' in subject:
                        updated_subject['topics'] = subject['topics']
                    if 'theme' in subject:
                        updated_subject['theme'] = subject['theme']
                    if 'summary' in subject:
                        updated_subject['summary'] = subject['summary']
                    
                    # Update voting annotations
                    updated_voting = []
                    for voting in subject.get('voting', []):
                        updated_vote = {
                            'voting_evidence': {},
                            'voters': {'in_favor': [], 'against': [], 'abstention': [], 'blank': []},
                            'non_voters': [],
                            'global_tally': None
                        }
                        
                        # Update voting evidence
                        if 'voting_evidence' in voting:
                            ve = voting['voting_evidence']
                            ve_key = f"voting_evidence_{ve['start']}_{ve['end']}"
                            adj_ve = annotation_map.get(ve_key, ve)
                            updated_vote['voting_evidence'] = {
                                'text': anonymized_text[adj_ve['start']:adj_ve['end']],
                                'start': adj_ve['start'],
                                'end': adj_ve['end']
                            }

                        # Update vote_type (método de votação) inside voting object
                        if 'vote_type' in voting:
                            vt = voting['vote_type']
                            vt_key = f"voting_vote_type_{vt['start']}_{vt['end']}"
                            adj_vt = annotation_map.get(vt_key, vt)
                            updated_vote['vote_type'] = {
                                'text': anonymized_text[adj_vt['start']:adj_vt['end']],
                                'start': adj_vt['start'],
                                'end': adj_vt['end']
                            }
                        
                        # Update voters (including blank)
                        for category in ['in_favor', 'against', 'abstention', 'blank']:
                            for voter in voting.get('voters', {}).get(category, []):
                                voter_key = f"voter_{category}_{voter['start']}_{voter['end']}"
                                adj_voter = annotation_map.get(voter_key, voter)
                                updated_vote['voters'][category].append({
                                    'text': anonymized_text[adj_voter['start']:adj_voter['end']],
                                    'start': adj_voter['start'],
                                    'end': adj_voter['end']
                                })
                        
                        # Update non-voters
                        for non_voter in voting.get('non_voters', []):
                            nv_key = f"non_voter_{non_voter['start']}_{non_voter['end']}"
                            adj_nv = annotation_map.get(nv_key, non_voter)
                            updated_vote['non_voters'].append({
                                'text': anonymized_text[adj_nv['start']:adj_nv['end']],
                                'start': adj_nv['start'],
                                'end': adj_nv['end']
                            })

                        # Update global_tally offsets/text when span exists
                        gt = voting.get('global_tally')
                        if isinstance(gt, dict):
                            updated_gt = gt.copy()
                            if gt.get('start') is not None and gt.get('end') is not None:
                                gt_key = f"global_tally_{gt['start']}_{gt['end']}"
                                adj_gt = annotation_map.get(gt_key, gt)
                                updated_gt['start'] = adj_gt['start']
                                updated_gt['end'] = adj_gt['end']
                                updated_gt['text'] = anonymized_text[adj_gt['start']:adj_gt['end']]
                            updated_vote['global_tally'] = updated_gt
                        
                        updated_voting.append(updated_vote)
                    
                    updated_subject['voting'] = updated_voting

                    # Update sub-subjects with adjusted offsets
                    if 'sub_subjects' in subject:
                        updated_sub_subjects = []
                        for sub_subj in subject['sub_subjects']:
                            ss_key = f"sub_subject_boundary_{sub_subj['start']}_{sub_subj['end']}"
                            adj_ss = annotation_map.get(ss_key, sub_subj)
                            updated_ss: Dict[str, Any] = {
                                'text': anonymized_text[adj_ss['start']:adj_ss['end']],
                                'start': adj_ss['start'],
                                'end': adj_ss['end'],
                            }
                            if 'theme' in sub_subj:
                                updated_ss['theme'] = sub_subj['theme']
                            # Sub-subject voting
                            updated_ss_voting = []
                            for ss_voting in sub_subj.get('voting', []):
                                updated_ss_vote = {
                                    'voting_evidence': {},
                                    'voters': {'in_favor': [], 'against': [], 'abstention': [], 'blank': []},
                                    'non_voters': [],
                                    'global_tally': None
                                }
                                if 'voting_evidence' in ss_voting:
                                    ve = ss_voting['voting_evidence']
                                    ve_key = f"sub_subject_voting_evidence_{ve['start']}_{ve['end']}"
                                    adj_ve = annotation_map.get(ve_key, ve)
                                    updated_ss_vote['voting_evidence'] = {
                                        'text': anonymized_text[adj_ve['start']:adj_ve['end']],
                                        'start': adj_ve['start'],
                                        'end': adj_ve['end']
                                    }
                                if 'vote_type' in ss_voting:
                                    vt = ss_voting['vote_type']
                                    vt_key = f"sub_subject_voting_vote_type_{vt['start']}_{vt['end']}"
                                    adj_vt = annotation_map.get(vt_key, vt)
                                    updated_ss_vote['vote_type'] = {
                                        'text': anonymized_text[adj_vt['start']:adj_vt['end']],
                                        'start': adj_vt['start'],
                                        'end': adj_vt['end']
                                    }
                                for category in ['in_favor', 'against', 'abstention', 'blank']:
                                    for voter in ss_voting.get('voters', {}).get(category, []):
                                        vk = f"sub_subject_voter_{category}_{voter['start']}_{voter['end']}"
                                        adj_v = annotation_map.get(vk, voter)
                                        updated_ss_vote['voters'][category].append({
                                            'text': anonymized_text[adj_v['start']:adj_v['end']],
                                            'start': adj_v['start'],
                                            'end': adj_v['end']
                                        })
                                for non_voter in ss_voting.get('non_voters', []):
                                    nv_key = f"sub_subject_non_voter_{non_voter['start']}_{non_voter['end']}"
                                    adj_nv = annotation_map.get(nv_key, non_voter)
                                    updated_ss_vote['non_voters'].append({
                                        'text': anonymized_text[adj_nv['start']:adj_nv['end']],
                                        'start': adj_nv['start'],
                                        'end': adj_nv['end']
                                    })

                                gt = ss_voting.get('global_tally')
                                if isinstance(gt, dict):
                                    updated_gt = gt.copy()
                                    if gt.get('start') is not None and gt.get('end') is not None:
                                        gt_key = f"sub_subject_global_tally_{gt['start']}_{gt['end']}"
                                        adj_gt = annotation_map.get(gt_key, gt)
                                        updated_gt['start'] = adj_gt['start']
                                        updated_gt['end'] = adj_gt['end']
                                        updated_gt['text'] = anonymized_text[adj_gt['start']:adj_gt['end']]
                                    updated_ss_vote['global_tally'] = updated_gt

                                updated_ss_voting.append(updated_ss_vote)
                            if updated_ss_voting:
                                updated_ss['voting'] = updated_ss_voting
                            updated_sub_subjects.append(updated_ss)
                        updated_subject['sub_subjects'] = updated_sub_subjects

                    updated_subjects.append(updated_subject)
                
                # Update metadata with adjusted offsets
                updated_metadata = {}
                for field_name, field_value in metadata.items():
                    if isinstance(field_value, dict) and 'start' in field_value and 'end' in field_value:
                        meta_key = f"metadata_{field_name}_{field_value['start']}_{field_value['end']}"
                        adj_meta = annotation_map.get(meta_key, field_value)
                        # Preserve original structure, update offsets and text/name
                        updated_field = field_value.copy()
                        updated_field['start'] = adj_meta['start']
                        updated_field['end'] = adj_meta['end']
                        anonymized_value = anonymized_text[adj_meta['start']:adj_meta['end']]
                        if 'name' in updated_field:
                            updated_field['name'] = anonymized_value
                        elif 'text' in updated_field:
                            updated_field['text'] = anonymized_value
                        updated_metadata[field_name] = updated_field
                    elif isinstance(field_value, list):
                        updated_list = []
                        for item in field_value:
                            if isinstance(item, dict) and 'start' in item and 'end' in item:
                                item_key = f"metadata_{field_name}_item_{item['start']}_{item['end']}"
                                adj_item = annotation_map.get(item_key, item)
                                # Preserve original structure, update offsets and text/name
                                updated_item = item.copy()
                                updated_item['start'] = adj_item['start']
                                updated_item['end'] = adj_item['end']
                                anonymized_value = anonymized_text[adj_item['start']:adj_item['end']]
                                if 'name' in updated_item:
                                    updated_item['name'] = anonymized_value
                                elif 'text' in updated_item:
                                    updated_item['text'] = anonymized_value
                                updated_list.append(updated_item)
                            else:
                                updated_list.append(item)
                        updated_metadata[field_name] = updated_list
                    else:
                        updated_metadata[field_name] = field_value
                
                # Remove temporary original_start/original_end fields from personal_info
                for pi in anonymized_personal_info:
                    pi.pop('original_start', None)
                    pi.pop('original_end', None)
                
                # Sort personal_info by start position
                anonymized_personal_info.sort(key=lambda x: x.get('start', 0))
                
                # Update document
                doc_data['full_text'] = anonymized_text
                doc_data['personal_info'] = anonymized_personal_info
                doc_data['subjects'] = updated_subjects
                doc_data['metadata'] = updated_metadata
                
                logger.info(f"    ✅ Anonymized successfully")
        
        # Write output
        output_file = output_dir / input_file.name
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"✅ Saved to: {output_file.name}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error processing {input_file.name}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Anonymize personal information in parsed subject files"
    )
    
    parser.add_argument(
        '--input_dir',
        type=str,
        required=True,
        help='Input directory with parsed subject files (from step 1)'
    )
    
    parser.add_argument(
        '--output_dir',
        type=str,
        required=True,
        help='Output directory for anonymized files'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logger.setLevel(logging.DEBUG)
    
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    
    if not input_dir.exists():
        logger.error(f"Input directory not found: {input_dir}")
        return 1
    
    # Find all JSON files
    json_files = list(input_dir.glob("*_subjects.json"))
    
    if not json_files:
        logger.error(f"No *_subjects.json files found in {input_dir}")
        return 1
    
    logger.info(f"Found {len(json_files)} files to process")
    
    success_count = 0
    for json_file in json_files:
        if anonymize_parsed_file(json_file, output_dir):
            success_count += 1
    
    logger.info("=" * 80)
    logger.info(f"✅ Anonymization complete: {success_count}/{len(json_files)} files processed")
    logger.info("=" * 80)
    
    return 0 if success_count == len(json_files) else 1


if __name__ == "__main__":
    exit(main())
