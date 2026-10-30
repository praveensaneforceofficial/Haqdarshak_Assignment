"""
Haqdarshak Scheme Knowledge Base - Interactive Reviewer UI
Built with Streamlit. Enables researchers to inspect AI drafts, verify exact evidence quotes,
and resolve cross-source discrepancies before publishing to Haqdarshaks and citizens.
"""

import os
import sys
import json
import streamlit as st
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Configure page layout
st.set_page_config(
    page_title="Haqdarshak Scheme Knowledge Base",
    page_icon="🇮🇳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header { font-size: 26px; font-weight: 700; color: #1E3A8A; margin-bottom: 0px; }
    .sub-header { font-size: 15px; color: #4B5563; margin-bottom: 20px; }
    .badge-found { background-color: #DEF7EC; color: #03543F; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 12px; }
    .badge-conflict { background-color: #FDE8E8; color: #9B1C1C; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 12px; }
    .badge-missing { background-color: #F3F4F6; color: #374151; padding: 4px 10px; border-radius: 6px; font-weight: 600; font-size: 12px; }
    .evidence-box { background-color: #F9FAFB; border-left: 4px solid #3B82F6; padding: 10px 14px; margin-top: 8px; border-radius: 0 6px 6px 0; font-size: 13px; }
    .conflict-card { border: 1px solid #FCA5A5; background-color: #FEF2F2; padding: 12px; border-radius: 8px; margin-bottom: 12px; }
</style>
""", unsafe_allow_html=True)

from src.extractors import RuleBasedSchemeExtractor, OpenAISchemeExtractor
from src.verifier import ExactEvidenceVerifier
from src.reconciler import SchemeReconciler
from src.pipeline import SchemePipeline

ENV_API_KEY = os.getenv("OPENAI_API_KEY", "")

@st.cache_resource
def get_pipeline(use_openai: bool, api_key: str):
    verifier = ExactEvidenceVerifier()
    reconciler = SchemeReconciler()
    resolved_key = api_key.strip() if api_key.strip() else ENV_API_KEY
    if use_openai and resolved_key:
        extractor = OpenAISchemeExtractor(api_key=resolved_key)
    else:
        extractor = RuleBasedSchemeExtractor()
    return SchemePipeline(extractor=extractor, verifier=verifier, reconciler=reconciler)

# Sidebar Controls
st.sidebar.image("https://haqdarshak.com/wp-content/uploads/2021/04/hd-logo.png", width=180)
st.sidebar.markdown("### ⚙️ Pipeline Settings")
engine_choice = st.sidebar.radio("Select Extractor Engine:", ["OpenAI GPT-4o-mini (LLM)", "Deterministic Engine (Offline)"])
use_openai = "OpenAI" in engine_choice
api_key_input = st.sidebar.text_input("OpenAI API Key (or loaded from .env):", value=ENV_API_KEY if use_openai else "", type="password")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Sample Documents")
sample_docs = {
    "Doc 1: English Circular (MP)": "data/doc_1_english_circular.txt",
    "Doc 2: Hindi Order (UP)": "data/doc_2_hindi_circular.txt",
    "Doc 3: MyScheme Portal (Contradicting)": "data/doc_3_myscheme_portal_conflict.txt",
    "Doc 4: Scanned OCR Noise (Rajasthan)": "data/doc_4_scanned_noisy_ocr.txt"
}
selected_sample = st.sidebar.selectbox("Load Sample Circular:", list(sample_docs.keys()))

# Load text
default_text = ""
if os.path.exists(sample_docs[selected_sample]):
    with open(sample_docs[selected_sample], "r", encoding="utf-8") as f:
        default_text = f.read()

# Header
st.markdown('<div class="main-header">🇮🇳 Haqdarshak Scheme Knowledge Base Reviewer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AI-Assisted Field Extraction with Verifiable Evidence & Cross-Source Reconciliation</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📄 Document Extraction & Review", "⚔️ Multi-Source Conflict Reconciliation", "📊 Benchmark Evaluation"])

with tab1:
    col_input, col_output = st.columns([1, 1.2])

    with col_input:
        st.subheader("Source Document")
        doc_ref = st.text_input("Source Document Reference / Filename:", value=selected_sample)
        doc_text = st.text_area("Paste or Edit Document Text:", value=default_text, height=480)
        run_btn = st.button("🚀 Run AI Extraction", type="primary", use_container_width=True)

    with col_output:
        st.subheader("Extracted Scheme Record (Review Draft)")
        if run_btn or "records" in st.session_state:
            if run_btn:
                with st.spinner("Analyzing document and verifying text citations..."):
                    pipeline = get_pipeline(use_openai, api_key_input)
                    st.session_state["records"] = pipeline.process_document(doc_text, doc_ref)
            
            records = st.session_state["records"]
            
            for field, rec in records.items():
                status_badge = f'<span class="badge-found">FOUND ({rec.confidence})</span>' if rec.status == "found" else f'<span class="badge-missing">NOT FOUND</span>'
                with st.expander(f"**{field.upper().replace('_', ' ')}** — {status_badge}", expanded=True):
                    if rec.status == "found":
                        st.markdown(f"**Extracted Value:** `{rec.value}`")
                        if rec.evidence:
                            st.markdown(f"""
                            <div class="evidence-box">
                                📌 <b>Exact Evidence Quote:</b> "<i>{rec.evidence.exact_text}</i>"<br>
                                📍 <b>Location:</b> {rec.evidence.location} &nbsp;|&nbsp; 📅 <b>Captured:</b> {rec.evidence.capture_date}
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption(f"Reason: {rec.note or 'Field not present in source document.'}")
            
            st.divider()
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Approve & Publish to Mobile App", use_container_width=True):
                    st.success("Record approved by researcher! Published to Haqdarshak Agent Network.")
            with col_b:
                st.download_button(
                    "💾 Export Approved JSON",
                    data=json.dumps({k: v.to_dict() for k, v in records.items()}, indent=2),
                    file_name="approved_scheme_record.json",
                    mime="application/json",
                    use_container_width=True
                )

with tab2:
    st.subheader("⚔️ Multi-Source Conflict Detection & Reconciliation")
    st.markdown("Compares **State Government Circular** vs. **National MyScheme Portal** to prevent outdated data reaching field agents.")

    if st.button("🔍 Run Dual-Source Cross-Reference", type="primary"):
        with st.spinner("Reconciling official circular with portal listing..."):
            pipeline = get_pipeline(use_openai, api_key_input)
            with open("data/doc_1_english_circular.txt", "r", encoding="utf-8") as f:
                c_text = f.read()
            with open("data/doc_3_myscheme_portal_conflict.txt", "r", encoding="utf-8") as f:
                p_text = f.read()
            reconciled = pipeline.process_and_reconcile(
                primary_text=c_text,
                primary_source_ref="doc_1_english_circular.txt",
                secondary_text=p_text,
                secondary_source_ref="doc_3_myscheme_portal_conflict.txt",
                scheme_id="SCHEME-MP-001",
                primary_name="Official State Circular",
                secondary_name="MyScheme National Portal"
            )
            
            conflicts_found = [r for r in reconciled.values() if r.status == "conflict"]
            st.warning(f"⚠️ Detected {len(conflicts_found)} conflicting fields between official circular and portal.")

            for rec in conflicts_found:
                st.markdown(f"""
                <div class="conflict-card">
                    <h4 style="color:#9B1C1C; margin:0 0 8px 0;">⚔️ Field Conflict: {rec.field.upper()}</h4>
                    <p><b>Note:</b> {rec.note}</p>
                </div>
                """, unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    st.info(f"**{rec.conflicts[0].source_name}:**\n\nValue: `{rec.conflicts[0].value}`\n\nQuote: *\"{rec.conflicts[0].evidence.exact_text}\"*")
                with c2:
                    st.warning(f"**{rec.conflicts[1].source_name}:**\n\nValue: `{rec.conflicts[1].value}`\n\nQuote: *\"{rec.conflicts[1].evidence.exact_text}\"*")
                st.radio(f"Select authorized version for {rec.field}:", [f"Keep {rec.conflicts[0].source_name}", f"Keep {rec.conflicts[1].source_name}", "Manual Override"], key=f"sel_{rec.field}")
                st.divider()

with tab3:
    st.subheader("📊 Evaluation Benchmark Report")
    st.markdown("Field-by-field accuracy against hand-checked ground truth and zero-hallucination verification.")
    
    if os.path.exists("data/evaluation_report.json"):
        with open("data/evaluation_report.json", "r", encoding="utf-8") as f:
            eval_data = json.load(f)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Overall Field Accuracy", f"{eval_data['overall_field_accuracy_pct']}%")
        m2.metric("Evidence Grounding Rate", f"{eval_data['evidence_attribution_validity_pct']}%", "Verifiable in Text")
        m3.metric("Conflict Recall", f"{eval_data['conflict_detection_recall_pct']}%", "Discrepancies Caught")

        st.markdown("### Field-by-Field Breakdown")
        table_rows = [{"Field Name": k, "Accuracy (%)": f"{v}%", "Production Gate": "PASS" if v >= 85 else "MANUAL REVIEW"} for k, v in eval_data["field_accuracies"].items()]
        st.table(table_rows)
    else:
        st.info("Run evaluation using python -m src.evaluate to populate metrics.")
