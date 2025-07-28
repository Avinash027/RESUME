import streamlit as st
import tempfile
import os
from main import load_document, extract_text_from_documents, get_matching_score_summary_and_edits
import requests
from urllib.parse import urlparse

# Set page config
st.set_page_config(
    page_title="Resume & JD Matching Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .score-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        margin: 1rem 0;
    }
    .score-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
    }
    .edit-item {
        background-color: #e8f4fd;
        padding: 0.5rem;
        margin: 0.3rem 0;
        border-left: 4px solid #1f77b4;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

def main():
    st.markdown('<h1 class="main-header"> Resume & JD Matching Engine</h1>', unsafe_allow_html=True)
    st.markdown("### Upload your resume and provide a job description to get an AI-powered compatibility analysis with suggested improvements!")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        groq_api_key = st.text_input("Groq API Key", type="password", value=os.getenv("GROQ_API_KEY", ""))
        if groq_api_key:
            os.environ["GROQ_API_KEY"] = groq_api_key
        
        st.markdown("---")
        st.markdown("### Instructions")
        st.markdown("""
        1. **Upload Resume**: Upload your resume in PDF, DOCX, or TXT format
        2. **Job Description**: Paste the job description or provide a URL
        3. **Analyze**: Click the analyze button to get your matching score
        4. **Review**: Check the suggested edits to improve your resume
        """)
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header(" Resume Upload")
        uploaded_file = st.file_uploader(
            "Choose your resume file",
            type=['pdf', 'docx', 'txt'],
            help="Upload your resume in PDF, DOCX, or TXT format"
        )
        
        resume_text = ""
        if uploaded_file is not None:
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{uploaded_file.name.split('.')[-1]}") as tmp_file:
                tmp_file.write(uploaded_file.getvalue())
                tmp_file_path = tmp_file.name
            
            try:
                # Load and extract text from document
                documents = load_document(tmp_file_path)
                resume_text = extract_text_from_documents(documents)
                
                st.success(f" Resume loaded successfully! ({len(resume_text)} characters)")
                
                # Show preview of resume text
                with st.expander(" Resume Preview"):
                    st.text_area("Resume Content", resume_text[:1000] + "..." if len(resume_text) > 1000 else resume_text, height=200, disabled=True)
                
            except Exception as e:
                st.error(f" Error loading resume: {str(e)}")
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
    
    with col2:
        st.header(" Job Description")
        
        # Option to input job description via text or URL
        input_method = st.radio("Input method:", ["Paste Text", "URL"])
        
        jd_text = ""
        if input_method == "Paste Text":
            jd_text = st.text_area(
                "Paste the job description here:",
                height=300,
                placeholder="Paste the complete job description here..."
            )
        else:
            url = st.text_input("Job Description URL:", placeholder="https://example.com/job-posting")
            if url and st.button("Fetch from URL"):
                try:
                    # Simple URL fetching (in a real app, you might want more sophisticated scraping)
                    response = requests.get(url, timeout=10)
                    if response.status_code == 200:
                        jd_text = response.text[:5000]  # Limit to first 5000 characters
                        st.success(" Job description fetched successfully!")
                        st.text_area("Fetched Content Preview:", jd_text[:500] + "..." if len(jd_text) > 500 else jd_text, height=150, disabled=True)
                    else:
                        st.error(f" Failed to fetch URL. Status code: {response.status_code}")
                except Exception as e:
                    st.error(f" Error fetching URL: {str(e)}")
        
        if input_method == "Paste Text" and jd_text:
            st.success(f"Job description entered! ({len(jd_text)} characters)")
    
    # Analysis section
    st.markdown("---")
    st.header(" Analysis")
    
    if st.button(" Analyze Resume Match", type="primary", use_container_width=True):
        if not resume_text:
            st.error(" Please upload a resume first!")
            return
        
        if not jd_text:
            st.error(" Please provide a job description!")
            return
        
        if not os.getenv("GROQ_API_KEY"):
            st.error(" Please provide your Groq API key in the sidebar!")
            return
        
        # Show loading spinner
        with st.spinner("Analyzing your resume... This may take a moment."):
            try:
                # Get analysis results
                results = get_matching_score_summary_and_edits(resume_text, jd_text)
                
                # Display results
                st.success(" Analysis complete!")
                
                # Create three columns for results
                col1, col2, col3 = st.columns([1, 2, 2])
                
                with col1:
                    st.markdown('<div class="score-container">', unsafe_allow_html=True)
                    st.markdown("###  Matching Score")
                    if results["matching_score"]:
                        score_color = "green" if results["matching_score"] >= 70 else "orange" if results["matching_score"] >= 50 else "red"
                        st.markdown(f'<div class="score-value" style="color: {score_color};">{results["matching_score"]}/100</div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="score-value" style="color: gray;">N/A</div>', unsafe_allow_html=True)
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with col2:
                    st.markdown("### Summary")
                    if results["summary"]:
                        st.markdown(results["summary"])
                    else:
                        st.info("No summary available")
                
                with col3:
                    st.markdown("### Suggested Edits")
                    if results["suggested_edits"]:
                        for edit in results["suggested_edits"]:
                            st.markdown(f'<div class="edit-item">{edit}</div>', unsafe_allow_html=True)
                    else:
                        st.info("No specific edits suggested")
                
                # Additional insights section
                st.markdown("---")
                st.header(" Additional Insights")
                
                insight_col1, insight_col2 = st.columns(2)
                
                with insight_col1:
                    st.markdown("### Key Strengths")
                    if results["matching_score"] and results["matching_score"] >= 70:
                        st.success("Strong match! Your resume aligns well with the job requirements.")
                    elif results["matching_score"] and results["matching_score"] >= 50:
                        st.warning("Good potential! Some improvements could strengthen your application.")
                    else:
                        st.error("Significant gaps identified. Consider major revisions to better match the role.")
                
                with insight_col2:
                    st.markdown("### Next Steps")
                    st.markdown("""
                    1. **Review suggested edits** carefully
                    2. **Update your resume** based on recommendations
                    3. **Re-analyze** to see improvement
                    4. **Tailor your cover letter** to address any remaining gaps
                    """)
                
            except Exception as e:
                st.error(f"Error during analysis: {str(e)}")
                st.info("Please check your API key and try again.")

if __name__ == "__main__":
    main()

