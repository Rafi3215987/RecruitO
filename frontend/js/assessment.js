import { api } from "./api.js";

const status = document.querySelector("#assessment-status");
const root = document.querySelector("#assessment-report");
const applicationId = new URLSearchParams(location.search).get("application_id");

function textElement(tag, text, className = "") {
  const element = document.createElement(tag);
  element.textContent = text ?? "";
  if (className) element.className = className;
  return element;
}

function renderList(title, values, renderValue) {
  const section = document.createElement("section");
  section.append(textElement("h2", title));
  const list = document.createElement("ul");
  if (!values?.length) list.append(textElement("li", "No recorded evidence."));
  else values.forEach((value) => list.append(textElement("li", renderValue(value))));
  section.append(list);
  return section;
}

try {
  if (!applicationId) throw new Error("An application ID is required.");
  const report = await api.getAssessment(applicationId);
  const content = [
    textElement("p", "CONFIDENTIAL · HUMAN REVIEW REQUIRED", "eyebrow"),
    textElement("h1", `${report.candidate_name} — ${report.job_title}`),
    textElement("p", report.overall_position, "assessment-position"),
    textElement("p", report.cv_assessment
      ? `CV score: ${report.cv_assessment.score}/100 · Current CV-only rank: ${report.cv_assessment.rank}`
      : "CV scoring has not been completed."),
    renderList("Strengths with CV evidence", report.strengths, (item) => `${item.requirement}: “${item.evidence}”`),
    renderList("Weaknesses and interview flags", report.weaknesses, (item) => `${item.requirement}: ${item.evidence}${item.segment_ids?.length ? ` (transcript segment IDs: ${item.segment_ids.join(", ")})` : ""}`),
    renderList("Evidence gaps", report.evidence_gaps, (item) => `${item.requirement ?? item.text} (not explored in the interview)`),
    renderList("Areas to verify with a human", report.areas_to_verify, (item) => `${item.requirement}: ${item.reason}`),
  ];
  if (report.cv_assessment) {
    const components = report.cv_assessment.components || {};
    const categories = Object.entries(components.categories || {});
    content.push(renderList("CV category scores", categories, ([name, item]) =>
      `${name}: ${item.score}/100 (${item.earned_points}/${item.available_points} points). ${item.comment || ""}`));
    content.push(renderList("CV requirement evidence", components.requirements || [], (item) =>
      `${item.status.replaceAll("_", " ")} · ${item.requirement} · ${item.score}/${item.weight} points. `
      + `${item.evidence_quote ? `CV evidence: “${item.evidence_quote}”. ` : "No direct CV quote recorded. "}`
      + `${item.rationale || ""}`));
  }
  if (report.interview_assessment) {
    const metrics = Object.entries(report.interview_assessment.component_averages)
      .map(([name, score]) => `${name}: ${score ?? "not scored"}/5`).join(" · ");
    content.push(textElement("p", `Interview evidence averages: ${metrics}`));
    content.push(renderList("Interview question-and-answer evidence", report.interview_assessment.evidence || [], (item) => {
      const scores = ["relevance", "accuracy", "completeness", "articulation"]
        .map((name) => `${name} ${item[name] ?? "not scored"}/5`).join(", ");
      const requirements = item.requirement_names?.length ? item.requirement_names.join("; ") : "No requirement mapping recorded";
      return `Question segment(s) ${item.question_segment_ids.join(", ")}; answer segment(s) ${item.answer_segment_ids.join(", ")}. `
        + `Requirements: ${requirements}. Scores: ${scores}. ${item.summary}`;
    }));
    const extended = report.interview_assessment;
    content.push(textElement("p", `F9 evidence-backed interview score: ${extended.f9_weighted_total_out_of_100 ?? "not available"}/100`));
    content.push(renderList("F9 interview dimensions", extended.f9_dimensions || [], (item) =>
      `${item.dimension.replaceAll("_", " ")}: ${item.rating}/5 (weight ${Math.round(item.weight * 100)}%). `
      + `${item.rationale}. Transcript segment(s): ${item.transcript_segment_ids.join(", ")}`));
    content.push(renderList("F8 CV claim follow-up prompts", extended.f8_claim_verification || [], (item) =>
      `${item.label}: ${item.claim}. CV evidence: “${item.cv_quote}”. ${item.follow_up_prompt} `
      + `Transcript segment(s): ${item.transcript_segment_ids.length ? item.transcript_segment_ids.join(", ") : "none recorded"}`));
    if (extended.f10_quality) {
      const quality = extended.f10_quality;
      const interviewerPercent = quality.candidate_talk_percent == null
        ? "not available" : `${(100 - quality.candidate_talk_percent).toFixed(2)}%`;
      content.push(textElement("p", `F10 talk-time: candidate ${quality.candidate_talk_percent ?? "not available"}% (${quality.candidate_talk_seconds}s); interviewer ${interviewerPercent} (${quality.interviewer_talk_seconds}s). Question relevance: ${quality.question_relevance_rating}/5. ${quality.question_quality_rationale}`));
      content.push(renderList("F10 interviewer recommendations", quality.recommendations, (item) => item));
    }
  } else {
    content.push(textElement("p", "Interview analysis is not available yet."));
  }
  root.replaceChildren(...content);
  root.hidden = false;
  status.textContent = "Assessment loaded. Use this report to support a human review; it is not an automated hiring decision.";
} catch (error) {
  status.textContent = error.message;
}

document.querySelector("#print-assessment").addEventListener("click", () => window.print());
