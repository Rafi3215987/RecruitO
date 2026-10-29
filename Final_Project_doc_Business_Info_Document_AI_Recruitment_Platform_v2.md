Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

**BUSINESS INFORMATION DOCUMENT (BID)** AI-Powered Recruitment & Interview Intelligence Platform 

_Final Evaluation Assignment — AI Trainee Developer Programme_ 

|**Document Attribute**|**Detail**|
|---|---|
|**Document Type**|Business Information Document (BID) / Assignment Brief|
|**Programme**|AI Trainee Developer — Final Evaluation|
|**Project Name**|To be proposed by each trainee (see Section 2.3)|
|**Mode of Work**|Individual (solo) — no team collaboration permitted|
|**Total Duration**|17 working days(1<sup>st </sup>October to 27<sup>th </sup>October 2026)|
|**Phase 1**|Requirement Understanding, Clarification & WBS — 2 days|
|**Phase 2**|Core Development, Submission & Presentation — 15 days|
|**Primary Audience**|AI Trainee Developers|
|**Secondary Audience**|Trainers, Technical Mentors, Evaluation Panel|
|**Version**|1.0|
|**Status**|Issued for Execution|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 1 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# **Table of Contents** 

|**1. Document Purpose & Audience....................................................................................................... 4**|
|---|
|1.1 Purpose............................................................................................................................................. 4|
|1.2 Intended Audience............................................................................................................................4|
|1.3 How to Read This Document.............................................................................................................4|
|**2. Project Overview & Background...................................................................................................... 5**|
|2.1 Business Context............................................................................................................................... 5|
|2.2 The Proposed Solution......................................................................................................................5|
|2.3 Project Naming — Trainee Responsibility.........................................................................................5|
|**3. Objectives & Goals.......................................................................................................................... 7**|
|3.1 Business Objectives...........................................................................................................................7|
|3.2 Learning & Evaluation Objectives..................................................................................................... 7|
|3.3 Definition of Success......................................................................................................................... 8|
|**4. Scope..............................................................................................................................................9**|
|4.1 In-Scope.............................................................................................................................................9|
|4.2 Out-of-Scope..................................................................................................................................... 9|
|4.3 Scope Boundary Guidance.............................................................................................................. 10|
|**5. Functional Features....................................................................................................................... 11**|
|5.1 Feature Summary............................................................................................................................11|
|5.2 Stage 1 — Pre-Interview................................................................................................................. 11|
|5.3 Stage 2 — During-Interview............................................................................................................12|
|5.4 Stage 3 — Post-Interview................................................................................................................13|
|**6. Creative / Innovation Feature (Trainee-Independent Task)............................................................. 16**|
|6.1 Purpose of This Task........................................................................................................................16|
|6.2 Requirements..................................................................................................................................16|
|6.3 Assessment Dimensions..................................................................................................................17|
|6.4 Constraints...................................................................................................................................... 17|
|**7. Non-Functional Requirements....................................................................................................... 18**|
|7.1 Performance & Responsiveness......................................................................................................18|
|7.2 Security............................................................................................................................................18|
|7.3 Candidate Data Privacy................................................................................................................... 18|
|7.4 Reliability, Maintainability & Usability............................................................................................19|
|**8. Technical Requirements & Constraints...........................................................................................21**|
|8.1 Mandatory Technology Stack..........................................................................................................21|
|8.2 LangGraph Usage Expectations.......................................................................................................21|
|8.3 Dockerisation Requirements...........................................................................................................21|
|8.4 GitHub Repository Requirements................................................................................................... 22|
|8.5 Sample Data Provision.................................................................................................................... 23|
|<br>8.6 Recommended but Optional...........................................................................................................23|
|**9. Project Phases & Timeline..............................................................................................................24**|
|9.1 Phase Summary...............................................................................................................................24|
|9.2 Phase 1 — Detailed Plan (Days 1–3)............................................................................................... 24|
|9.3 Phase 2 — Detailed Plan (Days 4–20)............................................................................................. 25|
|<br>9.4 Milestones & Gates.........................................................................................................................26|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 2 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

|**10. Deliverables................................................................................................................................ 27**|
|---|
|10.1 Phase 1 Deliverables (Due End of Day 3)...................................................................................... 27|
|10.2 Phase 2 Deliverables (Due End of Day 20)....................................................................................27|
|10.3 Submission Standards................................................................................................................... 28|
|**11. Evaluation Criteria & Weightage.................................................................................................. 29**|
|11.1 Overall Weightage.........................................................................................................................29|
|11.2 Bonus Marks — Stretch Features..................................................................................................30|
|11.3 Feature-Level Scoring Rubric........................................................................................................ 30|
|11.4 Deductions.................................................................................................................................... 31|
|11.5 What Distinguishes a Strong Submission......................................................................................31|
|**12. Assumptions & Constraints..........................................................................................................32**|
|12.1 Assumptions..................................................................................................................................32|
|12.2 Constraints.................................................................................................................................... 32|
|12.3 Known Risks...................................................................................................................................33|
|**13. AI Usage Guidelines..................................................................................................................... 34**|
|13.1 Permitted Use of AI.......................................................................................................................34|
|13.2 Activities Without AI Support....................................................................................................... 34|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 3 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# 1. Document Purpose & Audience 

## 1.1 Purpose 

This Business Information Document (BID) defines the business context, functional expectations, technical constraints, delivery timeline, and evaluation framework for the final assessment project of the AI Trainee Developer Programme. 

The document serves three purposes simultaneously: 

- **Business brief —** It communicates business intent rather than technical specifications. It describes what the business needs and why, leaving the "how" to the trainee. 

- **Assignment contract —** It sets out mandatory deliverables, phase gates, submission standards and the weighted criteria against which work will be graded. 

- **Instructional guide —** It provides guidance notes throughout to help trainees approach requirement analysis, work breakdown, prioritisation and delivery in a professional manner. 

## 1.2 Intended Audience 

|**Audience**|**How This Document Should Be Used**|
|---|---|
|**AI Trainee Developers**|Primary audience. Read the full document before starting. Treat it as the<br>authoritative statement of scope and acceptance. Raise ambiguities during<br>Phase 1 rather than assuming.|
|**Trainers & Technical**<br>**Mentors**|Reference for clarification sessions, checkpoint reviews, and progress<br>tracking against the stated phase plan.|
|**Evaluation Panel**|Basis for scoring. Section 11 defines the weightage model applied at final<br>submission and presentation.|
|**Programme Coordinators**|Reference for schedule, milestone dates, resource provisioning (sample<br>CVs) and submission logistics.|



## 1.3 How to Read This Document 

Sections 2 to 4 establish business context and boundaries. Sections 5 and 6 define what must be built. Sections 7 and 8 define quality and technology constraints. Sections 9 to 12 define how the work will be planned, delivered, and judged. 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 4 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# 2. Project Overview & Background 

## 2.1 Business Context 

Recruitment teams across the industry face a persistent bottleneck: the volume of applications received for any given role far exceeds the human capacity available to assess them consistently. Screening is frequently performed under time pressure, evaluation criteria drift between reviewers, and interview outcomes are recorded as unstructured notes that are difficult to compare, audit or defend. 

