from typing import Dict, Any

def route_intent(message: str) -> Dict[str, Any]:
    """
    Advanced Cognitive Classifier for SolGent.
    Segments student and corporate employee tasks to enforce tailored system postures.
    """
    msg_lower = message.lower()
    
    intent = {
        "workflow": "GENERAL_KNOWLEDGE",
        "needs_youtube": False,
        "needs_commerce": False,
        "yt_query": message,
        "commerce_query": message,
        "system_hint": ""
    }

    # 1. DEVELOPER WORKSPACE ENGINE
    if any(k in msg_lower for k in ["code", "bug", "error", "api", "docker", "git", "database", "function", "compile", "syntax"]):
        intent["workflow"] = "DEVELOPER_WORKSPACE"
        intent["system_hint"] = (
            "The user is operating inside a software engineering workspace. Prioritize clean documentation, "
            "production-grade error isolation parameters, and safe execution contexts. Always format code using markdown block syntaxes."
        )
        if "error" in msg_lower or "bug" in msg_lower:
            intent["system_hint"] += " Provide an isolated root-cause hypothesis followed by an explicit step-by-step patch path."
        return intent

    # 2. STUDENT KNOWLEDGE COMPANION
    elif any(k in msg_lower for k in ["explain", "learn", "study", "exam", "syllabus", "concept", "theory", "why does", "definition"]):
        intent["workflow"] = "STUDENT_COMPANION"
        intent["needs_youtube"] = True  
        intent["yt_query"] = f"{message} comprehensive academic tutorial"
        intent["system_hint"] = (
            "The user is seeking conceptual domain mastery. Break down dense definitions using clean practical analogies, "
            "sequential operational logic, and crisp key-takeaway highlights. Avoid monolithic walls of text."
        )
        return intent

    # 3. TECHNICAL DIY HARDWARE & RESOURCE PROCUREMENT
    elif any(k in msg_lower for k in ["build", "hardware", "component", "buy", "sensor", "arduino", "raspberry", "schematic", "tools", "purchase"]):
        intent["workflow"] = "DIY_HARDWARE"
        intent["needs_youtube"] = True
        intent["needs_commerce"] = True  
        intent["yt_query"] = f"how to build {message} electronics step by step"
        intent["commerce_query"] = message
        intent["system_hint"] = (
            "The user is mapping physical hardware components or procurement requirements. Itemize exact tooling profiles, "
            "pinout schema precautions, and safety parameters. Evaluate suggestions based on strict comparative functional pros and cons."
        )
        return intent

    # 4. EMPLOYEE ADMINISTRATIVE PRODUCTIVITY
    elif any(k in msg_lower for k in ["draft", "email", "summary", "report", "resume", "portfolio", "optimize statement", "roadmap", "proposal"]):
        intent["workflow"] = "EMPLOYEE_PRODUCTIVITY"
        intent["system_hint"] = (
            "The user is pursuing executive corporate production targets. Maintain an elite, high-impact business configuration tone. "
            "Utilize metric-driven formatting structures and concise executive action summary bullet points."
        )
        return intent

    intent["system_hint"] = "Provide an elite, highly informative, balanced, and contextually granular response."
    return intent