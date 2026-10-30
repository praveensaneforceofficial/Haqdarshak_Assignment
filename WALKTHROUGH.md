# Walkthrough & Presentation Notes

This document provides answers to the mandatory evaluation points specified in lines 31–36 and 74–77 of the case study brief for Problem A1.

---

### 1. One decision you made, and the option you decided against

* **Decision Made:** Explicitly preserve disagreeing values under a `status: "conflict"` object, capturing both the official state circular claim and the MyScheme portal claim along with their verbatim citations and locations.
* **Option Decided Against:** Deciding between sources automatically (e.g. automatically trusting the government gazette over the portal via hardcoded priority, or asking the LLM to synthesize a single "compromise" number).
* **Why:** In welfare operations, assuming precedence without domain verification leads to catastrophic outcomes (e.g. an agent promising a beneficiary ₹1,500 based on an unnotified circular when the portal only disburses ₹1,250, or missing an early deadline). Flagging conflicts transparently empowers the human researcher to make the call.

---

### 2. Where your work falls short, and how someone would notice

* **Shortcoming 1: Nested tabular eligibility criteria.** 
  * *How someone would notice:* In schemes where benefit amounts vary across sub-criteria (e.g. ₹1,000 for ages 55–74 vs. ₹1,250 for 75+), the system extracts the entire text clause into `benefit_amount` rather than parsing it into conditional tiered sub-records.
* **Shortcoming 2: Severe OCR ligature degradation in regional scripts.**
  * *How someone would notice:* When scanned Hindi PDFs contain distorted complex conjunct characters (matras and conjuncts like "कृषक" scanned as "क षक"), exact string searching for evidence verification drops in confidence, flagging false "not found" statuses.

---

### 3. The main assumptions you made, and why

1. **Assumption:** *Human verification is always available for every scheme draft before publishing.*
   * *Why:* The pipeline is designed to optimize researcher review time, not eliminate the researcher. High recall with evidence citation is prioritized over aggressive autonomous decision-making.
2. **Assumption:** *Evidence must be verifiable verbatim in the source text.*
   * *Why:* If the model cannot ground an extracted value to an exact substring in the source document, it is marked as ungrounded or left empty. In civic tech, an empty field requiring manual input is vastly superior to a confidently hallucinated false entitlement.
3. **Assumption:** *Documents are processed at scheme-level chunks.*
   * *Why:* Complex 80-page gazettes covering multiple schemes should be segmented into scheme-specific sections prior to field extraction.

---

### 4. Also explain: What "field-level accuracy" means, in words a programme team would use

> *"Think of a scheme card like an identity card with 10 boxes to fill: name, department, amount, eligibility, documents, deadline, etc.*
> 
> *'Field-level accuracy' simply means: out of every 100 times the AI fills a specific box, how many times did it get that exact box 100% right with proof from the official paper?*
> 
> *Instead of giving the AI a general score like '85% good', field-level accuracy tells us exactly which boxes we can rely on (e.g., finding the website link is 100% reliable) and which boxes our team still needs to look at carefully (e.g., complex document lists or changing deadlines). It ensures our field workers never give wrong information to a citizen."*

---

### 5. A question about how you work: 
> *"A senior researcher tells you the AI got a benefit amount wrong. You check, and the AI's value matches the PDF. What do you do next?"*

1. **Listen first and do not be defensive:** I assume the senior researcher has domain and on-the-ground context that the PDF alone does not capture (e.g., a subsequent government amendment, court stay order, or a ground reality where an administrative deduction occurs).
2. **Walk through the evidence together:** Show them the AI's exact quote, page, and paragraph from the PDF so they see why the AI extracted that number.
3. **Investigate the discrepancy:**
   * Is this PDF outdated? (Was there a corrigendum or newer circular?)
   * Did the scheme change rules during budget announcements?
   * Was there conditional fine print elsewhere in the PDF (e.g., "up to ₹1,500, but ₹1,000 base") that the prompt missed?
4. **Take action:**
   * Update the scheme record with the verified amount agreed upon with the researcher.
   * Add the researcher's correction and the edge-case PDF to our regression test suite.
   * If the issue was an updated corrigendum, log an engineering improvement: ensure our ingestion pipeline links amendment gazettes to base circulars.
