import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import PDFList from "../components/PDFList";

vi.mock("../components/PDFItem", () => ({
  default: ({ doc }) => (
    <div>{doc.filename}</div>
  ),
}));

describe("PDFList", () => {
  it("renders nothing while loading", () => {
    const { container } = render(
      <PDFList
        docs={[]}
        isLoading={true}
        onDocumentsChanged={vi.fn()}
      />
    );

    expect(container.firstChild).toBeNull();
  });

  it("shows empty message", () => {
    render(
      <PDFList
        docs={[]}
        isLoading={false}
        onDocumentsChanged={vi.fn()}
      />
    );

    expect(
      screen.getByText("No PDFs uploaded yet.")
    ).toBeInTheDocument();
  });

  it("renders one document", () => {
    render(
      <PDFList
        docs={[
          {
            id: 1,
            filename: "AI.pdf",
          },
        ]}
        isLoading={false}
        onDocumentsChanged={vi.fn()}
      />
    );

    expect(
      screen.getByText("AI.pdf")
    ).toBeInTheDocument();
  });

  it("renders multiple documents", () => {
    render(
      <PDFList
        docs={[
          {
            id: 1,
            filename: "AI.pdf",
          },
          {
            id: 2,
            filename: "ML.pdf",
          },
        ]}
        isLoading={false}
        onDocumentsChanged={vi.fn()}
      />
    );

    expect(
      screen.getByText("AI.pdf")
    ).toBeInTheDocument();

    expect(
      screen.getByText("ML.pdf")
    ).toBeInTheDocument();
  });

  it("renders correct number of PDF items", () => {
    render(
      <PDFList
        docs={[
          {
            id: 1,
            filename: "One.pdf",
          },
          {
            id: 2,
            filename: "Two.pdf",
          },
          {
            id: 3,
            filename: "Three.pdf",
          },
        ]}
        isLoading={false}
        onDocumentsChanged={vi.fn()}
      />
    );

    expect(
      screen.getAllByText(/\.pdf$/i)
    ).toHaveLength(3);
  });

  it("passes without crashing", () => {
    const { container } = render(
      <PDFList
        docs={[]}
        isLoading={false}
        onDocumentsChanged={vi.fn()}
      />
    );

    expect(container).toBeTruthy();
  });
});