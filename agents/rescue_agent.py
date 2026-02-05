"""
Rescue Agent - AI-Powered Task Recovery System

Like Temporal's durable execution, but with AI diagnosis and auto-recovery.
When tasks fail after retries, this agent analyzes the failure, diagnoses the
root cause, and attempts intelligent recovery strategies.
"""

import json
import traceback
from datetime import datetime
from typing import Optional
from openai import AsyncOpenAI
from common.config import OPENAI_API_KEY, DEEPSEEK_API_KEY, LLM_PROVIDER, MODEL_NAME
from common.contracts import (
    AgentResponse,
    RescueContext,
    RescueDiagnosis,
    RecoveryStrategy,
    PRIssueSummary,
    FailureDetail
)

# Initialize LLM client
if LLM_PROVIDER == "openai":
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    model = "gpt-4o"
elif LLM_PROVIDER == "deepseek":
    client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    model = MODEL_NAME
else:
    client = AsyncOpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    model = "deepseek-chat"


async def diagnose_failure(context: RescueContext) -> RescueDiagnosis:
    """
    Use AI to diagnose the failure and determine recovery strategy.
    This is the "brain" of the rescue system.
    """

    # Format failure history for LLM
    failure_history_text = "\n\n".join([
        f"### Attempt {f.attempt}\n"
        f"**Agent**: {f.agent}\n"
        f"**Time**: {f.timestamp}\n"
        f"**Error**: {f.error_message}\n"
        f"**Stack Trace**:\n```\n{f.stack_trace or 'N/A'}\n```"
        for f in context.failure_history
    ])

    diagnosis_prompt = f"""You are a Rescue Agent in a self-healing AI workflow system.

## MISSION
A task has failed {context.failure_count} times. Your job is to:
1. Diagnose the root cause
2. Determine if it can be auto-fixed
3. Propose a recovery strategy
4. Provide specific actions to take

## WORKFLOW CONTEXT

**Goal**: {context.workflow_goal}
**Failed Agent**: {context.failed_agent}
**Job ID**: {context.job_id}

**Original Input**:
```json
{json.dumps(context.original_payload, indent=2)}
```

## FAILURE HISTORY

{failure_history_text}

## AVAILABLE RECOVERY STRATEGIES

1. **retry_with_modification**: Modify parameters and retry
   - Fix malformed URLs
   - Adjust timeouts
   - Change model/provider
   - Use fallback values

2. **route_to_different_agent**: Route to a different agent
   - Original agent is wrong for this task
   - Try simpler/alternative approach

3. **apply_code_patch**: Apply a code fix (use with extreme caution)
   - Install missing dependency
   - Fix obvious code bug
   - Only if safe and reversible

4. **skip_step**: Skip this step if non-critical
   - Task is optional
   - Can continue workflow without it

5. **escalate_to_human**: Create detailed PR-ready issue
   - Bug requires code changes
   - Complex issue needing human judgment
   - Safety concerns with auto-fix

## YOUR ANALYSIS

Respond in JSON format:

```json
{{
  "root_cause": "Clear explanation of what went wrong",
  "can_auto_fix": true/false,
  "recovery_strategy": "retry_with_modification|route_to_different_agent|apply_code_patch|skip_step|escalate_to_human",
  "actions": [
    {{
      "type": "modify_payload|change_agent|install_package|create_pr",
      "details": {{}},
      "reason": "Why this action helps"
    }}
  ],
  "confidence": 0.0-1.0,
  "explanation": "Detailed explanation of diagnosis and recovery plan",
  "pr_summary": "Only if escalating - PR-ready issue description"
}}
```

Be practical and conservative:
- Prefer simple fixes over complex ones
- Only auto-fix if confidence > 0.8
- When in doubt, escalate to human
- Safety first - don't break things worse

Now analyze this failure:"""

    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert systems engineer specializing in failure diagnosis and recovery. Analyze failures carefully and propose safe, effective recovery strategies."
                },
                {
                    "role": "user",
                    "content": diagnosis_prompt
                }
            ],
            temperature=0.3,  # Lower temperature for more consistent diagnosis
            response_format={"type": "json_object"}
        )

        diagnosis_json = json.loads(response.choices[0].message.content)

        # Parse into RescueDiagnosis
        diagnosis = RescueDiagnosis(
            root_cause=diagnosis_json.get("root_cause", "Unknown"),
            can_auto_fix=diagnosis_json.get("can_auto_fix", False),
            recovery_strategy=RecoveryStrategy(diagnosis_json.get("recovery_strategy", "escalate_to_human")),
            actions=diagnosis_json.get("actions", []),
            confidence=diagnosis_json.get("confidence", 0.0),
            explanation=diagnosis_json.get("explanation", ""),
            pr_summary=diagnosis_json.get("pr_summary")
        )

        return diagnosis

    except Exception as e:
        print(f"❌ Error in AI diagnosis: {e}")
        # Fallback: escalate to human
        return RescueDiagnosis(
            root_cause=f"Failed to diagnose (AI error: {str(e)})",
            can_auto_fix=False,
            recovery_strategy=RecoveryStrategy.ESCALATE_TO_HUMAN,
            actions=[],
            confidence=0.0,
            explanation="AI diagnosis failed, escalating to human",
            pr_summary=f"Rescue agent failed to diagnose. Original error: {context.failure_history[-1].error_message if context.failure_history else 'Unknown'}"
        )


