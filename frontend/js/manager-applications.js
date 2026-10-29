import { api } from "./api.js?v=20261026-3";

const loginPanel = document.querySelector("#manager-login-panel");
const loginForm = document.querySelector("#manager-login-form");
const loginButton = document.querySelector("#manager-login-button");
const loginMessage = document.querySelector("#manager-login-message");
const managerLogoutButton = document.querySelector("#manager-logout-button");
const managerLogoutMessage = document.querySelector("#manager-logout-message");
const managerContent = document.querySelector("#manager-content");
const assistantWidget = document.querySelector("#assistant-widget");
const applicationsMessage = document.querySelector("#applications-message");
const applicationsList = document.querySelector("#manager-applications-list");
const managerJobsMessage = document.querySelector("#manager-jobs-message");
const managerJobsList = document.querySelector("#manager-jobs-list");
let loadInProgress = false;
let interviewersPromise = null;
const IMPORTED_EMAIL_SUFFIX = "@imported.recruito.invalid";
const RESCORE_OUTCOMES = {
  queued_new_version: "A new score version is queued; earlier versions are kept.",
  retrying: "The failed assessment is queued again.",
  unchanged_inputs: "The CV and requirements are unchanged, so the saved score already applies.",
  already_in_progress: "An assessment is already in progress.",
  resume_missing: "No readable CV is attached.",
};

function errorText(error) {
  return typeof error.detail === "string" ? error.detail : error.message;
}

function isImportedApplication(application) {
  return application.interview_scheduling_status === "manual"
    || (application.candidate_email || "").endsWith(IMPORTED_EMAIL_SUFFIX);
}

function schedulingStatusMessage(application) {
  const messages = {
    NO_HIRING_MANAGER_RECIPIENT: "RecruitO could not find a hiring-manager email to notify. Check that an active hiring manager owns this job.",
    JOB_CLOSED_OR_APPLICATION_FINALIZED: "Scheduling stopped because the job closed or the application reached a final status.",
  };
  if (application.interview_scheduled_at) {
    const when = new Intl.DateTimeFormat(undefined, { dateStyle: "medium", timeStyle: "short" })
      .format(new Date(application.interview_scheduled_at));
    return `Interview scheduled for ${when}. The candidate and interviewer have been emailed the details and their join link. Use the form below to reschedule.`;
  }
  if (application.interview_scheduling_status === "manual") {
    return "Batch-imported CV for screening and ranking. There is no candidate account, so RecruitO sends no emails; share the job link if you want this person to apply and interview.";
  }
  if (application.interview_scheduling_status === "manager_notified") {
    return "CV score exceeded 65/100. You were emailed that this candidate is ready to interview — assign a date, time, and interviewer below.";
  }
  if (application.interview_scheduling_status === "not_eligible") {
    return "No interview notification was sent because the CV score is 65/100 or below. The application remains under review; this is not an automatic rejection. You can still schedule an interview below.";
  }
  if (application.interview_scheduling_status === "blocked") {
    return messages[application.interview_scheduling_error_code]
      || "Interview scheduling needs attention. Review the hiring-manager account for this job.";
  }
  if (application.interview_scheduling_status === "cancelled") {
    return "Interview scheduling stopped because the job closed or the application reached a final status.";
  }
  if (["pending", "not_queued"].includes(application.interview_scheduling_status)) {
    return "RecruitO checks interview eligibility after CV scoring. A score above 65/100 emails you to schedule the interview.";
  }
  return "You can assign an interview date, time, and interviewer below.";
}

function loadInterviewers() {
  if (!interviewersPromise) {
    interviewersPromise = api.listInterviewers().catch((error) => {
      interviewersPromise = null;
      throw error;
    });
  }
  return interviewersPromise;
}

function toLocalDatetimeValue(date) {
  const offsetMs = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offsetMs).toISOString().slice(0, 16);
}

