# Policy-Based Agentic Safety v2
## Governed Multi-Stage Orchestration at Production Scale

**Tony Ochinang — TonyOS Lab**
**DAF v0.2.0 — May 2026**

---

## Abstract

Policy-Based Agentic Safety (PBAS) v1 established the foundational claim: *the model proposes, the system governs*. Every LLM action in a PBAS-governed system passes through a deterministic policy engine before execution. The model never acts unilaterally.

PBAS v2 extends this to multi-stage cognitive orchestration. A single user request now traverses four governed stages — Planning, Validation, Execution, and Collection — each with its own governance layer, each with its own LLM call, each with its own audit record. The governance principle does not weaken as the pipeline grows. It compounds.

This paper presents the PBAS v2 architecture as implemented in the Deterministic Agentic Framework (DAF) v0.2.0, validated by 972 tests including 77 adversarial tests, and demonstrated in two production-pattern Django applications. We show that multi-stage agentic governance is achievable without sacrificing framework-agnosticism, config-driven deployability, or the immutable audit guarantees that PBAS v1 established.

---

## 1. Introduction

### 1.1 The Limitation of Single-Stage Governance

PBAS v1 governed a single cognitive loop: the LLM proposes a plan, the policy engine evaluates it, a scoped agent executes approved steps. This model works for simple, bounded workflows. It breaks under three conditions that production systems routinely encounter:

**Complex tasks require decomposition.** A request to "summarise this financial report and extract all entities" is not one task. It is four tasks — read, classify, summarise, extract — with different tool requirements, different risk profiles, and different governance rules. A single planning call cannot adequately decompose, govern, and execute all four simultaneously.

**Governance decisions require context.** Approving a plan is different from approving an execution strategy. Validating that a tool call is safe is different from validating that the plan's intent is safe. A single policy evaluation cannot assess both semantic intent (what is this trying to do?) and structural safety (what tools will it actually call?) in one pass.

**Audit trails must be stage-aware.** A tamper-evident audit record that says "plan approved, workflow completed" is insufficient for compliance. Regulators and operators need to know which tasks were planned, which rules were evaluated against which tasks, which tools were called, and what each tool returned — staged, attributable, immutable.

### 1.2 PBAS v2: Multi-Stage Governed Orchestration

PBAS v2 addresses these limitations by extending the governance principle across four cognitive stages, each governed independently:

```
User Request
    ↓
[PLANNER STAGE]       LLM proposes a multi-task plan
    ↓
[VALIDATOR STAGE]     Two-layer governance:
                        Layer 1: Structural check (synchronous, no LLM)
                        Layer 2: Hybrid validator (LLM annotates → Rule engine decides)
    ↓
[EXECUTOR STAGE]      LLM coordinates per-task execution via MCP tool calls
    ↓
[COLLECTOR STAGE]     LLM assembles final response from task outputs
    ↓
Final Response + Audit Trail
```

The central claim of PBAS v1 — *the model proposes, the system governs* — holds at every stage. The planner proposes a plan. The validator governs it. The executor proposes tool calls. The MCP governance layer governs them. The collector proposes a final response. The output contract governs its structure. No stage acts without a corresponding governance layer.

### 1.3 Scope of This Paper

This paper covers:
- The PBAS v2 architecture and its four cognitive stages (Section 2)
- The Hybrid Validator: structural check + LLM annotation + rule engine (Section 3)
- MCP tool governance: how external tool access is governed (Section 4)
- Audit persistence and checkpointing: operational guarantees (Section 5)
- Real HITL gates: how human review is integrated structurally (Section 6)
- Config-driven deployment: the Django integration pattern (Section 7)
- Test evidence: 972 tests, 77 adversarial tests (Section 8)
- PBAS v2 claim matrix (Section 9)

---

## 2. Four-Stage Cognitive Architecture

### 2.1 Design Principle: Separation of Cognitive Concerns

Each stage does exactly one cognitive function. No stage can perform another stage's function. This separation is enforced architecturally — the stages are independent classes with independent LLM calls, independent output schemas, and independent governance layers.