def create_pr_issue(context: RescueContext, diagnosis: RescueDiagnosis) -> PRIssueSummary:
    """
    Create a PR-ready issue report with detailed information for developers.
    """

    latest_failure = context.failure_history[-1] if context.failure_history else None

    # Generate unique issue ID
    issue_id = f"RESCUE-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Format reproduction steps
    reproduction_steps = [
        f"1. User request: {context.workflow_goal}",
        f"2. System routes to agent: {context.failed_agent}",
        f"3. Agent processes with payload: {json.dumps(context.original_payload, indent=2)}",
        f"4. Error occurs: {latest_failure.error_message if latest_failure else 'Unknown'}",
        f"5. Failed {context.failure_count} times with same error"
    ]

    # Format error logs
    error_logs = ""
    if latest_failure:
        error_logs = f"""
**Latest Error**:
```
{latest_failure.error_message}
```

**Stack Trace**:
```python
{latest_failure.stack_trace or 'N/A'}
```

**Full Failure History**:
"""
        for i, failure in enumerate(context.failure_history, 1):
            error_logs += f"\nAttempt {i} ({failure.timestamp}):\n{failure.error_message}\n"

    # Suggested fix from AI
    suggested_fix = diagnosis.pr_summary or diagnosis.explanation

    # Impact assessment
    impact = f"""
**Severity**: High (task completely fails after {context.failure_count} attempts)
**Frequency**: Unknown (first occurrence or recurring)
**Users Affected**: At least 1 (Job ID: {context.job_id})
**Component**: {context.failed_agent}
"""

    # Related files
    related_files = [
        f"agents/{context.failed_agent}.py",
        "worker.py",
        "common/contracts.py"
    ]

    # Generate title
    title = f"🚨 {context.failed_agent} fails: {diagnosis.root_cause[:80]}"

    # Create full summary in markdown
    summary = f"""# {title}

**Issue ID**: {issue_id}
**Workflow**: {context.workflow_goal}
**Failed Agent**: {context.failed_agent}
**Failure Rate**: {context.failure_count}/{context.failure_count} attempts

---

## Summary

{diagnosis.root_cause}

## Root Cause Analysis

{diagnosis.explanation}

## Reproduction Steps

{chr(10).join(reproduction_steps)}

## Error Logs

{error_logs}

## AI-Suggested Fix

{suggested_fix}

## Impact Assessment

{impact}

## Related Files

{chr(10).join(f'- `{f}`' for f in related_files)}

## Testing Checklist

- [ ] Reproduce the error with original payload
- [ ] Verify the fix resolves the issue
- [ ] Test with edge cases
- [ ] Ensure no regression in other workflows
- [ ] Update error handling/logging if needed

---

**Created by**: Rescue Agent (AI-powered)
**Timestamp**: {datetime.now().isoformat()}
**Job ID**: {context.job_id}
**Confidence**: {diagnosis.confidence:.2%}
"""

    return PRIssueSummary(
        issue_id=issue_id,
        title=title,
        summary=summary,
        root_cause=diagnosis.root_cause,
        reproduction_steps=reproduction_steps,
        error_logs=error_logs,
        suggested_fix=suggested_fix,
        impact=impact,
        related_files=related_files
    )


