import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Base configuration class"""
    
    # ========================================
    # API KEYS & EXTERNAL SERVICES
    # ========================================
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # ========================================
    # APPLICATION SETTINGS
    # ========================================
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '5000'))
    
    # ========================================
    # INTERVIEW CONFIGURATION
    # ========================================
    MAX_QUESTIONS = int(os.getenv('MAX_QUESTIONS', '5'))
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '30'))  # minutes
    MIN_RESPONSE_LENGTH = int(os.getenv('MIN_RESPONSE_LENGTH', '5'))  # words
    
    # ========================================
    # LLM SETTINGS
    # ========================================
    GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
    LLM_TEMPERATURE = float(os.getenv('LLM_TEMPERATURE', '0.1'))
    MAX_TOKENS = int(os.getenv('MAX_TOKENS', '1000'))
    
    # ========================================
    # SCORING CONFIGURATION
    # ========================================
    SCORING_WEIGHTS = {
        'technical_accuracy': int(os.getenv('TECHNICAL_ACCURACY_WEIGHT', '40')),
        'methodology': int(os.getenv('METHODOLOGY_WEIGHT', '30')),
        'clarity': int(os.getenv('CLARITY_WEIGHT', '20')),
        'best_practices': int(os.getenv('BEST_PRACTICES_WEIGHT', '10'))
    }
    
    PROFICIENCY_THRESHOLDS = {
        'advanced': int(os.getenv('ADVANCED_THRESHOLD', '80')),
        'intermediate': int(os.getenv('INTERMEDIATE_THRESHOLD', '60')),
        'basic': int(os.getenv('BASIC_THRESHOLD', '40'))
    }
    
    # ========================================
    # SECURITY SETTINGS
    # ========================================
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '30'))
    
    # ========================================
    # LOGGING CONFIGURATION
    # ========================================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'logs/interviewer.log')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # ========================================
    # QUESTION BANK CONFIGURATION
    # ========================================
    QUESTION_DIFFICULTIES = {
        'basic': 1,
        'intermediate': 2,
        'advanced': 3
    }
    
    ADAPTIVE_DIFFICULTY_SETTINGS = {
        'increase_threshold': 0.8,  # Increase difficulty if success rate > 80%
        'decrease_threshold': 0.4,  # Keep/decrease if success rate < 40%
        'min_difficulty': 1,
        'max_difficulty': 3
    }
    
    # ========================================
    # FEEDBACK SETTINGS
    # ========================================
    FEEDBACK_TEMPLATES = {
        'excellent': "Excellent response! {feedback}",
        'good': "Good answer. {feedback}",
        'satisfactory': "Satisfactory response. {feedback}",
        'needs_improvement': "This area needs improvement. {feedback}"
    }
    
    # ========================================
    # HIRING RECOMMENDATIONS
    # ========================================
    HIRING_RECOMMENDATIONS = {
        75: "Strong Hire - Excellent Excel skills demonstrated",
        60: "Hire - Good Excel foundation with room for growth", 
        45: "Consider - Basic skills present, may need training",
        0: "No Hire - Insufficient Excel proficiency for role requirements"
    }
    
    @classmethod
    def validate_config(cls):
        """Validate configuration and return list of errors"""
        errors = []
        
        # Check required fields
        if not cls.GROQ_API_KEY:
            errors.append("GROQ_API_KEY is required")
            
        # Validate scoring weights sum to 100
        total_weight = sum(cls.SCORING_WEIGHTS.values())
        if total_weight != 100:
            errors.append(f"Scoring weights must sum to 100, current sum: {total_weight}")
            
        # Validate thresholds are in ascending order
        thresholds = cls.PROFICIENCY_THRESHOLDS
        if not (thresholds['basic'] < thresholds['intermediate'] < thresholds['advanced']):
            errors.append("Proficiency thresholds must be in ascending order")
            
        # Validate positive values
        if cls.MAX_QUESTIONS <= 0:
            errors.append("MAX_QUESTIONS must be positive")
            
        if cls.MIN_RESPONSE_LENGTH <= 0:
            errors.append("MIN_RESPONSE_LENGTH must be positive")
            
        return errors
    
    @classmethod
    def get_config_summary(cls):
        """Get configuration summary for logging/debugging"""
        return {
            'max_questions': cls.MAX_QUESTIONS,
            'session_timeout': cls.SESSION_TIMEOUT,
            'groq_model': cls.GROQ_MODEL,
            'scoring_weights': cls.SCORING_WEIGHTS,
            'proficiency_thresholds': cls.PROFICIENCY_THRESHOLDS,
            'has_groq_key': bool(cls.GROQ_API_KEY)
        }

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    FLASK_ENV = 'development'
    LOG_LEVEL = 'DEBUG'

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    FLASK_ENV = 'production'
    LOG_LEVEL = 'INFO'
    
    # Override with more secure defaults
    SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '15'))  # Shorter timeout
    RATE_LIMIT_PER_MINUTE = int(os.getenv('RATE_LIMIT_PER_MINUTE', '10'))  # Stricter rate limiting

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Override for testing
    MAX_QUESTIONS = 3
    MIN_RESPONSE_LENGTH = 1
    SESSION_TIMEOUT = 5

# Configuration factory
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(config_name=None):
    """Get configuration based on environment or name"""
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    return config_map.get(config_name, config_map['default'])

# Convenience function to get current config
def current_config():
    """Get current configuration instance"""
    return get_config()()

# Excel-specific configuration helpers
class ExcelQuestionConfig:
    """Configuration for Excel questions and evaluation"""
    
    QUESTION_CATEGORIES = [
        'Basic Functions',
        'Data Analysis', 
        'Pivot Tables',
        'Formulas & Functions',
        'Data Visualization',
        'Macros & Automation',
        'Data Management',
        'Advanced Analytics'
    ]
    
    DIFFICULTY_PROGRESSION = {
        1: ['VLOOKUP', 'SUM', 'AVERAGE', 'Cell References'],
        2: ['Pivot Tables', 'Conditional Formatting', 'SUMIFS', 'Data Validation'],
        3: ['Macros', 'VBA', 'Power Query', 'Dynamic Arrays', 'Complex Modeling']
    }
    
    EVALUATION_RUBRIC = {
        'technical_accuracy': {
            'description': 'Correctness of Excel knowledge and terminology',
            'excellent': 'Completely accurate with advanced insights',
            'good': 'Mostly accurate with minor gaps', 
            'satisfactory': 'Generally correct but lacks depth',
            'poor': 'Contains significant technical errors'
        },
        'methodology': {
            'description': 'Logical approach and problem-solving method',
            'excellent': 'Optimal approach with alternatives considered',
            'good': 'Sound methodology with good reasoning',
            'satisfactory': 'Basic approach that would work',
            'poor': 'Flawed or inefficient methodology'
        },
        'clarity': {
            'description': 'Clear communication and explanation',
            'excellent': 'Crystal clear with excellent structure',
            'good': 'Clear and well-organized explanation',
            'satisfactory': 'Understandable but could be clearer',
            'poor': 'Confusing or poorly structured'
        },
        'best_practices': {
            'description': 'Awareness of Excel best practices and efficiency',
            'excellent': 'Demonstrates advanced best practices',
            'good': 'Shows good awareness of best practices',
            'satisfactory': 'Basic understanding of good practices',
            'poor': 'Limited awareness of best practices'
        }
    }

# Session management configuration
class SessionConfig:
    """Configuration for session management"""
    
    SESSION_STATES = [
        'initialized',
        'in_progress', 
        'completed',
        'expired',
        'error'
    ]
    
    SESSION_DATA_STRUCTURE = {
        'session_id': str,
        'current_question': int,
        'total_score': int,
        'max_score': int,
        'responses': list,
        'difficulty_level': int,
        'questions_asked': list,
        'started_at': str,
        'completed_at': str,
        'status': str,
        'candidate_info': dict
    }