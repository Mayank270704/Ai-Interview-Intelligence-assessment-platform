# AI Interview Intelligence & Assessment Platform — Copilot Instructions

## 1. Project Mission

This project is a production-oriented, multimodal AI Interview Intelligence & Assessment Platform.

The platform must behave like an intelligent human interviewer rather than a predefined questionnaire or simple LLM chatbot.

The candidate uploads a resume. The system analyzes the resume, builds a structured candidate model, understands the candidate's skills, projects, experience, technologies, achievements, and claims, and then conducts a dynamic interview.

The interview must be generated at runtime based on:

* Resume content
* Candidate profile
* Candidate claims
* Interview objectives
* Previous questions
* Previous answers
* Previous evaluations
* Current knowledge state
* Interview context
* Relevant retrieved knowledge
* Interview difficulty
* Conversation history

The platform must support three interaction modes:

1. Text Interview
2. Voice Interview
3. Video Interview with an AI interviewer avatar

All three modes must use the same underlying interview intelligence and conversation state.

---

# 2. Core Product Principle

The platform is NOT a fixed question bank.

Never design the primary interview flow around:

Question 1 → Question 2 → Question 3 → Question 4

Instead, use an adaptive reasoning loop:

Resume
→ Candidate Understanding
→ Interview Strategy
→ Question Generation
→ Candidate Answer
→ Answer Understanding
→ Knowledge Retrieval when necessary
→ Answer Evaluation
→ Knowledge State Update
→ Interviewer Decision
→ Follow-up / Challenge / Topic Transition / Difficulty Change
→ New Question
→ Repeat

Every subsequent question should be generated according to the evolving conversation and candidate performance.

---

# 3. Interviewer Brain

The Interviewer Brain is the central intelligence of the platform.

Location:

backend/app/ai/interviewer_brain/

Responsibilities:

* Understand candidate context
* Maintain interview objectives
* Maintain conversation state
* Maintain interviewer memory
* Determine what competency to investigate
* Determine how deeply to probe
* Generate questions
* Generate follow-up questions
* Challenge vague or unsupported answers
* Investigate resume claims
* Identify inconsistencies
* Detect knowledge gaps
* Decide whether to continue probing
* Decide whether to increase difficulty
* Decide whether to decrease difficulty
* Decide whether to change topic
* Decide when sufficient evidence has been collected
* Maintain a natural interviewer conversation

The Interviewer Brain is an orchestrator.

It may use:

* Candidate Intelligence
* Resume Intelligence
* Answer Intelligence
* Knowledge Intelligence
* World Knowledge/RAG
* Evaluation Engine
* Adaptive Engine
* LLM

Do not place business logic belonging to these systems directly inside the API routes.

---

# 4. No Predefined Interview Sequence

Do not implement a hardcoded sequence of interview questions.

Do not create logic such as:

if question_number == 1:
ask X

if question_number == 2:
ask Y

Questions may be generated dynamically by the AI.

A knowledge base may contain concepts, competencies, examples, references, and evaluation criteria.

A knowledge base must NOT become a rigid question sequence.

---

# 5. Resume Intelligence

Location:

backend/app/ai/resume_intelligence/

The resume is a primary source of candidate context.

The system should extract and structure:

* Personal professional information
* Education
* Skills
* Technologies
* Work experience
* Projects
* Certifications
* Achievements
* Responsibilities
* Quantitative claims
* Technical claims
* Project claims
* Domain knowledge
* Tools and frameworks

Important claims must be represented separately.

Example:

Candidate claim:

"Improved model accuracy by 18%."

The system should preserve this as a claim that can later be investigated during the interview.

The interviewer should be able to ask questions that verify whether the candidate genuinely understands the claims made in the resume.

---

# 6. Resume-Grounded Interviewing

Questions should be strongly grounded in the candidate's actual resume.

Example:

Resume:
"Built a BERT-based sentiment analysis system."

The system should not immediately default to generic questions such as:

"What is BERT?"

Instead, the interviewer should investigate the candidate's actual work.

Possible progression:

* Explain how you built the system.
* Why did you choose BERT?
* How did you prepare the dataset?
* What tokenizer did you use?
* What did fine-tuning involve?
* Why did you choose that training strategy?
* What were the failure cases?
* How did you evaluate the model?
* What would you change if the dataset were ten times larger?

The exact questions must be dynamically generated based on the candidate's responses.

---

# 7. Deep Technical Interviewing

