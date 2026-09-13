/**
 * The one description of the app's navigation.
 *
 * Pages are grouped: the bottom bar shows one tab per group, and a group that
 * holds more than one page gets a sub-tab strip under the header. That keeps
 * the bar to five tabs on a phone while the pages themselves stay separate
 * routes — deep links and the back button are unaffected.
 */
export const NAV_GROUPS = [
  {
    key: 'attendance',
    // `label` is the bottom bar, which is a fifth of a phone screen wide;
    // `title` is the header, where the full name fits.
    label: 'Attendance',
    title: 'Attendance Manager',
    icon: 'fa-check-circle',
    children: [{ name: 'AttendanceManager', label: 'Attendance', icon: 'fa-check-circle' }],
  },
  {
    key: 'performance',
    label: 'Performance',
    title: 'Performance Management',
    icon: 'fa-star',
    children: [
      { name: 'PerformanceManager', label: 'Performance', icon: 'fa-star' },
      { name: 'StudentProfile', label: 'Student Profile', icon: 'fa-id-card-o' },
    ],
  },
  {
    key: 'dashboard',
    label: 'Dashboard',
    title: 'Attendance Dashboard',
    icon: 'fa-bar-chart',
    children: [{ name: 'AttendanceDashboard', label: 'Dashboard', icon: 'fa-bar-chart' }],
  },
  {
    key: 'late',
    label: 'Late',
    title: 'Late Permission',
    icon: 'fa-clock-o',
    children: [{ name: 'LatePermission', label: 'Late Permission', icon: 'fa-clock-o' }],
  },
  {
    key: 'reports',
    label: 'Reports',
    title: 'Reports & Mistakes',
    icon: 'fa-list-alt',
    children: [
      { name: 'AttendanceReports', label: 'Reports', icon: 'fa-list-alt' },
      { name: 'StudentMistakes', label: 'Mistakes', icon: 'fa-exclamation-triangle' },
    ],
  },
]

/** The group a route name belongs to, or undefined for anything outside the shell. */
export function groupForRoute(name) {
  return NAV_GROUPS.find((g) => g.children.some((c) => c.name === name))
}

/** Where a bottom-bar tap lands: the first page of the group. */
export function landingRoute(group) {
  return group.children[0].name
}