```
Stage        Cognitive Function          LLM Role           Governance
────────────────────────────────────────────────────────────────────────
Planner      Decompose task into         Proposes sub-tasks  Budget + agent
             governed sub-tasks          with rationale      permission check

Validator    Assess safety of plan       Annotates semantic  Rule engine decides
             against policy              properties only     based on annotations

Executor     Coordinate task execution   Proposes tool       MCP governance layer
             via MCP tool calls          call sequences      enforces per-tool rules

Collector    Assemble final response     Proposes response   Output contract
             from task outputs           from outputs        schema validation
```

### 2.2 The Planner Stage

The planner receives the user's task and produces a `PlanProposal` — a structured decomposition of the task into governable sub-tasks. Each sub-task specifies:

- `task_id` — unique identifier, referenced in all downstream stages
- `name` — human-readable description of what the task does
- `agent_required` — which agent class handles this task
- `tools_required` — which MCP tools this task will call
- `estimated_cost` — cost estimate in USD, checked against budget policy
- `task_type` — type classification for permission checking
- `rationale` — the planner's reasoning, preserved in audit trail

The planner never has access to tools, agents, or execution context. Its output is a proposal only. No step executes until the validator approves the plan.

**Key invariant:** `PlanProposal` is immutable from the moment the planner produces it. The validator, executor, and collector all receive the same `PlanProposal`. No downstream stage can modify what the planner proposed.

### 2.3 The Validator Stage

The validator is the governance kernel of PBAS v2. It consists of two independent layers that execute in sequence:

**Layer 1 — Structural Check (synchronous, no LLM):**

Before any LLM call, the rule engine performs deterministic checks on the plan:

- Agent permission: is `agent_required` defined in policy `agent_roles`?
- Tool permission: is every tool in `tools_required` listed in the agent's `permitted_tools`?
- Task type permission: is `task_type` in the agent's `permitted_task_types`?
- Step budget: does `estimated_cost` exceed `budget_policy.max_cost_per_step_usd`?
- Workflow budget: does `total_estimated_cost` exceed `budget_policy.max_cost_per_workflow_usd`?

Any structural violation immediately rejects the plan. No LLM annotation is requested. No human review is possible. The violation is final.

**Layer 2 — Hybrid Validation (LLM annotates, rule engine decides):**

If Layer 1 passes, the validator LLM annotates each task's semantic properties:

- `action_class` — what kind of action is this? (read_only, write, delete, send, publish, execute, transform, query)
- `reversible` — can this action be undone?
- `touches_pii` — does this task access personally identifiable information?
- `external_access` — does this task call external services?
- `confidence` — the annotator's confidence in its own annotation

**Critical: the annotator classifies. The rule engine decides.**

The annotator's output is immediately subjected to ground truth override from the tool registry. If the tool governance config says a tool's `action_class` is `delete`, that overrides any annotation that says `read_only`. Tool config is authoritative. LLM annotation is advisory.

The rule engine then evaluates:
- `risk_policy.always_gate_action_classes` — gates regardless of annotation
- `risk_policy.irreversible_min_confidence` — gates low-confidence irreversible actions
- `risk_policy.gate_on_pii_access` — gates PII access
- `risk_policy.gate_on_external_access` — gates external calls
- `compliance_rules` — evaluates every configured rule in order

The final decision is exactly one of: `approve` | `reject` | `gate`. The decision is produced by the rule engine, not the LLM. The LLM provides facts. The policy produces verdicts.

### 2.4 The Executor Stage

The executor receives an approved plan and coordinates its execution. For each sub-task, it:

1. Instantiates the appropriate agent with its `ScopedContext` — a runtime object containing only the tools the agent is permitted to use
2. Calls the agent's LLM with the task description
3. Calls each MCP tool the agent requests
4. Collects the tool output as a `TaskOutput`
5. Proceeds to the next task

**MCP tool governance** enforces per-tool policy at the call level:
- `action_class` from tool governance config is authoritative (not from LLM response)
- `expose_tools` in server config limits which tools are registered
- Unknown tools receive `DEFAULT_TOOL_GOVERNANCE` (maximum restriction: `action_class=write`, `reversible=False`, `may_access_pii=True`, `risk_level=high`)
- Tool responses are data — they cannot modify governance config