The interviewer must be capable of going deep into a concept.

Use progressive probing when appropriate:

Fundamental
→ Concept
→ Mechanism
→ Implementation
→ Trade-off
→ Failure Mode
→ Real-world Scenario
→ Architecture / Design

The interviewer should not move to a new topic merely because the candidate answered one question.

If the answer reveals uncertainty, investigate the uncertainty.

If the answer reveals strong knowledge, increase depth or difficulty.

Avoid repetitive questioning.

---

# 8. Candidate Answer Intelligence

Location:

backend/app/ai/answer_intelligence/

The system must analyze candidate answers before deciding the next question.

Analyze:

* Meaning
* Relevance
* Technical correctness
* Concept coverage
* Missing concepts
* Misconceptions
* Reasoning quality
* Completeness
* Technical depth
* Contradictions
* Unsupported claims
* Uncertainty
* Relationship to the resume
* Relationship to previous answers

The answer analysis must produce structured information that can be consumed by the Interviewer Brain.

---

# 9. Evaluation Engine

Location:

backend/app/ai/evaluation_engine/

Evaluation must be evidence-based.

Do not simply ask an LLM:

"Give this answer a score out of 10."

Instead, evaluate against explicit criteria.

Possible dimensions:

* Correctness
* Relevance
* Completeness
* Conceptual understanding
* Technical depth
* Reasoning
* Application ability
* Problem solving
* Communication

The system should retain evidence explaining why a score was assigned.

Evaluation should be reproducible and structured.

---

# 10. Knowledge State

The platform should maintain an evolving estimate of the candidate's knowledge.

Example:

Machine Learning:
High confidence

NLP:
Moderate confidence

Transformers:
Low confidence

The knowledge state must be updated after interview evidence is collected.

Do not treat one answer as absolute proof of knowledge.

Knowledge estimates should accumulate evidence over the interview and across future interviews where appropriate.

---

# 11. Adaptive Interview Engine

Location:

backend/app/ai/adaptive_engine/

The Adaptive Engine determines the next interview action.

Possible actions:

* Deep follow-up
* Clarification
* Challenge
* Increase difficulty
* Decrease difficulty
* Explore related concept
* Investigate resume claim
* Change topic
* Present practical scenario
* Present system-design scenario
* Conclude topic
* End interview

The system must choose the next action based on the current candidate state and interview objectives.

---

# 12. Interview Memory

Location:

backend/app/ai/interviewer_brain/memory.py

Maintain relevant interview memory including:

* Questions already asked
* Answers received
* Topics discussed
* Concepts demonstrated
* Concepts not demonstrated
* Weak areas
* Strong areas
* Resume claims investigated
* Unresolved questions
* Current interview objective
* Current topic
* Current depth
* Previous interviewer decisions

Do not repeatedly ask questions that have already been sufficiently answered.

---

# 13. LLM Architecture

Location:

backend/app/ai/llm/

The LLM is responsible for reasoning and generation.

Use an abstraction layer.

Application code should not directly depend on a specific provider wherever possible.

Use:

* Provider abstraction
* Model routing
* Structured outputs
* Validation
* Error handling
* Retry handling
* Timeout handling
* Token/cost tracking

Do not hardcode API keys.

Do not scatter provider-specific calls throughout the codebase.

---

# 14. Structured LLM Outputs

Prefer structured outputs over uncontrolled free-form responses when the backend needs machine-readable information.

For example:

Question generation should be capable of returning structured information such as:

* Question
* Topic
* Subtopic
* Difficulty
* Interview objective
* Expected concepts
* Evaluation criteria
* Reason for asking

Evaluation should similarly return structured data.

Always validate LLM-generated structured data before using it.

Never blindly trust model output.

---

# 15. RAG and World Knowledge

Location:

backend/app/ai/world_knowledge/

The platform must support retrieval-augmented generation.

RAG can provide:

* Technical knowledge
* Documentation
* Research material
* Domain information
* Resume context
* Internal knowledge
* Relevant external information

RAG must be used when additional knowledge is useful or necessary.

Do not blindly perform web searches after every candidate answer.

The Interviewer Brain should determine when external knowledge is required.

---

# 16. Knowledge Sources

Separate knowledge sources logically.

Possible sources:

* Resume knowledge
* Internal technical knowledge
* Curated documentation
* Research papers
* External web knowledge

Retrieved information must be passed into the LLM as contextual evidence.

The system should preserve source information where practical.

External information should not automatically be treated as truth.

