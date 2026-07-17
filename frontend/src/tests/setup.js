import "@testing-library/jest-dom";
// Canvas mock for ChatPage tests
Object.defineProperty(HTMLCanvasElement.prototype, "getContext", {
  value: () => ({
    fillStyle: "",
    fillRect: vi.fn(),
    clearRect: vi.fn(),
    beginPath: vi.fn(),
    arc: vi.fn(),
    fill: vi.fn(),
    stroke: vi.fn(),
    moveTo: vi.fn(),
    lineTo: vi.fn(),
    closePath: vi.fn(),
    createRadialGradient: () => ({
      addColorStop: vi.fn(),
    }),
  }),
});

global.requestAnimationFrame = (cb) => setTimeout(cb, 0);
global.cancelAnimationFrame = (id) => clearTimeout(id);