### 2.5 The Collector Stage

The collector receives all `TaskOutput` objects from the executor and assembles the final response. Its LLM call synthesises outputs into a coherent, user-facing reply. The output is validated against the `output_contract` schema before being returned as `FinalResponse`.

`FinalResponse.outcome` is set by `StageRunner` — not by the collector. The collector's LLM cannot claim the workflow succeeded or failed. The runner makes that determination from the execution outputs.

---

## 3. The Hybrid Validator in Detail

### 3.1 Why Two Layers

A validator with only a structural check cannot catch semantic risks. A validator with only LLM annotation cannot be trusted deterministically — the same input can produce different annotations across calls, and a jailbroken or adversarial model can misclassify intentionally.

The hybrid approach captures the strengths of both:

| Property | Structural Check | LLM Annotation | Rule Engine |
|---|---|---|---|
| Speed | Synchronous | Async | Synchronous |
| LLM call | None | One | None |
| Input | Plan + policy | Plan + policy + context | Annotation + policy |
| Output | Violations | Per-task annotations | Violations + gates |
| Deterministic | Yes | No | Yes |
| Can be jailbroken | No | Theoretically | No |

The rule engine is the final arbiter. It cannot be jailbroken because it does not receive free-form LLM output as instructions — it receives a structured `TaskAnnotation` object and evaluates it against compiled policy rules.

### 3.2 Ground Truth Override

The annotator LLM can be wrong. It can also be adversarial. The ground truth override mechanism ensures tool governance config always wins:

```python
# _apply_ground_truth in validator.py
tool_action_class = tool.governance.action_class  # authoritative
if tool_action_class != annotation.action_class:
    annotation.action_class = tool_action_class   # override
    annotation.ground_truth_applied = True
```

This invariant is tested adversarially: a model that annotates a `delete` tool as `read_only` cannot prevent the rule engine from gating it. The ground truth override fires before rule evaluation.

### 3.3 Missing Annotations Gate by Default

If the annotator LLM fails to return an annotation for a task (network error, schema violation, or adversarial omission), that task receives a gate by default:

```python
if ann is None:
    gates.append(PolicyGate(
        task_id = task.task_id,
        rule    = "validator.missing_annotation",
        reason  = "No annotation for task. Human review required by default.",
    ))
```

The system fails closed. A missing annotation is never silently approved.

---

## 4. MCP Tool Governance

### 4.1 Tool Access as a Governance Boundary

Model Context Protocol (MCP) provides tool access to agents. In a PBAS v2 system, every MCP tool has an associated governance configuration that defines its safety properties:

```yaml
tool_governance:
  read_document:
    action_class:   read_only
    reversible:     true
    may_access_pii: false
    risk_level:     low
    on_error:       fail_step
    on_timeout:     fail_step

  delete_records:
    action_class:   delete
    reversible:     false
    may_access_pii: false
    risk_level:     high
    on_error:       escalate
    on_timeout:     escalate
```

This configuration is **set at server registration time** — before any workflow runs. It cannot be changed by a tool response. It cannot be overridden by an agent. It is the authoritative source of truth for what a tool does.

### 4.2 Four Governance Invariants

**Invariant 1 — expose_tools is the access boundary.**
Only tools listed in `expose_tools` are registered in the tool registry. Calling an unlisted tool is impossible — it does not exist in the registry.

**Invariant 2 — Unknown tools get maximum restriction.**
Any tool discovered via MCP `tools/list` that is not in `tool_governance` receives `DEFAULT_TOOL_GOVERNANCE`: `action_class=write`, `reversible=False`, `may_access_pii=True`, `risk_level=high`. The system fails closed on unknown tools.

**Invariant 3 — Tool response content cannot modify governance.**
Tool responses are structured data passed to the executor. They are not instructions. An MCP server that returns `{"action_class": "read_only"}` in its response does not thereby change its governance classification. Governance is read from config at registration — never from runtime responses.

