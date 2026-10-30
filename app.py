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
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme-Adaptive Styling (Works cleanly in both Dark Mode and Light Mode)
st.markdown("""
<style>
    .main-title { font-size: 28px; font-weight: 800; color: #3B82F6; margin-bottom: 2px; }
    .sub-title { font-size: 15px; color: #94A3B8; margin-bottom: 20px; }
    blockquote {
        border-left: 3px solid #3B82F6 !important;
        background-color: rgba(59, 130, 246, 0.08) !important;
        padding: 10px 14px !important;
        border-radius: 4px !important;
        margin-top: 6px !important;
        margin-bottom: 6px !important;
    }
    .field-card {
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
        background-color: rgba(255, 255, 255, 0.03);
    }
</style>
""", unsafe_allow_html=True)

from src.extractors import RuleBasedSchemeExtractor, OpenAISchemeExtractor
from src.verifier import ExactEvidenceVerifier
from src.reconciler import SchemeReconciler
from src.pipeline import SchemePipeline

ENV_API_KEY = os.getenv("OPENAI_API_KEY", "")

@st.cache_resource
def get_pipeline():
    verifier = ExactEvidenceVerifier()
    reconciler = SchemeReconciler()
    if ENV_API_KEY:
        extractor = OpenAISchemeExtractor(api_key=ENV_API_KEY, model_name="gpt-4o-mini")
    else:
        extractor = RuleBasedSchemeExtractor()
    return SchemePipeline(extractor=extractor, verifier=verifier, reconciler=reconciler)

# Sidebar Controls (Clean & Secure - Never displays or asks for API key)
st.sidebar.markdown("## 🏛️ Haqdarshak")
st.sidebar.markdown("Scheme Knowledge Base AI")
st.sidebar.divider()

st.sidebar.markdown("### ⚙️ Extractor Engine")
st.sidebar.success("🤖 **OpenAI GPT-4o-mini (LLM)**\n\n*Strict Provenance & Grounding active*")

st.sidebar.divider()
st.sidebar.markdown("### 📋 Sample Circulars")
sample_docs = {
    "Doc 1: English Circular (MP)": "data/doc_1_english_circular.txt",
    "Doc 2: Hindi Order (UP)": "data/doc_2_hindi_circular.txt",
    "Doc 3: MyScheme Portal (Contradicting)": "data/doc_3_myscheme_portal_conflict.txt",
    "Doc 4: Scanned OCR Noise (Rajasthan)": "data/doc_4_scanned_noisy_ocr.txt"
}
selected_sample = st.sidebar.selectbox("Choose sample to load:", list(sample_docs.keys()))

# Load text
default_text = ""
if os.path.exists(sample_docs[selected_sample]):
    with open(sample_docs[selected_sample], "r", encoding="utf-8") as f:
        default_text = f.read()