The consequences are well understood by hiring organisations: 

- Qualified candidates are missed because screening is shallow and keyword-driven. 

- Different interviewers apply different standards to the same role, producing non-comparable outcomes. 

- Interview content is lost; only a subjective summary survives. 

- Hiring decisions cannot be traced back to evidence, creating fairness and compliance exposure. 

- The cycle time from application to decision is long, and strong candidates withdraw. 

## 2.2 The Proposed Solution 

The business requires an AI-powered Recruitment & Interview Intelligence Platform that supports the hiring workflow end to end — from the moment a CV is received, through the live interview, to a consolidated, evidence-backed candidate assessment. 

The platform is expected to operate across three logical stages: 

|**Stage**|**Business Intent**|
|---|---|
||Ingest and understand CVs, measure them objectively against defined job|
|**Pre-Interview**|requirements, and produce a ranked, scored shortlist so that interviewer time is<br>spent on the right candidates.|
|**During-Interview**|Conduct the interview through an integrated video interface while capturing the<br>conversation as structured, speaker-attributed data instead of ad-hoc notes.|
||Analyse what was actually asked and answered, and merge that evidence with|
|**Post-Interview**|pre-interview screening into one consolidated assessment that a hiring manager<br>can act on.|



_The platform is intended to augment human decision-making, not to replace it. Every AI-generated score, ranking or flag must be explainable and traceable to the underlying evidence._ 

## 2.3 Project Naming — Trainee Responsibility 

No project name is assigned in this document. This omission is deliberate. 

**Each trainee must propose their own project name and product identity as a graded deliverable.** The 

name is not a cosmetic exercise; it is treated as a signal of product thinking. Trainers will assess whether the trainee understood the problem well enough to articulate what the product is and who it serves. 

The naming deliverable must include: 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 5 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

- A proposed product name. 

- A one-line positioning statement (what it does, for whom). 

- A short rationale of two to four sentences explaining the reasoning behind the name. 

- Consistent application of the name across the repository, README, application interface and final presentation. 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 6 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# 3. Objectives & Goals 

## 3.1 Business Objectives 

|**#**|**Objective**|**Success Indicator**|
|---|---|---|
|**B1**|Reduce manual CV screening effort|A batch of CVs can be screened and ranked against a job<br>requirement without manual review of each document.|
|**B2**|Improve consistency of candidate<br>evaluation|The same candidate and job requirement produce a<br>stable, reproducible score with a visible breakdown.|
|**B3**|Capture interview content as<br>structured data|Every interview produces a speaker-attributed transcript<br>rather than free-form notes.|
|**B4**|Enable evidence-based hiring decisions|Each assessment cites the CV content and transcript<br>segments that justify its conclusions.|
|**B5**|Shorten time-to-decision|A consolidated assessment is available immediately after<br>the interview concludes.|



## 3.2 Learning & Evaluation Objectives 

Beyond the product itself, this assignment is designed to assess the following competencies: 

|**#**|**Competency**|**How It Is Demonstrated**|
|---|---|---|
|**L1**|Requirement analysis|Quality and depth of clarification questions and<br>documented assumptions in Phase 1.|
|**L2**|Planning & estimation|Realism, granularity and traceability of the Work<br>Breakdown Structure.|
|**L3**|Agentic AI engineering|Appropriate use of LangGraph for multi-step, stateful<br>reasoning rather than single monolithic prompts.|
|**L4**|Backend & API design|Clean, documented FastAPI service boundaries and data<br>contracts.|
|**L5**|System integration|Ability to combine video, audio, transcription, LLM<br>reasoning and persistence into one coherent application.|
|**L6**|Delivery discipline|Dockerised, reproducible build; clean repository;<br>meaningful commit history.|
|**L7**|Creativity & initiative|Originality and value of the self-proposed innovation<br>feature and product name.|
|**L8**|Communication|Clarity of documentation and the final presentation and<br>demonstration.|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 7 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

## 3.3 Definition of Success 

A submission is considered successful when all of the following hold: 

- All six Core (Mandatory) features are implemented and demonstrable end to end. 

- One original Creative / Innovation feature is implemented with a written rationale. 

- The application runs from a clean machine using documented Docker commands, with no undocumented manual setup. 

- The GitHub repository contains a complete README, clear setup instructions and an incremental commit history. 

- A proposed project name and product positioning are presented and applied consistently. 

- The trainee can explain and defend their architectural decisions during the presentation. 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 8 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# 4. Scope 

## 4.1 In-Scope 

|**Area**|**Included in Scope**|
|---|---|
|**Job Requirement Definition**|Ability to define or configure a job requirement profile — required skills,<br>qualifications, minimum experience and selection criteria.|
|**Job Post**|We are looking for a talented and motivated professional to join our team.<br>If you are interested in this opportunity, please send your CV to the contact<br>email provided in the job post.<br>Feel free to share this opportunity with anyone who may be interested.|
|**CV Ingestion & Parsing**|Upload and parse candidate CVs (minimum: PDF; DOCX support<br>encouraged) and extract structured attributes.|
|**Screening & Ranking**|Automated matching of parsed CVs against the job requirement profile,<br>with an ordered candidate ranking.|
|**Candidate Scoring**|Objective, criteria-weighted suitability scoring with a visible breakdown per<br>criterion.|
|**Video Interview**|An integrated video-chat interface supporting a real-time interviewer–<br>candidate session with concurrent audio capture.|
|**Speech Recognition**|Transcription of both participants with speaker attribution and a structured,<br>timestamped transcript.|
|**Q&A Analysis**|Analysis of interviewer questions and candidate responses for relevance,<br>accuracy, completeness and quality.|
|**Consolidated Assessment**|A unified candidate report combining screening, scoring and interview<br>analysis.|
|**Innovation Feature**|One original, trainee-conceived feature with documented rationale.|
|**Packaging & Delivery**|Dockerised application, GitHub repository, README, setup documentation<br>and final presentation.|



## 4.2 Out-of-Scope 

The following are explicitly excluded. Trainees must not spend effort here; doing so will be treated as a scope-management failure. 

|**Area**|**Excluded — Rationale**|
|---|---|
|**Production deployment**|No cloud hosting, CI/CD pipelines, load balancing or infrastructure-as-code<br>required. Local Docker execution is sufficient.|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 9 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

|**Area**|**Excluded — Rationale**|
|---|---|
|**Enterprise authentication**|No SSO, LDAP, OAuth provider integration or enterprise identity<br>management. Simple role separation is acceptable.|
|**ATS / HRIS integration**|No integration with commercial applicant tracking or HR information<br>systems.|
|**Payroll, offer & onboarding**|The workflow ends at the consolidated candidate assessment.|
|**Job posting & sourcing**|No job-board publishing, candidate sourcing or application-portal<br>functionality.|
|**Interview scheduling &**<br>**calendaring**|Calendar integration and automated scheduling are excluded unless a<br>trainee elects it as their innovation feature.|
|**Multi-tenancy & billing**|No tenant isolation, subscription management or commercial licensing<br>logic.|
|**Native mobile applications**|Web-based delivery only.|
|**Custom model training**|Training or fine-tuning foundation models from scratch is out of scope. Use<br>of existing models and APIs is expected.|
|**Formal accessibility**<br>**certification**|WCAG conformance auditing is not required, though sensible accessibility<br>practice is welcome.|