**Invariant 4 — action_class from config overrides annotation.**
The ground truth override in the validator applies tool governance `action_class` to the annotation before rule evaluation. A tool classified as `delete` in governance config will be treated as `delete` regardless of how the planner annotates it.

---

## 5. Audit Persistence and Checkpointing

### 5.1 Audit Persistence

Every workflow run generates an immutable, append-only audit trail. Six event types are written automatically by `StageRunner` at every stage transition:

```
WORKFLOW_STARTED     tenant, user, task (truncated to 200 chars)
PLAN_PROPOSED        sub_task_count, total_cost, agents, tools
PLAN_EVALUATED       decision, violation_count, gate_count, violations, gates
STEP_COMPLETED       task_id, agent, success, tools_called, duration_ms
STEP_FAILED          task_id, agent, success=False, error
WORKFLOW_COMPLETED   outcome, iterations, duration_ms, confidence, completeness
```

The application provides the store implementation. DAF provides the write calls automatically:

```python
# From StageRunner.run() — called automatically on every workflow
await self._audit.write(AuditRecord.make(
    request_id = uuid.UUID(request.request_id),
    tenant_id  = request.tenant_id,
    user_id    = request.user_id,
    event_type = AuditEventType.PLAN_EVALUATED,
    payload    = {
        "decision":        validation.decision,
        "violation_count": len(validation.violations),
        "gate_count":      len(validation.gates),
        "violations":      [...],
        "gates":           [...],
    },
))
```

Four store implementations are provided: `NullAuditStore` (default, no persistence), `LogAuditStore` (server log output), `SQLiteAuditStore` (single-process persistence), `CompositeAuditStore` (fan-out to multiple stores simultaneously). Applications wire them via `StageRunner.from_config(audit_store=...)`.

### 5.2 Checkpointing for Workflow Resume

Checkpoints enable workflow recovery after server restart. This is required for production HITL gates — a human review that takes hours cannot survive on in-memory state.

`StageRunner` writes checkpoints at four transitions:

```
execution_start    → WorkflowCheckpoint(state=running, pending_tasks=[...])
after_each_task    → checkpoint.mark_task_complete(task_id, result, cost)
at_hitl_gate       → checkpoint.mark_awaiting_hitl(paused_at_task, review_id)
after_hitl_resume  → checkpoint.mark_resuming()
on_completion      → checkpoint.mark_completed() then delete
on_escalation      → checkpoint.mark_failed(reason) then preserve
```

Failed checkpoints are preserved — not deleted. An operator can inspect the checkpoint, understand why the workflow failed, fix the underlying issue, and replay from the last successful task.

---

## 6. Real HITL Gates

### 6.1 The Problem with Auto-Approval

PBAS v1 included a `ManualGateway` that auto-approved all gate requests. This was an acknowledged placeholder. In production, a governance system that always approves gates provides no governance at all.

PBAS v2 defines the structural HITL interface and provides a reference Django implementation.

### 6.2 The HITL Interface

`ManualGateway.request_review()` is the interface:

```python
async def request_review(
    request_id: str,
    gates:      list[PolicyGate],
    plan:       PlanProposal,
) -> bool:
    """
    Returns True (approved) or False (rejected).
    Blocks until human decision or timeout.
    """
```

DAF defines the interface. The application provides the implementation. The `StageRunner` is paused at the gate — it awaits the return value of `request_review()` before proceeding.

### 6.3 The Django Implementation

`DjangoHITLGateway` implements the interface for Django deployments:

1. Creates a `DAFGateRequest` record with the gate details, plan data, and context
2. Logs the review URL: `[DAF HITL] Review at: /hitl/<gate_id>/`
3. Polls the DB every 2 seconds for a human decision
4. Returns `True` (approved) or `False` (rejected) to `StageRunner`
5. Times out after `hitl_timeout_seconds` (from risk policy config) and returns `False`

The review page at `/hitl/<gate_id>/` shows the reviewer:
- Which policy rules triggered the gate
- The full proposed plan with task descriptions, agents, and tools
- The estimated cost
- Name field + note field + Approve / Reject buttons

