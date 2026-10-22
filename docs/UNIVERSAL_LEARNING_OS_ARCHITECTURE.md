# Universal Learning OS — Architecture baseline (v0.1)

## Scope and principles
Ağıllı Müəllim is NOT a Grade 5 app. It must support Grades 1–11, IELTS/CEFR, university, law and professional learning with reusable core services. Preserve existing FastAPI, React and MongoDB and all user data. No destructive ingestion, production deployment or automatic merge.

## Confirmed repository observations (architecture/universal-learning-os)
- backend/server.py currently configures Gemini via emergentintegrations; tutor prompt is age/grade-specific.
- backend/ingest_textbook.py exists on this branch; not present on main when checked.
- backend/quiz_engine.py, backend/progress_manager.py, backend/smart_notes.py and frontend QuizCard/SmartNotes components exist. Their presence does NOT prove end-to-end correctness.
- Existing textbook context is truncated in tutor prompt; importer and PDF page/figure fidelity require validation.
- Source branch: feature/merge-main; main must remain untouched.

## Proposed stable contracts
1. LearningProgram: id, type (school/CEFR/exam/professional), jurisdiction, framework_version, locale, level_scheme.
2. SourceDocument: id, edition, effective_from, revision, file_hash, source_uri, original_asset, ingestion_status.
3. ContentNode: id, source_document_id, parent_id, node_type, title, order, page_refs, bbox_refs, content_blocks, extraction_confidence, review_status.
4. LearningObjective: id, program_id, competency_id, prerequisites, mastery_criteria.
5. LessonPlan: objective_ids, ordered source_node_ids, explanation_steps, examples, practice_blueprint, citations.
6. BoardAction: version, action_type, payload, source_node_id, lesson_step_id, timing_marker; allowlisted renderers only.
7. AssessmentItem: objective_ids, difficulty, answer_key, distractor_rationale, validation_status, source_refs, version.
8. StudentEvidence: student_id, objective_id, item_id, response, rubric, outcome, misconception_tags, timestamp.
9. StudentMastery: student_id, objective_id, estimate, confidence, last_practiced, next_review_at, algorithm_version.
10. ExamBlueprint: program, objective_weights, difficulty_mix, item_count, duration, access_policy, version.

## Pipeline
Upload -> malware/file validation -> immutable original storage -> PDF layout/text/formula/figure extraction -> table of contents/section graph -> source-grounded structured nodes -> validation and human review of low-confidence nodes -> publish approved version -> retrieval by objective and source refs -> tutor lesson step -> board and voice events -> assessment evidence -> mastery and parent report.

All stages idempotent, versioned, auditable and resumable. Never infer an official curriculum mapping without source or review.

## First vertical slice
Grade 5 Mathematics, 'Natural ədədlər'. Demonstrate original PDF viewer, page-accurate citations, complete lesson content, diagnostic question, interruptible follow-up, structured whiteboard, graded practice, saved session and evidence-based mastery. Do not declare complete based on a 3-question counter.

## Cross-domain proof
Without modifying core contracts, import one history and one English lesson. Validate timelines/maps and pronunciation/grammar via plugins/renderers. Law later needs authoritative versioned source synchronization and effective-date retrieval.

## Delivery sequence
M0 read-only audit and fixture inventory; M1 schemas + non-destructive compatibility adapters + tests; M2 ingestion and page/figure fidelity; M3 tutor orchestrator and board protocol; M4 assessments/mastery; M5 real voice and subject pilots; M6 Emergent preview/deploy after acceptance.

## Engineering ownership
GitHub/Codex: design, code, tests, PRs. ChatGPT: architecture review, acceptance and risk register. Emergent: integration test, runtime secrets, preview, deployment. User approves architecture, risky migrations and deploy.

## Acceptance gates
No regression in existing student profiles, sessions, notes, quiz, parent PIN; no secrets in commits; no destructive migrations; source fidelity tests; safety and prompt-injection tests; explainable question grading; fallback for unavailable AI providers; measurable latency/cost targets established through tests.

## Next task for Codex
Audit real source paths and produce a file-by-file risk matrix and migration plan. Do not modify application code or run importer. Compare feature/merge-main with main, inspect textbook ingest, /chat, quiz, notes, mastery, frontend state and tests. Then propose minimal M1 PR with backward compatibility and rollback.
