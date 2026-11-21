"""Writes ISJ107V_A5_Q3.2_Class.puml from backend/app/models.py, so the class diagram cannot drift from the code.
Run from backend/ with the project's Python:  PYTHONPATH=. python ../docs/a5/uml/gen_class.py
Every attribute, relationship and service operation drawn is checked against the real code; a wrong name stops the script."""
import enum, importlib, os, sys
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("DATABASE_URL", "postgresql://x:x@localhost:5432/x")
from app import models
from app.database import Base

# class -> attributes worth showing (a subset; the check below proves each one exists in the model, and its type is read from the model)
SHOW = {
    "WSA": ["id", "name", "province", "blue_drop_score", "nrw_percent", "maint_pct", "cap_status", "cap_due_date", "risk_level", "lat", "lng"],
    "CitizenReport": ["id", "issue_type", "description", "reference_code", "case_status", "admin_comment", "lat", "lng", "resolved_at"],
    "ReportAssignment": ["id", "status", "instructions", "due_at", "contractor_note", "admin_note", "fixed_at", "closed_at"],
    "Contractor": ["id", "name", "contact_name", "phone", "email", "is_active"],
    "ContractorCoverage": ["issue_types"],
    "User": ["id", "email", "hashed_password", "role", "is_active", "wsa_id", "contractor_id"],
    "RiskScoreHistory": ["risk_level", "probability", "model_source", "model_version", "scored_by", "scored_at"],
    "Alert": ["alert_type", "message", "acknowledged_at"],
    "AuditLog": ["action", "table_name", "old_value", "new_value", "created_at"],
}
# (from, to, from-multiplicity, to-multiplicity, label, foreign key column that proves it)
REL = [
    ("CitizenReport", "WSA", "0..*", "1", "about", "wsa_id"),
    ("ReportAssignment", "CitizenReport", "0..*", "1", "ticket for", "report_id"),
    ("ReportAssignment", "Contractor", "0..*", "1", "worked by", "contractor_id"),
    ("ReportAssignment", "User", "0..*", "0..1", "assigned by", "assigned_by"),
    ("ContractorCoverage", "Contractor", "0..*", "1", "set up for", "contractor_id"),
    ("ContractorCoverage", "WSA", "0..*", "1", "covers", "wsa_id"),
    ("User", "Contractor", "0..*", "0..1", "works for", "contractor_id"),
    ("User", "WSA", "0..*", "0..1", "limited to", "wsa_id"),
    ("Alert", "WSA", "0..*", "1", "raised for", "wsa_id"),
    ("RiskScoreHistory", "WSA", "0..*", "1", "scores", "wsa_id"),
    ("AuditLog", "User", "0..*", "0..1", "done by", "user_id"),
]
# the service classes: (name, [(module, function)], [(target class, label)])  the functions are imported to prove they exist
SERVICES = [
    ("RiskModel", [("ai.predict", "predict_wsa_risk")], [("WSA", "reads"), ("RiskScoreHistory", "results saved as")]),
    ("AiService", [("app.routes.ai", "call_openai"), ("app.routes.ai", "get_cap_draft"), ("ai.query_agent", "run_query_agent")], [("WSA", "reads")]),
    ("AlertService", [("app.alert_helpers", "raise_high_risk_alert"), ("app.alert_helpers", "raise_report_volume_spike_alert"),
                      ("app.alert_helpers", "raise_geo_cluster_alert"), ("app.alert_helpers", "raise_assignment_overdue_alerts")], [("Alert", "creates")]),
    ("TicketRules", [("app.assignment_helpers", "can_serve"), ("app.assignment_helpers", "notify"), ("app.assignment_helpers", "public_repair_status")],
     [("ReportAssignment", "checks")]),
    ("AuditService", [("app.audit_helpers", "write_audit")], [("AuditLog", "writes")]),
]
ENUM_ATTRS = {"UserRole", "IssueType", "AlertType", "ModelSource", "CAPStatus", "RiskLevel", "AuditAction"}
SQL_TYPES = {"UUID": "UUID", "String": "String", "Text": "String", "Float": "Float", "Numeric": "Float", "Integer": "Integer", "Boolean": "Boolean",
             "DateTime": "DateTime", "Date": "Date", "JSONB": "JSON", "JSON": "JSON"}

classes = {m.class_.__name__: m for m in Base.registry.mappers}
def type_name(cls, attr):
    col = classes[cls].columns[attr]
    enum_class = getattr(col.type, "enum_class", None)
    if enum_class is not None: return enum_class.__name__
    return SQL_TYPES.get(type(col.type).__name__, type(col.type).__name__)

for cls, attrs in SHOW.items():
    cols = {c.name for c in classes[cls].columns}
    bad = [a for a in attrs if a not in cols]
    if bad: sys.exit(f"{cls} has no column(s) {bad}")
for a, b, _, _, _, fk in REL:
    fks = {f.parent.name: f.column.table.name for f in classes[a].class_.__table__.foreign_keys}
    if fks.get(fk) != classes[b].class_.__tablename__: sys.exit(f"{a}.{fk} is not a foreign key to {b}")
for name, ops, targets in SERVICES:
    for module, fn in ops:
        if not hasattr(importlib.import_module(module), fn): sys.exit(f"{module} has no function {fn}")
    for target, _ in targets:
        if target not in SHOW and target not in {s[0] for s in SERVICES}: sys.exit(f"{name} points at unknown {target}")
for e in ENUM_ATTRS:
    assert issubclass(getattr(models, e), enum.Enum)

out = ["@startuml", "skinparam shadowing false", "skinparam dpi 200", "skinparam defaultFontName Helvetica", "skinparam classAttributeIconSize 0",
       "left to right direction", "skinparam nodesep 22", "skinparam ranksep 60", "hide empty methods",
       "title HydroSentinel: Class Diagram", ""]
for cls, attrs in SHOW.items():
    out.append(f"class {cls} {{")
    out += [f"  {a} : {type_name(cls, a)}" for a in attrs]
    out.append("}")
for name, ops, _ in SERVICES:
    out.append(f"class {name} <<service>> {{")
    out += [f"  {fn}()" for _, fn in ops]
    out.append("}")
out.append("")
for a, b, ma, mb, label, _ in REL:
    out.append(f'{a} "{ma}" --> "{mb}" {b} : {label}')
for name, _, targets in SERVICES:
    for target, label in targets:
        out.append(f"{name} ..> {target} : {label}")
out.append("@enduml")
open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ISJ107V_A5_Q3.2_Class.puml"), "w").write("\n".join(out) + "\n")
print("class diagram source written:", len(SHOW), "classes,", len(SERVICES), "services,", len(REL), "relationships, all verified against the code")