The decision is written to `DAFGateRequest.status`. The polling loop detects it and unblocks `StageRunner`. The workflow resumes (or is stopped) without any code change.

### 6.4 Checkpoint-HITL Integration

The checkpoint written at the gate (`state=awaiting_hitl`) persists the full workflow context. If the server restarts while a review is pending:

1. The `DAFGateRequest` record still exists in the DB
2. The `DAFWorkflowCheckpoint` record still exists in the DB
3. When the server restarts, a monitoring job can resume pending workflows from their checkpoints
4. The reviewer's decision is already in the DB — the resumed workflow reads it immediately

Gate reviews survive server restarts. No workflow context is lost.

---

## 7. Config-Driven Deployment: The Django Integration Pattern

### 7.1 Framework-Agnosticism Proved

DAF v0.2.0 integrates with Django via one interface: `LLMClient`. The consuming application implements `BaseLLMClient.complete()`. `StageRunner` does the rest.

Two production-pattern Django applications demonstrate this:

| Application | Domain | Tasks per workflow | MCP tools | Mock flag |
|---|---|---|---|---|
| daf-chat-demo | Conversational AI | 1 | 2 (search, context) | One flag |
| daf-docsummarizer | Document analysis | 4 | 4 (read, classify, summarise, extract) | One flag |

Neither application modified any DAF Stage 2 file. The entire integration is in `apps.py`:

```python
runner = StageRunner.from_config(
    config,
    llm_client       = LLMClient(mock_config=config.llm.mock),
    mcp_client       = mcp,
    audit_store      = CompositeAuditStore(DjangoAuditStore(), LogAuditStore()),
    checkpoint_store = DjangoCheckpointStore(),
    hitl_gateway     = DjangoHITLGateway(timeout_seconds=300),
)
```

### 7.2 The `daf_config` Django App

All DAF configuration lives in Django admin via the `daf_config` reusable app. No YAML files needed after initial seeding:

| Model | Purpose |
|---|---|
| `DAFRuntimeConfig` | Project, environment, `mock_enabled` flag, budget/risk/loop policies |
| `DAFOrchestrator` | Stage instructions (real prompt) + mock_response (fixture) per stage/scenario |
| `DAFAgent` | Base prompt, permitted tools, permitted task types |
| `DAFMCPServer` | URL, tool governance, mock responses per tool |
| `DAFComplianceRule` | Rule reference, condition (field/operator/value), action |
| `DAFDocumentType` | Document category, keywords, scenario linkage (doc summariser only) |
| `DAFDocument` | Document content, type linkage, word count auto-calculated (doc summariser only) |
| `DAFAuditRecord` | Append-only audit trail, view-only in admin |
| `DAFWorkflowCheckpoint` | Active workflow state, filterable by state |
| `DAFGateRequest` | Pending HITL reviews with approve/reject UI |

### 7.3 The Single Mock Flag

The `DAFRuntimeConfig.mock_enabled` flag is the single control point for real vs mock operation. Setting it to `True` in Django admin makes the entire pipeline use fixture responses from `DAFOrchestrator.mock_response`. Setting it to `False` routes all LLM calls to the real API.

No code change. No deployment. One admin page.

This design reflects a core PBAS v2 principle: **the pipeline is identical in mock and live modes**. The same governance rules, the same output contracts, the same audit writes, the same compliance checks — all execute regardless of the mock flag. The flag only changes where the LLM response comes from. Everything else is constant.

### 7.4 Scenario-Driven Configuration

Each document type in the doc summariser links to a DAF scenario:

```
DAFDocument.doc_type → DAFDocumentType.scenario → DAFOrchestrator records
                                                 → DAFAgent records
```

A financial report uses scenario `doc_financial`. A legal contract uses scenario `doc_legal`. Each scenario has its own planner instructions, validator instructions, executor instructions, and collector instructions — tuned for the document type. Adding a new document type is a Django admin operation. No code change required.

---

## 8. Test Evidence

### 8.1 Test Suite Overview

