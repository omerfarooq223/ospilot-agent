# Restricted MCP-Style Tools

OS Pilot exposes a narrow local tool layer. These tools are regular Python functions in the MVP, structured like MCP tools so the agent cannot perform open-ended system actions.

## Exposed Tools

System:

```text
get_system_metrics()
get_process_snapshot(limit=20)
get_top_processes(metric="memory" | "cpu", limit=10)
analyze_performance_pressure()
detect_idle_heavy_apps()
get_disk_usage()
```

Files:

```text
list_roots()
scan_selected_folder(root_path, min_size_mb=30)  # range: 30 MB – 5 GB, user-adjustable from UI
find_developer_junk(root_path)
scan_cache_folders(root_path)
estimate_cleanup_space(items)
detect_project_type(project_root)
detect_project_root(path)
rebuildability_for(path, project_root, item_type)
path_identity(path)
action_path_identity(action)
action_identity_mismatch_reason(action)
```

Workspace intelligence:

```text
profile_workspace(root_path, items=None, process_links=None)
link_processes_to_root(root_path)
build_cleanup_scenarios(cleanup_actions, advisory_actions=None)
simulate_scenario(scenario, all_actions)
validate_approved_actions(plan_actions, approved_action_ids)
```

Safety:

```text
is_protected_path(path)
classify_file_risk(path)
validate_cleanup_plan(plan)
```

Quarantine:

```text
quarantine_item(path, reason, expected_identity=None, artifact_name=None, project_type="Unknown")
restore_item(quarantine_id)
list_quarantine()
```

Reporting:

```text
write_audit_log(event)
generate_maintenance_report()
export_report(format="html" | "pdf")
```

API-only user experience helpers:

```text
browse_folders(path)
start_scan(folder, min_size_mb)
get_scan_job(job_id)
cancel_scan_job(job_id)
autopilot_quarantine(session_id)
list_ignored_folders()
add_ignored_folder(path)
remove_ignored_folder(path)
scan_history(limit)
```

Local memory and feedback:

```text
save_scan_snapshot(folder, observation, plan)
get_last_snapshot(folder)
compute_delta(current_items, current_bytes, current_reclaimable, previous)
record_restore(original_path, artifact_name=None, project_type="Unknown")
restore_penalty(artifact_name, project_type)
```

## Blocked Behaviors

```text
run_any_command
delete_any_file
format_disk
edit_registry
kill_process
install_update
modify_system_settings
scan_full_disk_by_default
trust_browser_submitted_cleanup_plan
trust_browser_submitted_autopilot_candidates
```

## Project Intelligence Fields

Scan items and maintenance actions include:

```text
project_root
project_type
rebuildability
recovery_recipe
evidence
dormant_days
confidence
linked_processes
path_device
path_inode
path_mtime_ns
path_is_symlink
```

These fields let OS Pilot explain why `node_modules` with `package-lock.json` is safer to quarantine than an unknown model checkpoint or large user-created file.

Maintenance plans can also include:

```text
diagnosis_result
scan_delta
```

`diagnosis_result` contains the structured agent summary, top risks, recommended scenario, urgency level, confidence, and fallback flag. `scan_delta` describes how the same folder changed since the last saved scan snapshot.

## Scenario Outputs

The planner returns:

```text
workspace_profile
cleanup_scenarios
simulation_results
validation
```

These objects power the Conservative / Balanced / Deep Review cards, before/after estimates, and active-process blocks in the UI and exported report.

## Execution Revalidation

Approval is not enough by itself. Before quarantine, OS Pilot revalidates that:

```text
action id exists in the server-side plan
action mode is Quarantine
path is not protected
path is not a symlink
path identity still matches scan-time device/inode/mtime
no live process is currently linked to the path or project root
```

If any check fails, the action is skipped and an audit event is written.