Use source validation and relevance checks.

---

# 17. RAG Architecture

Preferred flow:

Candidate Answer
→ Interviewer Brain
→ Determine whether external/contextual knowledge is required
→ Retrieval
→ Reranking
→ Source Validation
→ Context Construction
→ LLM Reasoning
→ Interview Decision

Do not implement:

Candidate Answer
→ Web Search
→ LLM

for every turn.

Optimize retrieval for relevance, latency, reliability, and cost.

---

# 18. Voice Architecture

Location:

backend/app/ai/voice_intelligence/

Voice and text must use the same interview engine.

Voice flow:

Candidate Speech
→ Speech-to-Text
→ Candidate Answer
→ Interview Core
→ Next Question
→ Text-to-Speech
→ Candidate

Do not create a separate interview brain for voice.

The voice system is an interaction layer around the core interview engine.

---

# 19. Voice Communication Analysis

Where technically and ethically appropriate, analyze communication signals such as:

* Response latency
* Speaking rate
* Pause patterns
* Filler words
* Repetition
* Speech clarity

Do not claim that these signals definitively determine psychological traits, confidence, honesty, intelligence, or personality.

Treat them as communication indicators.

---

# 20. Video Interview and Avatar

Location:

backend/app/ai/avatar_intelligence/

The video interviewer consists of:

* AI-generated response
* Voice
* Avatar
* Lip synchronization
* Controlled facial expressions
* Controlled gestures
* Timing

The avatar must NOT make interview decisions.

The Interviewer Brain makes decisions.

The Avatar Intelligence layer translates interviewer output into visual behavior.

Architecture:

Interviewer Brain
→ Response
→ TTS
→ Avatar Controller
→ Expression / Gesture / Lip Sync
→ Candidate

Keep avatar behavior controlled and deterministic where possible.

---

# 21. Text, Voice, and Video Must Share State

All modes must use the same:

* Interview ID
* Conversation state
* Candidate model
* Knowledge state
* Interview strategy
* Evaluation state
* Interview history

A user should be able to switch modes without restarting the interview where technically feasible.

Example:

Voice
→ Text
→ Voice

must continue the same interview session.

---

# 22. Backend Architecture

Use the following dependency direction:

API
→ Services
→ AI / Domain Logic
→ Repositories
→ Database

API routes should remain thin.

Do not place:

* LLM calls
* RAG logic
* business rules
* database-heavy logic
* interview reasoning

directly inside API route files.

---

# 23. Database Architecture

Use PostgreSQL as the primary relational database.

Use pgvector where vector search is required.

Core entities include:

* Users
* Resumes
* Resume sections
* Candidate profiles
* Skills
* Projects
* Claims
* Interviews
* Questions
* Answers
* Evaluations
* Knowledge states
* Communication metrics
* Job descriptions

Database models must represent relationships clearly.

Do not duplicate data unnecessarily.

Use migrations for schema changes.

Never manually modify production schema without a migration.

---

# 24. Async Processing

Use background workers for expensive or asynchronous tasks such as:

* Resume processing
* Large document processing
* Embedding generation
* Non-blocking evaluation
* Analytics processing
* Cleanup jobs

Do not block real-time interview interaction with unnecessary background operations.

Real-time interview paths must prioritize low latency.

---

# 25. Real-Time Communication

Voice/video interview interactions may require WebSocket or equivalent real-time communication.

Keep real-time transport separate from interview intelligence.

Transport layer:
handles communication.

Interview Core:
handles reasoning.

AI services:
handle intelligence.

---

# 26. Frontend Architecture

The frontend must consume backend APIs/services.

The frontend must not contain AI business logic.

Do not place:

* LLM prompts
* evaluation logic
* RAG logic
* scoring logic
* interviewer decision logic

inside React components.

Frontend responsibilities include:

* User interface
* Interview interaction
* Voice controls
* Video/avatar presentation
* Resume upload
* Dashboard
* Analytics visualization
* State presentation

---

# 27. Security

Never commit secrets.

Never hardcode:

* API keys
* database passwords
* tokens
* private credentials

Use environment variables.

Validate uploaded files.

Restrict file types and sizes.

Protect user data.

Treat resumes and interview transcripts as sensitive user content.

Implement authentication and authorization before production deployment.

Do not expose internal prompts or private evaluation state unnecessarily.

---

# 28. Error Handling

Production code must handle:

