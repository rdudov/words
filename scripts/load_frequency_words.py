#!/usr/bin/env python3
"""
Script to load frequency words from text files into the database.

Usage:
    python scripts/load_frequency_words.py

This script reads frequency word lists from data/frequency_lists/ and
loads them into the words table for use as distractors in multiple choice questions.

File format: one word per line, ordered by frequency (most common first).
Example:
    data/frequency_lists/en_A1.txt
    data/frequency_lists/en_A2.txt
    data/frequency_lists/ru_A1.txt
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.words.infrastructure.database import get_session
from src.words.models.word import Word
from src.words.repositories.word import WordRepository
from src.words.utils.logger import get_event_logger

logger = get_event_logger(__name__)

FREQUENCY_LISTS_DIR = project_root / "data" / "frequency_lists"


async def load_words_from_file(
    filepath: Path,
    language: str,
    level: str,
    session: AsyncSession
) -> int:
    """
    Load words from a frequency list file.
    
    Args:
        filepath: Path to frequency list file
        language: Language code (e.g., "en", "ru")
        level: CEFR level (e.g., "A1", "A2")
        session: Database session
        
    Returns:
        Number of words loaded (excluding duplicates)
    """
    if not filepath.exists():
        logger.warning(
            "frequency_file_not_found",
            filepath=str(filepath)
        )
        return 0
    
    word_repo = WordRepository(session)
    loaded_count = 0
    skipped_count = 0
    
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = [line.strip().lower() for line in f if line.strip()]
    
    logger.info(
        "loading_frequency_words",
        filepath=filepath.name,
        total_lines=len(lines),
        language=language,
        level=level
    )
    
    for rank, word_text in enumerate(lines, start=1):
        # Skip if word is too short or too long
        if len(word_text) < 2 or len(word_text) > 50:
            continue
            
        # Check if word already exists
        existing = await word_repo.find_by_text_and_language(word_text, language)
        
        if existing:
            skipped_count += 1
            continue
        
        # Create new word
        word = Word(
            word=word_text,
            language=language,
            level=level,
            frequency_rank=rank,
            translations={}  # Will be filled later by translation service
        )
        
        session.add(word)
        loaded_count += 1
        
        # Commit in batches of 100
        if loaded_count % 100 == 0:
            await session.commit()
            logger.info(
                "batch_committed",
                loaded=loaded_count,
                skipped=skipped_count
            )
    
    # Final commit
    await session.commit()
    
    logger.info(
        "frequency_words_loaded",
        filepath=filepath.name,
        loaded=loaded_count,
        skipped=skipped_count
    )
    
    return loaded_count


async def load_all_frequency_lists():
    """Load all frequency lists from data/frequency_lists/ directory."""
    if not FREQUENCY_LISTS_DIR.exists():
        logger.error(
            "frequency_lists_dir_not_found",
            path=str(FREQUENCY_LISTS_DIR)
        )
        print(f"Error: Directory not found: {FREQUENCY_LISTS_DIR}")
        return
    
    # Pattern: {language}_{level}.txt (e.g., en_A1.txt, ru_B1.txt)
    txt_files = list(FREQUENCY_LISTS_DIR.glob("*.txt"))
    
    if not txt_files:
        logger.warning(
            "no_frequency_files_found",
            path=str(FREQUENCY_LISTS_DIR)
        )
        print(f"No .txt files found in {FREQUENCY_LISTS_DIR}")
        print("Create files like: en_A1.txt, en_A2.txt, ru_A1.txt, etc.")
        return
    
    total_loaded = 0
    
    async with get_session() as session:
        for filepath in txt_files:
            # Parse filename: en_A1.txt -> language=en, level=A1
            filename = filepath.stem  # Remove .txt
            
            if '_' not in filename:
                logger.warning(
                    "invalid_filename_format",
                    filename=filepath.name
                )
                print(f"Skipping {filepath.name} - invalid format (expected: language_level.txt)")
                continue
            
            parts = filename.split('_', 1)
            language = parts[0].lower()
            level = parts[1].upper()
            
            # Validate level
            valid_levels = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
            if level not in valid_levels:
                logger.warning(
                    "invalid_level",
                    filename=filepath.name,
                    level=level
                )
                print(f"Skipping {filepath.name} - invalid level '{level}' (expected: {', '.join(valid_levels)})")
                continue
            
            print(f"\nLoading {filepath.name} ({language}, {level})...")
            loaded = await load_words_from_file(filepath, language, level, session)
            total_loaded += loaded
            print(f"  → Loaded {loaded} words")
    
    print(f"\n✅ Total words loaded: {total_loaded}")
    logger.info("frequency_loading_complete", total_loaded=total_loaded)


async def main():
    """Main entry point."""
    print("=" * 60)
    print("Loading frequency word lists into database")
    print("=" * 60)
    
    try:
        await load_all_frequency_lists()
    except Exception as e:
        logger.exception("frequency_loading_failed")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