function buildInterviewScheduleForm(application) {
  const form = document.createElement("form");
  form.className = "interview-schedule-form";
  const heading = document.createElement("h4");
  heading.textContent = application.interview_scheduled_at ? "Reschedule this interview" : "Schedule an interview";

  const whenLabel = document.createElement("label");
  whenLabel.textContent = "Interview date and time";
  const when = document.createElement("input");
  when.type = "datetime-local";
  when.required = true;
  when.setAttribute("aria-label", `Interview date and time for ${application.candidate_name}`);
  const minMoment = new Date(Date.now() + 60_000);
  when.min = toLocalDatetimeValue(minMoment);
  if (application.interview_scheduled_at) {
    when.value = toLocalDatetimeValue(new Date(application.interview_scheduled_at));
  }
  whenLabel.append(when);

  const interviewerLabel = document.createElement("label");
  interviewerLabel.textContent = "Interviewer";
  const interviewerSelect = document.createElement("select");
  interviewerSelect.required = true;
  interviewerSelect.setAttribute("aria-label", `Interviewer for ${application.candidate_name}`);
  const loadingOption = document.createElement("option");
  loadingOption.value = "";
  loadingOption.textContent = "Loading interviewers…";
  loadingOption.disabled = true;
  loadingOption.selected = true;
  interviewerSelect.append(loadingOption);
  interviewerLabel.append(interviewerSelect);

  const durationLabel = document.createElement("label");
  durationLabel.textContent = "Duration (minutes)";
  const duration = document.createElement("input");
  duration.type = "number";
  duration.min = "15";
  duration.max = "240";
  duration.step = "5";
  duration.required = true;
  duration.value = String(application.interview_duration_minutes || 30);
  duration.setAttribute("aria-label", `Interview duration for ${application.candidate_name}`);
  durationLabel.append(duration);

  const button = document.createElement("button");
  button.className = "button button-primary";
  button.type = "submit";
  button.textContent = application.interview_scheduled_at ? "Save new time and notify" : "Schedule and notify";

  const feedback = document.createElement("p");
  feedback.className = "public-jobs-message";
  feedback.setAttribute("role", "status");

  form.append(heading, whenLabel, interviewerLabel, durationLabel, button, feedback);

  loadInterviewers().then((interviewers) => {
    interviewerSelect.replaceChildren();
    if (!interviewers.length) {
      const none = document.createElement("option");
      none.value = "";
      none.textContent = "No active interviewers — create one first";
      none.disabled = true;
      none.selected = true;
      interviewerSelect.append(none);
      interviewerSelect.disabled = true;
      button.disabled = true;
      return;
    }
    const placeholder = document.createElement("option");
    placeholder.value = "";
    placeholder.textContent = "Choose an interviewer";
    placeholder.disabled = true;
    placeholder.selected = !application.interviewer_id;
    interviewerSelect.append(placeholder);
    for (const interviewer of interviewers) {
      const option = document.createElement("option");
      option.value = String(interviewer.id);
      option.textContent = `${interviewer.full_name} (${interviewer.email})`;
      if (application.interviewer_id === interviewer.id) option.selected = true;
      interviewerSelect.append(option);
    }
  }).catch((error) => {
    loadingOption.textContent = `Could not load interviewers: ${error.message}`;
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    const chosen = new Date(when.value);
    if (Number.isNaN(chosen.getTime()) || chosen.getTime() <= Date.now()) {
      feedback.textContent = "Choose an interview time in the future.";
      return;
    }
    button.disabled = true;
    feedback.textContent = "Saving the interview and queueing emails…";
    try {
      await api.scheduleInterview(application.id, {
        scheduled_at: chosen.toISOString(),
        duration_minutes: Number(duration.value),
        interviewer_id: Number(interviewerSelect.value),
      });
      feedback.textContent = "Interview scheduled. The candidate and interviewer have been emailed.";
      await loadApplications();
    } catch (error) {
      feedback.textContent = errorText(error);
    } finally {
      button.disabled = false;
    }
  });
  return form;
}

function scoreStatusMessage(application) {
  if (application.score_status === "completed") {
    return isImportedApplication(application)
      ? `LangGraph CV assessment: ${application.total_score}/100. Imported CVs are ranked only; no invitation is sent.`
      : `LangGraph CV assessment: ${application.total_score}/100. Scores above 65/100 email the hiring manager to schedule an interview; the hiring manager still makes the final selection.`;
  }
  if (["pending", "processing"].includes(application.score_status)) {
    return "LangGraph is assessing this CV automatically. The score, evidence, and ranking will appear here when processing finishes.";
  }
  if (application.score_status === "failed") {
    const reasons = {
      MISSING_REQUIREMENTS: "This job has no scoring requirements.",
      RESUME_NOT_FOUND: "The uploaded CV could not be found.",
      RESUME_UNREADABLE: "The CV has too little readable text or is in an unsupported format.",
      APPLICATION_INPUTS_CHANGED: "The CV or job requirements changed during scoring.",
      SCORING_ATTEMPTS_EXHAUSTED: "The scoring service could not complete the automatic assessment.",
      SCORING_SERVICE_ERROR: "The scoring service could not complete the automatic assessment.",
      SCORING_OUTPUT_INVALID: "The model's answer repeatedly failed evidence checks, so no score was saved.",
    };
    return `Automatic CV assessment needs attention. ${reasons[application.score_error_code] || "The scoring service could not complete the assessment."} Correct the CV or job requirements if they are wrong; service errors need administrator attention.`;
  }
  if (application.score_status === "not_started" && !application.resume_file_name) {
    return "No CV is attached to this application, so automatic scoring cannot run. The candidate must upload a CV with their application.";
  }
  return "Automatic CV scoring has not started. Check that this job has requirements and refresh.";
}

