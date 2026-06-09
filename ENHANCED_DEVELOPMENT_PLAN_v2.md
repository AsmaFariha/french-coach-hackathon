# French Coach — Enhanced Development Plan v2

## Current State Assessment

**What works:**
- Basic notebook with gender coloring
- Lesson import to database (15+ classes saved)
- Word cards (spaCy annotation)
- Chat coach (placeholder, needs LLM)
- Exercise skeleton (no real generation)
- Summary tab (placeholder)

**What needs work:**
- Smart lesson browser (by date, topic, auto-categorized)
- Rich text editing (bold, italic, formatting, images, translations inline)
- Grammar tools (gender checker, translator as tabs)
- Exercise generation (5-10 varied types per lesson)
- Visual exercises (contextual scenarios + smart image caching)
- Pronunciation (browser Web Speech API, not working)
- Summary dashboard (real progress tracking, learning metrics)

---

## Phase 1: Smart Lesson Browser & UI Overhaul (Days 1-2)

### 1.1 Lesson Browser Sidebar (Expandable, left of Notebook)

Goal: Users can browse all saved lessons by date and auto-detected topics.

Features:
- Left sidebar with collapsible "By Date" and "By Topic" sections
- Search/filter box
- Click to load any lesson

Implementation:
- Extract topics using spaCy NER + keyword extraction
- Auto-categorize lessons
- Store category in pages.metadata JSONB field

Expected outcome: User can browse 15+ lessons in <1 second.

---

### 1.2 Lessons Browser Tab (Full-page view)

Goal: A separate tab showing all lessons in a card grid with summaries.

Features:
- Grid of lesson cards with title, date, category, word count
- AI-generated one-line summary (LLM-cached)
- Click card to open in Notebook tab
- Filter by category / date range

Expected outcome: Beautiful, browsable overview of all lessons.

---

## Phase 2: Rich Text Editing in Notebook (Days 3-4)

### 2.1 Markdown Editor with Formatting Toolbar

Goal: Replace plain textarea with a real editor supporting bold, italic, headers, images.

Features:
- Toolbar buttons: Bold, Italic, Headers, Lists, Code blocks
- Markdown preview (side-by-side)
- Image upload (drag-drop or paste)
- Copy/paste with formatting from Word/Notion

Implementation:
- Use EasyMDE markdown editor embedded in Gradio via gr.HTML + JavaScript
- Store raw markdown in pages.raw_text
- Render with marked.js for preview

Expected outcome: Notebook feels like Notion.

---

### 2.2 Inline Tools (Select word → Translate, Gender Check, Pronounce)

Goal: Right-click or select-and-click to translate, check gender, or hear pronunciation.

Features:
- Select text → Floating toolbar with 3 buttons: Translate, Gender, Pronounce
- Translate: English → French (LLM)
- Gender: Shows masc/fem for nouns (spaCy + cache)
- Pronounce: TTS plays selected text (browser speechSynthesis)

Expected outcome: Select word → instant gender/translate/pronounce.

---

## Phase 3: Grammar & Translation Tools (Days 5-6)

### 3.1 Dedicated Gender Checker Tab

Goal: Quick reference tool for noun gender.

Features:
- Input: Type French nouns
- Output: Gender (masc/fem), articles (le/la, un/une), example sentence
- Show morphological patterns (e.g., -tion = fem)

Implementation:
- Two-column layout
- Use spaCy + gender lexicon (cached)

Expected outcome: Fast gender lookups, users build intuition.

---

### 3.2 Dedicated Translator Tab

Goal: Quick English ↔ French translation with context.

Features:
- Input: English or French phrase
- Output: Translation, alternatives, example sentence, grammar notes
- Optional context (e.g., "in a café")

Implementation:
- LLM-powered
- Cache results by input + context

Expected outcome: No need to switch to Google Translate.

---

## Phase 4: Advanced Text Exercises (Days 7-8)

### 4.1 Text Exercise Generation (5-10 per lesson)

Goal: Each lesson auto-generates multiple exercise types.

Features:
- 10 exercise types: fill-in-blank, multiple choice, error detection, translation, grammar rule, reordering, cloze, listening (TTS), selection, matching
- Generate 5-10 exercises per lesson (mixed types)
- Difficulty: Mix A1/A2

Implementation:
- exercises.py: 10 generator functions (one per type)
- LLM for context, alternatives, error types
- Save to DB: type, content (JSON), model_answer, hint

UI:
- Tabbed interface under Exercises
- One exercise at a time, "Next exercise" button
- Immediate feedback, link to grammar explanation

