from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
import csv
import io
import os
from datetime import datetime
import uuid
import random
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try importing Groq
try:
    from groq import Groq
    GROQ_AVAILABLE = True
except ImportError:
    print("Warning: Groq library not available. Using fallback evaluation.")
    GROQ_AVAILABLE = False

app = Flask(__name__)

# Configure CORS
CORS(app, origins=['http://localhost:5000', 'http://127.0.0.1:5000', 'http://localhost:3000'])

# Configure logging
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=getattr(logging, os.getenv('LOG_LEVEL', 'INFO')),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/interviewer.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ExcelInterviewer:
    def __init__(self):
        # Basic configuration
        self.config = {
            'max_questions': int(os.getenv('MAX_QUESTIONS', '5')),
            'min_response_length': int(os.getenv('MIN_RESPONSE_LENGTH', '5')),
            'groq_model': os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile'),
            'llm_temperature': float(os.getenv('LLM_TEMPERATURE', '0.1')),
            'max_tokens': int(os.getenv('MAX_TOKENS', '1000')),
            'technical_weight': int(os.getenv('TECHNICAL_ACCURACY_WEIGHT', '40')),
            'methodology_weight': int(os.getenv('METHODOLOGY_WEIGHT', '30')),
            'clarity_weight': int(os.getenv('CLARITY_WEIGHT', '20')),
            'best_practices_weight': int(os.getenv('BEST_PRACTICES_WEIGHT', '10'))
        }
        
        # Initialize Groq client
        self.groq_client = None
        if GROQ_AVAILABLE:
            try:
                groq_api_key = os.getenv('GROQ_API_KEY')
                if groq_api_key:
                    self.groq_client = Groq(api_key=groq_api_key)
                    logger.info("Groq client initialized successfully")
                else:
                    logger.warning("GROQ_API_KEY not found, using fallback evaluation")
            except Exception as e:
                logger.error(f"Failed to initialize Groq client: {str(e)}")
        
        self.sessions = {}
        self.questions = self.load_questions()
        logger.info("ExcelInterviewer initialized")
        
    def load_questions(self):
        """Load questions from CSV data"""
        questions_data = """category,difficulty,question,ideal_answer,points
Basic,1,"Explain the difference between VLOOKUP and INDEX-MATCH functions.","VLOOKUP searches vertically in first column and returns value from specified column. INDEX-MATCH is more flexible - INDEX returns value at intersection, MATCH finds position. INDEX-MATCH can look left, handles column insertions better, and is generally more robust.",20
Basic,1,"How would you remove duplicates from a dataset in Excel?","Multiple methods: 1) Data tab > Remove Duplicates tool, 2) Advanced Filter with 'Unique records only', 3) Using formulas like UNIQUE() function in newer Excel versions. Remove Duplicates is most common for simple cases.",15
Intermediate,2,"You have sales data with dates, regions, and amounts. How would you create a summary showing total sales by month and region?","Create a Pivot Table: 1) Select data, 2) Insert > PivotTable, 3) Drag Date to Rows (group by month), Region to Columns, Amount to Values (SUM). Alternatively use SUMIFS with date criteria or Power Query for complex scenarios.",25
Intermediate,2,"Explain conditional formatting and give a practical example.","Conditional formatting applies visual formatting based on cell values or formulas. Example: Highlight cells >1000 in green, <500 in red for sales targets. Use Home > Conditional Formatting, choose rule type, set conditions and formatting. Useful for data bars, color scales, icon sets.",20
Advanced,3,"How would you automate a repetitive task in Excel?","Multiple approaches: 1) Record Macro (Developer tab), 2) Write VBA code for complex logic, 3) Use Power Query for data transformations, 4) Power Automate for workflow automation. Macros best for repetitive formatting/calculations, Power Query for data processing.",30
Advanced,3,"Explain dynamic arrays and spill ranges in modern Excel.","Dynamic arrays automatically resize based on formula results. Functions like FILTER, SORT, UNIQUE return arrays that 'spill' into adjacent cells. Spill range is the area occupied by dynamic array. Use # to reference entire spill range. Enables more powerful, flexible formulas.",25
Basic,1,"What's the difference between relative and absolute cell references?","Relative references (A1) change when copied to different cells. Absolute references ($A$1) stay fixed. Mixed references ($A1 or A$1) fix either row or column. Use F4 to toggle reference types. Critical for formulas that need fixed reference points.",15
Intermediate,2,"How would you handle errors in Excel formulas?","Use error handling functions: IFERROR, ISERROR, IFNA. Example: =IFERROR(VLOOKUP(A1,data,2,FALSE),'Not Found'). Also use data validation to prevent errors, check for #N/A, #VALUE!, #DIV/0! etc. Power Query also has error handling capabilities.",20"""
        
        questions = []
        reader = csv.DictReader(io.StringIO(questions_data))
        for row in reader:
            questions.append({
                'category': row['category'],
                'difficulty': int(row['difficulty']),
                'question': row['question'],
                'ideal_answer': row['ideal_answer'],
                'points': int(row['points'])
            })
        return questions
    
    def create_session(self):
        """Create new interview session"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            'session_id': session_id,
            'current_question': 0,
            'total_score': 0,
            'max_score': 0,
            'responses': [],
            'difficulty_level': 1,
            'questions_asked': [],
            'started_at': datetime.now().isoformat(),
            'completed_at': None,
            'status': 'active'
        }
        logger.info(f"Created session {session_id}")
        return session_id
    
    def get_next_question(self, session_id):
        """Get next question based on performance"""
        session = self.sessions.get(session_id)
        if not session or session['status'] != 'active':
            return None
            
        # Filter questions by current difficulty and not already asked
        available_questions = [
            q for q in self.questions 
            if q['difficulty'] <= session['difficulty_level'] + 1
            and q not in session['questions_asked']
        ]
        
        if not available_questions or session['current_question'] >= self.config['max_questions']:
            return None
            
        # Select question based on performance
        if session['current_question'] == 0:
            question = next((q for q in available_questions if q['difficulty'] == 1), available_questions[0])
        else:
            success_rate = session['total_score'] / session['max_score'] if session['max_score'] > 0 else 0
            if success_rate > 0.8:
                session['difficulty_level'] = min(3, session['difficulty_level'] + 1)
            elif success_rate < 0.4:
                session['difficulty_level'] = max(1, session['difficulty_level'])
                
            suitable_questions = [q for q in available_questions if q['difficulty'] == session['difficulty_level']]
            question = random.choice(suitable_questions) if suitable_questions else random.choice(available_questions)
        
        session['questions_asked'].append(question)
        session['current_question'] += 1
        session['max_score'] += question['points']
        
        return {
            'question_number': session['current_question'],
            'question': question['question'],
            'category': question['category'],
            'difficulty': question['difficulty'],
            'total_questions': self.config['max_questions']
        }
    
    def evaluate_response_with_groq(self, session_id, response, current_question):
        """Evaluate response using Groq LLM"""
        try:
            if not self.groq_client:
                return None
                
            evaluation_prompt = f"""