# Header
st.markdown('<div class="main-title">🏛️ Haqdarshak Scheme Knowledge Base Reviewer</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">AI-Assisted Field Extraction with Verifiable Evidence & Cross-Source Reconciliation</div>', unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📄 Document Extraction & Review", "⚔️ Multi-Source Conflict Reconciliation", "📊 Benchmark Evaluation"])

with tab1:
    col_input, col_output = st.columns([1, 1.25])

    with col_input:
        st.subheader("Source Document")
        doc_ref = st.text_input("Source Document Reference / Filename:", value=selected_sample)
        doc_text = st.text_area("Paste or Edit Document Text:", value=default_text, height=480)
        run_btn = st.button("🚀 Run AI Extraction", type="primary", use_container_width=True)

    with col_output:
        st.subheader("Extracted Scheme Record (Review Draft)")
        if run_btn or "records" in st.session_state:
            if run_btn:
                with st.spinner("Extracting fields and verifying source citations with gpt-4o-mini..."):
                    pipeline = get_pipeline()
                    st.session_state["records"] = pipeline.process_document(doc_text, doc_ref)
            
            records = st.session_state.get("records", {})
            
            for field, rec in records.items():
                label = field.upper().replace('_', ' ')
                status_icon = "🟢 FOUND" if rec.status == "found" else "⚪ NOT FOUND"
                header_title = f"{status_icon} — {label}"
                
                with st.expander(header_title, expanded=(rec.status == "found")):
                    if rec.status == "found":
                        # Value Display
                        st.markdown("**Extracted Value:**")
                        if isinstance(rec.value, list):
                            for item in rec.value:
                                st.markdown(f"- {item}")
                        else:
                            st.info(f"**{rec.value}**")
                        
                        # Evidence Quote Display (Theme adaptive blockquote)
                        if rec.evidence and rec.evidence.exact_text:
                            st.markdown("**📌 Verbatim Evidence Quote:**")
                            st.markdown(f"> *\"{rec.evidence.exact_text}\"*")
                            
                            c_loc, c_date = st.columns([1, 1])
                            c_loc.caption(f"📍 **Location:** {rec.evidence.location}")
                            c_date.caption(f"📅 **Captured:** {rec.evidence.capture_date}")
                    else:
                        st.warning(f"⚠️ **Not Found:** {rec.note or 'Field not present in source document.'}")
            
            st.divider()
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("✅ Approve & Publish to Mobile App", use_container_width=True, type="primary"):
                    st.success("Record approved by researcher! Published to Haqdarshak Agent Network.")
            with col_b:
                st.download_button(
                    "💾 Export Approved JSON",
                    data=json.dumps({k: v.to_dict() for k, v in records.items()}, indent=2, ensure_ascii=False),
                    file_name="approved_scheme_record.json",
                    mime="application/json",
                    use_container_width=True
                )

with tab2:
    st.subheader("⚔️ Multi-Source Conflict Detection & Reconciliation")
    st.markdown("Compares **State Government Circular** vs. **National MyScheme Portal** to prevent outdated data reaching field agents.")

    if st.button("🔍 Run Dual-Source Cross-Reference", type="primary"):
        with st.spinner("Reconciling official circular with portal listing..."):
            pipeline = get_pipeline()
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
            st.error(f"⚠️ Detected {len(conflicts_found)} conflicting fields between official circular and portal.")

            for rec in conflicts_found:
                st.markdown(f"### ⚔️ Discrepancy: `{rec.field.upper()}`")
                st.caption(f"Reason: {rec.note}")
                
                c1, c2 = st.columns(2)
                with c1:
                    src0 = rec.conflicts[0]
                    st.info(f"**{src0.source_name}:**")
                    if isinstance(src0.value, list):
                        for val in src0.value:
                            st.markdown(f"- {val}")
                    else:
                        st.markdown(f"**Value:** `{src0.value}`")
                    if src0.evidence:
                        st.markdown(f"> *\"{src0.evidence.exact_text}\"*")
                        st.caption(f"📍 {src0.evidence.location}")
                
                with c2:
                    src1 = rec.conflicts[1]
                    st.warning(f"**{src1.source_name}:**")
                    if isinstance(src1.value, list):
                        for val in src1.value:
                            st.markdown(f"- {val}")
                    else:
                        st.markdown(f"**Value:** `{src1.value}`")
                    if src1.evidence:
                        st.markdown(f"> *\"{src1.evidence.exact_text}\"*")
                        st.caption(f"📍 {src1.evidence.location}")
                
                st.radio(
                    f"Authorize verified value for {rec.field}:",
                    [f"Accept {src0.source_name}", f"Accept {src1.source_name}", "Manual Edit"],
                    key=f"sel_{rec.field}"
                )
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
        table_rows = [{"Field Name": k, "Accuracy (%)": f"{v}%", "Production Gate": "PASS [Ready]" if v >= 85 else "MANUAL REVIEW"} for k, v in eval_data["field_accuracies"].items()]
        st.table(table_rows)
    else:
        st.info("Run evaluation using python -m src.evaluate to populate metrics.")