## 4.3 Scope Boundary Guidance 

##### **Guidance Note — Protecting Your Scope** 

Seventeen development days is less time than it appears once integration and debugging are accounted for. The most common failure mode is over-building the first feature and running out of time before the interview pipeline is working. 

Build a thin end-to-end slice first — CV in, interview conducted, assessment out — then deepen each stage. A shallow but complete pipeline is worth substantially more marks than one beautifully engineered module and four unfinished ones. 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 10 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# 5. Functional Features 

Features are grouped by the stage of the recruitment workflow in which they operate. Within each stage, Core (Mandatory) features must be delivered; Stretch (Bonus) features are optional and carry additional credit. 

## 5.1 Feature Summary 

|**#**|**Feature**|**Stage**|**Priority**|**Classification**|
|---|---|---|---|---|
|**F1**|CV Screening & Requirement-Based<br>Candidate Ranking|Pre-Interview|Must Have|Core|
|**F2**|AI-Based Candidate Scoring|Pre-Interview|Must Have|Core|
|**F3**|AI-Powered Video Interview|During-Interview|Must Have|Core|
|**F4**|Real-Time Speech Recognition &<br>Transcription|During-Interview|Must Have|Core|
|**F5**|AI-Based Interview Question & Answer<br>Analysis|Post-Interview|Must Have|Core|
|**F6**|Consolidated Candidate Assessment|Post-Interview|Must Have|Core|
|**F7**|Candidate Identification & Real-Time<br>Profile Overview|During-Interview|Could Have|Stretch|
|**F8**|CV Claim Verification Through Interview<br>Analysis|Post-Interview|Could Have|Stretch|
|**F9**|Comprehensive Candidate Interview<br>Scoring|Post-Interview|Could Have|Stretch|
|**F10**|Interview Quality Assessment|Post-Interview|Could Have|Stretch|
|**F11**|Trainee-Proposed Innovation Feature|Any|Must Have|Creative|



## 5.2 Stage 1 — Pre-Interview 

This stage covers everything that happens before a candidate enters an interview: ingesting CVs, understanding the job requirement, and producing a ranked and scored shortlist. 

### 5.2.1 Core (Mandatory) Features 

#### **F1 — CV Screening & Requirement-Based Candidate Ranking** 

The system must automatically analyse and screen submitted CVs against a defined set of job requirements and rank candidates by overall suitability. 

#### **Expected behaviour:** 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 11 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

- Accept a job requirement profile covering required and preferred skills, qualifications, minimum years of experience and any additional selection criteria. 

- Ingest and parse multiple CVs in a single batch and extract structured information — contact details, education, work history, skills, certifications, project experience. 

- Match extracted attributes against the requirement profile using semantic understanding, not literal keyword matching alone. A CV stating "built REST services in Django" should register against a "Python web development" requirement. 

- Produce an ordered ranking of all screened candidates with a clear indication of relative suitability. 

- Expose the reasoning: for each candidate, indicate which requirements were met, partially met or unmet, with supporting evidence drawn from the CV. 

- Handle imperfect input gracefully — non-standard layouts, missing sections, multi-column formats and scanned or image-heavy documents should fail safely rather than crash the batch. 

#### **F2 — AI-Based Candidate Scoring** 

The system must evaluate each candidate against predefined requirements and generate an objective suitability score. 

#### **Expected behaviour:** 

- Score across distinct dimensions at minimum: technical skills, relevant experience, and academic or professional qualifications. Additional dimensions may be defined by the trainee. 

- Support configurable weighting per dimension so that the profile can be tuned per role. 

- Present both an aggregate score and the per-dimension breakdown that produced it. 

- Accompany each dimension score with a short natural-language justification. 

- Produce stable, reproducible results — the same CV and requirement profile should not yield materially different scores on repeated runs. 

- Persist scores so that they can be retrieved later and merged into the consolidated assessment. 

### 5.2.2 Stretch (Bonus) Features — Pre-Interview 

_No stretch features are defined for this stage. Trainees who wish to extend the pre-interview stage should do so through their Innovation Feature (Section 6)._ 

## 5.3 Stage 2 — During-Interview 

This stage covers the live interview session: the video interaction itself and the real-time capture and structuring of the conversation. 

### 5.3.1 Core (Mandatory) Features 

#### **F3 — AI-Powered Video Interview** 

The system must allow interviews to be conducted through an integrated video-chat interface that enables real-time communication while continuously capturing audio and conversation data for analysis. 

#### **Expected behaviour:** 

- Provide a browser-based video and audio session between interviewer and candidate. 

- Support the basic session lifecycle: create or schedule a session, join, conduct, and end. 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 12 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

- Capture the audio stream continuously throughout the session and route it into the analysis pipeline. 

- Associate every session with a specific candidate and a specific job requirement profile. 

- Provide standard in-call controls — mute, camera toggle, end session. 

- Degrade gracefully on network interruption; a dropped frame must not terminate the recording or lose the transcript captured so far. 

- Persist the session record, including start and end times and participants. 

#### **F4 — Real-Time Speech Recognition & Transcription** 

The system must capture and transcribe the speech of both interviewer and interviewee, distinguish between speakers, and generate a structured interview transcript. 

#### **Expected behaviour:** 

- Transcribe speech during the session with minimal perceptible lag. 

- Attribute each utterance to the correct speaker (speaker diarisation or channel separation). 

- Timestamp each utterance so that transcript segments can be referenced later as evidence. 

- Produce a structured transcript — a sequence of speaker-attributed, timestamped turns — rather than an undifferentiated block of text. 

- Persist the transcript and make it retrievable after the session ends. 

- Handle accented speech, overlapping speech and silence without failing; imperfect transcription is acceptable provided the system remains stable. 

### 5.3.2 Stretch (Bonus) Features — During-Interview 

#### **F7 — Candidate Identification & Real-Time Profile Overview** 

Identify the interviewee via facial and/or voice recognition, retrieve their stored information, and present a concise profile overview within the interview interface. 

- Match the person joining the session against the candidate records already in the system. 

- On a confident match, surface a compact profile panel to the interviewer — name, headline experience, key skills, pre-interview score and flagged areas to probe. 

- Handle non-identification and low-confidence matches explicitly; never silently assume an identity. 

- Treat biometric data with particular care — see Section 7.3 on candidate data privacy. Consent handling must be visible in the flow. 

## 5.4 Stage 3 — Post-Interview 

This stage converts captured interview data into analysis, and merges that analysis with pre-interview screening into a single decision-support artefact. 

### 5.4.1 Core (Mandatory) Features 

#### **F5 — AI-Based Interview Question & Answer Analysis** 

The system must analyse interviewer questions and candidate responses to determine how effectively the candidate addressed the job requirements. 

