import { useReducer, useEffect } from "react";
import {
  FocusStateData,
  FocusAction,
  FOCUS_STATES,
  SessionHistory,
} from "../types";

const initialState: FocusStateData = {
  status: FOCUS_STATES.IDLE,
  activeTaskId: null,
  durationMinutes: 25,
  remainingSeconds: 25 * 60,
  history: [],
};

function focusReducer(
  state: FocusStateData,
  action: FocusAction
): FocusStateData {
  switch (action.type) {
    case "START":
      return {
        ...state,
        status: FOCUS_STATES.RUNNING,
        activeTaskId: action.payload.taskId,
        durationMinutes: action.payload.duration,
        remainingSeconds: action.payload.duration * 60,
      };
    case "PAUSE":
      return { ...state, status: FOCUS_STATES.PAUSED };
    case "RESUME":
      return { ...state, status: FOCUS_STATES.RUNNING };
    case "TICK":
      if (state.status !== FOCUS_STATES.RUNNING) {
        return state;
      }
      if (state.remainingSeconds <= 0) {
        return { ...state, status: FOCUS_STATES.COMPLETED };
      }
      return { ...state, remainingSeconds: state.remainingSeconds - 1 };
    case "ABANDON":
      const abandonedSession: SessionHistory = {
        id: Date.now(),
        date: new Date().toISOString(),
        duration: state.durationMinutes,
        outcome: "abandoned",
      };
      return {
        ...state,
        status: FOCUS_STATES.IDLE,
        activeTaskId: null,
        history: [abandonedSession, ...state.history],
      };
    case "RESET_COMPLETED":
      const completedSession: SessionHistory = {
        id: Date.now(),
        date: new Date().toISOString(),
        duration: state.durationMinutes,
        outcome: "completed",
      };
      return {
        ...state,
        status: FOCUS_STATES.IDLE,
        activeTaskId: null,
        history: [completedSession, ...state.history],
      };
    case "SET_DURATION":
      return { ...state, durationMinutes: action.payload };
    default:
      return state;
  }
}

export const useFocusSession = () => {
  const [state, dispatch] = useReducer(focusReducer, initialState);

  useEffect(() => {
    let interval: NodeJS.Timeout | null = null;
    if (state.status === FOCUS_STATES.RUNNING) {
      interval = setInterval(() => {
        dispatch({ type: "TICK" });
      }, 1000);
    }
    return () => {
      if (interval) {
        clearInterval(interval);
      }
    };
  }, [state.status]);

  return {
    focusState: state.status,
    remainingSeconds: state.remainingSeconds,
    activeTaskId: state.activeTaskId,
    selectedDuration: state.durationMinutes,
    history: state.history,
    actions: {
      start: (taskId: string | null, duration: number) =>
        dispatch({ type: "START", payload: { taskId, duration } }),
      pause: () => dispatch({ type: "PAUSE" }),
      resume: () => dispatch({ type: "RESUME" }),
      abandon: () => dispatch({ type: "ABANDON" }),
      reset: () => dispatch({ type: "RESET_COMPLETED" }),
      setDuration: (mins: number) =>
        dispatch({ type: "SET_DURATION", payload: mins }),
    },
  };
};
