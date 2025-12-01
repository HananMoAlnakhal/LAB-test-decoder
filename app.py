"""
Lab Report Decoder - Flask Application
Professional web interface for lab report analysis
"""

from flask import Flask, render_template, request, jsonify, session
from werkzeug.utils import secure_filename
import os
import tempfile
import secrets
from pdf_extractor import LabReportExtractor
from rag_engine import LabReportRAG
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', secrets.token_hex(16))

# Note: No OpenAI API key needed - using Hugging Face models!
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = tempfile.gettempdir()

# Initialize RAG system (singleton)
rag_system = None

def get_rag_system():
    """Lazy load RAG system"""
    global rag_system
    if rag_system is None:
        rag_system = LabReportRAG()
    return rag_system

@app.route('/')
def index():
    """Main page"""
    return render_template('index.html')

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle PDF upload and extraction"""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not file.filename.lower().endswith('.pdf'):
            return jsonify({'error': 'Only PDF files are allowed'}), 400
        
        # Save file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Extract lab results
            extractor = LabReportExtractor()
            results = extractor.extract_from_pdf(filepath)
            
            if not results:
                return jsonify({'error': 'No lab results found in PDF'}), 400
            
            # Convert to JSON-serializable format
            results_data = [
                {
                    'test_name': r.test_name,
                    'value': r.value,
                    'unit': r.unit,
                    'reference_range': r.reference_range,
                    'status': r.status
                }
                for r in results
            ]
            
            # Store in session
            session['results'] = results_data
            
            return jsonify({
                'success': True,
                'results': results_data,
                'count': len(results_data)
            })
        
        finally:
            # Clean up temp file
            if os.path.exists(filepath):
                os.remove(filepath)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/explain', methods=['POST'])
def explain_results():
    """Generate explanations for lab results"""
    try:
        results_data = session.get('results')
        
        if not results_data:
            return jsonify({'error': 'No results found. Please upload a PDF first.'}), 400
        
        # Convert back to LabResult objects
        from pdf_extractor import LabResult
        results = [
            LabResult(
                test_name=r['test_name'],
                value=r['value'],
                unit=r['unit'],
                reference_range=r['reference_range'],
                status=r['status']
            )
            for r in results_data
        ]
        
        # Generate explanations
        rag = get_rag_system()
        explanations = rag.explain_all_results(results)
        
        return jsonify({
            'success': True,
            'explanations': explanations
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/ask', methods=['POST'])
def ask_question():
    """Answer follow-up questions"""
    try:
        data = request.get_json()
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'No question provided'}), 400
        
        results_data = session.get('results')
        
        if not results_data:
            return jsonify({'error': 'No results found. Please upload a PDF first.'}), 400
        
        # Convert back to LabResult objects
        from pdf_extractor import LabResult
        results = [
            LabResult(
                test_name=r['test_name'],
                value=r['value'],
                unit=r['unit'],
                reference_range=r['reference_range'],
                status=r['status']
            )
            for r in results_data
        ]
        
        # Get answer
        rag = get_rag_system()
        answer = rag.answer_followup_question(question, results)
        
        return jsonify({
            'success': True,
            'question': question,
            'answer': answer
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/summary', methods=['GET'])
def get_summary():
    """Generate overall summary"""
    try:
        results_data = session.get('results')
        
        if not results_data:
            return jsonify({'error': 'No results found. Please upload a PDF first.'}), 400
        
        # Convert back to LabResult objects
        from pdf_extractor import LabResult
        results = [
            LabResult(
                test_name=r['test_name'],
                value=r['value'],
                unit=r['unit'],
                reference_range=r['reference_range'],
                status=r['status']
            )
            for r in results_data
        ]
        
        # Generate summary
        rag = get_rag_system()
        summary = rag.generate_summary(results)
        
        # Calculate statistics
        stats = {
            'total': len(results),
            'normal': sum(1 for r in results if r.status == 'normal'),
            'high': sum(1 for r in results if r.status == 'high'),
            'low': sum(1 for r in results if r.status == 'low'),
            'unknown': sum(1 for r in results if r.status == 'unknown')
        }
        
        return jsonify({
            'success': True,
            'summary': summary,
            'stats': stats
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/clear', methods=['POST'])
def clear_session():
    """Clear session data"""
    session.clear()
    return jsonify({'success': True})

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 16MB.'}), 413

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    if not(os.path.isdir('chroma_db/')):
         os.system("python build_vector_db.py")
    #any available port
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)