# Project Planner

Project Planner is an ERPNext/Frappe v15 enhancement layer for users who are familiar with basic Microsoft Project planning workflows.

It **does not replace** ERPNext's standard `Project`, `Task`, or `Task Depends On` DocTypes. Those remain the system of record.

## First PR scope

- Frappe app scaffold for ERPNext/Frappe v15.
- Idempotent migrate patch containing the supplied Custom Field and Property Setter exports.
- Project Number added to the standard Project Link search fields.
- `Project Planner Settings` single DocType.
- Whitelisted planning APIs over standard Project/Task records.
- Frappe-UI/Vue planner shell with:
  - standard Project Link search;
  - task hierarchy grid;
  - checkbox multi-selection;
  - toolbar Link / Unlink / Refresh actions;
  - FS / SS / FF / SF dependency type;
  - lag / lead input;
  - visible successor relationships.

The supplied **Project Gantt View** Custom HTML Block is treated as a UX/behavior reference, not the final architecture.

## Dependency convention

The current Project Planner convention intentionally treats rows in `Task.depends_on` as **successors**:

```
Task A.depends_on -> Task B
```

means:

```
Task A -> Task B
predecessor  successor
```

This differs from ERPNext's native predecessor interpretation in some Task controller methods. The initial PR isolates the planner UI/API but does not yet override the full ERPNext Task scheduling controller. That controller alignment should be reviewed and tested before automatic recursive scheduling is moved from site Server Scripts into the app.

## Install

```bash
bench get-app https://github.com/Aakvatech-Limited/Project-Planner
bench --site <site> install-app project_planner
bench --site <site> migrate
```

## Build the Frappe-UI frontend

```bash
cd apps/Project-Planner/frontend
yarn install
yarn build
cd ../..
bench build --app project_planner
```

The build writes the frontend bundle into `project_planner/public/frontend`. Open **Project Planner** from Desk after the assets are built.

## Development direction

The next planner UX iterations can add MS Project-style toolbar actions such as Indent, Outdent, Add Task, Delete Task, Milestone, Baseline, zoom controls, and a synchronized Gantt pane without replacing the ERPNext Project/Task data model.