* LLM failures
* Rate limits
* Timeouts
* Invalid model output
* Retrieval failures
* STT failures
* TTS failures
* Network failures
* Database failures
* Invalid uploads
* Interrupted interviews

The application should degrade gracefully.

For example, if voice fails, the interview should be able to fall back to text where feasible.

Never silently swallow important errors.

---

# 29. Observability

Implement structured logging.

Track where appropriate:

* Request latency
* LLM latency
* Token usage
* Estimated AI cost
* Retrieval latency
* STT latency
* TTS latency
* Interview turn latency
* Errors
* Model/provider failures

Do not log sensitive user data unnecessarily.

---

# 30. Testing

Testing is mandatory.

Maintain:

* Unit tests
* Integration tests
* API tests
* AI tests
* Evaluation tests

AI evaluation must include benchmark-style tests.

Important AI components should be tested for:

* Correctness
* Consistency
* Relevance
* Structured output validity
* Question diversity
* Resume grounding
* Follow-up quality
* Evaluation reliability

Do not consider the project complete simply because the application runs.

---

# 31. AI Evaluation Benchmark

The project must eventually maintain an evaluation dataset containing examples such as:

* Question
* Candidate answer
* Expected concepts
* Missing concepts
* Incorrect concepts
* Human evaluation
* AI evaluation
* Difficulty
* Topic

Use this benchmark to evaluate the quality of the AI interviewer.

The goal is to measure whether AI evaluation aligns reasonably with human judgment.

Do not assume LLM scores are automatically correct.

---

# 32. AI Safety and Reliability

The system must distinguish:

* Candidate claims
* Retrieved facts
* Model-generated hypotheses
* Verified information
* Evaluation evidence

Do not present uncertain model conclusions as objective facts.

The interviewer should challenge candidates professionally without being abusive, insulting, or manipulative.

Avoid discriminatory or irrelevant interview criteria.

Do not infer protected characteristics.

Do not use facial analysis to make unsupported claims about candidate personality, intelligence, honesty, or competence.

---

# 33. Code Quality

Use:

* Clear naming
* Type hints
* Small focused modules
* Explicit interfaces
* Dependency injection where useful
* Proper error handling
* Testable functions
* Separation of concerns

Avoid:

* Giant files
* Giant functions
* Circular dependencies
* Duplicated business logic
* Hidden global state
* Magic constants
* Hardcoded credentials
* Unnecessary abstractions

Prefer simple, maintainable solutions.

---

# 34. Dependency Policy

Do not add a dependency merely because it makes one small task easier.

Before adding a major dependency, consider:

* Maintenance
* Security
* Performance
* License
* Community support
* Deployment complexity
* Whether the functionality can reasonably be implemented with existing dependencies

Do not introduce microservices, Kubernetes, Kafka, or other infrastructure without an actual architectural requirement.

Complexity must be justified by a real need.

---

# 35. AI Provider Independence

Keep AI provider integrations behind interfaces.

The system should be designed so that components such as:

* LLM
* Embeddings
* STT
* TTS

can be replaced without rewriting the entire application.

Do not tightly couple business logic to one provider.

---

# 36. No Fake AI

Do not create placeholder behavior that pretends to be intelligent in production paths.

Do not:

* hardcode fake scores
* randomly generate evaluation scores
* hardcode fake interview questions
* create fake knowledge states
* simulate AI reasoning with random rules

During development, mocks may be used only when explicitly identified as mocks and isolated from production implementations.

---

# 37. Development Discipline

When implementing a feature:

1. Understand the existing architecture.
2. Identify the correct module.
3. Reuse existing abstractions.
4. Make the smallest appropriate change.
5. Add or update tests.
6. Validate the change.
7. Do not modify unrelated files.

Do not restructure the project without explicit instruction.

Do not rename architectural modules without approval.

Do not create new top-level architectural layers without approval.

---

# 38. Documentation Discipline

Important architectural decisions must be reflected in:

docs/

Relevant documentation includes:

* ARCHITECTURE.md
* SYSTEM_DESIGN.md
* AI_ARCHITECTURE.md
* INTERVIEW_BRAIN.md
* WORLD_KNOWLEDGE.md
* EVALUATION_FRAMEWORK.md
* VOICE_ARCHITECTURE.md
* AVATAR_ARCHITECTURE.md
* DATABASE_DESIGN.md
* API_SPECIFICATION.md
* SECURITY.md
* TESTING.md
* DEPLOYMENT.md

When an architectural decision changes, update the relevant documentation.