| Suite | Tests | Coverage |
|---|---|---|
| v0.1.0 unit tests | 569 | Policy engine, scoped context, input processor |
| v0.1.0 adversarial | 53 | Injection resistance, execution invariants |
| Stage 2 unit tests | 390 | All four stages, config loader, MCP client, rule engine |
| Stage 2 integration | 24 | Happy path, gate path, replan path, budget path |
| Stage 2 adversarial | 24 | LLM injection, rule engine bypass, MCP governance, pipeline integrity |
| Audit store tests | 24 | NullAuditStore, LogAuditStore, SQLiteAuditStore, CompositeAuditStore, StageRunner integration |
| Checkpoint tests | 16 | NullCheckpointStore, SQLiteCheckpointStore, full lifecycle, StageRunner integration |
| Chat demo | 25 | Views, DAF integration, session, admin |
| Doc summariser | 43 | Views, DAF integration, documents, reports, admin |
| **Total** | **972** | |

### 8.2 Adversarial Test Categories

The 77 adversarial tests (53 v0.1.0 + 24 Stage 2) cover:

**Input injection** — adversarial content in the task field does not become instructions. Zone isolation is enforced at the prompt level.

**Policy engine invariants** — malformed proposals, manipulated confidence scores, and attempts to bypass policy dimensions all fail at the policy engine, not at the application level.

**Execution invariants** — agent result manipulation, HITL response forgery, and direct registry manipulation cannot bypass execution constraints.

**Scoped context** — tools not in `ScopedContext` cannot be called. Python-level manipulation cannot bypass the permission check.

**LLM response injection (Stage 2)** — LLM annotations claiming `read_only` for a `delete` tool are overridden by ground truth. Low-confidence irreversible actions are gated. Missing annotations gate by default.

**Rule engine bypass (Stage 2)** — compliance block rules always fire. Compliance gate rules always gate. The structural check has no LLM calls (synchronous invariant). The result type is always valid.

**MCP tool governance (Stage 2)** — tool `action_class` from config is authoritative. Unknown tools get maximum restriction defaults. Tool responses cannot inject governance overrides.

**Pipeline integrity (Stage 2)** — `request_id` is preserved through all stages. The max iterations hard limit fires on perpetual rejection. Concurrent workflows have isolated audit records. The pipeline completes normally without optional stores.

### 8.3 The Bug Found by Adversarial Tests

During Stage 2 adversarial test development, one genuine bug was discovered and fixed:

`_apply_ground_truth` in `daf/stages/validator.py` read `tool.action_class` directly, but `ToolInfo` in the v0.1.0 codebase uses `tool.governance.action_class` (nested). The Stage 2 `MCPClient` builds `ToolInfo` with flat `action_class`, so tests against live MCP data passed. But tests against v0.1.0-style `ToolInfo` objects (as the adversarial tests use) failed.

The fix: `_apply_ground_truth` now resolves governance via both paths — flat attributes first (Stage 2 MCPClient `ToolInfo`), then nested `governance` object (v0.1.0 `ToolInfo`). Ground truth override now also includes `may_access_pii` — a tool flagged `may_access_pii=True` in governance config overrides LLM annotation even when the LLM claims no PII access.

This is the intended function of an adversarial test suite: it found a real bypass path that unit tests and integration tests missed.

---

## 9. PBAS v2 Claim Matrix