#### **Expected behaviour:** 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 13 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

- Segment the transcript into question–answer pairs, correctly associating each response with the question that prompted it. 

- Evaluate each response on, at minimum: relevance to the question asked, factual and technical accuracy, completeness, and overall quality of articulation. 

- Map questions and answers back to the specific job requirements they address, so coverage gaps become visible. 

- Provide a short written justification for each evaluation, referencing the transcript segment that supports it. 

- Handle follow-up questions, clarifications and multi-part answers sensibly. 

- Identify requirements that were never explored during the interview. 

#### **F6 — Consolidated Candidate Assessment** 

The system must combine CV screening, requirement-based scoring and interview analysis into a single consolidated, structured assessment supporting consistent, data-driven hiring decisions. 

#### **Expected behaviour:** 

- Merge pre-interview screening results, candidate scores and post-interview Q&A analysis into one coherent candidate report. 

- Present an overall suitability position supported by component scores, not a single opaque number. 

- Summarise strengths, weaknesses, evidence gaps and recommended areas for further verification. 

- Make the report exportable or printable in a readable format (PDF, structured HTML or equivalent). 

- Support side-by-side comparison of multiple assessed candidates for the same role. 

- Maintain traceability throughout — every conclusion should be attributable to CV content or a transcript segment. 

### 5.4.2 Stretch (Bonus) Features — Post-Interview 

#### **F8 — CV Claim Verification Through Interview Analysis** 

- Cross-reference claims made in the CV against what the candidate said during the interview. 

- Flag inconsistencies, contradictions and claims that were asserted but never substantiated. 

- Distinguish clearly between a genuine contradiction, an unverified claim and a claim that was simply never discussed. 

- Present flags as prompts for human follow-up, never as accusations or automated rejections. 

#### **F9 — Comprehensive Candidate Interview Scoring** 

- Generate an overall interview performance score distinct from the CV-based score. 

- Score across technical competency, communication, relevance of responses, problem-solving approach, depth of experience demonstrated, and alignment with job requirements. 

- Provide the per-dimension breakdown and supporting evidence. 

#### **F10 — Interview Quality Assessment** 

- Evaluate the quality of the interview process itself, not only the candidate. 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 14 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

- Assess relevance and effectiveness of the interviewer questions, coverage of the required competencies, consistency of process across candidates, and overall interaction quality. 

- Recommend improvements — competencies left unexplored, questions that produced little signal, imbalanced speaking time. 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 15 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# 6. Creative / Innovation Feature (Trainee-Independent Task) 

## 6.1 Purpose of This Task 

Every trainee must propose and implement ONE original feature of their own that meaningfully enhances the platform. 

This task is deliberately unspecified. The features in Section 5 tell you what to build; this section asks you to decide what should be built. It is included because engineering judgement — identifying a real gap, evaluating whether it is worth solving, and delivering it within constraints — cannot be assessed through prescribed requirements. 

Because every trainee will propose something different, this task also gives trainers a clear, uncontaminated view of individual thinking and initiative. 

## 6.2 Requirements 

|**#**|**Requirement**|**Detail**|
|---|---|---|
|**C1**|Originality|The feature must be the trainee's own idea. It must not be one<br>of features F1–F10, nor a cosmetic variation, subset or renaming<br>of them.|
|**C2**|Relevance|It must enhance the recruitment and interview intelligence<br>platform. An unrelated capability bolted on will not be credited.|
|**C3**|Written rationale|A short document (approximately 300–500 words) stating the<br>problem it solves, who benefits, the value it adds, and why it was<br>prioritised over alternatives the trainee considered.|
|**C4**|Independent design|Designed and implemented by the trainee alone, without<br>trainer-provided specification.|
|**C5**|Working implementation|It must be implemented and demonstrable in the running<br>application. A concept or mock-up alone does not satisfy this<br>requirement.|
|**C6**|Integration|It must integrate coherently with the rest of the platform rather<br>than existing as a disconnected side module.|
|**C7**|Documentation|It must be documented in the README, clearly identified as the<br>Innovation Feature.|
|**C8**|Presentation|It must be demonstrated and justified during the final<br>presentation.|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 16 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

## 6.3 Assessment Dimensions 

|**Dimension**|**What Trainers Will Look For**|
|---|---|
|**Problem identification**|Does the feature address a real gap in the recruitment workflow, or a<br>hypothetical one?|
|**Originality**|Is the thinking genuinely the trainee's own, or an obvious extension of<br>the given list?|
|**Value articulation**|Can the trainee explain who benefits and why, in business terms rather<br>than technical terms?|
|**Prioritisation judgement**|Did the trainee weigh alternatives and choose deliberately, or pick the<br>first idea that occurred?|
|**Technical execution**|Is it actually working, reasonably built and integrated?|
|**Scope discipline**|Was it delivered without compromising the Core features?|



## 6.4 Constraints 

- Exactly one innovation feature is required. Additional features will not attract additional marks and may indicate poor prioritisation. 

- It must not be attempted at the expense of Core features. 

- It must respect all non-functional requirements in Section 7, particularly candidate data privacy. 

- It must operate within the technical constraints in Section 8. 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 17 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# 7. Non-Functional Requirements 

## 7.1 Performance & Responsiveness 

|**#**|**Requirement**|**Expectation**|
|---|---|---|
|**N1**|CV parsing throughput|A batch of 20 CVs should be parsed, screened, scored and ranked<br>within a reasonable, documented time window. State your<br>measured figure in the README.|
|**N2**|Transcription latency|Transcribed text should appear with minimal perceptible delay<br>during the live session.|
|**N3**|Video session quality|The video and audio session must remain usable and stable for the<br>duration of a typical interview.|
|**N4**|API responsiveness|Non-AI API endpoints should respond quickly. Long-running AI<br>operations must be asynchronous, with progress or status<br>feedback rather than a blocked request.|
|**N5**|Concurrency|The system should tolerate at least one active interview session<br>alongside background CV processing without failure.|
|**N6**|Graceful degradation|Failure of an external AI service must produce a clear error state,<br>not a crash or silent data loss.|



## 7.2 Security 

|**#**|**Requirement**|**Expectation**|
|---|---|---|
|**N7**|Credential management|All API keys, secrets and connection strings must be supplied via<br>environment variables. No secret may ever be committed to the<br>repository. Provide a .env.example with placeholder values.|
|**N8**|Input validation|All API inputs must be validated. Uploaded files must be checked<br>for type and size before processing.|
|**N9**|Access separation|Interviewer and candidate capabilities must be separated. A<br>candidate must not be able to access scoring, ranking or<br>assessment data.|
|**N10**|Transport security|Where media streams and APIs are exposed, use secure transport.<br>Document any local-development exceptions.|
|**N11**|Dependency hygiene|Pin dependency versions. Avoid unmaintained or unnecessary<br>packages.|
|**N12**|Error disclosure|Error responses must not leak stack traces, file paths, internal<br>configuration or prompt content to the client.|



7.3 Candidate Data Privacy 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 18 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

