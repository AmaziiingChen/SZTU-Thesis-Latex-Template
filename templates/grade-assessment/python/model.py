from pathlib import Path
import sys
TEMPLATES_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TEMPLATES_DIR))
from common.python.assessment_forms import DataError, validate_data as _validate
def validate_data(raw):
    return _validate(raw, "grade-assessment")
