import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import InputBox from "../components/InputBox";

describe("InputBox Component", () => {
  it("renders textarea", () => {
    render(<InputBox onSend={vi.fn()} disabled={false} />);

    expect(
      screen.getByPlaceholderText("Ask something about your PDFs...")
    ).toBeInTheDocument();
  });

  it("sends message when send button is clicked", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<InputBox onSend={onSend} disabled={false} />);

    const textarea = screen.getByPlaceholderText(
      "Ask something about your PDFs..."
    );

    await user.type(textarea, "Hello AI");

    const button = screen.getByRole("button");

    await user.click(button);

    expect(onSend).toHaveBeenCalledWith("Hello AI");
  });

  it("trims whitespace before sending", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<InputBox onSend={onSend} disabled={false} />);

    const textarea = screen.getByPlaceholderText(
      "Ask something about your PDFs..."
    );

    await user.type(textarea, "   Test Question   ");

    await user.click(screen.getByRole("button"));

    expect(onSend).toHaveBeenCalledWith("Test Question");
  });

  it("does not send empty message", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<InputBox onSend={onSend} disabled={false} />);

    const textarea = screen.getByPlaceholderText(
      "Ask something about your PDFs..."
    );

    await user.type(textarea, "     ");

    await user.click(screen.getByRole("button"));

    expect(onSend).not.toHaveBeenCalled();
  });

  it("clears textarea after sending", async () => {
    const user = userEvent.setup();

    render(<InputBox onSend={vi.fn()} disabled={false} />);

    const textarea = screen.getByPlaceholderText(
      "Ask something about your PDFs..."
    );

    await user.type(textarea, "Hello");

    await user.click(screen.getByRole("button"));

    expect(textarea).toHaveValue("");
  });

  it("sends on Enter key", () => {
    const onSend = vi.fn();

    render(<InputBox onSend={onSend} disabled={false} />);

    const textarea = screen.getByPlaceholderText(
      "Ask something about your PDFs..."
    );

    fireEvent.change(textarea, {
      target: { value: "Enter Test" },
    });

    fireEvent.keyDown(textarea, {
      key: "Enter",
      code: "Enter",
      charCode: 13,
    });

    expect(onSend).toHaveBeenCalledWith("Enter Test");
  });

  it("does not send on Shift+Enter", () => {
    const onSend = vi.fn();

    render(<InputBox onSend={onSend} disabled={false} />);

    const textarea = screen.getByPlaceholderText(
      "Ask something about your PDFs..."
    );

    fireEvent.change(textarea, {
      target: { value: "Multi Line" },
    });

    fireEvent.keyDown(textarea, {
      key: "Enter",
      code: "Enter",
      shiftKey: true,
    });

    expect(onSend).not.toHaveBeenCalled();
  });

  it("does not send when disabled", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<InputBox onSend={onSend} disabled={true} />);

    const textarea = screen.getByPlaceholderText(
      "Ask something about your PDFs..."
    );

    await user.type(textarea, "Hello");

    await user.click(screen.getByRole("button"));

    expect(onSend).not.toHaveBeenCalled();
  });

  it("button is disabled when component is disabled", () => {
    render(<InputBox onSend={vi.fn()} disabled={true} />);

    expect(screen.getByRole("button")).toBeDisabled();
  });
});