**This section is mandatory and will be assessed.** CVs and interview recordings contain personal data — names, contact details, addresses, employment history, education records, voice and facial imagery. Trainees are expected to handle this data responsibly, exactly as they would in a production hiring system. 

|**#**|**Requirement**|**Expectation**|
|---|---|---|
|**N13**|Use mock or anonymised<br>data|Use only the 20 provided sample CVs, or synthetic data you create.<br>Never use real CVs belonging to real individuals who have not<br>consented.|
|**N14**|No personal data in the<br>repository|Do not commit CVs, recordings, transcripts, screenshots containing<br>personal details, or database dumps. Add these paths to .gitignore.|
|**N15**|Anonymise demonstration<br>material|Redact or replace identifying details in screenshots, README<br>examples, presentation slides and logs.|
|||Store only what the feature genuinely requires. Do not retain raw|
|**N16**|Data minimisation|audio or video beyond what is needed to produce the transcript,<br>unless justified.|
|||If implementing F7 (facial or voice identification), treat biometric|
|**N17**|Biometric caution|data as the most sensitive category. Make consent explicit in the<br>flow and state clearly in the README how the data is stored and<br>for how long.|
|**N18**|Third-party disclosure|Document in the README which external services receive<br>candidate data (LLM providers, transcription APIs) and what is<br>transmitted to each.|
|**N19**|Deletion capability|Provide a means of deleting a candidate and their associated data.<br>A documented administrative endpoint or script is sufficient.|
|**N20**|Fairness awareness|Scoring must be based on job-relevant criteria only. Do not use,<br>infer or store protected characteristics such as age, gender,<br>ethnicity, nationality, religion or marital status as scoring inputs.<br>Note any fairness limitations of your approach in the README.|



## 7.4 Reliability, Maintainability & Usability 

|**#**|**Requirement**|**Expectation**|
|---|---|---|
|**N21**|Reproducibility|The application must start reliably on a clean machine using only<br>the documented Docker commands.|
|**N22**|Observability|Implement structured logging for key operations and failures. Logs<br>must not contain personal data or secrets.|
|**N23**|Code quality|Consistent structure, meaningful naming, separation of concerns,<br>and no large blocks of commented-out or dead code.|
|**N24**|Documentation|README covering purpose, architecture, setup, configuration,<br>usage and known limitations. FastAPI endpoints documented via|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 19 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

|**#**|**Requirement**|**Expectation**|
|---|---|---|
|||OpenAPI.|
|**N25**|Usability|The interface must be navigable without verbal explanation. Long-<br>running operations must show progress. Errors must be<br>understandable to a non-technical user.|
|**N26**|Data persistence|Candidate records, scores, transcripts and assessments must<br>survive an application restart.|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 20 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# 8. Technical Requirements & Constraints 

## 8.1 Mandatory Technology Stack 

The following are non-negotiable. Deviation requires written approval from a trainer during Phase 1 and must be recorded in the clarification document. 

