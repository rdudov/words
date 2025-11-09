# Task 3.7: Auto Word Selection Service

**Status:** 🔴 PENDING
**Phase:** 3 - Word Management
**Priority:** P0 (Critical)
**Complexity:** 🟡 Medium
**Estimated Time:** 3-4 hours

## Related Use Cases

- **UC1:** Регистрация и выбор языка обучения (шаг 6: "Бот формирует начальный список слов")
- **UC3:** Автоматическое формирование списка слов

## Related Non-Functional Requirements

- **Performance:** Автоподбор слов должен завершаться за < 5 секунд
- **Data Model:** Использовать таблицы words и user_words

## Description

### What

Сервис для автоматического подбора и добавления слов в персональный словарь пользователя при регистрации на основе уровня CEFR.

### Why

**Проблема:** Сейчас после регистрации (Task 2.6: Registration Handler) пользователь получает пустой словарь и не может начать обучение.

**Решение:** Автоматически добавить начальный набор слов (50-100) соответствующих уровню пользователя, чтобы он мог сразу начать урок.

**Business Value:**
- Улучшенный onboarding новых пользователей
- Мгновенный старт обучения без ручного добавления слов
- Соответствие требованиям UC1 и UC3

### How

1. Создать `AutoWordSelectionService` в `src/words/services/`
2. Реализовать метод `populate_initial_words(profile_id, level, count=50)`
3. Загрузить частотный список для указанного CEFR уровня
4. Выбрать N самых частотных слов
5. Для каждого слова:
   - Получить перевод через Translation Service (с кешированием)
   - Добавить в базу через Word Service
   - Установить статус "new"
6. Вызвать из Registration Handler после создания профиля

## Files

### To Create

- `src/words/services/auto_word_selection.py` - AutoWordSelectionService класс

### To Modify

- `src/words/bot/handlers/registration.py` - вызов автоподбора после создания профиля
- `tests/services/test_auto_word_selection.py` - unit тесты

## Implementation Details

### auto_word_selection.py

