---
title: French Coach
emoji: 🗼
colorFrom: indigo
colorTo: yellow
sdk: gradio
sdk_version: "6.17.3"
app_file: app_custom.py
pinned: true
license: apache-2.0
tags:
  - build-small-hackathon
  - backyard-ai
  - best-minicpm-build
  - off-brand
  - best-agent
  - best-demo
  - bonus-quest-champion
---

# 🇫🇷 French Coach

**A living French notebook that turns your class notes into practice — built for a real person studying for Canada's TEF/TCF exams.**

French Coach is a Backyard-AI study tutor for an adult learning French on a four-month
timeline for Canadian immigration (target CLB/NCLC 7). It collapses the usual mess of
class notes plus three browser tabs (translate / pronounce / gender-check) into one
surface — and adds practice the learner can't get between classes.

It runs on **self-hosted MiniCPM models** — nothing leaves the Space.

## What it does

- **Smart notebook.** Write or paste class notes. Nouns are colored by gender at a
  glance; click any word for its meaning, gender, and a one-line grammar note, with
  pronunciation on tap. Saved pages are auto-titled and categorized by a curator pass.
- **The Coach Agent.** The core feature. From the current lesson it produces a set of
  5–7 mixed exercises (fill-in-the-blank, multiple choice, error detection, reorder,
  translation) through a **plan → generate → critique → revise** loop — a small
  multi-step agent that grounds each set in the lesson *and* the official A1–A2 CEFR
  syllabus, then reviews its own output for a single unambiguous answer before showing
  it. It's not a one-shot prompt; it checks and fixes its own work.
- **Visual exercises.** MiniCPM-V reads an image and the app generates French
  comprehension questions grounded in what's actually in it.
- **Chat coach, dialogue, and pronunciation practice**, all grounded in the lesson.
- **Encouraging by design.** Points are additive only — never deducted, never tied to
  correctness. The daily summary leads with gains and frames gaps as "ready to practice
  next." No streaks to lose, no red error states, no shaming. Ever.

## How it's built

- **Models (all under the 32B cap, self-hosted on ZeroGPU):**
  - **MiniCPM4.1-8B-Instruct** — text reasoning: the Coach Agent, chat, word cards,
    grammar tools, summaries.
  - **MiniCPM-V 4.6** (~1.3B) — vision: reads images for the visual exercises.
  - <!-- BREAK-GLASS: if text runs via API instead of self-hosting, change the line
       above to: "text runs on Qwen2.5-7B-Instruct via the HF Inference API; vision
       runs on MiniCPM-V 4.6." Keep it accurate to what actually shipped. -->
- **Custom UI** built with **gr.Server** + a React frontend served through the Gradio
  app — past the default Gradio look (Off-Brand).
- **Gradio SDK Space** under the `build-small-hackathon` org.
- **Supabase** (hosted Postgres) for persistence: notebook pages, exercises, and an
  append-only points ledger.
- Deterministic French NLP (gender / part-of-speech / lemma) via spaCy runs instantly,
  offline; only meaning, grammar, exercises, and dialogue hit the LLM.

## Why it's more than a chatbot wrapper

The gender-mapped notebook, the image-grounded visual exercises, and above all the
**Coach Agent's self-critique loop** make this a tool that reasons in multiple steps,
not a single LLM call behind a text box.

## Links

- 🎬 Demo video: https://www.loom.com/share/7b96f5523d104e99a1834509c5d57e1f
- 📣 Social post: https://www.linkedin.com/posts/asma-fariha_buildsmall-smallllms-minicpm-share-7472418971804381184-Or_C/
- Built on MiniCPM (OpenBMB). Made for one real learner — and dogfooded daily.
