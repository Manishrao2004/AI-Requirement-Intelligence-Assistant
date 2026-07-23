"""Requirement Analysis Tools — pure Python @tool functions for LangGraph ToolNode binding.
These tools are visualizable in LangSmith and bound to agents via llm.bind_tools().
"""
import re
from langchain_core.tools import tool


@tool
def validate_requirement(req_id: str, text: str, category: str) -> dict:
    """Validate a single software requirement for clarity, testability, and completeness.

    Call this tool for EACH requirement you extract before including it in the final output.
    Requirements scoring below 60 should be rewritten based on the issues returned.

    Args:
        req_id: The requirement ID (e.g. FR-1, NFR-2, BR-3)
        text: The full requirement text to validate
        category: One of 'functional', 'non_functional', or 'business_rule'

    Returns:
        dict with score (0-100), is_valid flag, list of issues, and a rewrite suggestion.
    """
    issues = []
    score = 100

    # 1. Vague / subjective term check
    vague_terms = [
        "fast", "quick", "easy", "user-friendly", "efficient", "robust",
        "scalable", "flexible", "modern", "simple", "intuitive", "good",
        "better", "best", "appropriate", "adequate", "reasonable", "nice",
        "smooth", "seamless", "powerful", "smart",
    ]
    found_vague = [t for t in vague_terms if re.search(rf"\b{re.escape(t)}\b", text, re.IGNORECASE)]
    if found_vague:
        issues.append(
            f"Vague/subjective terms: {', '.join(found_vague)}. "
            "Replace with measurable criteria (e.g., 'response time < 200 ms')."
        )
        score -= min(30, len(found_vague) * 10)

    # 2. Non-functional requirements must have a measurable metric
    if category == "non_functional" and not re.search(r"\d+", text):
        issues.append(
            "Non-functional requirement lacks a measurable metric. "
            "Add a concrete target (e.g., 99.9% uptime, < 500 ms, 10 000 concurrent users)."
        )
        score -= 25

    # 3. Minimum detail check
    if len(text.split()) < 6:
        issues.append(
            "Too brief — requirement cannot be implemented or tested from this description. "
            "Provide context, actor, action, and acceptance criteria."
        )
        score -= 30

    # 4. No clear actor/subject
    if not re.search(
        r"\b(system|user|admin|customer|client|api|service|application|platform|module|database)\b",
        text,
        re.IGNORECASE,
    ):
        issues.append(
            "No clear actor or subject. "
            "Specify who or what performs the action (e.g., 'The system shall…', 'The user can…')."
        )
        score -= 15

    # 5. 'Shall be' without a measurable spec
    if re.search(r"\bshall be\b", text, re.IGNORECASE) and not re.search(r"\d+", text):
        issues.append(
            "'Shall be' without a measurable target is ambiguous. "
            "Add a specific, verifiable acceptance criterion."
        )
        score -= 10

    # 6. Compound requirement (contains 'and' linking two distinct actions — may need splitting)
    verbs = re.findall(r"\b(shall|must|should|will)\b", text, re.IGNORECASE)
    if len(verbs) > 2:
        issues.append(
            "Possible compound requirement — contains multiple obligations. "
            "Consider splitting into separate requirements for better traceability."
        )
        score -= 10

    score = max(0, score)
    return {
        "req_id": req_id,
        "score": score,
        "is_valid": score >= 60,
        "issues": issues,
        "suggestion": (
            "Rewrite as: 'The [actor] shall [specific, verifiable action] [measurable constraint / acceptance criterion].'"
            if issues
            else "Well-defined requirement — no issues found."
        ),
    }


@tool
def check_conflict(
    req_a_id: str,
    req_a_text: str,
    req_b_id: str,
    req_b_text: str,
) -> dict:
    """Check whether two requirements conflict or contradict each other.

    Call this tool when two requirements appear potentially contradictory — for example,
    one specifies 'always online' while another says 'works offline', or they assign
    different numeric values to the same parameter.

    Args:
        req_a_id: ID of the first requirement (e.g. FR-3)
        req_a_text: Full text of the first requirement
        req_b_id: ID of the second requirement (e.g. FR-7)
        req_b_text: Full text of the second requirement

    Returns:
        dict with has_conflict flag, conflict_description, and a resolution recommendation.
    """
    signals = []

    # 1. Numeric value contradiction on shared keywords
    nums_a = set(re.findall(r"\b\d+(?:\.\d+)?\b", req_a_text))
    nums_b = set(re.findall(r"\b\d+(?:\.\d+)?\b", req_b_text))
    if nums_a and nums_b and nums_a.isdisjoint(nums_b):
        stop_words = {"shall", "should", "must", "system", "user", "that", "with", "have", "been", "this", "from"}
        shared = (
            {w.lower() for w in req_a_text.split()} &
            {w.lower() for w in req_b_text.split()}
        ) - stop_words
        meaningful = {w for w in shared if len(w) > 4}
        if meaningful:
            signals.append(
                f"Contradictory numeric values ({', '.join(nums_a)} vs {', '.join(nums_b)}) "
                f"on shared topic: {', '.join(list(meaningful)[:3])}"
            )

    # 2. Logical / semantic opposites
    opposite_pairs = [
        (r"\b(always|mandatory|must always|required at all times)\b", r"\b(never|prohibited|must not|forbidden|not allowed)\b"),
        (r"\b(online|connected|real.?time|live)\b",                  r"\b(offline|disconnected|cached|local.?only)\b"),
        (r"\b(synchronous|blocking|sequential)\b",                    r"\b(asynchronous|non.?blocking|concurrent)\b"),
        (r"\b(encrypt(ed)?|encrypted at rest)\b",                     r"\b(plain.?text|unencrypted|cleartext)\b"),
        (r"\b(public|open|unauthenticated|anonymous)\b",              r"\b(private|restricted|authenticated|authorized only)\b"),
        (r"\b(read.?only|immutable)\b",                               r"\b(editable|mutable|writable|modifiable)\b"),
        (r"\b(single.?sign.?on|sso)\b",                               r"\b(separate login|individual credentials)\b"),
    ]
    for pos_pat, neg_pat in opposite_pairs:
        a_pos = bool(re.search(pos_pat, req_a_text, re.IGNORECASE))
        b_neg = bool(re.search(neg_pat, req_b_text, re.IGNORECASE))
        a_neg = bool(re.search(neg_pat, req_a_text, re.IGNORECASE))
        b_pos = bool(re.search(pos_pat, req_b_text, re.IGNORECASE))
        if (a_pos and b_neg) or (a_neg and b_pos):
            signals.append("Logical contradiction: requirements specify mutually exclusive behaviors")
            break

    has_conflict = bool(signals)
    return {
        "req_a_id": req_a_id,
        "req_b_id": req_b_id,
        "has_conflict": has_conflict,
        "conflict_description": signals[0] if signals else None,
        "recommendation": (
            f"Resolve contradiction between {req_a_id} and {req_b_id}: "
            "merge into one requirement, add conditional scoping (e.g., 'when X, do Y; otherwise Z'), "
            "or remove the lower-priority requirement."
            if has_conflict
            else "No conflict detected — requirements are compatible."
        ),
    }


