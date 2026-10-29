import { api } from "./api.js";

const status = document.querySelector("#comparison-status");
const wrap = document.querySelector("#comparison-table-wrap");
const jobId = new URLSearchParams(location.search).get("job_id");
const formatAverage = (value) => value == null ? "—" : `${value}/5`;

try {
  if (!jobId) throw new Error("A job ID is required.");
  const comparison = await api.getAssessmentComparison(jobId);
  document.querySelector("#comparison-title").textContent = `${comparison.job_title} · candidate comparison`;
  const table = document.createElement("table");
  table.className = "assessment-comparison-table";
  const head = document.createElement("thead");
  const headerRow = document.createElement("tr");
  for (const label of ["Candidate", "CV score", "Interview score", "Relevance", "Accuracy", "Completeness", "Articulation", "Evidence gaps"]) {
    const cell = document.createElement("th");
    cell.scope = "col";
    cell.textContent = label;
    headerRow.append(cell);
  }
  head.append(headerRow);
  const body = document.createElement("tbody");
  for (const candidate of comparison.candidates) {
    const row = document.createElement("tr");
    const metrics = candidate.interview_component_averages;
    const values = [candidate.candidate_name, candidate.cv_score == null ? "Not scored" : `${candidate.cv_score}/100`, candidate.f9_weighted_total_out_of_100 == null ? "Not scored" : `${candidate.f9_weighted_total_out_of_100}/100`, formatAverage(metrics.relevance), formatAverage(metrics.accuracy), formatAverage(metrics.completeness), formatAverage(metrics.articulation), candidate.evidence_gaps.map((item) => item.requirement).join("; ") || "None recorded"];
    values.forEach((value) => { const cell = document.createElement("td"); cell.textContent = value; row.append(cell); });
    body.append(row);
  }
  table.append(head, body);
  wrap.replaceChildren(table);
  status.textContent = "Scores and transcript indicators support a human comparison; they do not determine a hiring outcome.";
} catch (error) {
  status.textContent = error.message;
}

document.querySelector("#print-comparison").addEventListener("click", () => window.print());
