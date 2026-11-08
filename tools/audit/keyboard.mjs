// The keyboard check of the browser audit (task 062): a keyboard user needs
// two things axe cannot judge. First, the element that takes the focus has to
// *look* focused (WCAG 2.1, 2.4.7 Focus Visible). Second, the Tab key has to
// be able to leave every place of the page (WCAG 2.1, 2.1.2 No Keyboard
// Trap). This module is the pure part: it takes plain data (the snapshots of
// the tabbable elements, the stops of the walk) and returns failure strings,
// so the logic is tested without a browser. The walk that produces the data
// lives in browser-audit.mjs (real Tab keystrokes through the DevTools
// Input domain).

// How often the walk may press Tab at most, and how many consecutive presses
// on the same element count as a trap.
export const MAX_TAB_PRESSES = 60;
export const TRAP_WINDOW = 5;

// The computed-style families the visible-focus decision compares: a
// difference between the focused and the unfocused snapshot of one element
// counts as a visible focus indicator.
export const FOCUS_PROPERTIES = [
  "outlineStyle",
  "outlineWidth",
  "outlineColor",
  "boxShadow",
  "borderTopColor",
  "borderTopWidth",
  "backgroundColor",
  "color",
  "textDecorationLine",
];

const pixelWidth = (value) => {
  const parsed = Number.parseFloat(value ?? "");
  return Number.isFinite(parsed) ? parsed : 0;
};

/**
 * Whether the focused computed style of one element carries something an
 * unaided eye can see, compared with the unfocused computed style of the
 * same element: any difference in one of the FOCUS_PROPERTIES families, or
 * an outline-style other than none with a width above 0. The comparison is
 * by computed style, not by contrast: the contrast of the focus ring is a
 * matter for axe and the design tokens.
 */
export function hasVisibleFocusIndicator(unfocused, focused) {
  if (!focused) return false;
  if (focused.outlineStyle !== "none" && focused.outlineStyle !== undefined && pixelWidth(focused.outlineWidth) > 0) return true;
  if (!unfocused) return false;
  for (const property of FOCUS_PROPERTIES) {
    if (unfocused[property] !== focused[property]) return true;
  }
  return false;
}

/**
 * The keyboard-check failures of one audited state. The plain data:
 * - `tabbable`: the tabbable elements of the state, in the order of the page,
 *   as `{ label, unfocused }` (`label` is the data-testid, or the tag plus
 *   the accessible name; `unfocused` is the computed-style snapshot taken
 *   before the walk). An entry may carry `visible: false`; only tabbable
 *   elements that are visible have to be reached (anything inside a closed
 *   dialog or with `inert` must be left out when the list is collected).
 * - `stops`: one entry per Tab press that focused an element of the page,
 *   `{ label, index, visible, focused }`; `index` is the position of the
 *   focused element in `tabbable` (null when the element is not one of
 *   them, the browser chrome for example), `focused` the computed-style
 *   snapshot taken while the element is focused.
 * - `presses`: how many Tab presses the walk made in total.
 * - `leftContent`: whether the walk ended because the focus left the page
 *   content (the browser chrome, or document.body again).
 * Returns one failure string per problem, in the voice of the other checks.
 */
export function keyboardFailures({
  tabbable = [],
  stops = [],
  presses = 0,
  leftContent = false,
  maxPresses = MAX_TAB_PRESSES,
  trapWindow = TRAP_WINDOW,
} = {}) {
  const failures = [];

  // Visible focus (WCAG 2.4.7): the first stop of each tabbable element decides.
  const seen = new Set();
  for (const stop of stops) {
    if (typeof stop.index !== "number" || seen.has(stop.index)) continue;
    seen.add(stop.index);
    if (!hasVisibleFocusIndicator(tabbable[stop.index]?.unfocused, stop.focused)) {
      failures.push(`no visible focus indicator on ${stop.label}`);
    }
  }

  // Keyboard trap (WCAG 2.1.2), shape one: trapWindow consecutive presses on
  // the same element while it is not the last tabbable one.
  const keyOf = (stop) => (typeof stop.index === "number" ? stop.index : stop.label);
  for (let i = 0; i + trapWindow <= stops.length; i++) {
    const key = keyOf(stops[i]);
    if (stops.slice(i + 1, i + trapWindow).every((stop) => keyOf(stop) === key) && key !== tabbable.length - 1) {
      failures.push(`keyboard trap: the focus stayed on ${stops[i].label} for ${trapWindow} consecutive Tab presses`);
      break;
    }
  }

  // Keyboard trap, shape two: the walk ran out of presses without the focus
  // ever leaving the content, although the page has fewer tabbable elements.
  if (!leftContent && presses >= maxPresses && tabbable.length < maxPresses) {
    failures.push(`keyboard trap: ${presses} Tab presses never left the content of a page with ${tabbable.length} tabbable element(s)`);
  }

  // The walk against the list: a visible tabbable element the walk never
  // focused is out of the Tab order (or behind something that eats the key).
  const visited = new Set(stops.map((stop) => stop.index).filter((index) => typeof index === "number"));
  for (const [i, entry] of tabbable.entries()) {
    if (entry.visible === false) continue;
    if (!visited.has(i)) failures.push(`the tabbable element ${entry.label} was never reached by the walk`);
  }

  return failures;
}
