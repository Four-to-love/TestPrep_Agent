# agents/skills/nmsi_calculator/nmsi_calculator.py

# Encapsulated constants so the skill is fully portable
STATE_CUTOFFS = {
    "AL": 212, "AK": 212, "AZ": 218, "AR": 212, "CA": 221, "CO": 217, 
    "CT": 221, "DE": 220, "FL": 216, "GA": 219, "HI": 216, "ID": 214, 
    "IL": 219, "IN": 215, "IA": 212, "KS": 214, "KY": 212, "LA": 212, 
    "ME": 214, "MD": 222, "MA": 222, "MI": 216, "MN": 218, "MS": 212, 
    "MO": 214, "MT": 212, "NE": 213, "NV": 215, "NH": 219, "NJ": 223, 
    "NM": 212, "NY": 220, "NC": 219, "ND": 212, "OH": 216, "OK": 212, 
    "OR": 217, "PA": 219, "RI": 217, "SC": 212, "SD": 212, "TN": 215, 
    "TX": 219, "UT": 212, "VT": 216, "VA": 221, "WA": 220, "WV": 212, 
    "WI": 215, "WY": 212, "DC": 223, "US Territories": 212, "International": 223
}

def calculate_selection_index(rw_score: int, math_score: int) -> int:
    """Calculates the National Merit Selection Index (NMSI) out of 228."""
    if not rw_score or not math_score:
        return 0
    return int(((2 * rw_score) + math_score) / 10)

def get_state_target(state_code: str) -> int:
    """Retrieves the NMSI target for a given state. Defaults to 220 if not found."""
    # Clean the input to ensure it matches our dictionary keys
    clean_code = str(state_code).strip().upper()
    return STATE_CUTOFFS.get(clean_code, 220)