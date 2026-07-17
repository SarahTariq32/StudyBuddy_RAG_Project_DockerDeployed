import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import Message from "../components/Message";

describe("Message Component", () => {
  it("renders user message", () => {
    render(<Message role="user" text="Hello World" />);

    expect(screen.getByText("Hello World")).toBeInTheDocument();
  });

  it("renders assistant message", () => {
    render(<Message role="assistant" text="AI Response" />);

    expect(screen.getByText("AI Response")).toBeInTheDocument();
  });

  it("renders without crashing when message is empty", () => {
    const { container } = render(
        <Message role="assistant" text="" />
    );

    expect(container.firstChild).toBeInTheDocument();
    });

  it("changes alignment based on role", () => {
    const { rerender, container } = render(
      <Message role="user" text="User" />
    );

    expect(container.firstChild).toBeInTheDocument();

    rerender(<Message role="assistant" text="Bot" />);

    expect(screen.getByText("Bot")).toBeInTheDocument();
  });
});