|**Layer**|**Mandated**<br>**Technology**|**Requirement**|
|---|---|---|
|**Backend language**|Python|All backend and AI logic must be written in Python. A recent<br>stable version (3.10 or later) is recommended.|
|**Agent /**<br>**orchestration**|LangGraph|LangGraph is the preferred and expected framework for<br>agent implementation and orchestration. Multi-step<br>reasoning workflows should be modelled as explicit graphs<br>with defined state, nodes and transitions — not as a chain<br>of ad-hoc prompt calls.|
|**API framework**|FastAPI|All backend services must be exposed through FastAPI, with<br>Pydantic models for request and response validation and<br>automatic OpenAPI documentation.|
|**Containerisation**|Docker|The complete application must be containerised. Multi-<br>service setups must be orchestrated with Docker Compose.|
|**Source control**|GitHub|The project must be submitted as a GitHub repository with<br>a complete, incremental commit history.|
|**Frontend**|Trainee's choice|Any framework or approach may be used. The choice must<br>be justified in the README and in the presentation.|



## 8.2 LangGraph Usage Expectations 

LangGraph is mandated because the problem is genuinely multi-stage and stateful. Trainers will specifically assess whether it has been used meaningfully. 

- Model reasoning workflows as graphs with clearly defined state, nodes and edges. 

- Use it where it adds value — CV analysis pipelines, interview response evaluation, consolidated assessment generation. 

- Maintain explicit state across steps rather than rebuilding context from scratch on each call. 

- Implement error handling and retry paths within the graph. 

- Be prepared to explain your graph topology, why each node exists, and what state flows between them. 

_Wrapping a single LLM call in a one-node graph to satisfy the requirement on paper will be identified and will not be credited._ 

## 8.3 Dockerisation Requirements 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 21 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

|**#**|**Requirement**|**Detail**|
|---|---|---|
|**D1**|Complete containerisation|Backend, frontend and any supporting services (database, cache,<br>vector store) must run in containers.|
|**D2**|Single-command startup|The reviewer must be able to bring the full application up with one<br>documented command.|
|**D3**|Compose orchestration|Use Docker Compose to define services, networks, volumes and<br>dependencies.|
|**D4**|Environment configuration|All configuration via environment variables. Ship a .env.example;<br>never ship a populated .env.|
|**D5**|Persistent volumes|Use named volumes so that data survives container restarts.|
|**D6**|Clean-machine verification|Before submission, verify startup on a machine with no prior<br>project artefacts or cached local dependencies.|
|**D7**|Image discipline|Use appropriate base images and a .dockerignore. Avoid<br>unnecessarily large images.|
|**D8**|Documented commands|The README must list every command required to build, run, stop<br>and reset the application.|



## 8.4 GitHub Repository Requirements 

|**#**|**Requirement**|**Detail**|
|---|---|---|
|**G1**|Repository access|A GitHub repository shared with the trainer team before the<br>submission deadline.|
|**G2**|README completeness|Project name, positioning statement, feature list (Core, Stretch<br>attempted, Innovation), architecture overview, technology stack<br>with justification, prerequisites, setup and run instructions,<br>configuration reference, usage walkthrough, privacy notes, and<br>known limitations.|
|**G3**|Commit history|Incremental, meaningful commits made throughout the 17<br>development days. A single bulk commit at the end is a significant<br>negative signal.|
|**G4**|Commit messages|Descriptive and specific. "Implement speaker diarisation for<br>transcript segmentation" — not "update", "fix" or "wip".|
|**G5**|Branching|A sensible branching approach is encouraged. Keep the default<br>branch in a working state.|
|**G6**|Repository hygiene|A proper .gitignore. No secrets, no candidate data, no virtual<br>environments, no build artefacts, no IDE configuration.|
|**G7**|Project documentation|The clarification document, WBS and innovation-feature rationale<br>must be committed to the repository, ideally under a /docs|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 22 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

|**#**|**Requirement**|**Detail**|
|---|---|---|
|||directory.|
|**G8**|Final tag|Tag the final submission commit (for example, v1.0-final) so the<br>evaluated state is unambiguous.|



## 8.5 Sample Data Provision 

**Twenty sample CVs will be provided** for development, testing and demonstration purposes. 

- The sample set is representative of realistic input, including varied formats, layouts and levels of completeness. 

- All demonstrations during the final presentation must use this sample set unless otherwise agreed. 

- Trainees may create additional synthetic CVs to test edge cases; these should be committed under a clearly marked test-data directory. 

- The provided CVs must not be committed to a public repository. Follow requirement N14. 

## 8.6 Recommended but Optional 

The following are suggestions, not requirements. Trainees are free to choose alternatives. 

- Relational or document database for candidate, session and assessment persistence. 

- Vector store for semantic CV and requirement matching. 

- WebRTC-based approach for the video interview interface. 

- A managed or self-hosted speech-to-text service for transcription and diarisation. 

- Background task handling for long-running AI operations. 

- Automated tests for core business logic. 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 23 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# 9. Project Phases & Timeline 

The assignment runs for 20 working days across two phases. The day-wise plan below is indicative and represents the trainer's expected pacing. Trainees are expected to produce their own detailed plan in Phase 1 and may adjust sequencing — but the phase boundaries and the final submission date are fixed. 

## 9.1 Phase Summary 

|**Phase**|**Title**|**Duration**|**Primary Outcome**|
|---|---|---|---|
|**Phase 1**|Requirement Understanding,<br>Clarification & WBS Preparation|Days 1–3|Approved clarification document,<br>proposed project name and a<br>detailed Work Breakdown Structure.|
|**Phase 2**|Core Development, Submission &<br>Presentation|Days 4–20|Working Dockerised application,<br>GitHub repository, final submission<br>and presentation.|



## 9.2 Phase 1 — Detailed Plan (Days 1–3) 

|**Day**|**Focus**|**Key Activities**|**Expected Output**|
|---|---|---|---|
|**Day 1**|Requirement study &<br>domain research|Read this BID end to end. Research the<br>recruitment and interview domain.<br>Identify ambiguous, incomplete or<br>conflicting requirements. Survey<br>candidate technologies for video,<br>transcription and CV parsing. Draft the<br>clarification question list.|Draft clarification<br>questions; initial technology<br>research notes.|
|**Day 2**|Clarification & solution<br>conceptualisation|Raise clarification questions with the<br>trainer. Record answers and any agreed<br>assumptions. Draft the high-level<br>architecture and LangGraph agent<br>design. Finalise the technology stack.<br>Propose the project name and<br>positioning.|Clarification document with<br>trainer responses; high-<br>level architecture; proposed<br>project name and rationale.|
|**Day 3**|Work breakdown &<br>planning|Decompose the scope into work<br>packages and tasks. Estimate effort per<br>task. Sequence the 17 development<br>days. Identify risks, dependencies and<br>mitigations. Initialise the GitHub<br>repository with structure and README<br>skeleton.|Work Breakdown Structure;<br>17-day delivery plan; risk<br>register; initialised<br>repository. Phase 1 gate<br>review.|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 24 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

## 9.3 Phase 2 — Detailed Plan (Days 4–20) 

|**Days**<br>**Days 4–5**|**Focus**<br>Foundation &<br>environment setup|**Key Activities**<br>Repository structure. FastAPI<br>application skeleton with health<br>endpoint. Dockerfile and Docker<br>Compose. Database schema and<br>models. CV upload and parsing<br>pipeline. Base LangGraph graph and<br>state definition.|**Expected Output**<br>Running containerised<br>skeleton; CV ingestion<br>working.|
|---|---|---|---|
|**Days 6–8**|Pre-Interview core (F1,<br>F2)|Job requirement profile definition.<br>Semantic CV-to-requirement<br>matching. Candidate ranking logic.<br>Multi-dimensional scoring with<br>configurable weights. Score<br>justification generation. Screening and<br>ranking UI.|F1 and F2 complete and<br>demonstrable on the 20<br>sample CVs.|
|**Days 9–11**|During-Interview core,<br>part 1 (F3)|Video-chat interface. Session lifecycle<br>management. Real-time audio and<br>video streaming. Continuous audio<br>capture. Session persistence and<br>linkage to candidate and job profile.|F3 complete; a live<br>interview session can be<br>conducted end to end.|
|**Days 12–**<br>**13**|During-Interview core,<br>part 2 (F4)|Speech-to-text integration. Speaker<br>diarisation or channel separation.<br>Timestamped, structured transcript<br>generation. Live transcript display.<br>Transcript persistence and retrieval.|F4 complete; speaker-<br>attributed transcripts<br>produced and stored.|
|**Days 14–**<br>**15**|Post-Interview core (F5,<br>F6)|Question–answer pair segmentation.<br>Response evaluation across relevance,<br>accuracy, completeness and quality.<br>Requirement coverage mapping.<br>Consolidated assessment generation.<br>Report view and export. Candidate<br>comparison.|F5 and F6 complete; all<br>six Core features<br>working end to end.|
|**Days 16–**<br>**17**|Creative / Innovation<br>feature (F11)|Finalise the innovation concept. Write<br>the rationale document. Design,<br>implement and integrate the feature.<br>Test it against the sample data set.|F11 implemented and<br>documented; rationale<br>committed to /docs.|
|**Day 18**|Stretch features &<br>hardening|Attempt one or more stretch features<br>only if all Core features are complete.<br>Otherwise, harden Core: error<br>handling, logging, privacy controls,<br>input validation, UI polish.|Optional F7–F10;<br>hardened, stable<br>application.|
|**Day 19**|Integration, testing &<br>documentation|Full end-to-end testing with all 20<br>sample CVs. Clean-machine Docker|Release candidate;<br>complete|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 25 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

|**Days**|**Focus**|**Key Activities**|**Expected Output**|
|---|---|---|---|
|||verification. README completion.<br>Architecture diagram. Anonymise all<br>demonstration material. Prepare<br>presentation and demo script.|documentation;<br>rehearsed demo.|
|**Day 20**|Final submission &<br>presentation|Final bug fixes and freeze. Tag the<br>release. Submit the repository. Deliver<br>the presentation: problem framing,<br>project name and positioning,<br>architecture walkthrough, live<br>demonstration, innovation feature<br>justification, lessons learned, Q&A.|Final submission;<br>presentation delivered.|



## 9.4 Milestones & Gates 

|**Milestone**|**Description**|**Gate Criteria**|
|---|---|---|
|**M1 — End of**<br>**Day 3**|Phase 1 gate review|Clarification document, project name proposal and<br>WBS submitted and reviewed. Repository<br>initialised.|
|**M2 — End of**<br>**Day 8**|Pre-Interview checkpoint|F1 and F2 demonstrable against the sample CV set.|
|**M3 — End of**<br>**Day 13**|Interview pipeline checkpoint|F3 and F4 demonstrable; a full interview can be<br>conducted and transcribed.|
|**M4 — End of**<br>**Day 15**|Core feature completion|All six Core features working end to end.|
|**M5 — End of**<br>**Day 17**|Innovation feature complete|F11 implemented, integrated and documented<br>with rationale.|
|**M6 — End of**<br>**Day 19**|Release candidate|Clean-machine Docker verification passed;<br>documentation complete.|
|**M7 — Day 20**|Final submission & presentation|Repository tagged and submitted; presentation<br>delivered.|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 26 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# 10. Deliverables 

All deliverables listed below are mandatory unless explicitly marked optional. 

## 10.1 Phase 1 Deliverables (Due End of Day 3) 

|**#**|**Deliverable**|**Description & Acceptance**|
|---|---|---|
|**P1.1**|Proposed project name &<br>positioning|Product name, one-line positioning statement and a two-to-four-<br>sentence rationale. Must be applied consistently thereafter.|
|**P1.2**|Requirement clarification<br>document|A structured list of ambiguities identified, questions raised, trainer<br>responses received, and assumptions adopted where no answer was<br>available. Quality of the questions is assessed, not merely their<br>quantity.|
|**P1.3**|Work Breakdown Structure<br>(WBS)|Hierarchical decomposition to task level with effort estimates,<br>dependencies, sequencing across the 17 development days, and a<br>definition of done per task.|
|**P1.4**|High-level architecture<br>outline|System component diagram, proposed technology stack with<br>justification, and the intended LangGraph agent design.|
|**P1.5**|Risk register|Identified technical and schedule risks with likelihood, impact and<br>mitigation approach.|
|**P1.6**|Initialised GitHub<br>repository|Repository created, structured, shared with trainers, with a README<br>skeleton and a working .gitignore.|



## 10.2 Phase 2 Deliverables (Due End of Day 20) 

|**#**|**Deliverable**|**Description & Acceptance**|
|---|---|---|
|**P2.1**|Working Dockerised<br>application|Complete application running via documented Docker commands,<br>verified on a clean machine, with all six Core features and the<br>Innovation feature functional.|
|**P2.2**|GitHub repository|Final repository with complete source code, incremental commit<br>history, and a tagged final release commit.|
|**P2.3**|README documentation|Complete as specified in requirement G2.|
|**P2.4**|Innovation feature<br>rationale|The 300–500-word rationale document described in requirement C3,<br>committed under /docs.|
|**P2.5**|Updated WBS & plan|The evolved WBS showing actual versus planned progress,<br>committed under /docs.|
|**P2.6**|Architecture<br>documentation|Final architecture diagram and a description of the LangGraph agent<br>design as built.|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 27 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

|**#**|**Deliverable**|**Description & Acceptance**|
|---|---|---|
|**P2.7**|Privacy & data handling<br>note|A short statement covering which external services receive<br>candidate data, what is stored, retention approach and known<br>fairness limitations.|
|**P2.8**|Final presentation|A 20–30 minute session: problem framing, project name and<br>positioning, architecture walkthrough, live demonstration using the<br>20 sample CVs, innovation feature justification, challenges and<br>lessons learned, followed by Q&A.|
|**P2.9**|Presentation deck|Supporting slides, with all demonstration material anonymised.|



## 10.3 Submission Standards 

- All deliverables must be submitted by the end of Day 20. Late submissions attract a penalty at the panel's discretion. 

- Documentation deliverables must be committed to the repository under /docs, not sent separately. 

- The application must run without trainee intervention. "It works on my machine" is not an acceptable outcome. 

- No candidate personal data may be present in the submitted repository. 

- The trainee must be able to explain any part of the submitted codebase on request. 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 28 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# 11. Evaluation Criteria & Weightage 

The submission is scored out of 100 marks, with additional bonus credit available for stretch features. The weighting reflects the programme's priorities: disciplined delivery of the mandatory scope, sound engineering, and demonstrated independent thinking. 

## 11.1 Overall Weightage 

|**#**|**Evaluation Area**|**Weightage**|**What Is Assessed**|
|---|---|---|---|
|**E1**|Phase 1 — Requirement<br>Understanding, Clarification & WBS|10%|Depth of requirement analysis, quality of<br>clarification questions, realism and<br>granularity of the WBS, risk identification<br>and architecture thinking.|
|**E2**|Core Features — Pre-Interview (F1,<br>F2)|15%|CV screening accuracy, semantic matching<br>quality, ranking logic, scoring dimensions,<br>weighting configurability and justification<br>transparency.|
||||Video session stability, audio capture|
|**E3**|Core Features — During-Interview<br>(F3, F4)|15%|reliability, transcription quality, speaker<br>attribution accuracy and transcript<br>structure.|
||||Q&A segmentation, evaluation quality,|
|**E4**|Core Features — Post-Interview (F5,<br>F6)|15%|requirement coverage mapping,<br>consolidation logic and traceability of<br>conclusions to evidence.|
||||Originality, problem relevance, quality of|
|**E5**|Creative / Innovation Feature (F11)|10%|written rationale, prioritisation judgement,<br>implementation quality and integration.|
|**E6**|Proposed Project Name & Product<br>Thinking|5%|Appropriateness and memorability of the<br>name, clarity of positioning, quality of<br>rationale and consistency of application<br>across repository, UI, docs and<br>presentation.|
||||Meaningful LangGraph usage, FastAPI|
|**E7**|Technical Implementation Quality|10%|design, architecture, code quality,<br>separation of concerns and error handling.|
|**E8**|Dockerisation & Repository Quality|8%|Single-command startup, clean-machine<br>reproducibility, Compose configuration,<br>commit history quality, repository hygiene<br>and README completeness.|
|**E9**|Non-Functional Requirements|5%|Performance, security, and in particular<br>candidate data privacy handling and|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 29 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

|**#**|**Evaluation Area**|**Weightage**|**What Is Assessed**|
|---|---|---|---|
||||fairness awareness.|
||||Clarity of communication, quality of live|
|**E10**|Final Presentation & Demonstration|7%|demo, ability to justify decisions and|
||||handle technical questions.|
||**TOTAL**|**100%**||



## 11.2 Bonus Marks — Stretch Features 

Stretch features are credited only when all six Core features are complete and working. Bonus marks are capped at 10 marks in total. 

|**#**|**Stretch Feature**|**Bonus**|**Condition**|
|---|---|---|---|
|**F7**|Candidate Identification & Real-Time Profile<br>Overview|Up to +3|All Core features complete;<br>consent and biometric<br>privacy handled (N17).|
||||All Core features complete;|
|**F8**|CV Claim Verification Through Interview Analysis|Up to +3|flags framed as human<br>follow-up prompts.|
||||All Core features complete;|
|**F9**|Comprehensive Candidate Interview Scoring|Up to +2|per-dimension breakdown<br>provided.|
||||All Core features complete;|
|**F10**|Interview Quality Assessment|Up to +2|actionable<br>recommendations<br>produced.|
||**MAXIMUM BONUS**|**+10**||



## 11.3 Feature-Level Scoring Rubric 

Each feature is assessed against the following scale, applied proportionally within its weighting band. 

|**Rating**|**Band**|**Description**|
|---|---|---|
|**Excellent**|90–100%|Fully functional, robustly handled edge cases, well integrated,<br>clearly explainable, evidence-backed output.|
|**Good**|75–89%|Fully functional for the main path with minor gaps in edge-case<br>handling or transparency.|
|**Satisfactory**|60–74%|Functional but limited — works on happy path only, shallow<br>analysis or weak justification.|
|**Partial**|40–59%|Implemented but unreliable, incomplete or poorly integrated with|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 30 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

|**Rating**|**Band**|**Description**|
|---|---|---|
|||the rest of the platform.|
|**Minimal**|1–39%|Attempted but not working, or present only as a stub or mock.|
|**Not delivered**|0%|Absent from the submission.|



## 11.4 Deductions 

|**Condition**|**Impact**|
|---|---|
|**Application does not start from a clean machine using**<br>**documented commands**|Up to −10 marks|
|**Secrets, credentials or API keys committed to the**<br>**repository**|Up to −8 marks|
|**Candidate personal data committed to the repository**|Up to −8 marks|
|**Single bulk commit or absent commit history**|Up to −5 marks|
|**Stretch features attempted while Core features remain**<br>**incomplete**|Up to −5 marks (scope management)|
|**Innovation feature duplicates or trivially varies a listed**<br>**feature**|Innovation marks (E5) forfeited|
|**Evidence of work not performed by the trainee, or inability**<br>**to explain submitted code**|Referral to the panel; may result in<br>disqualification|
|**Late submission**|At panel discretion|



## 11.5 What Distinguishes a Strong Submission 

- Complete Core delivery over partial breadth — all six mandatory features working beats a scattering of half-built ones. 

- Explainable AI output — every score and flag traceable to evidence rather than emerging from an opaque prompt. 

- Genuine LangGraph usage — stateful, multi-node reasoning the trainee can walk through and defend. 

- Effortless setup — the reviewer runs one command and the application works. 

- Visible thinking — a clarification document and WBS that show the problem was genuinely understood. 

- Independent judgement — an innovation feature that addresses a real gap, with a rationale that convinces. 

- Honest limitations — a README that states clearly what does not work and why, rather than overstating. 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 31 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# 12. Assumptions & Constraints 

## 12.1 Assumptions 

|**#**|**Assumption**|
|---|---|
|**A1**|Trainees have working knowledge of Python, REST API concepts and basic containerisation, and can<br>independently research unfamiliar libraries.|
|**A2**|Trainees have access to a development machine capable of running Docker and a local video<br>session.|
|**A3**|Access to the required AI and speech-to-text services (or approved alternatives) will be available for<br>the duration of the assignment.|
|**A4**|Twenty sample CVs will be provided at the start of Phase 1 and are representative of realistic<br>recruitment input.|
|**A5**|A trainer will be available during Phase 1 to respond to clarification questions within a reasonable<br>turnaround.|
|**A6**|Interviews demonstrated during evaluation will be simulated, using mock candidates and the<br>provided sample data.|
|**A7**|Transcription and analysis are expected in English unless otherwise agreed during Phase 1.|
|**A8**|Imperfect AI output is acceptable and expected. The system is assessed on design, transparency<br>and robustness, not on achieving benchmark-grade model accuracy.|
|**A9**|A single concurrent interview session is sufficient for demonstration purposes.|
|**A10**|Trainees will raise blockers promptly rather than losing days to a problem that a short conversation<br>could resolve.|



## 12.2 Constraints 

|**#**|**Constraint**|**Detail**|
|---|---|---|
|**CN1**|Fixed duration|20 working days total. Phase boundaries and the Day 20 submission<br>date are fixed and will not be extended.|
|**CN2**|Solo delivery|Work must be performed individually. Collaboration between<br>trainees on design or code is not permitted. General discussion of<br>concepts is acceptable; sharing implementations is not.|
|**CN3**|Mandated stack|Python, LangGraph, FastAPI and Docker are non-negotiable without<br>documented trainer approval.|
|**CN4**|Local execution only|The application must run locally via Docker. Cloud deployment is<br>neither required nor credited.|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 32 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

|**#**|**Constraint**|**Detail**|
|---|---|---|
|**CN5**|Sample data only|Development and demonstration must use the provided sample CVs<br>or trainee-generated synthetic data. Real personal data is<br>prohibited.|
|**CN6**|Privacy compliance|All requirements in Section 7.3 are mandatory and assessed.|
|**CN7**|External service<br>dependency|Reliance on third-party AI services introduces cost, rate-limit and<br>availability risk. Trainees must design for failure and document any<br>limits encountered.|
|**CN8**|Scope discipline|Out-of-scope work (Section 4.2) will not be credited and may be<br>penalised as poor prioritisation.|
|**CN9**|Originality|The innovation feature must be the trainee's own. AI coding<br>assistants may be used as tools, but the trainee must fully<br>understand and be able to explain every part of the submission.|
|**CN10**|Demonstrability|Any feature that cannot be demonstrated live during the<br>presentation will be treated as not delivered.|



## 12.3 Known Risks 

|**Risk**|**Likelihood**|**Suggested Mitigation**|
|---|---|---|
|**Real-time video and audio**<br>**pipeline proves harder than**<br>**estimated**|High|Prototype the riskiest component early, during Days 4–5,<br>rather than deferring it to Day 9.|
|**Speaker diarisation accuracy**<br>**is poor**|Medium|Consider separate audio channels per participant instead of<br>relying on diarisation from a mixed stream.|
|**CV parsing fails on non-**<br>**standard layouts**|High|Design for graceful failure from the outset; log and skip<br>rather than aborting the batch.|
|**External AI service rate**<br>**limits or cost caps reached**|Medium|Cache aggressively during development; batch requests;<br>avoid re-running full pipelines unnecessarily.|
|**Over-engineering the first**<br>**feature**|High|Deliver a thin end-to-end slice first, then deepen. Track<br>progress against the WBS daily.|
|**Docker works locally but not**<br>**on a clean machine**|Medium|Verify on a clean environment by Day 19 at the latest, not<br>on Day 20.|



AI Trainee Developer Programme — Final Evaluation Assignment | Page 33 of 34 

Business Information Document | AI-Powered Recruitment & Interview Intelligence Platform 

# 13. AI Usage Guidelines 

This section defines where AI tools may and may not be used during the project. These guidelines apply to both phases and must be followed by every trainee. 

## 13.1 Permitted Use of AI 

Trainees may use AI to support the following activities: 

|**#**|**Activity**|
|---|---|
|**AI1**|Coding|
|**AI2**|UI design|
|**AI3**|Paid LLM or local LLM|
|**AI4**|Speech-to-text|
|**AI5**|Video feed collection|



## 13.2 Activities Without AI Support 

The following activities must be completed by the trainee without any support from AI: 

|**#**|**Activity**|
|---|---|
|**NA1**|Work Breakdown Structure (WBS)|
|**NA2**|Software Requirements Specification (SRS)|
|**NA3**|Workflow diagram|



Wherever AI is used, the trainee remains fully responsible for the output and must be able to understand and explain every part of the submission (see constraint CN9). 

#### **End of Document** 

_This Business Information Document is issued for execution. Questions regarding interpretation should be raised during the Phase 1 clarification window._ 

AI Trainee Developer Programme — Final Evaluation Assignment | Page 34 of 34 