| Claim | Status | Evidence |
|---|---|---|
| Model proposes, system governs at every stage | ✅ Proven | 4 governed stages, 972 tests |
| Planner output is immutable from proposal | ✅ Proven | PlanProposal frozen, passed by reference |
| Structural check has no LLM calls | ✅ Proven | Synchronous invariant test, `test_structural_check_has_no_llm_calls` |
| LLM annotates, rule engine decides | ✅ Proven | `HybridValidator`, rule engine tests |
| Tool governance config overrides LLM annotation | ✅ Proven | Ground truth override, adversarial tests |
| Unknown tools get maximum restriction | ✅ Proven | `DEFAULT_TOOL_GOVERNANCE`, governance tests |
| Missing annotation gates by default | ✅ Proven | `validator.missing_annotation` rule, adversarial test |
| Max iterations hard limit enforced | ✅ Proven | `max_replan_attempts`, adversarial test |
| Audit trail written at every stage transition | ✅ Proven | 6 event types, `StageRunner.run()`, audit tests |
| Audit trail is append-only | ✅ Proven | `SQLiteAuditStore` INSERT only, no UPDATE |
| Checkpoints save at every task completion | ✅ Proven | `mark_task_complete` on every output |
| Checkpoints survive server restart | ✅ Proven | SQLite/Django persistence, checkpoint tests |
| HITL gate suspends pipeline until human decision | ✅ Proven | `DjangoHITLGateway` polling loop |
| HITL gate state survives server restart | ✅ Proven | `DAFGateRequest` + `DAFWorkflowCheckpoint` in DB |
| Framework-agnostic: one interface to implement | ✅ Proven | `BaseLLMClient.complete()`, two Django demos |
| Config-driven: zero code change to switch mock/live | ✅ Proven | `mock_enabled` flag in `DAFRuntimeConfig` |
| All config in admin: no YAML files at runtime | ✅ Proven | `daf_config` Django app, 10 models |
| Concurrent workflows have isolated audit records | ✅ Proven | `test_concurrent_workflows_have_isolated_request_ids` |
| Adversarial test suite as hard ship gate | ✅ Proven | 77 adversarial tests, all passing |
| Adversarial tests can find real bugs | ✅ Proven | `_apply_ground_truth` bug found and fixed |

---

## 10. Limitations and Future Work

### 10.1 Current Limitations

**ScopedContext instantiation.** In PBAS v1, `ScopedContext` was instantiated at the agent level — tools not in the scope literally did not exist in the Python object. In DAF v0.2.0, tool permission is checked by the rule engine during validation, not enforced at instantiation time. A v0.2.0 executor could theoretically call a tool that wasn't in the approved plan if the MCP client received it. The rule engine prevents this in practice, but the v0.1.0 stronger guarantee (tool does not exist in scope) should be restored in v0.3.0.

**No real LLM integration in demos.** Both Django demos use mock LLM responses from `DAFOrchestrator.mock_response`. The pipeline, governance, audit, checkpointing, and HITL all function correctly in mock mode. Live mode requires a concrete `LLMClient.complete()` implementation that calls Anthropic, OpenAI, or another provider. This is intentional — the demos prove the governance framework, not the LLM provider integration.

**HITL timeout behaviour.** `DjangoHITLGateway` returns `False` (rejected) on timeout. This is the safe default — an unanswered gate should not auto-approve. Future work should make the timeout action configurable: `escalate`, `auto_approve`, or `notify_and_extend`.

**Checkpoint resume is not yet automatic.** Checkpoints are saved and preserved on failure. Resuming from a checkpoint requires manually calling `StageRunner.resume(checkpoint)`. An automatic recovery daemon that detects stale `running` or `awaiting_hitl` checkpoints on server restart is planned for v0.3.0.

### 10.2 Future Work

**PBAS v3 — Multi-tenant governance.** Tenant-level policy isolation, per-tenant budget tracking, tenant-specific compliance rule sets, and tenant audit log isolation.

**PBAS v4 — Adversarial robustness benchmarks.** Systematic measurement of governance bypass resistance against published jailbreak techniques. Target: quantitative claim that DAF governance resists N% of published attacks.

**FastAPI reference implementation.** The same `daf_config` pattern implemented as a FastAPI application, demonstrating framework-agnosticism beyond Django.

---

## 11. Conclusion

PBAS v2 extends the foundational PBAS principle — *the model proposes, the system governs* — across a four-stage cognitive pipeline. At every stage, the LLM proposes and the system governs. The planner proposes a task decomposition. The validator governs it through structural check and rule engine. The executor proposes tool calls. The MCP governance layer governs them. The collector proposes a response. The output contract governs its structure.

This governance does not weaken as the pipeline grows. The hybrid validator adds a second governance layer. The ground truth override ensures tool config is authoritative over LLM annotation. The missing annotation gate ensures the system fails closed. The max iterations limit ensures adversarial rejection loops terminate. Concurrent workflows are isolated. Every stage transition is audited.

