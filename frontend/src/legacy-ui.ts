/**
 * UI inherited from the previous registry application.
 *
 * Keep this inventory until each item is replaced with a screen targeting the
 * current `records/*` API. The backend contract remains the source of truth.
 */
export const legacyUiInventory = {
  routes: [
    "/analytics",
    "/longitudinal-analytics",
    "/legacy-review",
    "/patients/:registryId/edit",
    "/entries/patients",
  ],
  fieldsWithoutCurrentApiRoutes: [],
  fieldsNeedingCurrentModelMapping: [
    "molecular test results (alteration_type is required)",
    "RECIST and iRECIST assessments",
    "pathological response assessments",
    "disease progression and survival follow-up",
  ],
} as const
