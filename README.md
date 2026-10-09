# Project Planner

**Project Planner** adds an MS Project-inspired planning interface to ERPNext while retaining the standard **Project**, **Task**, and **Task Depends On** records as the system of record.

It is intended for project managers and delivery teams who need to organize task hierarchies, define dependencies, and review schedules without maintaining a separate planning database.

## What it provides

- A Desk-based planning interface for ERPNext projects.
- Project selection through the standard Project Link search.
- Task hierarchy grid with multi-selection and Link / Unlink / Refresh actions.
- Four dependency relationships: Finish-to-Start (FS), Start-to-Start (SS), Finish-to-Finish (FF), and Start-to-Finish (SF).
- Lead and lag inputs and visible successor relationships.
- Project Planner Settings for app-level configuration.
- Whitelisted planning APIs operating on ERPNext Project and Task records.

The app extends ERPNext; it does not replace ERPNext's standard project management or permissions model.

## Who should use it?

| Audience | Typical use |
| --- | --- |
| Project managers | Review project tasks and their sequence |
| Implementation teams | Coordinate dependent delivery activities |
| Project coordinators | Link and unlink tasks using the planner |
| ERPNext administrators | Deploy and maintain a planner within ERPNext |

**Not a replacement for:** a standalone Microsoft Project installation, a full portfolio-management system, or an independent scheduling database.

## Planning workflow

1. Open **Project Planner** in ERPNext Desk.
2. Search for and select an existing Project.
3. Review the task hierarchy.
4. Select relevant tasks and use **Link** to establish relationships, or **Unlink** to remove them.
5. Specify the relationship type and lead/lag as appropriate.
6. Refresh and review the updated relationships.

The exact scheduling side effects depend on the installed app revision and ERPNext Task controller behavior; validate them in a test site before relying on automatic date propagation.

## Important dependency convention

**Project Planner intentionally interprets entries in `Task.depends_on` as successors.**

```text
Task A.depends_on -> Task B

Task A (predecessor) -> Task B (successor)
```

This differs from the predecessor interpretation used by some native ERPNext Task controller methods. Integrations, scripts, and reports that read `depends_on` must respect this convention. Test scheduling and circular-dependency handling against the specific deployed version.

## Compatibility and prerequisites

- **Frappe:** v15 or v16, per `pyproject.toml`.
- **ERPNext:** required; v15 or v16, per `pyproject.toml` and `hooks.py`.
- **Python:** 3.10 or newer.
- **Frontend tooling:** Node.js and npm available to the Bench host for source builds.
- **App name:** `project_planner`.

Compatibility declarations do not replace testing against the exact Frappe/ERPNext patch releases.

## Installation

```bash
bench get-app https://github.com/Aakvatech-Limited/Project-Planner
bench --site <site> install-app project_planner
bench --site <site> migrate
```

For production, select the branch appropriate to your Frappe major version and deployment policy rather than assuming the repository default branch is the correct release.

### Frontend assets

The root `package.json` exposes the frontend build. The app's install/migrate hooks check for missing or empty frontend assets and can build them when necessary. Existing but stale bundles are **not** automatically detected by this check.

After pulling changes to frontend source, rebuild explicitly:

```bash
bench build --app project_planner
bench --site <site> clear-cache
```

For frontend build troubleshooting:

```bash
cd apps/project_planner
npm run build
cd ../..
bench build --app project_planner
```

## Customizations and migration

Project Planner extends standard ERPNext records using exported Custom Fields and Property Setters. The repository currently declares the migration patch:

```text
project_planner.patches.v0_0.install_exported_customizations
```

The app also calls `project_planner.custom_fields.execute` from `after_install` and `after_migrate`.

**Important:** a successful Patch Log entry does not, by itself, prove that all expected custom fields exist. After installation or upgrade, confirm required fields in **Customize Form** and test the planner's dependency controls. If fields are missing, investigate the customization loader and its execution logs rather than repeatedly deleting Patch Log entries. Review whether repeated synchronization could overwrite legitimate site-specific changes before modifying customization logic.

## Configuration and permissions

- Review **Project Planner Settings** after installation.
- Ensure users have the necessary ERPNext Project and Task permissions.
- Test project search, task loading, dependency linking/unlinking, and schedule persistence with a non-administrator account.
- Keep application access and write permissions aligned with ERPNext roles.

## Upgrade checklist

1. Back up the site and database.
2. Update the app from the intended release branch.
3. Run `bench --site <site> migrate`.
4. Run `bench build --app project_planner` when frontend code changed.
5. Clear cache and reload Desk.
6. Verify custom fields, project search, task hierarchy, dependency relationships, and scheduling behavior.
7. Check browser console, server logs, and CI results if the planner fails to load.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Planner page fails to load | Browser console, built JS/CSS assets, Bench build output |
| `process is not defined` in browser | Frontend bundle and build-time environment substitutions |
| Project search returns no results | User permissions, Project Link search, network response |
| Dependency type field is missing | Custom Field records, customization loader, install/migrate logs |
| Dates do not propagate as expected | Successor convention, Task controller behavior, scheduling execution |
| Changes appear absent after upgrade | Stale frontend assets and browser/Desk cache |

## Technical architecture

- **Backend:** Frappe Python app with whitelisted APIs and ERPNext Project/Task records.
- **Frontend:** Vue/Frappe-UI planning interface built using the repository's frontend toolchain.
- **Data ownership:** standard ERPNext Project and Task DocTypes.
- **Deployment:** Bench-managed Frappe app with frontend assets.
- **Migration:** patch-based exported customizations plus installation/migration hooks.

## Roadmap

Potential future enhancements include indent/outdent, task creation/deletion, milestones, baselines, zoom controls, and a synchronized Gantt pane. These are **roadmap ideas**, not guaranteed current features.

## Security and operational considerations

Project data remains subject to ERPNext permissions. Administrators should review whitelisted API authorization and validate that task modifications respect project access restrictions. Test custom-field migrations and dependency scheduling on a staging site before production upgrades.

## Repository evidence reviewed

| File | Evidence |
| --- | --- |
| `pyproject.toml` | Package identity, Python version, Frappe/ERPNext dependency ranges |
| `project_planner/hooks.py` | ERPNext requirement, app registration, install/migrate hooks |
| `project_planner/patches.txt` | Exported customization migration patch |
| Previous `README.md` | Planner interface, dependency convention, frontend build behavior |

## To confirm before publishing

- Exact scheduling guarantees and supported dependency edge cases for each release branch.
- Customization migration behavior after the current refactor is merged.
- Screenshots and verified end-user workflow for the latest frontend.
- License file and version-specific support policy.

## Maintainer

**Aakvatech** — info@aakvatech.com

The app metadata declares the **MIT** license; refer to the repository's license file for the authoritative terms.