function renderJobOverviews(jobs, applications) {
  const openJobIds = new Set(
    [...managerJobsList.querySelectorAll("details[open][data-job-id]")]
      .map((details) => details.dataset.jobId),
  );
  if (!jobs.length) {
    managerJobsMessage.textContent = "No jobs are available in this hiring manager account yet.";
    managerJobsList.replaceChildren();
    return;
  }
  managerJobsMessage.textContent = "CV and interview assessments run automatically. Review the evidence, then confirm the final choice; RecruitO emails all applicants and closes the job.";
  const cards = jobs.map((job) => {
    const card = document.createElement("article");
    card.className = "public-job-card manager-job-overview";
    const title = document.createElement("h3");
    title.textContent = job.title;
    const metadata = document.createElement("p");
    metadata.className = "manager-job-metadata";
    const count = applications.filter((application) => application.job_id === job.id).length;
    metadata.textContent = `${job.seniority || "Seniority not specified"} · ${job.status} · ${count} ${count === 1 ? "applicant" : "applicants"}`;
    const details = document.createElement("details");
    details.className = "manager-job-details";
    const summary = document.createElement("summary");
    summary.textContent = "View job profile and ranked applicants";
    const content = document.createElement("div");
    content.className = "manager-job-detail-content";
    details.dataset.jobId = String(job.id);
    const feedback = document.createElement("p");
    feedback.className = "public-jobs-message";
    feedback.setAttribute("role", "status");
    details.append(summary, content);
    details.addEventListener("toggle", async () => {
      if (!details.open || details.dataset.loaded === "true") return;
      feedback.textContent = "Loading job profile and applicant scores…";
      if (!content.contains(feedback)) content.prepend(feedback);
      try {
        const [profile, ranking] = await Promise.all([api.getJob(job.id), api.getJobRanking(job.id)]);
        const profileSection = document.createElement("section");
        const profileHeading = document.createElement("h4");
        profileHeading.textContent = "Job profile";
        const description = document.createElement("p");
        description.className = "public-job-date";
        description.textContent = profile.external_post_url
          ? "The full job description is published on Blogger — open it with the link below. Edit the description from the job editor on the home page."
          : "The full job description is published on Blogger once the job is posted. Edit it from the job editor on the home page.";
        profileSection.append(profileHeading, description);
        if (profile.external_post_url) {
          const externalPost = document.createElement("a");
          externalPost.href = profile.external_post_url;
          externalPost.target = "_blank";
          externalPost.rel = "noopener noreferrer";
          externalPost.textContent = profile.external_post_provider === "blogger"
            ? "Open full description on Blogger"
            : "Open external job post";
          externalPost.className = "public-jobs-team-link";
          profileSection.append(externalPost);
        }
        const requirementsHeading = document.createElement("h4");
        requirementsHeading.textContent = "Scoring requirements";
        const requirements = document.createElement("ul");
        for (const requirement of profile.requirements || []) {
          const item = document.createElement("li");
          item.textContent = `${requirement.text} · ${requirement.kind}, ${requirement.category}, weight ${requirement.weight}/5`;
          requirements.append(item);
        }
        if (!requirements.childElementCount) {
          const item = document.createElement("li");
          item.textContent = "No requirements are set; automatic CV scoring cannot run until they are added.";
          requirements.append(item);
        }
        profileSection.append(requirementsHeading, requirements);

        const rankingHeading = document.createElement("h4");
        rankingHeading.textContent = `Applicants ranked by CV score (${ranking.applications.length})`;
        const rankedList = document.createElement("ol");
        rankedList.className = "manager-ranked-applicants";
        for (const applicant of ranking.applications) {
          const applicationRecord = applications.find((entry) => entry.id === applicant.application_id);
          const item = document.createElement("li");
          const label = document.createElement("span");
          if (applicant.rank) {
            label.textContent = `${applicant.rank}. ${applicant.candidate_name} — ${applicant.total_score}/100`;
          } else if (["pending", "processing"].includes(applicant.status)) {
            label.textContent = `${applicant.candidate_name} — CV scoring in progress`;
          } else if (applicant.status === "failed") {
            label.textContent = `${applicant.candidate_name} — scoring needs attention; open the application to retry`;
          } else if (applicant.status === "not_started" && !applicationRecord?.resume_file_name) {
            label.textContent = `${applicant.candidate_name} — CV missing; upload one to score`;
          } else {
            label.textContent = `${applicant.candidate_name} — score not available`;
          }
          item.append(label);
          if (applicant.status === "completed" && applicant.breakdown) {
            if (applicant.breakdown.overall_comment) {
              const overallComment = document.createElement("p");
              overallComment.className = "manager-score-status";
              overallComment.textContent = applicant.breakdown.overall_comment;
              item.append(overallComment);
            }
            const categories = applicant.breakdown.categories || {};
            for (const [category, result] of Object.entries(categories)) {
              const categoryComment = document.createElement("p");
              categoryComment.className = "manager-score-status";
              const label = category.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
              categoryComment.textContent = `${label}: ${result.score}/100 — ${result.comment}`;
              item.append(categoryComment);
            }
            const evidenceDetails = document.createElement("details");
            evidenceDetails.className = "manager-scoring-options";
            const evidenceSummary = document.createElement("summary");
            evidenceSummary.textContent = "Requirement scores and CV evidence";
            const evidenceList = document.createElement("ul");
            for (const requirement of applicant.breakdown.requirements || []) {
              const evidenceItem = document.createElement("li");
              const score = `${requirement.score}/${requirement.weight}`;
              const quote = requirement.evidence_quote ? ` CV evidence: “${requirement.evidence_quote}”` : " No direct CV quote was found.";
              evidenceItem.textContent = `${requirement.requirement}: ${score}. ${requirement.rationale}${quote}`;
              evidenceList.append(evidenceItem);
            }
            evidenceDetails.append(evidenceSummary, evidenceList);
            item.append(evidenceDetails);
          }
          const applicationLink = document.createElement("a");
          applicationLink.href = `#manager-application-${applicant.application_id}`;
          applicationLink.textContent = "Open application";
          applicationLink.className = "public-jobs-team-link";
          item.append(applicationLink);
          rankedList.append(item);
        }
        if (!ranking.applications.length) {
          const empty = document.createElement("p");
          empty.textContent = "No candidates have applied to this job yet.";
          profileSection.append(empty);
        }
        const sections = [profileSection, rankingHeading, rankedList];
        if (job.status === "approved") {
          sections.push(buildBatchImportPanel(job), buildJobRescorePanel(job));
        }
        if (job.status === "approved" && ranking.applications.length) {
          const finalizationForm = document.createElement("form");
          finalizationForm.className = "interview-schedule-form";
          const finalizationHeading = document.createElement("h4");
          finalizationHeading.textContent = "Finalize this job’s selection";
          const guidance = document.createElement("p");
          guidance.textContent = "Choose the candidate after reviewing their application and interview evidence. CV scores are supporting information; they do not choose for you. RecruitO will mark the other applicants not selected, email everyone, and close this job.";
          const candidateLabel = document.createElement("label");
          candidateLabel.textContent = "Candidate selected by the hiring team";
          const candidateSelect = document.createElement("select");
          candidateSelect.required = true;
          candidateSelect.setAttribute("aria-label", `Final candidate for ${job.title}`);
          const placeholder = document.createElement("option");
          placeholder.value = "";
          placeholder.textContent = "Choose a candidate after review";
          placeholder.disabled = true;
          placeholder.selected = true;
          candidateSelect.append(placeholder);
          for (const applicant of ranking.applications) {
            const option = document.createElement("option");
            option.value = String(applicant.application_id);
            option.textContent = applicant.rank
              ? `${applicant.rank}. ${applicant.candidate_name} — CV score ${applicant.total_score}/100`
              : `${applicant.candidate_name} — score pending or unavailable`;
            candidateSelect.append(option);
          }
          const reason = document.createElement("textarea");
          reason.minLength = 10;
          reason.maxLength = 1000;
          reason.required = true;
          reason.placeholder = "Record the human decision rationale (at least 10 characters)";
          const finalizeButton = document.createElement("button");
          finalizeButton.className = "button button-primary";
          finalizeButton.type = "submit";
          finalizeButton.textContent = "Confirm final choice and notify applicants";
          const resultMessage = document.createElement("p");
          resultMessage.className = "public-jobs-message";
          resultMessage.setAttribute("role", "status");
          finalizationForm.append(finalizationHeading, guidance, candidateLabel, candidateSelect, reason, finalizeButton, resultMessage);
          finalizationForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            if (!finalizationForm.reportValidity()) return;
            const selectedName = candidateSelect.selectedOptions[0]?.textContent || "this candidate";
            if (!window.confirm(`Confirm ${selectedName} as the final selection? RecruitO will email all applicants and close this job.`)) return;
            finalizeButton.disabled = true;
            resultMessage.textContent = "Saving the decision and queueing outcome emails…";
            try {
              const result = await api.finalizeJobSelection(job.id, {
                application_id: Number(candidateSelect.value),
                reason: reason.value.trim(),
              });
              resultMessage.textContent = `Selection recorded. Outcome emails queued for ${result.outcome_emails_queued} applicant(s).`;
              await loadApplications();
            } catch (error) {
              resultMessage.textContent = error.message;
            } finally {
              finalizeButton.disabled = false;
            }
          });
          sections.push(finalizationForm);
        } else if (job.status === "filled") {
          const finalizedMessage = document.createElement("p");
          finalizedMessage.className = "public-jobs-message";
          finalizedMessage.textContent = "Final selection recorded. Applicants have been notified and this job is closed.";
          sections.push(finalizedMessage);
        }
        content.replaceChildren(...sections);
        details.dataset.loaded = "true";
      } catch (error) {
        feedback.textContent = `Could not load this job’s profile or ranking: ${error.message}`;
      }
    });
    card.append(title, metadata, details);
    return card;
  });
  managerJobsList.replaceChildren(...cards);
  for (const details of managerJobsList.querySelectorAll("details[data-job-id]")) {
    if (openJobIds.has(details.dataset.jobId)) details.open = true;
  }
}