```python
"""
Auto Word Selection Service

Automatically selects and adds words to user's vocabulary based on CEFR level.
Implements UC3 - Автоматическое формирование списка слов.
"""

import logging
from typing import List
from pathlib import Path

from src.words.services.word import WordService
from src.words.services.translation import TranslationService
from src.words.config import settings, CEFR_LEVELS

logger = logging.getLogger(__name__)


class AutoWordSelectionService:
    """
    Service for automatically populating user vocabulary.

    Used during registration (UC1 step 6) to provide initial word set.
    """

    def __init__(
        self,
        word_service: WordService,
        translation_service: TranslationService
    ):
        self.word_service = word_service
        self.translation_service = translation_service
        self.frequency_lists_dir = Path("data/frequency_lists")

    async def populate_initial_words(
        self,
        profile_id: int,
        target_language: str,
        native_language: str,
        level: str,
        count: int = 50
    ) -> dict:
        """
        Automatically add initial words to user's vocabulary.

        Implements UC3 - Автоматическое формирование списка слов.

        Args:
            profile_id: Language profile ID
            target_language: Target language code (e.g., 'en')
            native_language: Native language code (e.g., 'ru')
            level: CEFR level (A1, A2, B1, B2, C1, C2)
            count: Number of words to add (default: 50)

        Returns:
            Dict with statistics:
            {
                'added': int,      # Successfully added words
                'skipped': int,    # Already exist in vocabulary
                'errors': int      # Failed to add
            }

        Raises:
            ValueError: If level is invalid or frequency list not found
        """

        logger.info(
            f"Auto-populating words for profile {profile_id}: "
            f"{target_language} level {level}, count={count}"
        )

        # Validate level
        if level not in CEFR_LEVELS:
            raise ValueError(f"Invalid CEFR level: {level}")

        # Load frequency list
        words = self._load_frequency_list(target_language, level, count)

        if not words:
            raise ValueError(
                f"Frequency list not found: {target_language}/{level}"
            )

        # Add words to vocabulary
        stats = {"added": 0, "skipped": 0, "errors": 0}

        for word_text in words:
            try:
                # Check if word already exists in user's vocabulary
                existing = await self.word_service.get_user_word(
                    profile_id, word_text
                )

                if existing:
                    logger.debug(f"Word '{word_text}' already in vocabulary")
                    stats["skipped"] += 1
                    continue

                # Get translation (from cache or LLM)
                translation_data = await self.translation_service.get_translation(
                    word=word_text,
                    source_language=target_language,
                    target_language=native_language
                )

                # Add word to vocabulary
                await self.word_service.add_word_to_user(
                    profile_id=profile_id,
                    word=word_text,
                    language=target_language,
                    translation_data=translation_data,
                    status="new"  # UC3 step 4: mark as "new"
                )

                stats["added"] += 1
                logger.debug(f"Added word '{word_text}' to vocabulary")

            except Exception as e:
                logger.error(
                    f"Failed to add word '{word_text}': {e}",
                    exc_info=True
                )
                stats["errors"] += 1

        logger.info(
            f"Auto-population complete for profile {profile_id}: "
            f"{stats}"
        )

        return stats

    def _load_frequency_list(
        self,
        language: str,
        level: str,
        count: int
    ) -> List[str]:
        """
        Load frequency list for given language and level.

        File structure: data/frequency_lists/{language}/{level}.txt
        Each line contains one word.

        Args:
            language: Language code (e.g., 'en')
            level: CEFR level (e.g., 'A1')
            count: Number of words to load

        Returns:
            List of words (up to count)
        """

        file_path = self.frequency_lists_dir / language / f"{level}.txt"

        if not file_path.exists():
            logger.error(f"Frequency list not found: {file_path}")
            return []

        words = []

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    word = line.strip()
                    if word:
                        words.append(word)

                    if len(words) >= count:
                        break

            logger.info(
                f"Loaded {len(words)} words from {file_path}"
            )
            return words

        except Exception as e:
            logger.error(
                f"Failed to load frequency list {file_path}: {e}",
                exc_info=True
            )
            return []
```

### Integration into Registration Handler

```python
# src/words/bot/handlers/registration.py

async def _complete_registration(
    message: Message,
    state: FSMContext,
    user_service: UserService,
    auto_word_service: AutoWordSelectionService  # ADD
):
    """Complete registration and create user profile"""

    # ... existing code to create user and profile ...

    # UC1 Step 6: Automatically populate initial words (UC3)
    try:
        stats = await auto_word_service.populate_initial_words(
            profile_id=profile.profile_id,
            target_language=profile.target_language,
            native_language=user.native_language,
            level=profile.level,
            count=50  # Initial word count
        )

        await message.answer(
            f"✅ Регистрация завершена!\n\n"
            f"Добавлено {stats['added']} слов для изучения.\n"
            f"Вы можете начать урок командой /lesson"
        )

    except Exception as e:
        logger.error(f"Failed to auto-populate words: {e}", exc_info=True)
        await message.answer(
            "✅ Регистрация завершена!\n\n"
            "Добавьте слова для изучения командой /add"
        )
```

## Integration Points

- **Word Service (Task 3.5):** Использует методы добавления слов
- **Translation Service (Task 3.3):** Получает переводы через кеш/LLM
- **Registration Handler (Task 2.6):** Вызывается после создания профиля
- **Frequency Lists (Task 7.3):** Читает частотные списки из data/

## Error Handling

### Exceptions to Handle

1. **FileNotFoundError:** Частотный список не найден
   - Логировать ошибку
   - Вернуть пустой результат или использовать fallback уровень

2. **LLM API Errors:** Не удалось получить перевод
   - Пропустить слово
   - Продолжить с остальными
   - Не прерывать весь процесс

3. **Database Errors:** Не удалось добавить слово
   - Логировать ошибку
   - Увеличить счетчик errors
   - Продолжить с остальными

### Graceful Degradation

