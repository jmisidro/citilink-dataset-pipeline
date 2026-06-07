#!/usr/bin/env python3
"""
CitiLink Subject-Centric Data Pipeline Runner (6-Step Thesis Version)

This script orchestrates the subject-centric data processing pipeline.

Step 1: step1_interval_extraction.py - Interval Extraction (Data Cleaning)
Step 2: step2_subject_parsing.py - Subject Parsing and Hierarchy Reconstruction
Step 3: step3_anonymization.py - Anonymization and Offset Remapping
Step 4: step4_metadata_translation.py - Metadata Translation
Step 5: step5_municipality_reorganization.py - Municipality Reorganization
Step 6: step6_agenda_reorganization.py - Agenda Item Reorganization
"""

import os
import sys
import subprocess
import argparse
import logging
from pathlib import Path
from typing import List, Optional
import json
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CitiLinkPipeline:
    def __init__(self, base_dir: str, debug: bool = False, skip_anonymization: bool = False):
        self.base_dir = Path(base_dir)
        self.debug = debug
        self.skip_anonymization = skip_anonymization

        # Define directory paths
        self.scripts_dir = self.base_dir / "scripts"
        self.inputs_dir = self.base_dir / "inputs"
        self.outputs_dir = self.base_dir / "outputs"
        self.logs_dir = self.base_dir / "logs"
        
        # Define step output directories matching the thesis section
        self.step1_output = self.outputs_dir / "01_interval_extraction"
        self.step2_output = self.outputs_dir / "02_subject_parsing"
        self.step3_output = self.outputs_dir / "03_anonymization"
        self.step4_output = self.outputs_dir / "04_metadata_translation"
        self.step5_output = self.outputs_dir / "05_municipality_reorganization"
        self.step6_output = self.outputs_dir / "06_agenda_reorganization"

        # Create output directories
        for directory in [self.outputs_dir, self.logs_dir, self.step1_output, self.step2_output, self.step3_output, self.step4_output, self.step5_output, self.step6_output]:
            directory.mkdir(exist_ok=True, parents=True)

    def run_command(self, cmd: List[str], description: str, cwd: Optional[Path] = None, step_name: str = None) -> bool:
        """Run a command and return success status."""
        try:
            logger.info(f"🚀 {description}")
            logger.info(f"Command: {' '.join(cmd)}")

            if cwd:
                logger.info(f"Working directory: {cwd}")

            # Create logs directory if it doesn't exist
            self.logs_dir.mkdir(exist_ok=True, parents=True)

            # Generate log file name
            if step_name:
                log_file = self.logs_dir / f"{step_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
            else:
                safe_desc = "".join(c for c in description.lower().replace(" ", "_") if c.isalnum() or c in "_-")
                log_file = self.logs_dir / f"{safe_desc}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"Command: {' '.join(cmd)}\n")
                f.write(f"Working directory: {cwd or self.base_dir}\n")
                f.write(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n")
                f.flush()

                result = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=cwd or self.base_dir
                )

            if result.returncode == 0:
                logger.info(f"✅ {description} completed successfully")
                logger.info(f"📝 Full logs: {log_file}")
                return True
            else:
                logger.error(f"❌ {description} failed with return code {result.returncode}")
                logger.error(f"📝 Check logs: {log_file}")
                return False

        except Exception as e:
            logger.error(f"❌ {description} failed with exception: {str(e)}")
            return False
    
    def step1_extract_intervals(self) -> bool:
        """
        Step 1: Interval Extraction (Data Cleaning)
        Removes invalid excerpts or non-deliberative content marked by boundary annotations.
        """
        logger.info("=" * 80)
        logger.info("STEP 1: Interval Extraction - Data Cleaning (step1_interval_extraction.py)")
        logger.info("=" * 80)
        
        # Check if script exists
        script_path = self.scripts_dir / "step1_interval_extraction.py"
        if not script_path.exists():
            logger.error("❌ step1_interval_extraction.py not found")
            return False
        
        # Directories
        rodrigo_dir = self.inputs_dir / "annotation_rute"
        inception_dir = self.inputs_dir / "inception_final"
        
        # Check if both directories exist
        if not rodrigo_dir.exists():
            logger.warning(f"Rodrigo directory not found: {rodrigo_dir}")
            logger.info("Skipping interval extraction - will use inception files as-is")
            return True
        
        if not inception_dir.exists():
            # Fallback to inception directory if inception_final doesn't exist
            inception_dir = self.inputs_dir / "inception"
            if not inception_dir.exists():
                logger.error(f"Neither inception_final nor inception directory found in inputs")
                return False
            logger.warning(f"Using fallback inception directory: {inception_dir}")
        
        logger.info(f"Extracting boundaries from: {rodrigo_dir}")
        logger.info(f"Applying to inception files from: {inception_dir}")
        
        cmd = [
            sys.executable,
            str(script_path),
            "--rodrigo_dir", str(rodrigo_dir),
            "--inception_dir", str(inception_dir),
            "--output_dir", str(self.step1_output)
        ]
        
        if self.debug:
            cmd.append("--debug")
        
        return self.run_command(cmd, "Extracting document intervals", step_name="step1_interval_extraction")
    
    def step2_parse_subjects(self) -> bool:
        """
        Step 2: Subject Parsing and Hierarchy Reconstruction
        Core parsing script to process INCEpTION files and extract subject-centric data.
        """
        logger.info("=" * 80)
        logger.info("STEP 2: Subject Parsing and Hierarchy Reconstruction (step2_subject_parsing.py)")
        logger.info("=" * 80)
        
        # Check if Step 1 output exists (extracted files)
        if self.step1_output.exists() and list(self.step1_output.glob("*.json")):
            inception_source = self.step1_output
            logger.info(f"Using interval-extracted files from {inception_source}")
            inception_files = list(inception_source.glob("*.json"))
        else:
            # Fallback to original input sources
            logger.info("Step 1 not run or no output - checking original input files")
            inception_files = list(self.inputs_dir.glob("*.json"))
            
            # If no files directly in inputs/, try subdirs
            if not inception_files:
                for subdir_name in ["inception_final", "inception", "annotation_rute"]:
                    inception_subdir = self.inputs_dir / subdir_name
                    if inception_subdir.exists():
                        inception_files = list(inception_subdir.glob("*.json"))
                        if inception_files:
                            logger.info(f"Using INCEpTION files from {inception_subdir}")
                            break
        
        if not inception_files:
            logger.error(f"No INCEpTION JSON files found in {self.inputs_dir}")
            return False
        
        logger.info(f"Found {len(inception_files)} files to process")
        
        success_count = 0
        for inception_file in inception_files:
            cmd = [
                sys.executable,
                str(self.scripts_dir / "step2_subject_parsing.py"),
                str(inception_file),
                "--output_dir", str(self.step2_output)
            ]
            
            if self.debug:
                cmd.append("--debug")
            
            if self.run_command(cmd, f"Parsing {inception_file.name}", step_name="step2_parsing"):
                success_count += 1
        
        logger.info(f"✅ Step 2 complete: {success_count}/{len(inception_files)} files parsed successfully")
        return success_count > 0
    
    def step3_anonymize(self) -> bool:
        """
        Step 3: Anonymization and Offset Remapping
        Replaces personal information with synthetic data and dynamically recalculates indices.
        """
        logger.info("=" * 80)
        if self.skip_anonymization:
            logger.info("STEP 3: Copying files (ANONYMIZATION SKIPPED BY USER)")
        else:
            logger.info("STEP 3: Anonymization and Offset Remapping (step3_anonymization.py)")
        logger.info("=" * 80)
        
        if self.skip_anonymization:
            # Copy files from Step 2 to Step 3 output without anonymization but sort personal_info
            logger.info("Sorting and copying original files...")
            self.step3_output.mkdir(exist_ok=True, parents=True)
            
            json_files = list(self.step2_output.glob("*_subjects.json"))
            if not json_files:
                logger.error(f"No parsed subjects JSON files found in {self.step2_output}")
                return False
            
            for json_file in json_files:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Sort personal_info in each document
                for municipality, docs in data.get("minutes", {}).items():
                    for doc_id, doc_data in docs.items():
                        personal_info = doc_data.get("personal_info", [])
                        if personal_info:
                            personal_info.sort(key=lambda x: x.get('start', 0))
                            doc_data['personal_info'] = personal_info
                
                dest_file = self.step3_output / json_file.name
                with open(dest_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"Processed: {json_file.name}")
            
            logger.info(f"✅ Processed {len(json_files)} files (no anonymization applied)")
            return True
        
        # Check if anonymization script exists
        script_path = self.scripts_dir / "step3_anonymization.py"
        if not script_path.exists():
            logger.error("❌ step3_anonymization.py not found")
            return False
        
        cmd = [
            sys.executable,
            str(script_path),
            "--input_dir", str(self.step2_output),
            "--output_dir", str(self.step3_output)
        ]
        
        if self.debug:
            cmd.append("--debug")
        
        return self.run_command(cmd, "Anonymizing personal information", step_name="step3_anonymization")
    
    def step4_translate(self) -> bool:
        """
        Step 4: Metadata Translation
        Translates topics and metadata values to English.
        """
        logger.info("=" * 80)
        logger.info("STEP 4: Metadata Translation (step4_metadata_translation.py)")
        logger.info("=" * 80)
        
        script_path = self.scripts_dir / "step4_metadata_translation.py"
        if not script_path.exists():
            logger.error("❌ step4_metadata_translation.py not found")
            return False
        
        cmd = [
            sys.executable,
            str(script_path),
            "--input_dir", str(self.step3_output),
            "--output_dir", str(self.step4_output)
        ]
        
        if self.debug:
            cmd.append("--debug")
        
        return self.run_command(cmd, "Translating metadata", step_name="step4_translation")
    
    def step5_reorganize(self) -> bool:
        """
        Step 5: Municipality Reorganization
        Groups documents by municipality into individual serialized files.
        """
        logger.info("=" * 80)
        logger.info("STEP 5: Municipality Reorganization (step5_municipality_reorganization.py)")
        logger.info("=" * 80)
        
        script_path = self.scripts_dir / "step5_municipality_reorganization.py"
        if not script_path.exists():
            logger.error("❌ step5_municipality_reorganization.py not found")
            return False
        
        cmd = [
            sys.executable,
            str(script_path),
            "--input_dir", str(self.step4_output),
            "--output_dir", str(self.step5_output)
        ]
        
        if self.debug:
            cmd.append("--debug")
        
        return self.run_command(cmd, "Reorganizing by municipality", step_name="step5_reorganize")
    
    def step6_reorganize_by_agendas(self) -> bool:
        """
        Step 6: Agenda Item Reorganization
        Restructures the data into an agenda-centric hierarchy.
        """
        logger.info("=" * 80)
        logger.info("STEP 6: Agenda Item Reorganization (step6_agenda_reorganization.py)")
        logger.info("=" * 80)
        
        script_path = self.scripts_dir / "step6_agenda_reorganization.py"
        if not script_path.exists():
            logger.error("❌ step6_agenda_reorganization.py not found")
            return False
        
        cmd = [
            sys.executable,
            str(script_path),
            "--input_dir", str(self.step5_output),
            "--output_dir", str(self.step6_output)
        ]
        
        if self.debug:
            cmd.append("--debug")
        
        return self.run_command(cmd, "Reorganizing by agenda items", step_name="step6_reorganize_agendas")
    
    def run_full_pipeline(self) -> bool:
        """Run all pipeline steps in sequence."""
        logger.info("=" * 80)
        logger.info("🚀 STARTING CITILINK DATASET TRANSFORMATION PIPELINE (6-STEP VERSION)")
        logger.info("=" * 80)
        
        steps = [
            (self.step1_extract_intervals, "Step 1: Interval Extraction (Data Cleaning)"),
            (self.step2_parse_subjects, "Step 2: Subject Parsing and Hierarchy Reconstruction"),
            (self.step3_anonymize, "Step 3: Anonymization and Offset Remapping"),
            (self.step4_translate, "Step 4: Metadata Translation"),
            (self.step5_reorganize, "Step 5: Municipality Reorganization"),
            (self.step6_reorganize_by_agendas, "Step 6: Agenda Item Reorganization")
        ]
        
        for i, (step_func, step_name) in enumerate(steps, 1):
            logger.info(f"\n{'='*80}")
            logger.info(f"Starting {step_name}")
            logger.info(f"{'='*80}")
            
            if not step_func():
                logger.error(f"❌ Pipeline failed at {step_name}")
                return False
        
        logger.info("\n" + "=" * 80)
        logger.info("🎉 PIPELINE COMPLETED SUCCESSFULLY!")
        logger.info("=" * 80)
        logger.info(f"📁 Step 1 (Interval Extracted):       {self.step1_output}")
        logger.info(f"📁 Step 2 (Parsed Subjects):          {self.step2_output}")
        if self.skip_anonymization:
            logger.info(f"📁 Step 3 (Original Data Copy):       {self.step3_output}")
        else:
            logger.info(f"📁 Step 3 (Anonymized Data):          {self.step3_output}")
        logger.info(f"📁 Step 4 (Translated Data):          {self.step4_output}")
        logger.info(f"📁 Step 5 (Municipality Reorganized): {self.step5_output}")
        logger.info(f"📁 Step 6 (Agenda Reorganized):       {self.step6_output}")
        
        return True