function buildBatchImportPanel(job) {
  const panel = document.createElement("details");
  panel.className = "manager-scoring-options";
  const summary = document.createElement("summary");
  summary.textContent = "Import a batch of CVs for screening";
  const guidance = document.createElement("p");
  guidance.textContent = "Select any number of PDF or DOCX CVs — they are processed in batches of 10, so large uploads stay reliable. Each CV is scored and ranked against this job's requirements. RecruitO reads each CV's name, email and phone and creates a candidate account. No email is sent at upload; a candidate is emailed a set-password invite only when you schedule their interview. A CV with no readable email is still scored.";
  const form = document.createElement("form");
  const files = document.createElement("input");
  files.type = "file";
  files.multiple = true;
  files.required = true;
  files.accept = ".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  files.setAttribute("aria-label", `CVs to import for ${job.title}`);
  const button = document.createElement("button");
  button.className = "button button-secondary";
  button.type = "submit";
  button.textContent = "Import and score CVs";
  const result = document.createElement("p");
  result.className = "public-jobs-message";
  result.setAttribute("role", "status");
  form.append(files, button);
  const CHUNK_SIZE = 10;
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const selected = Array.from(files.files);
    if (!selected.length) return;
    button.disabled = true;
    const totals = { queued: 0, duplicates: 0, rejected: 0, accounts_created: 0, no_email: 0 };
    const problems = [];
    try {
      // Upload in small batches so one huge request never stalls or times out;
      // each batch of 10 is scored before the next is sent.
      for (let start = 0; start < selected.length; start += CHUNK_SIZE) {
        const chunk = selected.slice(start, start + CHUNK_SIZE);
        result.textContent = `Processing ${start + 1}–${start + chunk.length} of ${selected.length} CV(s)…`;
        const response = await api.importJobResumes(job.id, chunk);
        totals.queued += response.queued || 0;
        totals.duplicates += response.duplicates || 0;
        totals.rejected += response.rejected || 0;
        totals.accounts_created += response.accounts_created || 0;
        totals.no_email += response.no_email || 0;
        for (const entry of response.results) {
          if (entry.status !== "queued") problems.push(`${entry.file_name}: ${entry.error}`);
        }
      }
      // The reload rebuilds this panel, so the outcome goes to the section status line.
      await loadApplications();
      managerJobsMessage.textContent = `${job.title}: ${totals.queued} CV(s) queued for scoring, ${totals.duplicates} already imported, ${totals.rejected} rejected.`
        + (totals.accounts_created ? ` ${totals.accounts_created} candidate account(s) created; each gets a set-password invite when you schedule their interview.` : "")
        + (totals.no_email ? ` ${totals.no_email} had no readable email.` : "")
        + (problems.length ? ` ${problems.join("; ")}.` : "")
        + " Scores appear in the ranking as they finish; use Refresh to update it.";
    } catch (error) {
      result.textContent = errorText(error) + " Some CVs may not have been processed — re-upload the remaining files.";
    } finally {
      button.disabled = false;
    }
  });
  panel.append(summary, guidance, form, result);
  return panel;
}