You are an expert Excel interviewer. Evaluate this candidate's response to an Excel question.

Question: {current_question['question']}
Ideal Answer: {current_question['ideal_answer']}
Candidate's Response: {response}

Evaluate based on these weighted criteria:
1. Technical Accuracy ({self.config['technical_weight']}%): Is the information correct?
2. Methodology ({self.config['methodology_weight']}%): Does the approach make sense?
3. Clarity ({self.config['clarity_weight']}%): Is the explanation clear and well-structured?
4. Best Practices ({self.config['best_practices_weight']}%): Does it follow Excel best practices?

Provide a score out of {current_question['points']} points and brief feedback.

Respond in JSON format:
{{
    "score": <number>,
    "feedback": "<constructive feedback>",
    "strengths": ["<strength1>", "<strength2>"],
    "improvements": ["<improvement1>", "<improvement2>"]
}}
"""
            
            chat_completion = self.groq_client.chat.completions.create(
                messages=[{"role": "user", "content": evaluation_prompt}],
                model=self.config['groq_model'],
                temperature=self.config['llm_temperature'],
                max_tokens=self.config['max_tokens']
            )
            
            evaluation_text = chat_completion.choices[0].message.content
            evaluation = json.loads(evaluation_text)
            logger.info(f"Groq evaluation completed for session {session_id}: score={evaluation['score']}")
            return evaluation
            
        except Exception as e:
            logger.error(f"Groq evaluation failed for session {session_id}: {str(e)}")
            return None
    
    def evaluate_response_fallback(self, response, current_question):
        """Fallback evaluation system when Groq is not available"""
        response_words = response.split()
        response_length = len(response_words)
        
        base_score = min(current_question['points'], max(1, response_length // 5))
        
        # Keyword matching for technical accuracy
        technical_keywords = {
            'vlookup': ['vlookup', 'lookup', 'vertical'],
            'pivot': ['pivot', 'table', 'summarize', 'group'],
            'formula': ['formula', 'function', 'calculate'],
            'formatting': ['format', 'conditional', 'highlight'],
            'reference': ['reference', 'absolute', 'relative', '$'],
            'macro': ['macro', 'vba', 'automate', 'script']
        }
        
        response_lower = response.lower()
        question_lower = current_question['question'].lower()
        
        keyword_bonus = 0
        found_keywords = []
        
        for topic, keywords in technical_keywords.items():
            if any(keyword in question_lower for keyword in keywords):
                if any(keyword in response_lower for keyword in keywords):
                    keyword_bonus += 2
                    found_keywords.append(topic)
        
        final_score = min(current_question['points'], base_score + keyword_bonus)
        
        # Generate feedback
        if final_score >= current_question['points'] * 0.8:
            feedback = "Good comprehensive answer covering key concepts."
            strengths = ["Covers main points", "Good technical understanding"]
        elif final_score >= current_question['points'] * 0.6:
            feedback = "Solid answer with room for more detail."
            strengths = ["Basic concepts covered"]
        else:
            feedback = "Answer needs more technical detail and examples."
            strengths = ["Response provided"]
        
        improvements = []
        if response_length < 20:
            improvements.append("Provide more detailed explanations")
        if not found_keywords:
            improvements.append("Include more technical terminology")
        if len(improvements) == 0:
            improvements.append("Consider adding practical examples")
        
        return {
            'score': final_score,
            'feedback': feedback,
            'strengths': strengths,
            'improvements': improvements
        }
    
    def evaluate_response(self, session_id, response):
        """Evaluate user response using available method"""
        session = self.sessions.get(session_id)
        if not session or not session['questions_asked']:
            return None
            
        current_question = session['questions_asked'][-1]
        
        # Validate response length
        if len(response.split()) < self.config['min_response_length']:
            return {
                'score': 0,
                'feedback': f'Please provide a more detailed response (minimum {self.config["min_response_length"]} words).',
                'strengths': [],
                'improvements': ['Provide more detailed explanations']
            }
        
        # Try Groq evaluation first, fallback if not available
        evaluation = None
        if self.groq_client:
            evaluation = self.evaluate_response_with_groq(session_id, response, current_question)
        
        if not evaluation:
            evaluation = self.evaluate_response_fallback(response, current_question)
            logger.info(f"Fallback evaluation completed for session {session_id}: score={evaluation['score']}")
        
        # Store response and evaluation
        session['responses'].append({
            'question': current_question['question'],
            'response': response,
            'evaluation': evaluation,
            'timestamp': datetime.now().isoformat()
        })
        
        session['total_score'] += evaluation['score']
        
        return evaluation
    
    def generate_final_report(self, session_id):
        """Generate comprehensive interview report"""
        session = self.sessions.get(session_id)
        if not session:
            return None
            
        session['status'] = 'completed'
        session['completed_at'] = datetime.now().isoformat()
        
        # Calculate overall performance
        overall_percentage = (session['total_score'] / session['max_score']) * 100 if session['max_score'] > 0 else 0
        
        # Determine proficiency level
        if overall_percentage >= 80:
            proficiency = "Advanced"
        elif overall_percentage >= 60:
            proficiency = "Intermediate"
        elif overall_percentage >= 40:
            proficiency = "Basic"
        else:
            proficiency = "Beginner"
        
        # Generate summary report
        detailed_report = f"""
