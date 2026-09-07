import '@testing-library/jest-dom/vitest'

// jsdom has no layout engine, so scrollIntoView is undefined; components call
// it for the "Why this edge?" jump.
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = () => {}
}