function buildJobRescorePanel(job) {
  const panel = document.createElement("details");
  panel.className = "manager-scoring-options";
  const summary = document.createElement("summary");
  summary.textContent = "Rescore all applicants";
  const guidance = document.createElement("p");
  guidance.textContent = "Use this after editing the job's requirements. Scores are never edited by hand; a rescore adds a new version and keeps the earlier ones. Unchanged inputs keep their saved score.";
  const form = document.createElement("form");
  const reason = document.createElement("textarea");
  reason.minLength = 10;
  reason.maxLength = 1000;
  reason.required = true;
  reason.placeholder = "Reason for rescoring (at least 10 characters)";
  const button = document.createElement("button");
  button.className = "button button-secondary";
  button.type = "submit";
  button.textContent = "Rescore applicants";
  const result = document.createElement("p");
  result.className = "public-jobs-message";
  result.setAttribute("role", "status");

  const progress = document.createElement("div");
  progress.className = "rescore-progress";
  progress.hidden = true;
  const progressLabel = document.createElement("p");
  progressLabel.className = "rescore-progress-label";
  progressLabel.setAttribute("role", "status");
  progressLabel.setAttribute("aria-live", "polite");
  const bar = document.createElement("div");
  bar.className = "rescore-progress-track";
  bar.setAttribute("role", "progressbar");
  bar.setAttribute("aria-valuemin", "0");
  bar.setAttribute("aria-valuemax", "100");
  const fill = document.createElement("div");
  fill.className = "rescore-progress-fill";
  bar.append(fill);
  progress.append(progressLabel, bar);

  form.append(reason, button);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    button.disabled = true;
    result.textContent = "Queueing rescoring…";
    try {
      const response = await api.rescoreJobApplications(job.id, reason.value.trim());
      const counts = {};
      for (const item of response.results) counts[item.outcome] = (counts[item.outcome] || 0) + 1;
      const summaryText = Object.entries(counts)
        .map(([outcome, count]) => `${count} applicant(s): ${RESCORE_OUTCOMES[outcome] || outcome}`)
        .join(" ") || "There are no applicants to rescore.";
      result.textContent = summaryText;
      await pollRescoreProgress(job, { progress, progressLabel, bar, fill });
      await loadApplications();
      managerJobsMessage.textContent = `${job.title} rescore complete. ${summaryText}`;
    } catch (error) {
      result.textContent = errorText(error);
    } finally {
      button.disabled = false;
    }
  });
  panel.append(summary, guidance, form, result, progress);
  return panel;
}