Expected outcome: User finishes lesson → gets 5-10 randomized exercises instantly.

---

## Phase 5: Visual Exercises with Smart Image Caching (Days 9-11)

### 5.1 Image Generation Pipeline (Day 9)

Goal: Pre-generate and cache 50+ images for A1/A2 topics.

Features:
- At app startup: Generate images for core topics (café, market, family, classroom, etc.)
- Model: Stable Diffusion 1.5 (via diffusers library) or Replicate API (free tier)
- Output: Save PNG files to /french-coach/generated_images/[topic]_variant_[1-5].png
- Database tracking: generated_images table

Implementation:
- New file: image_generator.py
  - define prompts for 15+ topics
  - generate 3-5 images per topic
  - save PNG files
  - return file paths

- New DB table: generated_images
  - id, topic, description, file_path, model_used, created_at

- On app startup: auto_generate_initial_images() runs once

Expected outcome: 50 high-quality cached images ready instantly.

---

### 5.2 Smart Image Selection Agent (Day 10)

Goal: Match lesson topics to appropriate images; avoid repeats.

Features:
- Input: Lesson ID, user ID, lesson content
- Process:
  1. Extract topics (spaCy NER + keywords)
  2. Find cached images matching those topics
  3. Check user_image_usage table (filter already-seen)
  4. Pick fresh image (round-robin)
  5. Track usage in DB
  6. Return image path

Implementation:
- New file: image_agent.py
  - select_image_for_lesson(lesson_id, user_id, lesson_content)

- New DB table: user_image_usage
  - id, user_id, image_id, used_in_lesson_id, used_at

- Update visual exercise generator: Call select_image_for_lesson()

Expected outcome: Users see relevant images, no repeats.

---

### 5.3 Auto-Generation Agent (Day 11)

Goal: Continuously detect new topics and generate images.

Features:
- Trigger: On app startup, or every 1 hour
- Process:
  1. Scan all lesson content
  2. Extract unique topics
  3. Compare against existing generated_images
  4. Identify NEW topics
  5. Generate 3-5 images for each
  6. Save to disk + DB

Implementation:
- New file: auto_image_generator.py
  - detect_new_topics()
  - auto_generate_missing_images()

- Wire into app startup (background thread or APScheduler)

Expected outcome: As users add lessons, images auto-generate for novel topics.

---

## Phase 6: Pronunciation & Audio (Days 12-13)

### 6.1 Fix Web Speech API Pronunciation

Goal: Microphone input + speech recognition works reliably.

Features:
- Listen mode: LLM reads French sentence aloud (TTS)
- User speaks: Browser Web Speech API listens + transcribes
- Feedback: Compare transcription to target, give correction
- Tone: Always encouraging

Implementation:
- Use browser SpeechRecognition API (native, no model)
- On button: TTS plays target → SR listens → transcript sent to Python → LLM evaluates
- Fallback: If SR fails, show "Click to hear" (TTS only) + "Type your answer"

Expected outcome: Users can practice pronunciation; app is forgiving.

---

## Phase 7: Smart Summary Dashboard (Days 13-14)

### 7.1 Enhanced Summary Tab

Goal: Daily snapshot of learning, motivation, progress.

Features:
- Today's progress: lessons reviewed, exercises done, points earned
- Strengths: detected concepts (auto-extracted from exercises)
- Next focus: recommended concept from syllabus
- Streak: days learning straight (no guilt if broken)
- Charts: daily bar, weekly progress, vocabulary growth
- Timeline: lessons covered (scrollable)

Implementation:
- Query DB for daily stats
- LLM generates encouraging summary text
- Chart library (Plotly/Recharts) for visualizations
- Show "Next to learn: [concept not yet covered]"

Expected outcome: Users see tangible progress. Motivation stays high.

---

## Phase 8: Polish & Deploy (Day 15)

### 8.1 Custom UI & Final Testing

Goal: Production-ready, polished app.

Features:
- Custom French-themed colors (blue, gold, wine red)
- Clean typography
- Responsive layout
- End-to-end testing

### 8.2 Deploy to HF Space on ZeroGPU

Goal: Public submission.

Implementation:
- Create Space: https://huggingface.co/spaces/build-small-hackathon/french-coach
- Push code (with ZeroGPU decorator for image generation)
- Pre-warm Space
- Record 2-minute demo video
- Write social post + Field Notes blog draft

---

## Complete Implementation Roadmap

Day 1: Lesson Browser Infrastructure
- Add metadata JSONB to pages
- Create get_lesson_categories()
- Update sidebar with collapsible sections
- Commit: "Day 1: Smart lesson browser by date and topic"

