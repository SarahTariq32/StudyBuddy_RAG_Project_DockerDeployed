// import { render, screen } from "@testing-library/react";
// import { describe, it, expect, vi } from "vitest";
// import ChatPage from "../pages/ChatPage";

// vi.mock("../components/Sidebar", () => ({
//   default: () => <div>Sidebar</div>,
// }));

// vi.mock("../components/ChatWindow", () => ({
//   default: () => <div>Chat Window</div>,
// }));

// describe("ChatPage", () => {
//   it("renders Sidebar", () => {
//     render(<ChatPage />);

//     expect(
//       screen.getByText("Sidebar")
//     ).toBeInTheDocument();
//   });

//   it("renders ChatWindow", () => {
//     render(<ChatPage />);

//     expect(
//       screen.getByText("Chat Window")
//     ).toBeInTheDocument();
//   });

//   it("renders both components together", () => {
//     render(<ChatPage />);

//     expect(
//       screen.getByText("Sidebar")
//     ).toBeInTheDocument();

//     expect(
//       screen.getByText("Chat Window")
//     ).toBeInTheDocument();
//   });

//   it("contains only one Sidebar", () => {
//     render(<ChatPage />);

//     expect(
//       screen.getAllByText("Sidebar")
//     ).toHaveLength(1);
//   });

//   it("contains only one ChatWindow", () => {
//     render(<ChatPage />);

//     expect(
//       screen.getAllByText("Chat Window")
//     ).toHaveLength(1);
//   });

//   it("renders page without crashing", () => {
//     const { container } = render(<ChatPage />);

//     expect(container).toBeTruthy();
//   });
// });


import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import ChatPage from "../pages/ChatPage";

vi.mock("../components/Sidebar", () => ({
  default: (props) => (
    <div>
      Sidebar
      <span>mobile:{String(props.isMobile)}</span>
      <span>open:{String(props.isOpen)}</span>
    </div>
  ),
}));

vi.mock("../components/ChatWindow", () => ({
  default: () => <div>Chat Window</div>,
}));

describe("ChatPage", () => {
  beforeEach(() => {
    window.innerWidth = 1200;
  });

  it("renders Sidebar", () => {
    render(<ChatPage />);

    expect(screen.getByText("Sidebar")).toBeInTheDocument();
  });

  it("renders ChatWindow", () => {
    render(<ChatPage />);

    expect(screen.getByText("Chat Window")).toBeInTheDocument();
  });

  it("desktop starts with sidebar open", () => {
    render(<ChatPage />);

    expect(
      screen.getByText("open:true")
    ).toBeInTheDocument();
  });

  it("desktop is not mobile", () => {
    render(<ChatPage />);

    expect(
      screen.getByText("mobile:false")
    ).toBeInTheDocument();
  });

  it("renders canvas", () => {
    const { container } = render(<ChatPage />);

    expect(
      container.querySelector("canvas")
    ).toBeInTheDocument();
  });

  it("renders successfully", () => {
    const { container } = render(<ChatPage />);

    expect(container).toBeTruthy();
  });
});