Two production-pattern Django applications demonstrate that PBAS v2 governance is achievable without framework lock-in, without YAML config files at runtime, and without changes to the DAF core as deployment requirements evolve. The `daf_config` Django app and its single `mock_enabled` flag demonstrate that the same governed pipeline runs identically in development and production — the only difference is where the LLM response comes from.

972 tests, including 77 adversarial tests, validate these claims. One genuine security bug was found and fixed by the adversarial test suite during development — demonstrating that adversarial testing as a hard ship gate is not a formality but a functional safeguard.

---

## Appendix A: DAF v0.2.0 Component Reference

```
daf/
├── config/
│   ├── loader.py          ConfigLoader — loads RuntimeConfig from YAML
│   └── models.py          RuntimeConfig, PolicyConfig, OrchestratorConfig,
│                          AgentRoleConfig, MCPServerConfig, ToolGovernance,
│                          BudgetPolicyConfig, RiskPolicyConfig, LoopPolicyConfig,
│                          ComplianceRule, ComplianceRuleCondition
├── engine/
│   └── runner.py          StageRunner, WorkflowRequest, FinalResponse,
│                          ManualGateway, _build_cycle_trace
├── mcp/
│   ├── client.py          MCPClient — connects servers, registers tools
│   ├── session.py         MCPSession — per-server connection lifecycle
│   └── transport.py       MCPTransport — streamable HTTP transport
├── stages/
│   ├── context.py         ContextAssembler — builds stage context
│   ├── planner.py         PlannerStage — task decomposition
│   ├── validator.py       HybridValidator, RuleEngine, TaskAnnotation,
│                          ValidationResult, PolicyViolation, PolicyGate
│   ├── executor.py        ExecutorStage — task execution via MCP
│   └── collector.py       CollectorStage — response assembly
└── runtime/
    ├── audit_store.py     AuditStore, NullAuditStore, LogAuditStore,
    │                      CompositeAuditStore
    ├── sqlite_audit_store.py    SQLiteAuditStore
    ├── checkpoint_store.py      CheckpointStore, NullCheckpointStore
    └── sqlite_checkpoint_store.py  SQLiteCheckpointStore
```

## Appendix B: Test Command Reference

```bash
# Full test suite
cd daf-v0.1.0-research
export PYTHONPATH=$(pwd)
pytest tests/ -q

# Stage 2 only
pytest tests/stage2/ -q

# Adversarial only (hard ship gate)
pytest tests/adversarial/ tests/stage2/test_adversarial_stage2.py -q

# Demo projects
cd daf-chat-demo && pytest tests/ -q
cd daf-docsummarizer && pytest tests/ -q
```

## Appendix C: PBAS v2 in One Diagram

```
User Request
│
├── [PLANNER]  LLM proposes PlanProposal
│              └── Structural check (sync, no LLM):
│                   • agent_roles permission
│                   • permitted_tools permission
│                   • budget check
│                   → REJECT on any violation
│
├── [VALIDATOR] Layer 2: LLM annotates TaskAnnotation per task
│              • action_class, reversible, touches_pii, external_access
│              └── Ground truth override from tool registry
│              └── Rule engine evaluates:
│                   • always_gate_action_classes
│                   • irreversible_min_confidence
│                   • gate_on_pii_access
│                   • compliance_rules (in order)
│                   → APPROVE | REJECT | GATE
│
├── [GATE]     (if GATE) DjangoHITLGateway:
│              • Creates DAFGateRequest in DB
│              • Shows reviewer: gates, plan, tools, cost
│              • Polls for decision (approve/reject)
│              • Returns bool to StageRunner
│
├── [EXECUTOR] Per approved task:
│              • Instantiates agent with ScopedContext
│              • LLM proposes tool calls
│              • MCPClient calls tool
│              • Tool governance enforced at call time
│              • TaskOutput collected
│
├── [COLLECTOR] LLM assembles FinalResponse from TaskOutputs
│              • Output contract schema validation
│              • outcome set by StageRunner (not collector)
│
└── FinalResponse + AuditTrail + CycleTrace
```