def main():
    parser = argparse.ArgumentParser(
        description="CitiLink Subject-Centric Data Pipeline (6-Step Thesis Version)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode for more verbose output"
    )
    parser.add_argument(
        "--skip-anonymization",
        action="store_true",
        help="Skip anonymization step and preserve original text in final dataset"
    )
    parser.add_argument(
        "--step",
        type=str,
        nargs='+',
        choices=['1', '2', '3', '4', '5', '6'],
        help="Run specific step(s). If not specified, runs all steps."
    )
    
    args = parser.parse_args()
    
    # Get the current script's directory as the base directory
    base_dir = Path(__file__).parent.resolve()
    
    # Create pipeline instance
    pipeline = CitiLinkPipeline(
        base_dir=str(base_dir), 
        debug=args.debug,
        skip_anonymization=args.skip_anonymization
    )
    
    # Run pipeline
    if args.step:
        success = True
        if '1' in args.step:
            success = success and pipeline.step1_extract_intervals()
        if '2' in args.step:
            success = success and pipeline.step2_parse_subjects()
        if '3' in args.step:
            success = success and pipeline.step3_anonymize()
        if '4' in args.step:
            success = success and pipeline.step4_translate()
        if '5' in args.step:
            success = success and pipeline.step5_reorganize()
        if '6' in args.step:
            success = success and pipeline.step6_reorganize_by_agendas()
    else:
        success = pipeline.run_full_pipeline()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