async function pollRescoreProgress(job, els) {
  const { progress, progressLabel, bar, fill } = els;
  const deadline = Date.now() + 10 * 60 * 1000; // give up after 10 minutes
  const render = (done, total) => {
    const pct = total ? Math.round((done / total) * 100) : 100;
    progress.hidden = false;
    fill.style.width = `${pct}%`;
    bar.setAttribute("aria-valuenow", String(pct));
    progressLabel.textContent = total
      ? `Scored ${done} of ${total} applicants (${pct}%).`
      : "There are no applicants to score.";
  };
  while (Date.now() < deadline) {
    let p;
    try {
      p = await api.getRescoreProgress(job.id);
    } catch {
      break; // stop polling on error; the ranking still refreshes below
    }
    render(p.done, p.total);
    if (p.total === 0 || p.remaining === 0) {
      progressLabel.textContent = p.total
        ? `Done — all ${p.total} applicants scored.`
        : "There are no applicants to score.";
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 2000));
  }
  progressLabel.textContent += " Still finishing in the background; use Refresh to see the latest.";
}

function applicationStatusLabel(value) {
  const labels = {
    submitted: "Under review",
    "selected for interview": "Interview stage",
    "interview scheduled": "Interview scheduled",
    "interview completed": "Awaiting decision",
    selected: "Selected",
    "not selected": "Not selected",
    "decision available": "Decision available",
    withdrawn: "Withdrawn by candidate",
  };
  return labels[value] || value;
}

