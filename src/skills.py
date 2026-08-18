import re
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills"

def get_relevant_skills(objective: str, history: list[str], max_skills: int = 3) -> str:
    """
    Deterministically retrieve the orchestrator skill plus a few specialist
    skills based on keyword matching from the objective and command history.
    """
    skills_text = []
    
    # 1. Always include the boss orchestrator
    orchestrator_path = SKILLS_DIR / "bug-bounty-orchestrator" / "SKILL.md"
    if orchestrator_path.exists():
        content = orchestrator_path.read_text(encoding="utf-8")
        skills_text.append(f"--- SKILL: bug-bounty-orchestrator ---\n{content}")
    
    # 2. Extract words from objective and history to form the search context
    context_text = f"{objective}\n" + "\n".join(history)
    words_in_context = set(re.findall(r'[a-z0-9]+', context_text.lower()))
    
    # 3. Score other skills by keyword matching
    skill_scores = []
    ignore_keywords = {'bug', 'bounty', 'skills', 'advanced', 'client', 'cloud', 'web'}
    
    if SKILLS_DIR.exists():
        for skill_dir in SKILLS_DIR.iterdir():
            if not skill_dir.is_dir() or skill_dir.name == "bug-bounty-orchestrator":
                continue
                
            parts = skill_dir.name.lower().split('-')
            keywords = {p for p in parts if p not in ignore_keywords}
            
            # Simple scoring: count how many keywords from the folder name are in the context
            score = sum(1 for kw in keywords if kw in words_in_context)
            
            # Add some manual synonyms mapping for better matching if needed
            # e.g., if "sql" in words_in_context and "injection" in keywords
            if "sql" in words_in_context and "injection" in keywords:
                score += 1
            if "sqli" in words_in_context and "injection" in keywords:
                score += 1
            if "nmap" in words_in_context and "recon" in keywords:
                score += 1
                
            if score > 0:
                skill_scores.append((score, skill_dir.name, skill_dir))
                
    # 4. Sort by score descending, then alphabetically by name to ensure determinism
    skill_scores.sort(key=lambda x: (-x[0], x[1]))
    
    # 5. Append the top N specialist skills
    for score, name, skill_dir in skill_scores[:max_skills]:
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            content = skill_file.read_text(encoding="utf-8")
            skills_text.append(f"--- SKILL: {name} ---\n{content}")
            
    return "\n\n".join(skills_text)
