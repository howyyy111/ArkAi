# ARKAIS Hackathon Tester Guide

This guide is for hackathon judges, reviewers, and testers who want to evaluate ARKAIS quickly.

It focuses on the intended demo path and the two included test files:

- [`mock_ml_notes.md`](./mock_ml_notes.md)
- [`mock_ml_exam.md`](./mock_ml_exam.md)

## Recommended Testing Time

You can test the main product loop in about 10 to 15 minutes.

If Google Workspace credentials are not configured, you can still test the core learning workflow in guest mode.

## What To Evaluate

ARKAIS is intended to show:

- an adaptive AI tutor
- learner identity and session persistence
- diagnostics and mastery tracking
- roadmap generation
- study material uploads
- grounded mock-test generation
- progress insights and reports
- optional Google Workspace saving

## Start The App

From the repository root:

```bash
python frontend_server.py
```

Open:

```text
http://127.0.0.1:4173
```

If port `4173` is already in use, set another port:

```powershell
$env:ARKAIS_FRONTEND_PORT="4174"
python frontend_server.py
```

Then open:

```text
http://127.0.0.1:4174
```

## Sign In Or Continue As Guest

When the app opens, use one of these options:

- Google Sign-In, if Firebase web auth is configured
- guest or email fallback, if testing locally

Guest mode is acceptable for hackathon judging.

## Test Flow 1: Tutor

Open the **Tutor** tab.

Try:

```text
Teach me overfitting in machine learning with one simple example.
```

Then try:

```text
Quiz me on supervised vs unsupervised learning.
```

Expected result:

- ARKAIS responds like a tutor
- the answer is short, structured, and beginner-friendly
- the chat is stored in the current session
- learner state and progress areas start to update

## Test Flow 2: Diagnostic

Open the **Plan** tab.

In the diagnostic section, use:

```text
Topic: Introduction to Machine Learning
Goal: Prepare for an exam
Study time: 1 hour
Level: Beginner
```

Click **Start diagnostic**.

Answer the diagnostic questions and submit.

Expected result:

- ARKAIS generates a short assessment
- answers are scored
- mastery information updates
- feedback appears after submission

## Test Flow 3: Roadmap

Stay in the **Plan** tab.

Use these roadmap inputs:

```text
Topic: Introduction to Machine Learning
Goal: Prepare for a university exam
Study time: 1 hour
Deadline: 14 days
Level: Beginner
Start date: choose any date
```

Click **Generate roadmap**.

Expected result:

- a phase-based study roadmap appears
- roadmap sessions are shown
- sessions can be opened and marked complete
- the Continue Learning card updates

Optional Google test:

- connect Google saves
- save roadmap tasks to Google Tasks
- save a selected session reminder to Google Calendar

## Test Flow 4: Materials Upload

Open the **Materials** tab.

Upload:

```text
mock_ml_notes.md
```

This file contains short notes about:

- supervised learning
- unsupervised learning
- reinforcement learning
- the ML pipeline
- overfitting and underfitting

Expected result:

- the file appears in the material library
- the material can be selected
- the app shows upload status and library usage

## Test Flow 5: Mock Test Generation

In the **Materials** tab, use the mock-test area.

Recommended inputs:

```text
Topic: Introduction to Machine Learning
Level: Beginner
Goal: Prepare for a university-style exam
Question count: 7
```

In the structure/settings field, paste or summarize:

```text
Use three sections:
Section A: multiple choice questions
Section B: short answer questions
Section C: one structured scenario question
```

For sample exam style, use:

```text
mock_ml_exam.md
```

Click **Create mock test**.

Expected result:

- ARKAIS creates a new mock test based on the uploaded notes
- the output follows the university exam style more closely when `mock_ml_exam.md` is provided
- a download option appears when generation succeeds

What judges should look for:

- whether the generated questions are grounded in the notes
- whether the exam structure resembles the sample exam
- whether the questions are useful for revision
- whether the UI makes this workflow easy to follow

## Test Flow 6: Insights And Report

Open the **Insights** tab.

Click **Refresh insights**.

Then click **Open report**.

Expected result:

- the app summarizes learner progress
- it shows diagnostic/roadmap/material signals
- it recommends next focus areas
- it can generate a weekly report

Optional Google test:

- connect Google saves
- save the weekly report to Google Docs

## Optional Test Flow: Google Saves

If OAuth credentials and Firestore are configured:

1. Open the account menu.
2. Click **Connect** for Google saves.
3. Complete Google OAuth.
4. Return to ARKAIS.
5. Try one of these:

```text
Save this tutor explanation to Google Docs.
```

```text
Save my roadmap sessions to Google Calendar.
```

```text
Create Google Tasks from my roadmap.
```

Expected result:

- ARKAIS uses the connected account
- successful saves return a confirmation
- Google Docs/Tasks/Calendar contain the exported item

## Suggested Judge Script

Use this short sequence if time is limited:

1. Continue as guest.
2. Ask Tutor: "Teach me overfitting in machine learning with one simple example."
3. Go to Plan and create a beginner roadmap for Introduction to Machine Learning.
4. Go to Materials and upload `mock_ml_notes.md`.
5. Use `mock_ml_exam.md` as the sample exam style.
6. Generate a mock test.
7. Go to Insights and refresh the learner snapshot.

This path exercises the strongest parts of the prototype without requiring Google OAuth.

## Known Configuration Notes

If AI generation does not work, check whether one of these is configured:

- `GEMINI_API_KEY`
- `GOOGLE_GENAI_USE_VERTEXAI=1` with `GOOGLE_CLOUD_PROJECT`

If Google Sign-In does not appear, Firebase web config may be missing. Guest mode is expected in that case.

If Google Docs, Tasks, Calendar, or Drive actions do not work, Google OAuth credentials may not be configured. This does not block the core learning demo.

## Files Used In This Guide

```text
mock_ml_notes.md
mock_ml_exam.md
```

These files are intentionally included so judges can test ARKAIS with predictable learning material.

