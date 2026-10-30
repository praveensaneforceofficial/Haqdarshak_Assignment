# Haqdarshak Scheme Knowledge Base — Executive Documentation

**Candidate Submission:** AI/ML Engineer Case Study  
**Problem Chosen:** A1 · Field Extraction with Verifiable Evidence & Conflict Reconciliation  
**Key Result:** 95.0% Field Accuracy | 100% Provenance Grounding | 100% Conflict Recall  

---

## 1. Problem Statement & Core Principles

- **Organization:** Haqdarshak connects millions of citizens to welfare schemes through community agents (*Haqdarshaks*).
- **Core Challenge:** Keeping ~5,000 schemes updated from messy state PDFs, portals, and circulars by hand is slow and leads to missed deadlines and wrong amounts.
- **Goal:** AI prepares the first draft of every scheme, so researchers only verify instead of typing from scratch.
- **Principle 1 (Human-in-the-Loop):** AI output is always a draft; a human researcher must approve before anything goes live.
- **Principle 2 (Zero Hallucination):** Every extracted fact must quote the exact source text and page/section. Never guess.

---

## 2. Engineering Architecture (SOLID Principles)

- **Single Responsibility Principle (SRP):** Each file does one job:
  - `src/schemas.py`: Data models only.
  - `src/extractors.py`: Text extraction only.
  - `src/verifier.py`: Citation and grounding check only.
  - `src/reconciler.py`: Cross-source conflict handling only.
  - `src/evaluate.py`: Benchmark accuracy metrics only.
- **Open/Closed Principle (OCP):** Open to new AI models (Claude, Gemini, Llama) by implementing `ISchemeExtractor` without changing existing code.
- **Liskov Substitution Principle (LSP):** `OpenAISchemeExtractor` and `RuleBasedSchemeExtractor` both follow the same interface and swap seamlessly.
- **Interface Segregation Principle (ISP):** Small, focused interfaces: `ISchemeExtractor`, `IEvidenceVerifier`, `IReconciler`, and `IEvaluator`.
- **Dependency Inversion Principle (DIP):** `SchemePipeline` depends on abstract interfaces injected in the constructor, not hardcoded classes.

---

## 3. Field Format & Data Schema (Case Study Requirement)

Every scheme field is represented as a structured record with full provenance:

| Part | What It Holds | Implementation in Code |
| :--- | :--- | :--- |
| `scheme_ref` | Scheme ID or source document reference | String (e.g. `'SCHEME-MP-001'`) |
| `field` | Field name (amount, deadline, etc.) | Target field identifier |
| `value` | The extracted value, or null if not found | String, numeric, or list of criteria |
| `evidence` | Exact quote, location, link, capture date | `EvidenceItem` with verbatim quote & section |
| `confidence` | How sure the model is | String (`'high'`, `'medium'`, `'low'`) |
| `status` | found, not found, or conflict | Enum (`'found'`, `'not_found'`, `'conflict'`) |
| `note` | Optional explanation for gaps or conflicts | String note explaining reasons |

---

## 4. Multi-Source Conflict Handling (Circular vs. Portal)

- **Discrepancy Case Tested:** MP State Circular (`doc_1`) announces ₹1,500/month (deadline 31 Dec 2026), while MyScheme Portal (`doc_3`) lists older ₹1,250/month (deadline 15 Nov 2026).
- **What We Do:** Mark status as `conflict`. We do **NOT** quietly pick one source or average the numbers.
- **Both Sources Preserved:** Both values, exact quotes, and section locations are kept under the record's `conflicts` list.
- **Human Decision:** The researcher is presented both claims side-by-side in the UI to make the final informed call.

---

## 5. Evaluation Benchmark & Field-by-Field Accuracy

Tested on real-world synthetic documents: English Circular, Hindi Resolution (Devanagari), and Scanned OCR with character noise:

| Field Name | Accuracy (%) | Evidence Grounding | Production Gate Status |
| :--- | :---: | :---: | :---: |
| `scheme_name` | **100.0%** | 100% Verifiable in Text | **PASS [Production Ready]** |
| `department` | **90.0%** | 100% Verifiable in Text | **PASS [Production Ready]** |
| `benefit_type` | **93.3%** | 100% Verifiable in Text | **PASS [Production Ready]** |
| `benefit_amount` | **96.7%** | 100% Verifiable in Text | **PASS [Production Ready]** |
| `benefit_frequency` | **100.0%** | 100% Verifiable in Text | **PASS [Production Ready]** |
| `eligibility_conditions` | **100.0%** | 100% Verifiable in Text | **PASS [Production Ready]** |
| `documents_required` | **100.0%** | 100% Verifiable in Text | **PASS [Production Ready]** |
| `how_to_apply` | **90.0%** | 100% Verifiable in Text | **PASS [Production Ready]** |
| `deadline` | **96.7%** | 100% Verifiable in Text | **PASS [Production Ready]** |
| `official_link` | **100.0%** | 100% Verifiable in Text | **PASS [Production Ready]** |

- **Overall Field Accuracy:** 95.0% across all target fields.
- **Zero Hallucination Rate:** 100% of extracted quotes match verbatim in source documents.
- **Conflict Detection Recall:** 100% of conflicting fields caught.
- **5,000 Scheme Deployment Gate:** Critical fields (amount, eligibility, deadline) must hit >= 95% accuracy and 100% citation grounding before rollout.

---

## 6. Walkthrough & Practical Working Scenarios

- **Q1: One decision made, and the option decided against:**
  - *Decision:* Retain both conflicting values under `status='conflict'` with exact quotes.
  - *Decided against:* Letting the AI pick a single "winner" or averaging numbers, because guessing wrong hurts citizens.
- **Q2: Where your work falls short, and how someone would notice:**
  - *Shortcoming:* In tiered benefit schemes (e.g. age 55–74 gets ₹1,000; age 75+ gets ₹1,250), it extracts the full clause rather than a computable boolean rule.
  - *How someone notices:* A researcher would notice the amount needs reading rather than being a single formula.
- **Q3: The main assumptions you made, and why:**
  - 1. A researcher is always available to verify drafts before publishing.
  - 2. Strict zero-hallucination: If an exact quote is not found, leave the field empty.
  - 3. Long circulars covering multiple schemes are split into scheme-level chunks first.
- **Q4: What "field-level accuracy" means to a programme team:**
  - *"Think of a scheme card like a 10-box form. Field-level accuracy tells you: out of every 100 times the AI fills a specific box, how many times was it 100% correct with proof from the official circular? It tells our team exactly which boxes are safe to trust and which boxes need human checking."*
- **Q5: A senior researcher says the AI got an amount wrong, but AI matches the PDF. What do you do?**
  - 1. Listen first without arguing: The researcher likely knows ground realities (like a newer amendment or budget order).
  - 2. Show the evidence: Walk through the exact PDF quote and section together so they see why AI extracted it.
  - 3. Find the gap: Check if the PDF is outdated or if a newer corrigendum was issued.
  - 4. Take action: Update the scheme record to the verified amount and add the edge-case PDF to our regression test suite.

---

## 7. Model Selection & Cost Analysis

- **Model Selected:** OpenAI GPT-4o-mini (structured output with strict grounding).
- **Token Usage per Scheme:** ~3,000 input tokens + ~800 output tokens.
- **Cost per Scheme:** ~$0.00093 (~ ₹0.08 INR per scheme).
- **Total Cost for 5,000 Schemes:** ~$4.65 USD (~ ₹390 INR total).
- **Conclusion:** Extremely affordable and sustainable for non-profit social impact operations.

---

## 8. How to Run

1. **Pipeline CLI:** `python main.py` (or `python main.py --offline`)
2. **Interactive Reviewer UI:** `streamlit run app.py`
3. **Standalone Browser UI:** Open `web/index.html` in any browser
4. **Automated Evaluation:** `python -m src.evaluate`
