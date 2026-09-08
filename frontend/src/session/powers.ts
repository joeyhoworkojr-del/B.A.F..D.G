import type { AccountEntitlements, StaffPower } from '../types'

/**
 * Whether the signed-in account holds a staff power.
 *
 * The server checks this again on every request it matters for — a hidden link
 * is a convenience for staff, never a control. Using the power rather than the
 * level string means adding a role does not mean hunting for `=== 'admin'`
 * comparisons scattered through the UI.
 */
export function can(ent: AccountEntitlements | null | undefined, power: StaffPower): boolean {
  return !!ent?.powers?.includes(power)
}

/** True for anyone with any staff role at all. */
export function isStaff(ent: AccountEntitlements | null | undefined): boolean {
  return (ent?.powers?.length ?? 0) > 0
}
