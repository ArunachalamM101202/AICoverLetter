import streamlit as st
import PyPDF2
import google.generativeai as genai
import os
from io import BytesIO
from datetime import datetime
import re
import base64
from dotenv import load_dotenv

# Set up Gemini API key

# Load environment variables from .env file
load_dotenv()


def initialize_genai():
    api_key = os.getenv("GEMINI_API_KEY")  # Load from .env

    if not api_key:
        api_key = st.sidebar.text_input(
            "Enter Gemini API Key:", type="password")
        if not api_key:
            st.sidebar.warning("Please enter your Gemini API Key to proceed")
            return None

    # Initialize the Gemini API
    genai.configure(api_key=api_key)
    return True


def extract_text_from_pdf(uploaded_file):
    if uploaded_file is not None:
        try:
            # Create a BytesIO object from the uploaded file
            pdf_bytes = BytesIO(uploaded_file.getvalue())
            pdf_reader = PyPDF2.PdfReader(pdf_bytes)
            text = ""
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text
        except Exception as e:
            st.error(f"Error extracting text from PDF: {str(e)}")
            return ""
    return ""


def extract_name_from_resume(resume_text):
    """Attempt to extract a name from the resume text"""
    # This is a simple approach - could be improved with more sophisticated NLP
    lines = resume_text.split('\n')
    # Try to find a name in the first few lines of the resume
    for line in lines[:5]:
        # Look for a line with just a name (2-3 words, no numbers or special chars)
        if 1 <= len(line.split()) <= 3 and re.match(r'^[A-Za-z\s\.\-]+$', line.strip()):
            return line.strip()
    return "Your Name"  # Default if no name found


def generate_cover_letter(company, role, job_desc, resume_text):
    try:
        # Get current date
        current_date = datetime.now().strftime("%B %d, %Y")

        # Configure the model
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 2048,
        }

        # Create the model
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            generation_config=generation_config
        )

        # Prepare the prompt
        prompt = f"""
Create a comprehensive professional cover letter (approximately 400 words) using these guidelines:
- Use clear, direct language and avoid complex terminology
- Aim for a Flesch reading score of 80 or higher
- Use active voice and avoid adverbs
- Avoid buzzwords and use plain English
- Use relevant industry jargon only when necessary
- Express calm confidence rather than being overly enthusiastic

Company: {company}
Job Role: {role}

Job Description:
{job_desc}

Resume Content:
{resume_text}

Format the letter with the following structure (all sections are required):

{current_date}

Dear Hiring Manager,

PARAGRAPH 1: A strong introduction that mentions the specific role you're applying for, how you learned about it, and a brief statement about why you're interested. Include a concise value proposition about what makes you an ideal candidate.

PARAGRAPH 2: A detailed explanation of your most relevant skills and experiences that directly align with the job requirements. Highlight 2-3 specific achievements with measurable results that demonstrate your capabilities. Reference information from your resume but don't simply repeat it.

PARAGRAPH 3: Discuss your technical or specialized qualifications that make you uniquely suited for this position. Connect your expertise directly to the company's needs or projects mentioned in the job description.

PARAGRAPH 4: Express specific appreciation for the company. Demonstrate your research by mentioning the company's values, recent accomplishments, products, or initiatives that you admire. Explain why you're enthusiastic about contributing to their specific mission or culture.

PARAGRAPH 5: A confident closing paragraph requesting an interview and expressing enthusiasm about the opportunity to contribute to their team. Include a thank you for their consideration.

Sincerely,

[Extract name from resume or use "Your Name" if not found]

IMPORTANT:
- The final letter must be approximately 400 words total
- Each paragraph should be substantive (3-5 sentences)
- Use specific details from both the job description and resume throughout
- Include at least one specific achievement with numerical results
- The fourth paragraph must specifically praise the company with researched details
"""

        # Generate the cover letter
        response = model.generate_content(prompt)
        return response.text

    except Exception as e:
        st.error(f"Error generating cover letter: {str(e)}")
        return f"An error occurred: {str(e)}"


