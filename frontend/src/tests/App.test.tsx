import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import { App } from "../routes/App";

describe("App", () => {
  it("renders the product name", () => {
    render(
      <MemoryRouter>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Study Podcast Generator" })).toBeInTheDocument();
  });

  it("renders the jobs route", () => {
    render(
      <MemoryRouter initialEntries={["/jobs"]}>
        <App />
      </MemoryRouter>,
    );

    expect(screen.getByRole("heading", { name: "Generation Jobs" })).toBeInTheDocument();
  });
});
