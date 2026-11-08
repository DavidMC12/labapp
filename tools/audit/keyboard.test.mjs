// Tests of the keyboard check (task 062) on its pure part, without a browser.
import assert from "node:assert/strict";
import { test } from "node:test";
import { FOCUS_PROPERTIES, MAX_TAB_PRESSES, TRAP_WINDOW, hasVisibleFocusIndicator, keyboardFailures } from "./keyboard.mjs";

const styled = (over = {}) => ({
  outlineStyle: "none",
  outlineWidth: "0px",
  outlineColor: "rgb(24, 36, 31)",
  boxShadow: "none",
  borderTopColor: "rgb(217, 212, 197)",
  borderTopWidth: "1px",
  backgroundColor: "rgba(0, 0, 0, 0)",
  color: "rgb(24, 36, 31)",
  textDecorationLine: "none",
  ...over,
});

// The examples of the audit page: the global visible focus style of
// globals.css is an outline of 3px in the focus token.
const rest = styled();
const focused = styled({ outlineStyle: "solid", outlineWidth: "3px", outlineColor: "rgb(31, 138, 108)" });

const state = ({ tabbable = [], stops = [], presses = 0, leftContent = false } = {}) => ({ tabbable, stops, presses, leftContent });
const tabbable = (over = {}, label = "app-shell-link") => [{ label, visible: true, unfocused: rest, ...over }];
const stop = (over = {}, label = "app-shell-link") => ({
  label,
  index: 0,
  visible: true,
  insideDocument: true,
  focused: focused,
  ...over,
});

test("a difference in any computed-style family counts as a visible focus indicator", () => {
  assert.equal(FOCUS_PROPERTIES.length, 9);
  // The whole property of the walk: focused against the same element unfocused.
  assert.equal(hasVisibleFocusIndicator(rest, focused), true);
});

test("each of the nine families alone decides visible, so one removed rule is caught", () => {
  const families = {
    outlineStyle: { outlineStyle: "solid" },
    outlineWidth: { outlineWidth: "3px" },
    outlineColor: { outlineColor: "rgb(31, 138, 108)" },
    boxShadow: { boxShadow: "rgb(122, 217, 188) 0px 0px 0px 3px" },
    borderTopColor: { borderTopColor: "rgb(31, 138, 108)" },
    borderTopWidth: { borderTopWidth: "3px" },
    backgroundColor: { backgroundColor: "rgb(15, 91, 70)" },
    color: { color: "rgb(15, 91, 70)" },
    textDecorationLine: { textDecorationLine: "underline" },
  };
  assert.deepEqual(Object.keys(families), FOCUS_PROPERTIES);
  for (const [property, over] of Object.entries(families)) {
    assert.equal(hasVisibleFocusIndicator(rest, styled(over)), true, property);
    assert.equal(hasVisibleFocusIndicator(rest, rest), false, property);
    assert.equal(hasVisibleFocusIndicator(undefined, rest), false, property);
  }
});

test("an outline that is there without any of the counted difference", () => {
  // Both snapshots already carry the same solid outline (an odd but possible
  // measurement): the ring of a width above 0 counts by itself.
  const ringed = styled({ outlineStyle: "solid", outlineWidth: "2px", outlineColor: "rgb(31, 138, 108)" });
  assert.equal(hasVisibleFocusIndicator(ringed, ringed), true);
  // A width of 0 shows nothing, on its own or with something like the same.
  const flat = styled({ outlineStyle: "solid", outlineWidth: "0px", outlineColor: "rgb(31, 138, 108)" });
  assert.equal(hasVisibleFocusIndicator(flat, flat), false);
});

test("a clean walk of a state answers no failure", () => {
  assert.deepEqual(
    keyboardFailures(
      state({
        tabbable: [
          { label: "app-shell-home-link", visible: true, unfocused: rest },
          { label: "app-shell-customers-link", visible: true, unfocused: rest },
        ],
        stops: [stop({}, "app-shell-home-link"), { ...stop({}, "app-shell-customers-link"), index: 1 }],
        presses: 3,
        leftContent: true,
      }),
    ),
    [],
  );
});

test("a state without a visible focus indicator fails on the right element", () => {
  assert.deepEqual(
    keyboardFailures(
      state({
        tabbable: tabbable({ unfocused: styled({ outlineStyle: "none", outlineWidth: "0px", outlineColor: "rgba(0, 0, 0, 0)" }) }, "auth-login-submit-button"),
        stops: [stop({ focused: styled({ outlineStyle: "none", outlineWidth: "0px", outlineColor: "rgba(0, 0, 0, 0)" }) }, "auth-login-submit-button")],
        presses: 2,
        leftContent: true,
      }),
    ),
    ["no visible focus indicator on auth-login-submit-button"],
  );
});