EXCEL SKILLS ASSESSMENT REPORT

Candidate Performance Summary:
- Overall Score: {session['total_score']}/{session['max_score']} ({overall_percentage:.1f}%)
- Proficiency Level: {proficiency}
- Questions Completed: {len(session['responses'])}/{self.config['max_questions']}
- Session Duration: {self._calculate_duration(session)} minutes

Performance Analysis:
"""
        
        for i, response in enumerate(session['responses'], 1):
            eval_data = response['evaluation']
            detailed_report += f"""
Question {i}: {eval_data['score']}/{session['questions_asked'][i-1]['points']} points
- Strengths: {', '.join(eval_data['strengths'])}
- Areas for Improvement: {', '.join(eval_data['improvements'])}
"""
        
        detailed_report += f"""
Overall Assessment:
The candidate demonstrates {proficiency.lower()} Excel proficiency. """
        
        if proficiency == "Advanced":
            detailed_report += "Excellent technical knowledge with strong problem-solving approach."
        elif proficiency == "Intermediate":
            detailed_report += "Good foundational skills with room for advanced feature mastery."
        elif proficiency == "Basic":
            detailed_report += "Basic understanding present, would benefit from additional training."
        else:
            detailed_report += "Limited Excel experience, requires comprehensive training program."
        
        return {
            'session_id': session_id,
            'overall_score': session['total_score'],
            'max_possible_score': session['max_score'],
            'percentage': overall_percentage,
            'proficiency_level': proficiency,
            'questions_answered': len(session['responses']),
            'detailed_responses': session['responses'],
            'report': detailed_report,
            'duration_minutes': self._calculate_duration(session),
            'recommendation': self._get_hiring_recommendation(overall_percentage)
        }
    
    def _calculate_duration(self, session):
        """Calculate interview duration"""
        try:
            start = datetime.fromisoformat(session['started_at'])
            end = datetime.fromisoformat(session.get('completed_at', datetime.now().isoformat()))
            return round((end - start).total_seconds() / 60, 1)
        except:
            return 0
    
    def _get_hiring_recommendation(self, percentage):
        """Get hiring recommendation based on score"""
        if percentage >= 75:
            return "Strong Hire - Excellent Excel skills demonstrated"
        elif percentage >= 60:
            return "Hire - Good Excel foundation with room for growth"
        elif percentage >= 45:
            return "Consider - Basic skills present, may need training"
        else:
            return "No Hire - Insufficient Excel proficiency for role requirements"

# Initialize the interviewer
interviewer = ExcelInterviewer()

@app.route('/start_interview', methods=['POST'])
def start_interview():
    """Start a new interview session"""
    try:
        session_id = interviewer.create_session()
        first_question = interviewer.get_next_question(session_id)
        
        logger.info(f"New interview session started: {session_id}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'message': f'Welcome to the AI Excel Mock Interview! I will ask you {interviewer.config["max_questions"]} questions to assess your Excel skills.',
            'question': first_question,
            'groq_available': interviewer.groq_client is not None
        })
    except Exception as e:
        logger.error(f"Failed to start interview: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/submit_response', methods=['POST'])
def submit_response():
    """Submit response and get next question"""
    try:
        data = request.json
        session_id = data.get('session_id')
        response = data.get('response', '').strip()
        
        if not session_id or not response:
            return jsonify({'success': False, 'error': 'Session ID and response required'}), 400
        
        logger.info(f"Response submitted for session {session_id}")
        
        # Evaluate current response
        evaluation = interviewer.evaluate_response(session_id, response)
        if not evaluation:
            return jsonify({'success': False, 'error': 'Invalid session'}), 400
        
        # Get next question
        next_question = interviewer.get_next_question(session_id)
        
        response_data = {
            'success': True,
            'evaluation': evaluation,
            'next_question': next_question
        }
        
        # If no more questions, generate final report
        if not next_question:
            report = interviewer.generate_final_report(session_id)
            response_data['final_report'] = report
            response_data['interview_complete'] = True
            logger.info(f"Interview completed for session {session_id}")
        
        return jsonify(response_data)
        
    except Exception as e:
        logger.error(f"Failed to submit response: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get_report', methods=['POST'])
def get_report():
    """Get final interview report"""
    try:
        data = request.json
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({'success': False, 'error': 'Session ID required'}), 400
        
        report = interviewer.generate_final_report(session_id)
        if not report:
            return jsonify({'success': False, 'error': 'Session not found or not complete'}), 404
        
        return jsonify({
            'success': True,
            'report': report
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'success': True,
        'message': 'Excel Mock Interviewer API is running',
        'total_questions': len(interviewer.questions),
        'active_sessions': len([s for s in interviewer.sessions.values() if s['status'] == 'active']),
        'groq_available': interviewer.groq_client is not None,
        'version': '2.1.1'
    })

@app.route('/')
def index():
    return render_template('index.html', 
                         title="Excel Mock Interviewer",
                         api_url="http://localhost:5000")

if __name__ == '__main__':
    host = os.getenv('HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5000'))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    logger.info(f"Starting Excel Mock Interviewer API on {host}:{port}")
    logger.info(f"Groq client available: {interviewer.groq_client is not None}")
    
    app.run(debug=debug, host=host, port=port)