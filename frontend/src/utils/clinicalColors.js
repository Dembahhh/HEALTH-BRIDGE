/**
 * Maps clinical classification categories to Tailwind CSS classes.
 * Centralised here so all components use consistent clinical colors.
 * Never hardcode clinical colors directly in components.
 */

export const SEVERITY_CLASSES = {
  normal: "bg-green-100 text-green-800",
  elevated: "bg-yellow-100 text-yellow-800",
  pre_diabetic: "bg-yellow-100 text-yellow-800",
  low_risk: "bg-yellow-100 text-yellow-800",
  stage_1: "bg-orange-100 text-orange-800",
  moderate_risk: "bg-orange-100 text-orange-800",
  stage_2: "bg-red-100 text-red-800",
  diabetic: "bg-red-100 text-red-800",
  high_risk: "bg-red-100 text-red-800",
  crisis: "bg-red-700 text-white",
  unknown: "bg-gray-100 text-gray-800",
};

export function getSeverityClass(category) {
  return SEVERITY_CLASSES[category?.toLowerCase()] ?? SEVERITY_CLASSES.unknown;
}