test("the second stop of the same element is not judged twice", () => {
  const tabbable3 = [
    { label: "one", visible: true, unfocused: rest },
    { label: "two", visible: true, unfocused: styled({ outlineColor: "rgba(0, 0, 0, 0)" }) },
  ];
  const stops = [
    stop({ index: 0, label: "one", focused: focused }),
    stop({ index: 1, label: "two", focused: styled({ outlineStyle: "none", outlineWidth: "0px", outlineColor: "rgba(0, 0, 0, 0)" }) }),
    stop({ index: 0, label: "one", focused: focused }),
  ];
  assert.deepEqual(keyboardFailures(state({ tabbable: tabbable3, stops, presses: 4, leftContent: true })), [
    "no visible focus indicator on two",
  ]);
});

test(`${TRAP_WINDOW} consecutive presses on an element of the middle fail as a keyboard trap`, () => {
  const stops = [stop({ index: 0, label: "one" })];
  for (let i = 0; i < TRAP_WINDOW; i++) stops.push(stop({ index: 1, label: "two" }));
  assert.deepEqual(keyboardFailures(state({ tabbable: tabbable(), stops, presses: 6, leftContent: false })), [
    "keyboard trap: the focus stayed on two for 5 consecutive Tab presses",
  ]);
});

test("the last tabbable element is allowed to take the presses (the walk is cut elsewhere)", () => {
  const stops = [stop({ index: 0, label: "one" })];
  for (let i = 0; i < TRAP_WINDOW; i++) stops.push(stop({ index: 1, label: "two" }));
  const withTwo = [
    { label: "one", visible: true, unfocused: rest },
    { label: "two", visible: true, unfocused: rest },
  ];
  assert.deepEqual(keyboardFailures(state({ tabbable: withTwo, stops, presses: 6, leftContent: false })), []);
});

test(`keyboard trap, second shape: ${MAX_TAB_PRESSES} presses that never leave the content`, () => {
  const stops = Array.from({ length: MAX_TAB_PRESSES }, (_, i) => stop({ index: i % 2, label: i % 2 ? "two" : "one" }));
  const even = [
    { label: "one", visible: true, unfocused: rest },
    { label: "two", visible: true, unfocused: rest },
  ];
  assert.deepEqual(
    keyboardFailures(state({ tabbable: even, stops, presses: MAX_TAB_PRESSES, leftContent: false })).filter((f) => f.includes("keyboard trap")),
    ["keyboard trap: 60 Tab presses never left the content of a page with 2 tabbable element(s)"],
  );
});

test("a walk that ended through the content answers no trap of the second shape", () => {
  assert.deepEqual(
    keyboardFailures(state({ tabbable: tabbable(), stops: [stop()], presses: 2, leftContent: true })),
    [],
  );
  // And neither does a walk cut for reaching the maximum with at least as many tabbable elements.
  assert.deepEqual(
    keyboardFailures(state({ tabbable: Array.from({ length: MAX_TAB_PRESSES }, () => ({ visible: true, unfocused: rest })), presses: MAX_TAB_PRESSES, leftContent: false })),
    Array.from({ length: MAX_TAB_PRESSES }, (_, i) => `the tabbable element undefined was never reached by the walk`),
  );
});

test("a visible tabbable element the walk never reached fails", () => {
  const list = [
    { label: "one", visible: true, unfocused: rest },
    { label: "two", visible: true, unfocused: rest },
    { label: "three", visible: true, unfocused: rest },
  ];
  const stops = [stop({ index: 0, label: "one" }), stop({ index: 2, label: "three" })];
  assert.deepEqual(
    keyboardFailures(state({ tabbable: list, stops, presses: 4, leftContent: true })),
    ["the tabbable element two was never reached by the walk"],
  );
});

test("a tabbable element that is not visible (a closed dialog, inert, hidden) has not to be reached", () => {
  const list = [
    { label: "one", visible: true, unfocused: rest },
    { label: "in-a-closed-dialog", visible: false, unfocused: rest },
  ];
  assert.deepEqual(keyboardFailures(state({ tabbable: list, stops: [stop()], presses: 2, leftContent: true })), []);
});

test("an element the list does not know (the chrome of the browser) only serves the stop conditions", () => {
  assert.deepEqual(
    keyboardFailures(state({ tabbable: tabbable(), stops: [stop(), { ...stop(), index: null, label: "nextjs-portal" }], presses: 3, leftContent: true })),
    [],
  );
});
