import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { App } from "../routes/App";

describe("App", () => {
  it("renders the product name", () => {
    render(<App />);

    expect(screen.getByRole("heading", { name: "Study Podcast Generator" })).toBeInTheDocument();
  });
});