function renderApplications(applications) {
  if (applications.length === 0) {
    applicationsMessage.textContent = "No applications have been submitted yet.";
    applicationsList.replaceChildren();
    return;
  }

  applicationsMessage.textContent = "When a CV scores above 65/100, RecruitO emails you to schedule. Open an application to assign a date, time, and interviewer; RecruitO then emails the candidate and interviewer.";
  const cards = applications.map((application) => {
    const card = document.createElement("article");
    card.className = "public-job-card manager-application-card";
    card.id = `manager-application-${application.id}`;

    const title = document.createElement("h3");
    title.textContent = application.candidate_name;

    const contact = document.createElement("p");
    contact.textContent = isImportedApplication(application)
      ? `Imported CV · ${application.resume_file_name || "no file name"} · no candidate account`
      : application.candidate_email;

    const details = document.createElement("p");
    const education = [application.education_qualification, application.department, application.institution_name]
      .filter(Boolean)
      .join(" · ");
    details.textContent = [application.candidate_phone, education, application.graduation_year]
      .filter(Boolean)
      .join(" · ");

    const role = document.createElement("p");
    role.textContent = `Role: ${application.job_title}`;

    const status = document.createElement("p");
    status.className = "candidate-application-status";
    status.textContent = `Application status: ${applicationStatusLabel(application.status)}`;
    const analysisStatus = document.createElement("p");
    analysisStatus.className = "manager-score-status";
    const analysisStatusText = {
      not_started: "Interview assessment: waiting for the interview to finish",
      pending: "Interview assessment: queued automatically",
      processing: "Interview assessment: processing transcript and evidence",
      completed: "Interview assessment: ready for your review",
      failed: `Interview assessment: needs attention${application.interview_analysis_error_code ? ` (${application.interview_analysis_error_code})` : ""}`,
    };
    analysisStatus.textContent = analysisStatusText[application.interview_analysis_status] || "Interview assessment: status unavailable";
    const schedulingStatus = document.createElement("p");
    schedulingStatus.className = "manager-score-status";
    schedulingStatus.textContent = schedulingStatusMessage(application);

    const applied = document.createElement("small");
    applied.className = "public-job-date";
    applied.textContent = `Applied ${new Intl.DateTimeFormat(undefined, {
      dateStyle: "medium",
    }).format(new Date(application.applied_at))}`;

    const assessmentActions = document.createElement("div");
    assessmentActions.className = "manager-assessment-actions";
    const scoreSummary = document.createElement("p");
    scoreSummary.className = "manager-score-status";
    scoreSummary.textContent = scoreStatusMessage(application);
    const assessmentResult = document.createElement("p");
    assessmentResult.className = "public-jobs-message";
    assessmentActions.append(scoreSummary, assessmentResult);

    const rescoreForm = document.createElement("form");
    rescoreForm.className = "interview-schedule-form";
    const rescoreReason = document.createElement("textarea");
    rescoreReason.minLength = 10;
    rescoreReason.maxLength = 1000;
    rescoreReason.required = true;
    rescoreReason.placeholder = "Reason for rescoring this CV (at least 10 characters)";
    const rescoreButton = document.createElement("button");
    rescoreButton.className = "button button-secondary";
    rescoreButton.type = "submit";
    rescoreButton.textContent = "Rescore against current requirements";
    rescoreForm.append(rescoreReason, rescoreButton);
    rescoreForm.hidden = !application.resume_file_name;
    rescoreForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!rescoreForm.reportValidity()) return;
      rescoreButton.disabled = true;
      assessmentResult.textContent = "Queueing a rescore…";
      try {
        const result = await api.rescoreApplication(application.id, rescoreReason.value.trim());
        await loadApplications();
        applicationsMessage.textContent = `${application.candidate_name}: ${RESCORE_OUTCOMES[result.outcome] || `rescore status ${result.score_status}.`}`;
      } catch (error) {
        assessmentResult.textContent = errorText(error);
      } finally {
        rescoreButton.disabled = false;
      }
    });

    const statusForm = document.createElement("form");
    statusForm.className = "interview-schedule-form";
    const statusLabel = document.createElement("label");
    statusLabel.textContent = "Candidate-facing status";
    const statusSelect = document.createElement("select");
    for (const value of ["under review", "interview stage", "not selected", "interview scheduled", "awaiting decision", "decision available"]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
      statusSelect.append(option);
    }
    const currentStatus = {
      submitted: "under review",
      "selected for interview": "interview stage",
      "not selected": "not selected",
      "interview scheduled": "interview scheduled",
      "interview completed": "awaiting decision",
      "decision available": "decision available",
    }[application.status] || "under review";
    statusSelect.value = currentStatus;
    statusSelect.setAttribute("aria-label", `Candidate-facing status for ${application.candidate_name}`);
    const reason = document.createElement("textarea");
    reason.minLength = 10;
    reason.maxLength = 1000;
    reason.required = true;
    reason.placeholder = "Reason for the status change (at least 10 characters)";
    const changeButton = document.createElement("button");
    changeButton.className = "button button-secondary";
    changeButton.type = "submit";
    changeButton.textContent = "Update status and notify candidate";
    const statusFeedback = document.createElement("p");
    statusFeedback.className = "public-jobs-message";
    statusForm.append(statusLabel, statusSelect, reason, changeButton, statusFeedback);
    if (["selected", "not selected", "withdrawn"].includes(application.status)) {
      statusForm.hidden = true;
    }
    statusForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      changeButton.disabled = true;
      try {
        await api.changeApplicationStatus(application.id, { status: statusSelect.value, reason: reason.value.trim() });
        statusFeedback.textContent = "Status updated and candidate email queued.";
        await loadApplications();
      } catch (error) {
        statusFeedback.textContent = error.message;
      } finally {
        changeButton.disabled = false;
      }
    });

    card.append(title, contact, details, role, status, schedulingStatus, analysisStatus, applied, assessmentActions, rescoreForm, statusForm);
    const interviewIsFinished = application.interview_status === "completed";
    const canSchedule = !isImportedApplication(application)
      && !["selected", "not selected", "withdrawn"].includes(application.status)
      && !interviewIsFinished;
    if (canSchedule) {
      card.append(buildInterviewScheduleForm(application));
    }
    const assessmentLink = document.createElement("a");
    assessmentLink.className = "button button-secondary";
    assessmentLink.href = `./assessment.html?application_id=${encodeURIComponent(application.id)}`;
    assessmentLink.textContent = "Open consolidated assessment";
    card.append(assessmentLink);
    const comparisonLink = document.createElement("a");
    comparisonLink.className = "button button-secondary";
    comparisonLink.href = `./assessment-comparison.html?job_id=${encodeURIComponent(application.job_id)}`;
    comparisonLink.textContent = "Compare job assessments";
    card.append(comparisonLink);
    if (application.resume_file_name) {
      const resume = document.createElement("a");
      resume.href = api.applicationResumeUrl(application.id);
      resume.textContent = `Download resume · ${application.resume_file_name}`;
      resume.target = "_blank";
      resume.rel = "noopener noreferrer";
      resume.className = "public-jobs-team-link";
      card.append(resume);
    }
    const interviewEnd = application.interview_scheduled_at
      ? Date.parse(application.interview_scheduled_at) + Number(application.interview_duration_minutes || 0) * 60_000
      : Number.NaN;
    const actualInterviewEnd = application.interview_ended_at
      ? Date.parse(application.interview_ended_at)
      : interviewEnd;
    const interviewIsPast = Number.isFinite(actualInterviewEnd) && actualInterviewEnd <= Date.now();
    if (application.interview_id && interviewIsPast) {
      const removeInterview = document.createElement("button");
      removeInterview.className = "button button-secondary";
      removeInterview.type = "button";
      removeInterview.textContent = "Remove past interview";
      removeInterview.addEventListener("click", async () => {
        const confirmed = window.confirm(
          "Remove this past interview from the hiring manager dashboard? The interview transcript, evaluation, and audit history will be retained."
        );
        if (!confirmed) return;
        removeInterview.disabled = true;
        statusFeedback.textContent = "Removing the past interview from this dashboard…";
        try {
          await api.removePastInterview(application.interview_id);
          await loadApplications();
        } catch (error) {
          statusFeedback.textContent = `Could not remove the interview: ${error.message}`;
          removeInterview.disabled = false;
        }
      });
      card.append(removeInterview);
    }
    return card;
  });
  applicationsList.replaceChildren(...cards);
}

