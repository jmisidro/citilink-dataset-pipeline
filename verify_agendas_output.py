#!/usr/bin/env python3
"""
Verification Script for CitiLink Agenda-Centric JSON Output (Step 4)

This script validates that the agenda-reorganized JSON files conform to the
expected structure.

It checks:
1. Overall structure (minutes -> Municipality -> DocumentID)
2. Document has agenda_items array instead of subjects array
3. Each agenda_item has item_id, item_title, and subjects array
4. Subjects within agenda_items maintain original document order
5. Subjects don't contain agenda_item field (it's been moved up)
6. All other subject fields remain intact (voting, theme, topics, etc.)
7. Metadata completeness and format
8. Field ordering and types
"""

import json
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AgendasValidator:
    def __init__(self, strict: bool = False, check_translations: bool = False):
        self.strict = strict
        self.check_translations = check_translations
        self.errors = []
        self.warnings = []
        self.stats = {
            'total_minutes': 0,
            'total_agenda_items': 0,
            'total_subjects': 0,
            'subjects_with_voting': 0,
            'subjects_with_discussion': 0,
            'total_participants': 0,
            'subjects_with_agenda_item_field': 0,  # Should be 0!
            'total_sub_subjects': 0,
            'subjects_with_blank_votes': 0,
        }
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate a single JSON file."""
        logger.info(f"Validating {file_path.name}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"❌ {file_path.name}: Invalid JSON - {str(e)}")
            return False
        except Exception as e:
            self.errors.append(f"❌ {file_path.name}: Failed to load - {str(e)}")
            return False
        
        # Validate structure
        if not self.validate_root_structure(data, file_path.name):
            return False
        
        # Validate each document
        for municipality, minutes in data['minutes'].items():
            for doc_id, document in minutes.items():
                if not self.validate_document(document, municipality, doc_id, file_path.name):
                    return False
        
        return len(self.errors) == 0
    
    def validate_root_structure(self, data: Dict, filename: str) -> bool:
        """Validate the root structure of the JSON."""
        if 'municipalities' not in data:
            self.errors.append(f"❌ {filename}: Missing 'municipalities' key at root level")
            return False
        
        if not isinstance(data['municipalities'], list):
            self.errors.append(f"❌ {filename}: 'municipalities' must be a list")
            return False
        
        if len(data['municipalities']) == 0:
            self.warnings.append(f"⚠️ {filename}: No municipalities found in 'municipalities' array")
        
        return True
    
    def validate_file(self, file_path: Path) -> bool:
        """Validate a single JSON file."""
        logger.info(f"Validating {file_path.name}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            self.errors.append(f"❌ {file_path.name}: Invalid JSON - {str(e)}")
            return False
        except Exception as e:
            self.errors.append(f"❌ {file_path.name}: Failed to load - {str(e)}")
            return False
        
        # Validate structure
        if not self.validate_root_structure(data, file_path.name):
            return False
        
        # Validate each municipality and its minutes
        for municipality_entry in data['municipalities']:
            if not self.validate_municipality(municipality_entry, file_path.name):
                return False
        
        return len(self.errors) == 0
    
    def validate_municipality(self, municipality_entry: Dict, filename: str) -> bool:
        """Validate a municipality entry."""
        # Check required keys
        if 'municipality' not in municipality_entry:
            self.errors.append(f"❌ {filename}: Municipality entry missing 'municipality' key")
            return False
        
        if 'minutes' not in municipality_entry:
            self.errors.append(f"❌ {filename}: Municipality entry missing 'minutes' key")
            return False
        
        municipality_name = municipality_entry['municipality']
        
        if not isinstance(municipality_entry['minutes'], list):
            self.errors.append(f"❌ {filename} [{municipality_name}]: 'minutes' must be a list")
            return False
        
        # Validate each document
        for document in municipality_entry['minutes']:
            if not self.validate_document(document, municipality_name, document.get('minute_id', 'UNKNOWN'), filename):
                return False
        
        return True
    
    def validate_document(self, document: Dict, municipality: str, doc_id: str, filename: str) -> bool:
        """Validate a single document structure."""
        self.stats['total_minutes'] += 1
        
        # Check required top-level keys
        required_keys = ['minute_id', 'full_text', 'metadata', 'agenda_items']
        for key in required_keys:
            if key not in document:
                self.errors.append(f"❌ {filename} [{doc_id}]: Missing required key '{key}'")
                return False
        
        # Validate that 'subjects' is NOT present (it should be under agenda_items now)
        if 'subjects' in document:
            self.errors.append(f"❌ {filename} [{doc_id}]: Document should NOT have 'subjects' at top level (should be under agenda_items)")
            return False
        
        # Validate minute_id matches
        if document['minute_id'] != doc_id:
            self.errors.append(f"❌ {filename} [{doc_id}]: minute_id mismatch (expected '{doc_id}', got '{document['minute_id']}')")
        
        # Validate full_text is present and is a string
        if not isinstance(document['full_text'], str):
            self.errors.append(f"❌ {filename} [{doc_id}]: 'full_text' must be a string")
        elif len(document['full_text']) == 0:
            self.warnings.append(f"⚠️ {filename} [{doc_id}]: 'full_text' is empty")
        
        # Validate metadata
        if not self.validate_metadata(document['metadata'], doc_id, filename):
            return False
        
        # Validate agenda_items
        if not isinstance(document['agenda_items'], list):
            self.errors.append(f"❌ {filename} [{doc_id}]: 'agenda_items' must be a list")
            return False
        
        # Track subject positions to verify ordering
        all_subject_starts = []
        
        for i, agenda_item in enumerate(document['agenda_items']):
            if not self.validate_agenda_item(agenda_item, doc_id, i + 1, filename, all_subject_starts):
                return False
        
        self.stats['total_agenda_items'] += len(document['agenda_items'])
        
        # Verify subjects are in order by start position
        if all_subject_starts != sorted(all_subject_starts):
            self.errors.append(
                f"❌ {filename} [{doc_id}]: Subjects are NOT in original document order! "
                f"Start positions: {all_subject_starts[:10]}..."
            )
        
        return True
    
    def validate_metadata(self, metadata: Dict, doc_id: str, filename: str) -> bool:
        """Validate metadata structure."""
        expected_keys = [
            'municipality', 'year', 'minute_number', 'date',
            'location', 'meeting_type', 'begin_time', 'end_time', 'participants'
        ]
        
        for key in expected_keys:
            if key not in metadata:
                if self.strict:
                    self.errors.append(f"❌ {filename} [{doc_id}]: Missing metadata key '{key}'")
                else:
                    self.warnings.append(f"⚠️ {filename} [{doc_id}]: Missing optional metadata key '{key}'")
        
        # Validate participants
        if 'participants' in metadata and metadata['participants'] is not None:
            if not isinstance(metadata['participants'], list):
                self.errors.append(f"❌ {filename} [{doc_id}]: metadata.participants must be a list")
            else:
                self.stats['total_participants'] += len(metadata['participants'])
        
        return True
    
    def validate_agenda_item(self, agenda_item: Dict, doc_id: str, item_num: int, 
                            filename: str, all_subject_starts: List[int]) -> bool:
        """Validate a single agenda_item structure."""
        # Check required keys
        required_keys = ['item_id', 'item_title', 'subjects']
        
        for key in required_keys:
            if key not in agenda_item:
                self.errors.append(
                    f"❌ {filename} [{doc_id}] Agenda Item #{item_num}: Missing required key '{key}'"
                )
                return False
        
        # Validate item_id is sequential
        if agenda_item['item_id'] != item_num:
            self.errors.append(
                f"❌ {filename} [{doc_id}] Agenda Item #{item_num}: "
                f"item_id should be {item_num}, got {agenda_item['item_id']}"
            )
        
        # Validate item_title is a string
        if not isinstance(agenda_item['item_title'], str):
            self.errors.append(
                f"❌ {filename} [{doc_id}] Agenda Item #{item_num}: 'item_title' must be a string"
            )
        
        # Validate subjects array
        if not isinstance(agenda_item['subjects'], list):
            self.errors.append(
                f"❌ {filename} [{doc_id}] Agenda Item #{item_num}: 'subjects' must be a list"
            )
            return False
        
        # Validate each subject
        for s_idx, subject in enumerate(agenda_item['subjects']):
            if not self.validate_subject(subject, doc_id, item_num, s_idx + 1, filename):
                return False
            
            # Track subject start positions for ordering verification
            if 'start' in subject and isinstance(subject['start'], int):
                all_subject_starts.append(subject['start'])
        
        self.stats['total_subjects'] += len(agenda_item['subjects'])
        
        return True
    
    def validate_subject(self, subject: Dict, doc_id: str, agenda_num: int, 
                        subject_num: int, filename: str) -> bool:
        """Validate a single subject structure."""
        # Check that 'agenda_item' field is NOT present
        if 'agenda_item' in subject:
            self.errors.append(
                f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num}: "
                f"Subject should NOT contain 'agenda_item' field (redundant with parent structure)"
            )
            self.stats['subjects_with_agenda_item_field'] += 1
        
        # Check required keys
        required_keys = ['subject_id', 'text', 'start', 'end', 'voting']
        
        for key in required_keys:
            if key not in subject:
                self.errors.append(
                    f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num}: "
                    f"Missing required key '{key}'"
                )
                return False
        
        # Validate types
        if not isinstance(subject['text'], str):
            self.errors.append(
                f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num}: "
                f"'text' must be a string"
            )
        
        if not isinstance(subject['start'], int) or not isinstance(subject['end'], int):
            self.errors.append(
                f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num}: "
                f"'start' and 'end' must be integers"
            )
        
        # Validate subject if present
        if 'subject' in subject and subject['subject'] is not None:
            if not isinstance(subject['subject'], dict):
                self.errors.append(
                    f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num}: "
                    f"'subject' must be an object"
                )
            elif not all(k in subject['subject'] for k in ['text', 'start', 'end']):
                self.warnings.append(
                    f"⚠️ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num}: "
                    f"'subject' missing text/start/end"
                )
            else:
                self.stats['subjects_with_discussion'] += 1
        
        # Validate voting array
        if not isinstance(subject['voting'], list):
            self.errors.append(
                f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num}: "
                f"'voting' must be an array"
            )
        else:
            if len(subject['voting']) > 0:
                self.stats['subjects_with_voting'] += 1
                for v_idx, voting in enumerate(subject['voting']):
                    if not self.validate_voting_object(voting, doc_id, agenda_num, subject_num, 
                                                       v_idx + 1, filename):
                        return False
        
        # Validate optional sub_subjects
        if 'sub_subjects' in subject:
            if not isinstance(subject['sub_subjects'], list):
                self.errors.append(
                    f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num}: "
                    f"'sub_subjects' must be a list"
                )
            else:
                self.stats['total_sub_subjects'] += len(subject['sub_subjects'])
                for ss_idx, sub_subj in enumerate(subject['sub_subjects']):
                    self.validate_sub_subject(
                        sub_subj, doc_id, agenda_num, subject_num, ss_idx + 1, filename
                    )

        # Track blank votes in any voting entry
        for v in subject.get('voting', []):
            if v.get('voters', {}).get('blank'):
                self.stats['subjects_with_blank_votes'] += 1
                break
        
        # Validate theme and topics if present
        if 'theme' in subject and not isinstance(subject['theme'], str):
            self.warnings.append(
                f"⚠️ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num}: "
                f"'theme' should be a string"
            )
        
        if 'topics' in subject:
            if not isinstance(subject['topics'], list):
                self.errors.append(
                    f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num}: "
                    f"'topics' must be a list"
                )
        
        return True
    
    def validate_voting_object(self, voting: Dict, doc_id: str, agenda_num: int, 
                               subject_num: int, voting_num: int, filename: str) -> bool:
        """Validate a voting object structure."""
        required_keys = ['voters', 'non_voters', 'global_tally', 'voting_evidence']
        
        for key in required_keys:
            if key not in voting:
                self.errors.append(
                    f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num} "
                    f"Voting #{voting_num}: Missing required key '{key}'"
                )
                return False
        
        # Validate voters structure (blank is optional but must be a list if present)
        if not isinstance(voting['voters'], dict):
            self.errors.append(
                f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num} "
                f"Voting #{voting_num}: 'voters' must be a dict"
            )
        else:
            for voter_type in ['in_favor', 'against', 'abstention']:
                if voter_type not in voting['voters']:
                    self.errors.append(
                        f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num} "
                        f"Voting #{voting_num}: 'voters.{voter_type}' missing"
                    )
            # blank is optional but must be a list if present
            if 'blank' in voting['voters'] and not isinstance(voting['voters']['blank'], list):
                self.errors.append(
                    f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num} "
                    f"Voting #{voting_num}: 'voters.blank' must be a list"
                )
        
        # Validate global_tally has type field
        if voting['global_tally'] is not None:
            if not isinstance(voting['global_tally'], dict):
                self.errors.append(
                    f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num} "
                    f"Voting #{voting_num}: 'global_tally' must be an object"
                )
            elif 'type' not in voting['global_tally']:
                self.warnings.append(
                    f"⚠️ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num} "
                    f"Voting #{voting_num}: 'global_tally' missing 'type' field"
                )
            elif voting['global_tally']['type'] not in ['unanimous', 'majority', None]:
                self.warnings.append(
                    f"⚠️ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num} "
                    f"Voting #{voting_num}: 'global_tally.type' should be 'unanimous', 'majority', or null"
                )
        
        return True
    
    def validate_sub_subject(self, sub_subj: Dict, doc_id: str, agenda_num: int,
                             subject_num: int, ss_num: int, filename: str) -> bool:
        """Validate a sub-subject entry."""
        loc = (f"❌ {filename} [{doc_id}] Agenda #{agenda_num} Subject #{subject_num} "
               f"SubSubject #{ss_num}")

        for key in ['text', 'start', 'end']:
            if key not in sub_subj:
                self.errors.append(f"{loc}: Missing required key '{key}'")
                return False

        if not isinstance(sub_subj['start'], int) or not isinstance(sub_subj['end'], int):
            self.errors.append(f"{loc}: 'start' and 'end' must be integers")

        if not isinstance(sub_subj['text'], str):
            self.errors.append(f"{loc}: 'text' must be a string")

        if 'theme' in sub_subj and not isinstance(sub_subj['theme'], str):
            self.warnings.append(f"⚠️ {filename} [{doc_id}] Agenda #{agenda_num} Subject "
                                 f"#{subject_num} SubSubject #{ss_num}: 'theme' should be a string")

        if 'vote_type' in sub_subj:
            vt = sub_subj['vote_type']
            if not isinstance(vt, dict) or not all(k in vt for k in ['text', 'start', 'end']):
                self.errors.append(f"{loc}: 'vote_type' must be an object with text/start/end")

        if 'voting' in sub_subj:
            if not isinstance(sub_subj['voting'], list):
                self.errors.append(f"{loc}: 'voting' must be a list")
            else:
                for v_idx, sv in enumerate(sub_subj['voting']):
                    self.validate_voting_object(
                        sv, doc_id, agenda_num, subject_num, v_idx + 1, filename
                    )

        return True

    def print_report(self):
        """Print validation report."""
        print("\n" + "=" * 80)
        print("📊 AGENDA-CENTRIC FORMAT VALIDATION REPORT")
        print("=" * 80)
        
        print(f"\n📈 Statistics:")
        print(f"   Total minutes validated: {self.stats['total_minutes']}")
        print(f"   Total agenda items: {self.stats['total_agenda_items']}")
        print(f"   Total subjects: {self.stats['total_subjects']}")
        print(f"   Subjects with voting: {self.stats['subjects_with_voting']}")
        print(f"   Subjects with subject: {self.stats['subjects_with_discussion']}")
        print(f"   Total participants in metadata: {self.stats['total_participants']}")
        print(f"   Total sub-subjects: {self.stats['total_sub_subjects']}")
        print(f"   Subjects with blank votes: {self.stats['subjects_with_blank_votes']}")
        print(f"   ❗ Subjects with agenda_item field (should be 0): {self.stats['subjects_with_agenda_item_field']}")
        
        if self.errors:
            print(f"\n❌ ERRORS FOUND: {len(self.errors)}")
            for error in self.errors[:20]:  # Show first 20 errors
                print(f"   {error}")
            if len(self.errors) > 20:
                print(f"   ... and {len(self.errors) - 20} more errors")
        else:
            print(f"\n✅ NO ERRORS FOUND")
        
        if self.warnings:
            print(f"\n⚠️ WARNINGS: {len(self.warnings)}")
            for warning in self.warnings[:20]:  # Show first 20 warnings
                print(f"   {warning}")
            if len(self.warnings) > 20:
                print(f"   ... and {len(self.warnings) - 20} more warnings")
        
        print("\n" + "=" * 80)
        
        if self.errors:
            print("❌ VALIDATION FAILED")
            return False
        else:
            print("✅ VALIDATION PASSED")
            return True

def main():
    parser = argparse.ArgumentParser(
        description="Validate CitiLink Agenda-Centric JSON output (Step 4)"
    )
    parser.add_argument(
        "--input_path",
        type=str,
        default="outputs/06_agenda_reorganization",
        help="Path to JSON file or directory containing JSON files"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enable strict mode (treat warnings as errors)"
    )
    
    args = parser.parse_args()
    
    input_path = Path(args.input_path)
    
    if not input_path.exists():
        logger.error(f"❌ Input path does not exist: {input_path}")
        sys.exit(1)
    
    # Find JSON files
    if input_path.is_file():
        json_files = [input_path]
    else:
        json_files = list(input_path.glob("*.json"))
    
    if not json_files:
        logger.error(f"❌ No JSON files found in {input_path}")
        sys.exit(1)
    
    logger.info(f"Found {len(json_files)} JSON file(s) to validate")
    
    # Create validator
    validator = AgendasValidator(strict=args.strict)
    
    # Validate all files
    all_valid = True
    for json_file in json_files:
        if not validator.validate_file(json_file):
            all_valid = False
    
    # Print report
    success = validator.print_report()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
