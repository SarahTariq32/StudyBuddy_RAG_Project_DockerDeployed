// import { render, screen } from "@testing-library/react";
// import { MemoryRouter } from "react-router-dom";
// import { describe, it, expect, vi } from "vitest";
// import App from "../App";

// vi.mock("../pages/LandingPage", () => ({
//   default: () => <div>Landing Page</div>,
// }));

// vi.mock("../pages/ChatPage", () => ({
//   default: () => <div>Chat Page</div>,
// }));

// vi.mock("../pages/OperationsDashboardPage", () => ({
//   default: () => <div>Operations Dashboard</div>,
// }));

// describe("App Routing", () => {
//   it("renders landing page on /", () => {
//     render(
//       <MemoryRouter initialEntries={["/"]}>
//         <App />
//       </MemoryRouter>
//     );

//     expect(
//       screen.getByText("Landing Page")
//     ).toBeInTheDocument();
//   });

//   it("renders chat page on /chat", () => {
//     render(
//       <MemoryRouter initialEntries={["/chat"]}>
//         <App />
//       </MemoryRouter>
//     );

//     expect(
//       screen.getByText("Chat Page")
//     ).toBeInTheDocument();
//   });

//   it("renders operations dashboard on /ops", () => {
//     render(
//       <MemoryRouter initialEntries={["/ops"]}>
//         <App />
//       </MemoryRouter>
//     );

//     expect(
//       screen.getByText("Operations Dashboard")
//     ).toBeInTheDocument();
//   });

//   it("renders only one page at a time", () => {
//     render(
//       <MemoryRouter initialEntries={["/chat"]}>
//         <App />
//       </MemoryRouter>
//     );

//     expect(screen.queryByText("Landing Page")).toBeNull();
//     expect(screen.getByText("Chat Page")).toBeInTheDocument();
//     expect(screen.queryByText("Operations Dashboard")).toBeNull();
//   });

//   it("renders without crashing", () => {
//     const { container } = render(
//       <MemoryRouter>
//         <App />
//       </MemoryRouter>
//     );

//     expect(container).toBeTruthy();
//   });

//   it("matches root route correctly", () => {
//     render(
//       <MemoryRouter initialEntries={["/"]}>
//         <App />
//       </MemoryRouter>
//     );

//     expect(
//       screen.getAllByText("Landing Page")
//     ).toHaveLength(1);
//   });
// });



import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import App from "../App";

vi.mock("../pages/LandingPage", () => ({
  default: () => <h1>Landing Page</h1>,
}));

vi.mock("../pages/ChatPage", () => ({
  default: () => <h1>Chat Page</h1>,
}));

vi.mock("../pages/OperationsDashboardPage", () => ({
  default: () => <h1>Operations Dashboard</h1>,
}));

describe("App", () => {
  it("renders successfully", () => {
    const { container } = render(<App />);
    expect(container).toBeTruthy();
  });

  it("shows Landing Page by default", () => {
    window.history.pushState({}, "", "/");

    render(<App />);

    expect(
      screen.getByRole("heading", {
        name: "Landing Page",
      })
    ).toBeInTheDocument();
  });

  it("shows Chat Page", () => {
    window.history.pushState({}, "", "/chat");

    render(<App />);

    expect(
      screen.getByRole("heading", {
        name: "Chat Page",
      })
    ).toBeInTheDocument();
  });

  it("shows Operations Dashboard", () => {
    window.history.pushState({}, "", "/ops");

    render(<App />);

    expect(
      screen.getByRole("heading", {
        name: "Operations Dashboard",
      })
    ).toBeInTheDocument();
  });

  it("contains only one router", () => {
    window.history.pushState({}, "", "/");

    const { container } = render(<App />);

    expect(container).toBeTruthy();
  });

  it("renders exactly one page", () => {
    window.history.pushState({}, "", "/chat");

    render(<App />);

    expect(screen.queryByText("Landing Page")).toBeNull();

    expect(
      screen.getByText("Chat Page")
    ).toBeInTheDocument();

    expect(
      screen.queryByText("Operations Dashboard")
    ).toBeNull();
  });
});