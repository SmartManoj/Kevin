import { createSlice } from "@reduxjs/toolkit";

export type Cell = {
  content: string;
  type: "input" | "output";
};

const initialCells: Cell[] = [];

export const cellSlice = createSlice({
  name: "cell",
  initialState: {
    cells: initialCells,
  },
  reducers: {
    appendJupyterInput: (state, action) => {
      state.cells.push({ content: action.payload, type: "input" });
    },
    appendJupyterOutput: (state, action) => {
      state.cells.push({ content: action.payload, type: "output" });
    },
    handleInputSubmission: (state, action) => {
      state.cells.push({ content: action.payload, type: "input" });
    },
    clearJupyter: (state) => {
      state.cells = [];
    },
  },
});

export const {
  appendJupyterInput,
  appendJupyterOutput,
  handleInputSubmission,
  clearJupyter,
} = cellSlice.actions;

export default cellSlice.reducer;