def create_html_cover_letter(cover_letter_text, company, role):
    """Convert the cover letter to a print-friendly HTML format"""
    try:
        # Process the cover letter text
        paragraphs = []
        date_line = ""
        signature_lines = []

        # Split the text into lines
        lines = cover_letter_text.split('\n')

        # Process each line
        current_paragraph = []
        in_signature = False

        for line in lines:
            # Identify the date (usually at the top)
            if not date_line and re.match(r'[A-Z][a-z]+ \d{1,2}, \d{4}', line.strip()):
                date_line = line.strip()
                continue

            # Check for signature section
            if 'Sincerely' in line or 'Regards' in line or in_signature:
                in_signature = True
                if line.strip():
                    signature_lines.append(line.strip())
                continue

            # Process regular paragraphs
            if line.strip():
                current_paragraph.append(line.strip())
            elif current_paragraph:
                paragraphs.append(' '.join(current_paragraph))
                current_paragraph = []

        # Add the last paragraph if it exists
        if current_paragraph:
            paragraphs.append(' '.join(current_paragraph))

        # Create HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cover Letter - {role} at {company}</title>
            <style>
                @media print {{
                    @page {{ size: letter; margin: 1in; }}
                }}
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.5;
                    font-size: 10pt;
                    color: #000;
                    max-width: 8.5in;
                    margin: 0 auto;
                    padding: 1in;
                }}
                .date {{
                    text-align: right;
                    margin-bottom: 20px;
                }}
                .content p {{
                    margin-bottom: 15px;
                    text-align: justify;
                }}
                .signature {{
                    margin-top: 30px;
                }}
                .print-button {{
                    display: block;
                    text-align: center;
                    margin: 20px auto;
                    padding: 10px 20px;
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 16px;
                    cursor: pointer;
                }}
                @media print {{
                    .print-button {{
                        display: none;
                    }}
                }}
            </style>
        </head>
        <body>
            <div class="date">{date_line}</div>
            
            <div class="content">
        """

        # Add paragraphs
        for para in paragraphs:
            html += f"<p>{para}</p>\n"

        # Add signature
        html += '<div class="signature">\n'
        for line in signature_lines:
            html += f"<p>{line}</p>\n"
        html += '</div>\n'

        # Add print button
        html += """
            </div>
            
            <button class="print-button" onclick="window.print()">Print / Save as PDF</button>
            
            <script>
                document.querySelector('.print-button').addEventListener('click', function() {
                    window.print();
                });
            </script>
        </body>
        </html>
        """

        return html

    except Exception as e:
        st.error(f"Error creating HTML: {str(e)}")
        return None


def get_html_download_link(html_string, filename):
    """Generate a link to download the HTML file"""
    b64 = base64.b64encode(html_string.encode()).decode()
    href = f'<a href="data:text/html;base64,{b64}" download="{filename}">📄 Download HTML</a>'
    return href


def main():
    st.set_page_config(
        page_title="AI Cover Letter Generator",
        page_icon="📝",
        layout="wide"
    )

    st.title("📝 AI-Powered Cover Letter Generator")
    st.markdown(
        "Upload your resume and job details to generate a tailored cover letter")

    # Initialize the API
    if initialize_genai() is None:
        return

    # Create two columns for input
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Job Details")
        company = st.text_input("Company Name")
        role = st.text_input("Job Role/Position")
        job_desc = st.text_area("Job Description", height=250)

    with col2:
        st.subheader("Your Resume")
        resume_file = st.file_uploader("Upload Resume (PDF)", type=["pdf"])

        if resume_file:
            with st.expander("Resume Preview"):
                resume_text = extract_text_from_pdf(resume_file)
                st.text_area("Extracted Text", resume_text, height=200)
        else:
            resume_text = ""

    # Generation button
    if st.button("Generate Cover Letter", type="primary"):
        if company and role and job_desc and resume_file:
            with st.spinner("Generating your cover letter..."):
                resume_text = extract_text_from_pdf(resume_file)
                generated_cover_letter = generate_cover_letter(
                    company, role, job_desc, resume_text)

            st.success("Cover letter generated successfully!")

            # Create HTML version for printing
            html_version = create_html_cover_letter(
                generated_cover_letter, company, role)

            # Display tabs for different views
            tab1, tab2 = st.tabs(["Cover Letter", "Print-Ready Version"])

            with tab1:
                st.subheader("Your Custom Cover Letter")
                st.markdown(generated_cover_letter)

                # Text download button
                st.download_button(
                    label="📄 Download as Text",
                    data=generated_cover_letter,
                    file_name=f"Cover_Letter_{company}_{role}.txt",
                    mime="text/plain"
                )

            with tab2:
                st.subheader("Print-Ready Version")
                st.markdown(
                    "Use your browser's print function (Ctrl+P / Cmd+P) to save as PDF")

                # Display the HTML version in an iframe
                if html_version:
                    st.components.v1.html(
                        html_version, height=600, scrolling=True)

                    # HTML Download option
                    st.markdown(get_html_download_link(
                        html_version, f"Cover_Letter_{company}_{role}.html"), unsafe_allow_html=True)

                    st.info("💡 **To save as PDF**: Click the 'Print / Save as PDF' button above, or open the downloaded HTML file in your browser and use the browser's print function, selecting 'Save as PDF' as the destination.")
        else:
            st.warning(
                "Please fill in all fields and upload your resume to generate a cover letter.")

    # Footer
    st.markdown("---")
    st.caption(
        "This tool uses Google's Gemini AI to generate cover letters. Your data is not stored.")


if __name__ == "__main__":
    main()