---

# 39. Current Development Philosophy

Build the intelligence before polishing the presentation.

Priority order:

1. Backend foundation
2. Database
3. LLM abstraction
4. RAG / knowledge layer
5. Resume intelligence
6. Candidate model
7. Interviewer Brain
8. Dynamic question generation
9. Answer intelligence
10. Evaluation engine
11. Adaptive interview engine
12. Text interview
13. Voice interview
14. Video/avatar interview
15. Knowledge analytics
16. Production hardening
17. Deployment

Do not begin with the avatar before the underlying interview engine works.

---

# 40. Definition of a Successful Interview

A successful interview is NOT:

"AI asked ten questions."

A successful interview is:

The AI understood the candidate's background, formed an interview strategy, investigated relevant competencies, generated questions dynamically, analyzed answers, followed interesting technical threads, challenged weak or unsupported answers, adapted difficulty, avoided unnecessary repetition, gathered sufficient evidence, and produced a transparent assessment grounded in the actual interview.

---

# 41. Copilot Operating Rule

Before writing code, inspect the relevant existing files.

Do not assume files, classes, functions, database models, APIs, or dependencies exist.

Do not invent architecture when the project already defines one.

Follow this instruction file and the architecture documentation.

If an implementation requires an architectural decision that is not defined, stop and clearly identify the decision instead of silently inventing a new architecture.

Do not modify unrelated files.

Do not generate the entire application in one step.

Implement features incrementally and keep each change testable.

The architecture defined by the project documentation and these instructions is the source of truth.

---

# 42. Final Architectural Principle

The platform should ultimately behave like:

UNDERSTAND
→ PLAN
→ ASK
→ LISTEN
→ ANALYZE
→ RETRIEVE
→ REASON
→ CHALLENGE
→ VERIFY
→ UPDATE KNOWLEDGE
→ ADAPT
→ ASK AGAIN

The AI interviewer should continuously build an evidence-based understanding of the candidate throughout the interview.

The goal is not to simulate intelligence through a sequence of prompts.

The goal is to engineer an adaptive interview intelligence system.
# 43. Minimal Code and Anti-Overengineering Rules

Write only the code that is necessary to implement the requested functionality.

Do not generate unnecessary code.

Do not create files, classes, functions, interfaces, utilities, wrappers, abstractions, configuration files, or dependencies unless they are required by the current implementation or established architecture.

Prefer the simplest correct implementation.

Avoid speculative code for future features.

Do not create placeholder implementations unless explicitly requested.

Do not create duplicate functionality when an existing module already provides it.

Before creating a new utility, service, helper, class, or abstraction, inspect the existing codebase and determine whether the functionality already exists.

Do not create a wrapper around a library or API unless the wrapper provides a clear architectural benefit.

Do not create multiple layers for simple operations.

Avoid unnecessary design patterns.

Do not introduce factories, managers, registries, adapters, providers, or interfaces merely for abstraction.

Use an abstraction only when there is a real requirement such as provider replacement, testability, separation of responsibilities, or significant complexity.

Do not add comments that merely restate what the code does.

Do not generate excessive documentation inside source files.

Keep functions focused and reasonably small, but do not split trivial logic into unnecessary functions.

Keep classes focused, but do not create classes when a simple function or module is sufficient.

Do not add unused imports.

Do not add unused variables.

Do not add unused dependencies.

Do not add configuration options that are not currently required.

Do not add endpoints that are not currently required.

Do not create database tables for features that have not been implemented.

Do not create frontend components for screens that are not currently being implemented.

Do not implement future roadmap features in advance.

Do not duplicate types between frontend and backend without a clear reason.

Do not duplicate business logic between frontend and backend.

Do not generate mock data unless explicitly requested.

Do not generate fake AI behavior.

Do not create fallback logic merely to hide an error.

Do not silently ignore errors.

Before adding code, ask:

1. Is this required for the current feature?
2. Does this functionality already exist?
3. Can the existing architecture handle it without another abstraction?
4. Is this code actually executed?
5. Is this dependency genuinely necessary?

If the answer is no, do not add it.

The project should grow incrementally.

A feature should introduce only the files and code required for that feature.

Prefer:

Simple → Correct → Testable → Maintainable

over:

Complex → Abstract → Speculative → Over-engineered

Do not optimize for the number of files or amount of code.

Optimize for correctness, clarity, reliability, performance, and maintainability.

Every line of production code should have a purpose.
