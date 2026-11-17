"""Writes ISJ107V_A5_Q3.2_Class.puml from backend/app/models.py, so the class diagram cannot drift from the code.
Run from backend/ with the project's Python:  python ../docs/a5/uml/gen_class.py
Every attribute and relationship drawn is checked against the real SQLAlchemy models; a wrong name stops the script."""
import enum, os, sys
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
from app import models
from app.database import Base

# class -> attributes worth showing (a subset; the audit proves each one exists in the model)
SHOW = {
    "WSA": ["name", "province", "blue_drop_score", "nrw_percent", "maint_pct", "cap_status", "risk_level", "lat", "lng"],
    "CitizenReport": ["issue_type", "description", "reference_code", "case_status", "admin_comment", "lat", "lng", "created_at", "resolved_at"],
    "User": ["email", "hashed_password", "role", "is_active", "wsa_id", "contractor_id", "last_login_at"],
    "Contractor": ["name", "contact_name", "phone", "email", "is_active"],
    "ContractorCoverage": ["contractor_id", "wsa_id", "issue_types"],
    "ReportAssignment": ["status", "instructions", "due_at", "contractor_note", "rejected_reason", "admin_note", "accepted_at", "started_at", "fixed_at", "closed_at"],
    "Notification": ["title", "body", "assignment_id", "read_at", "created_at"],
    "Alert": ["alert_type", "message", "acknowledged_at", "created_at"],
    "RiskScoreHistory": ["risk_level", "probability", "model_source", "model_version", "scored_at"],
    "AuditLog": ["action", "table_name", "record_id", "old_value", "new_value", "ip_address", "created_at"],
    "RefreshToken": ["token_hash", "expires_at", "revoked_at"],
    "Summary": ["content", "generated_at"],
}
# (from, to, from-multiplicity, to-multiplicity, label, foreign key column that proves it)
REL = [
    ("CitizenReport", "WSA", "*", "1", "about", "wsa_id"),
    ("ReportAssignment", "CitizenReport", "*", "1", "ticket for", "report_id"),
    ("ReportAssignment", "Contractor", "*", "1", "worked by", "contractor_id"),
    ("ReportAssignment", "User", "*", "0..1", "assigned by", "assigned_by"),
    ("ContractorCoverage", "Contractor", "*", "1", "", "contractor_id"),
    ("ContractorCoverage", "WSA", "*", "1", "covers", "wsa_id"),
    ("User", "Contractor", "*", "0..1", "works for", "contractor_id"),
    ("User", "WSA", "*", "0..1", "limited to", "wsa_id"),
    ("Notification", "User", "*", "1", "for", "user_id"),
    ("Notification", "ReportAssignment", "*", "0..1", "about", "assignment_id"),
    ("Alert", "WSA", "*", "1", "raised for", "wsa_id"),
    ("RiskScoreHistory", "WSA", "*", "1", "scores", "wsa_id"),
    ("AuditLog", "User", "*", "0..1", "done by", "user_id"),
    ("RefreshToken", "User", "*", "1", "session of", "user_id"),
]
ENUMS = ["UserRole", "IssueType", "AlertType", "ModelSource", "CAPStatus", "RiskLevel"]

classes = {m.class_.__name__: m for m in Base.registry.mappers}
for cls, attrs in SHOW.items():
    cols = {c.name for c in classes[cls].columns}
    bad = [a for a in attrs if a not in cols]
    if bad: sys.exit(f"{cls} has no column(s) {bad}")
for a, b, _, _, _, fk in REL:
    fks = {f.parent.name: f.column.table.name for f in classes[a].class_.__table__.foreign_keys}
    if fks.get(fk) != classes[b].class_.__tablename__: sys.exit(f"{a}.{fk} is not a foreign key to {b}")
for e in ENUMS:
    assert issubclass(getattr(models, e), enum.Enum)

out = ["@startuml", "skinparam shadowing false", "skinparam dpi 200", "skinparam defaultFontName Helvetica", "skinparam classAttributeIconSize 0",
       "left to right direction", "skinparam nodesep 25", "skinparam ranksep 60", "hide empty methods", "title HydroSentinel: Class Diagram (generated from backend/app/models.py)", ""]
for cls, attrs in SHOW.items():
    out.append(f"class {cls} {{")
    out += [f"  {a}" for a in attrs]
    out.append("}")
for e in ENUMS:
    out.append(f"enum {e} {{")
    out += [f"  {v.value}" for v in getattr(models, e)]
    out.append("}")
out.append("")
for a, b, ma, mb, label, _ in REL:
    out.append(f'{a} "{ma}" --> "{mb}" {b}' + (f" : {label}" if label else ""))
for cls, attr, enm in [("User", "role", "UserRole"), ("CitizenReport", "issue_type", "IssueType"), ("Alert", "alert_type", "AlertType"),
                       ("RiskScoreHistory", "model_source", "ModelSource"), ("WSA", "cap_status", "CAPStatus"), ("WSA", "risk_level", "RiskLevel")]:
    out.append(f"{cls} ..> {enm} : {attr}")
out.append("@enduml")
open(os.path.join(os.path.dirname(__file__), "ISJ107V_A5_Q3.2_Class.puml"), "w").write("\n".join(out) + "\n")
print("class diagram source written:", len(SHOW), "classes,", len(REL), "relationships, all verified against models.py")