Day 2: Lessons Tab
- Create LessonsBrowser tab with card grid
- Implement get_lesson_summary() (LLM-cached)
- Add filters
- Commit: "Day 2: Full-page lessons browser with summaries"

Days 3-4: Rich Text Editor
- Integrate EasyMDE
- Image upload
- Toolbar buttons
- Commit: "Days 3-4: Rich text editor with formatting and images"

Day 5: Inline Tools
- Selection listener JavaScript
- Floating toolbar
- Backend functions
- Commit: "Day 5: Inline tools for text selection"

Day 6: Gender & Translation Tabs
- Gender Checker tab
- Translator tab
- Commit: "Day 6: Dedicated tools"

Days 7-8: Text Exercise Generation
- 10 exercise types
- Generate 5-10 per lesson
- Commit: "Days 7-8: Multi-type exercise generation"

Day 9: Image Generation Pipeline
- image_generator.py (Stable Diffusion 1.5)
- generated_images table
- Generate 50 initial images
- Commit: "Day 9: Image generation pipeline + 50 cached images"

Day 10: Smart Image Selection Agent
- image_agent.py
- user_image_usage table
- Wire into exercises
- Commit: "Day 10: Smart image selection agent"

Day 11: Auto-Generation Agent
- auto_image_generator.py
- Detect new topics, generate images on demand
- Wire into app startup
- Commit: "Day 11: Auto-generation agent for new topics"

Days 12-13: Pronunciation Fix
- Web Speech API debug
- TTS + SR loop
- LLM evaluation
- Commit: "Days 12-13: Working pronunciation"

Days 13-14: Summary Dashboard
- Daily stats query
- LLM summary text
- Charts
- Commit: "Days 13-14: Smart summary dashboard"

Day 15: Polish & Deploy
- Custom French UI
- End-to-end testing
- Deploy to HF Space
- Record demo
- Commit: "Day 15: Final polish, deploy, submission-ready"

---

## How Claude Code Should Follow This Plan

Open Terminal:
```bash
cd ~/code/french-coach
claude
```

Paste this prompt:

```
Read CLAUDE.md and ENHANCED_DEVELOPMENT_PLAN_v2.md fully.

We are on Day [NUMBER] of the French Coach sprint.

Implement Day [NUMBER]: [FEATURE NAME]

Your tasks:
1. [List specific tasks from the plan]
2. Keep app running
3. Test before committing
4. Commit with clear message

Explain what you're doing as you go.
```

---

## Example: Day 9 Prompt

```
Read CLAUDE.md and ENHANCED_DEVELOPMENT_PLAN_v2.md fully.

We are on Day 9 of the French Coach sprint.

Implement Day 9: Image Generation Pipeline

Your tasks:
1. Create image_generator.py with generate_images_for_topic(topic, num_variants=3)
   - Use Stable Diffusion 1.5 via diffusers library (or Replicate API if simpler)
   - Define prompts for 15 topics: cafe, market, family, classroom, pharmacy, beach, restaurant, park, bookstore, train_station, bus_station, museum, bank, post_office, school
   - Generate 3-5 images per topic
   - Save PNG files to /generated_images/[topic]_variant_[1-5].png

2. Create generated_images table in db/init.sql:
   - id (UUID), topic (TEXT), description (TEXT), file_path (TEXT), model_used (TEXT), created_at (TIMESTAMPTZ)

3. Create auto_populate_images() in app.py that:
   - Runs once on startup
   - Calls generate_images_for_topic() for all 15 topics
   - Stores paths + metadata in DB

4. Test:
   - docker compose up -d
   - Wait for images to generate (~5-10 min)
   - Verify /generated_images/ has 50+ PNG files
   - Query: SELECT COUNT(*) FROM generated_images; returns ~50

5. Commit:
   git add -A
   git commit -m "Day 9: Image generation pipeline + 50 cached images"
   git push

If Stable Diffusion is too heavy, use Replicate API (free tier, no setup needed).
```

---

## Critical Notes

1. Keep the app running after each day
2. Test the feature before committing
3. Days 9-11 are interconnected (image generation chain)
4. Use HF Inference API for all LLM calls
5. Cache aggressively
6. Commit daily

---

## Timeline: 15 Days to Submission

Days 1-8: Core UI (50% effort)
Days 9-11: Visual exercises + image pipeline (30% effort, biggest impact)
Days 12-14: Pronunciation + summary (15% effort)
Day 15: Polish + deploy (5% effort)

Total: 15 focused days → production-ready app ready for June 15 deadline.