- Если автоподбор полностью не работает, регистрация должна завершиться успешно
- Пользователь сможет добавить слова вручную через /add
- Лучше пустой словарь, чем failed registration

## Testing

### Unit Tests

```python
# tests/services/test_auto_word_selection.py

import pytest
from pathlib import Path

@pytest.fixture
def auto_word_service(word_service, translation_service):
    return AutoWordSelectionService(word_service, translation_service)

@pytest.mark.asyncio
async def test_populate_initial_words_success(
    auto_word_service,
    mock_profile
):
    """Test successful word population"""

    stats = await auto_word_service.populate_initial_words(
        profile_id=mock_profile.profile_id,
        target_language="en",
        native_language="ru",
        level="A1",
        count=10
    )

    assert stats["added"] > 0
    assert stats["errors"] == 0

@pytest.mark.asyncio
async def test_populate_invalid_level(auto_word_service):
    """Test with invalid CEFR level"""

    with pytest.raises(ValueError, match="Invalid CEFR level"):
        await auto_word_service.populate_initial_words(
            profile_id=1,
            target_language="en",
            native_language="ru",
            level="Z99",
            count=10
        )

@pytest.mark.asyncio
async def test_load_frequency_list(auto_word_service):
    """Test frequency list loading"""

    words = auto_word_service._load_frequency_list("en", "A1", 20)

    assert len(words) > 0
    assert len(words) <= 20
    assert all(isinstance(w, str) for w in words)
```

### Integration Tests

1. Создать тестовый профиль
2. Вызвать populate_initial_words
3. Проверить, что слова добавлены в user_words
4. Проверить статус "new"
5. Проверить, что можно начать урок

### Manual Testing

1. Зарегистрировать нового пользователя
2. Проверить, что автоматически добавлены слова
3. Запустить /lesson и убедиться, что слова доступны
4. Проверить логи на ошибки

## Dependencies

**Blocked By:**
- Task 3.5: Word Service (методы добавления слов)
- Task 3.3: Translation Service (получение переводов)
- Task 7.3: Load Frequency Lists (файлы частотных списков)

**Blocks:**
- Task 2.6: Registration Handler (нужно добавить вызов автоподбора)

## Acceptance Criteria

- [ ] AutoWordSelectionService создан
- [ ] Метод populate_initial_words реализован
- [ ] Интеграция с Word Service и Translation Service
- [ ] Загрузка частотных списков работает
- [ ] Обработка ошибок реализована (graceful degradation)
- [ ] Unit тесты написаны (покрытие >80%)
- [ ] Integration тесты написаны
- [ ] Вызов из Registration Handler добавлен
- [ ] При регистрации автоматически добавляются слова
- [ ] Логирование работает корректно

## Implementation Notes

### Design Decisions

1. **Separate Service:** Вынесено в отдельный сервис для переиспользования
   - Можно будет вызвать при смене уровня (UC2)
   - Можно использовать для пополнения словаря

2. **Default Count = 50:** Баланс между:
   - Достаточно слов для начала
   - Не перегружать LLM запросами при регистрации

3. **Graceful Errors:** Ошибки не должны блокировать регистрацию
   - Пользователь всегда может добавить слова вручную

### Performance Considerations

- Если count=50 и каждый перевод занимает 1-2 сек, это 50-100 сек
- **Оптимизация:** Batch запросы к LLM (если API поддерживает)
- **Альтернатива:** Запускать автоподбор асинхронно после регистрации

### Future Enhancements

- Настраиваемое количество слов через settings
- Умный выбор слов (не только топ-N, но и разнообразие)
- Прогресс-бар при добавлении слов
- Возможность пропустить автоподбор

## References

- **requirements.md:** UC1 step 6 (lines 24-25)
- **requirements.md:** UC3 (lines 37-46)
- **requirements.md:** Data Model - words, user_words tables
- **plan_review_notes.md:** Section 2 - Missing UC3

---

**Created:** 2025-11-09
**Author:** Claude (based on requirements analysis)