@tool
def find_coverage_gaps(
    title: str,
    has_authentication: bool,
    has_authorization: bool,
    has_error_handling: bool,
    has_logging_monitoring: bool,
    has_security: bool,
    has_data_backup: bool,
    has_accessibility: bool,
    has_performance: bool,
) -> list:
    """Identify which standard software requirement categories are absent from the document.

    Call this tool ONCE after reviewing all extracted requirements.
    Set each boolean flag to True if the document already covers that category, False if it is missing.
    Returns a prioritised list of gap recommendations.

    Args:
        title: Project/system title for context
        has_authentication: True if login, logout, or session management requirements exist
        has_authorization: True if role-based access control or permission requirements exist
        has_error_handling: True if error messages, retries, or fallback behavior requirements exist
        has_logging_monitoring: True if audit trail, logging, or monitoring requirements exist
        has_security: True if encryption, OWASP, GDPR, or vulnerability management requirements exist
        has_data_backup: True if backup, recovery, RTO, or RPO requirements exist
        has_accessibility: True if WCAG, screen reader, or keyboard navigation requirements exist
        has_performance: True if response time, throughput, or SLA requirements exist

    Returns:
        List of gap dicts, each with 'category', 'suggestion', and 'reason'.
    """
    checks = [
        (
            has_authentication,
            "Authentication",
            (
                "Add requirements for: user login/logout, session timeout, "
                "multi-factor authentication (MFA), password policy, and account lockout after failed attempts."
            ),
            "Authentication is implied but no explicit requirements are defined — critical for any multi-user system.",
        ),
        (
            has_authorization,
            "Authorization & Role-Based Access Control",
            (
                "Add requirements for: user roles (admin, editor, viewer), "
                "permission matrices, privilege escalation prevention, and least-privilege enforcement."
            ),
            "Without RBAC requirements, access control cannot be designed or tested.",
        ),
        (
            has_error_handling,
            "Error Handling & Resilience",
            (
                "Add requirements for: user-facing error messages (no stack traces), "
                "retry logic with back-off, circuit breakers, graceful degradation, and timeout handling."
            ),
            "Missing error handling leads to poor UX and unhandled failures in production.",
        ),
        (
            has_logging_monitoring,
            "Audit Logging & Observability",
            (
                "Add requirements for: structured audit logs (who, what, when), "
                "log retention period, real-time alerting thresholds, and a health/status dashboard."
            ),
            "Logging is essential for debugging, security forensics, and regulatory compliance.",
        ),
        (
            has_security,
            "Security & Compliance",
            (
                "Add requirements for: TLS encryption in transit, AES-256 at rest, "
                "OWASP Top 10 mitigations, GDPR/HIPAA data handling, and annual penetration testing."
            ),
            "Security requirements prevent data breaches and ensure regulatory compliance.",
        ),
        (
            has_data_backup,
            "Data Backup & Disaster Recovery",
            (
                "Add requirements for: automated daily backups, "
                "off-site storage, RTO ≤ 4 hours, RPO ≤ 1 hour, and quarterly DR drills."
            ),
            "Without DR requirements, the system has no defined strategy for data loss or outage events.",
        ),
        (
            has_accessibility,
            "Accessibility",
            (
                "Add requirements for: WCAG 2.1 Level AA compliance, "
                "screen reader compatibility (ARIA labels), keyboard-only navigation, "
                "and minimum 4.5:1 color contrast ratio."
            ),
            "Accessibility ensures legal compliance (ADA, EAA) and inclusive user experience.",
        ),
        (
            has_performance,
            "Performance & Scalability SLAs",
            (
                "Add requirements for: API response time (p95 < 200 ms), "
                "page load time (< 3 s on 4G), concurrent user capacity, "
                "throughput (req/s), and auto-scaling triggers."
            ),
            "Performance SLAs are critical for system acceptance testing and infrastructure capacity planning.",
        ),
    ]

    return [
        {"category": category, "suggestion": suggestion, "reason": reason}
        for has_it, category, suggestion, reason in checks
        if not has_it
    ]
