# Workspace Tracking

This file is a local scratchpad for the coding agent.

Purpose:
- record the active task focus for this workspace
- note important local assumptions that should not be committed
- point to `progress.md` for completed work
- point to `prd.json` for near-term task status

Current focus:
- analyze the `AI鉴伪` architecture
- simplify image detection to a pure local execution path
- refresh repository documentation

Local environment rule:
- always use the `detect` conda environment for commands run under `C:\Users\admin\Desktop\SE\BUAA-SE-AID`
- every code or migration change must be followed by a full runtime verification pass before claiming completion; at minimum run migrations plus the relevant end-to-end or full test command for the affected app/workspace
- after every successful verification step, automatically run git management end-to-end: create a commit and attempt a push immediately; if push fails because of network or remote issues, record it and continue
