import { createSlice, PayloadAction } from "@reduxjs/toolkit";

type SliceState = { messages: Message[] };

const initialState: SliceState = {
  messages: [],
};

export const chatSlice = createSlice({
  name: "chat",
  initialState,
  reducers: {
    addUserMessage(
      state,
      action: PayloadAction<{ content: string; imageUrls: string[] }>,
    ) {
      const message: Message = {
        sender: "user",
        content: action.payload.content,
        imageUrls: action.payload.imageUrls,
      };
      state.messages.push(message);
    },

    addAssistantMessage(state, action: PayloadAction<string>) {
      const message: Message = {
        sender: "assistant",
        content: action.payload,
        imageUrls: [],
      };
      state.messages.push(message);
    },

    clearMessages(state) {
      state.messages = [];
    },

    removeLastAssistantMessage(state) {
      state.messages.pop();
    },
  },
});

export const {
  addUserMessage,
  addAssistantMessage,
  clearMessages,
  removeLastAssistantMessage,
} = chatSlice.actions;
export default chatSlice.reducer;