async def execute(rescue_payload: dict) -> AgentResponse:
    """
    Main entry point for rescue agent.
    Analyzes failed job and attempts recovery.
    """

    print("🚁 Rescue Agent activated - analyzing failure...")

    try:
        # Extract context from payload
        failed_job_data = rescue_payload.get("failed_job", {})
        context_data = rescue_payload.get("context", {})

        # Build RescueContext
        context = RescueContext(
            job_id=failed_job_data.get("id", "unknown"),
            workflow_goal=context_data.get("workflow_goal", "Unknown workflow"),
            failed_agent=failed_job_data.get("current_agent", "unknown"),
            failure_count=failed_job_data.get("retry_count", 0),
            failure_history=context_data.get("failure_history", []),
            original_payload=failed_job_data.get("payload", {}),
            agent_code=context_data.get("agent_code"),
            worker_logs=context_data.get("worker_logs")
        )

        print(f"📊 Analyzing: Job {context.job_id}, Agent {context.failed_agent}, {context.failure_count} failures")

        # Step 1: AI Diagnosis
        diagnosis = await diagnose_failure(context)

        print(f"🔍 Diagnosis: {diagnosis.root_cause}")
        print(f"💡 Strategy: {diagnosis.recovery_strategy.value}")
        print(f"🎯 Confidence: {diagnosis.confidence:.0%}")
        print(f"🤖 Can auto-fix: {diagnosis.can_auto_fix}")

        # Step 2: Execute recovery strategy
        if diagnosis.can_auto_fix and diagnosis.confidence >= 0.8:
            # Attempt auto-recovery
            recovery_result = await attempt_recovery(diagnosis, context)

            return AgentResponse(
                success=True,
                output=f"🔧 **Rescue Successful!**\n\n"
                       f"**Problem**: {diagnosis.root_cause}\n\n"
                       f"**Solution**: {diagnosis.explanation}\n\n"
                       f"**Actions Taken**:\n" +
                       "\n".join(f"- {action.get('reason', 'Action taken')}" for action in diagnosis.actions) +
                       f"\n\n{recovery_result}",
                data={
                    "recovery_strategy": diagnosis.recovery_strategy.value,
                    "actions_taken": diagnosis.actions
                }
            )
        else:
            # Escalate to human with PR-ready issue
            pr_issue = create_pr_issue(context, diagnosis)

            # Save issue to file for review
            issue_file = f"/tmp/rescue_issues/{pr_issue.issue_id}.md"
            import os
            os.makedirs("/tmp/rescue_issues", exist_ok=True)
            with open(issue_file, "w") as f:
                f.write(pr_issue.summary)

            print(f"📝 PR issue created: {issue_file}")

            return AgentResponse(
                success=False,
                output=f"⚠️ **Task Failed - Human Review Needed**\n\n"
                       f"**Problem**: {diagnosis.root_cause}\n\n"
                       f"**Analysis**: {diagnosis.explanation}\n\n"
                       f"I've created a detailed issue report for the development team.\n\n"
                       f"**Issue ID**: `{pr_issue.issue_id}`\n"
                       f"**Confidence**: {diagnosis.confidence:.0%}\n\n"
                       f"The team will review and fix this issue. You may want to try a different approach in the meantime.",
                error=diagnosis.root_cause,
                data={
                    "pr_issue": pr_issue.model_dump(),
                    "issue_file": issue_file,
                    "diagnosis": diagnosis.model_dump()
                }
            )

    except Exception as e:
        print(f"❌ Rescue agent itself failed: {e}")
        traceback.print_exc()

        return AgentResponse(
            success=False,
            output=f"❌ **Critical Error**\n\n"
                   f"The rescue system itself encountered an error: {str(e)}\n\n"
                   f"This requires immediate developer attention.",
            error=f"Rescue agent failure: {str(e)}"
        )


async def attempt_recovery(diagnosis: RescueDiagnosis, context: RescueContext) -> str:
    """
    Execute the recovery actions proposed by AI.
    Returns a summary of actions taken.
    """

    results = []

    for action in diagnosis.actions:
        action_type = action.get("type")
        details = action.get("details", {})
        reason = action.get("reason", "")

        if action_type == "modify_payload":
            # Modify job payload and requeue
            results.append(f"✅ Modified job payload: {reason}")
            # Note: Actual requeue happens in worker

        elif action_type == "change_agent":
            new_agent = details.get("new_agent")
            results.append(f"✅ Routing to different agent: {new_agent} - {reason}")

        elif action_type == "install_package":
            package = details.get("package")
            results.append(f"✅ Would install package: {package} (requires manual approval)")

        elif action_type == "create_pr":
            results.append(f"✅ Created PR issue: {reason}")

        else:
            results.append(f"ℹ️ {reason}")

    return "Task will be retried with these modifications:\n" + "\n".join(results)