async function loadApplications() {
  if (loadInProgress) return;
  loadInProgress = true;
  applicationsMessage.textContent = "Loading applications…";
  managerJobsMessage.textContent = "Loading jobs and applicant rankings…";
  try {
    const [jobs, applications] = await Promise.all([
      api.listJobs(),
      api.listApplications(),
    ]);
    renderJobOverviews(jobs, applications);
    renderApplications(applications);
  } catch (error) {
    applicationsMessage.textContent = error.message;
    managerJobsMessage.textContent = `Could not load jobs or applications: ${error.message}`;
  } finally {
    loadInProgress = false;
  }
}

async function showManager(user) {
  loginPanel.hidden = true;
  managerContent.hidden = false;
  managerLogoutButton.hidden = false;
  if (assistantWidget) assistantWidget.hidden = false;
  await loadApplications();
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  loginButton.disabled = true;
  loginMessage.textContent = "Signing in…";
  try {
    const user = await api.login(
      loginForm.elements.email.value.trim(),
      loginForm.elements.password.value,
    );
    if (user.role !== "hiring_manager") {
      await api.logout();
      throw new Error("This page is for hiring managers.");
    }
    loginForm.elements.password.value = "";
    await showManager(user);
  } catch (error) {
    loginMessage.textContent = error.message;
  } finally {
    loginButton.disabled = false;
  }
});

document.querySelector("#refresh-applications").addEventListener("click", loadApplications);
managerLogoutButton.addEventListener("click", async () => {
  managerLogoutButton.disabled = true;
  managerLogoutButton.textContent = "Signing out…";
  managerLogoutMessage.textContent = "Signing out…";
  try {
    await api.logout();
    window.location.replace(`./index.html?logged_out=${Date.now()}`);
  } catch (error) {
    managerLogoutButton.disabled = false;
    managerLogoutButton.textContent = "Sign out";
    managerLogoutMessage.textContent = `Could not sign out: ${error.message}`;
  }
});

async function restoreManagerSession() {
  try {
    const user = await api.getManagerProfile();
    if (user.role === "hiring_manager") {
      await showManager(user);
    }
  } catch {
    // Keep the sign-in form visible when there is no valid manager session.
  }
}

restoreManagerSession();

function refreshManagerDashboardWhenSafe() {
  if (managerContent.hidden || document.visibilityState !== "visible" || loadInProgress) return;
  const active = document.activeElement;
  const applicationsAreBeingEdited = active instanceof HTMLElement
    && (applicationsList.contains(active) || managerJobsList.contains(active))
    && active.matches("input:not([type=button]):not([type=submit]), textarea, select");
  if (applicationsAreBeingEdited) return;
  loadApplications();
}

window.setInterval(refreshManagerDashboardWhenSafe, 30_000);
window.addEventListener("focus", refreshManagerDashboardWhenSafe);
document.addEventListener("visibilitychange", refreshManagerDashboardWhenSafe);
